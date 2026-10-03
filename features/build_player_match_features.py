"""FEATURE-01: build deterministic player-match features.

This stage deliberately contains no ratings, labels, weights, percentiles or
expert thresholds. It only turns approved raw player-match inputs into
mathematically explicit ratios and per-90 normalizations.

Missing raw values remain NULL. Zero-minute rows never receive per-90 values.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
CATALOG_PATH = Path(__file__).with_name("catalog.json")
RAW_SOURCE_TYPE = "opta_player_stats"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FEATURE-01 player-match features")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--raw-source-type",
        default=RAW_SOURCE_TYPE,
        help=(
            "player_match_raw_stats.source_type to consume. "
            f"Default remains {RAW_SOURCE_TYPE!r}; reproducible synthetic demos may pass an explicit source."
        ),
    )
    return parser.parse_args()


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def sql_identifier(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe SQL identifier: {name}")
    return f'"{name}"'


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    raw_source_type = str(args.raw_source_type).strip()
    if not raw_source_type:
        raise ValueError("--raw-source-type must not be empty")
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    catalog = load_catalog()
    version = catalog["feature_version"]
    ratios = catalog["ratio_features"]
    per90 = catalog["per90_features"]
    expected_feature_names = [f["name"] for f in ratios + per90]

    if len(expected_feature_names) != len(set(expected_feature_names)):
        raise RuntimeError("Duplicate feature names in features/catalog.json")

    required_raw = {
        f["numerator"] for f in ratios
    } | {
        f["denominator"] for f in ratios
    } | {
        f["source"] for f in per90
    }

    with duckdb.connect(str(db_path)) as con:
        table_names = {
            r[0]
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
        }
        required_tables = {"player_match", "player_match_raw_stats", "player_match_features"}
        missing_tables = required_tables - table_names
        if missing_tables:
            raise RuntimeError(f"Missing required tables: {sorted(missing_tables)}")

        raw_columns = {
            r[1] for r in con.execute("PRAGMA table_info('player_match_raw_stats')").fetchall()
        }
        missing_raw = sorted(required_raw - raw_columns)
        if missing_raw:
            raise RuntimeError(f"Missing required raw columns: {missing_raw}")

        duplicate_raw = con.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT match_id, player_id, COUNT(*) AS n
                FROM player_match_raw_stats
                WHERE source_type = ?
                GROUP BY match_id, player_id
                HAVING COUNT(*) > 1
            )
            """,
            [raw_source_type],
        ).fetchone()[0]
        if duplicate_raw:
            raise RuntimeError(
                f"Found {duplicate_raw} duplicate raw player-match rows for {raw_source_type}"
            )

        con.execute(
            "DELETE FROM player_match_features WHERE feature_version = ?",
            [version],
        )

        base_join = """
            FROM player_match pm
            LEFT JOIN player_match_raw_stats r
              ON r.match_id = pm.match_id
             AND r.player_id = pm.player_id
             AND r.source_type = ?
        """

        for feature in ratios:
            numerator = sql_identifier(feature["numerator"])
            denominator = sql_identifier(feature["denominator"])
            con.execute(
                f"""
                INSERT INTO player_match_features (
                    match_id, player_id, feature_name, feature_value,
                    feature_text, feature_version
                )
                SELECT
                    pm.match_id,
                    pm.player_id,
                    ?,
                    CASE
                        WHEN r.{numerator} IS NULL OR r.{denominator} IS NULL THEN NULL
                        WHEN r.{denominator} <= 0 THEN NULL
                        ELSE CAST(r.{numerator} AS DOUBLE) / CAST(r.{denominator} AS DOUBLE)
                    END,
                    NULL,
                    ?
                {base_join}
                """,
                [feature["name"], version, raw_source_type],
            )

        for feature in per90:
            source = sql_identifier(feature["source"])
            con.execute(
                f"""
                INSERT INTO player_match_features (
                    match_id, player_id, feature_name, feature_value,
                    feature_text, feature_version
                )
                SELECT
                    pm.match_id,
                    pm.player_id,
                    ?,
                    CASE
                        WHEN pm.minutes_played IS NULL OR pm.minutes_played <= 0 THEN NULL
                        WHEN r.{source} IS NULL THEN NULL
                        ELSE CAST(r.{source} AS DOUBLE) * 90.0 / pm.minutes_played
                    END,
                    NULL,
                    ?
                {base_join}
                """,
                [feature["name"], version, raw_source_type],
            )

        player_match_rows = con.execute("SELECT COUNT(*) FROM player_match").fetchone()[0]
        feature_rows = con.execute(
            "SELECT COUNT(*) FROM player_match_features WHERE feature_version = ?",
            [version],
        ).fetchone()[0]
        non_null_rows = con.execute(
            """
            SELECT COUNT(*) FROM player_match_features
            WHERE feature_version = ? AND feature_value IS NOT NULL
            """,
            [version],
        ).fetchone()[0]
        distinct_matches = con.execute(
            """
            SELECT COUNT(DISTINCT match_id) FROM player_match_features
            WHERE feature_version = ?
            """,
            [version],
        ).fetchone()[0]
        distinct_players = con.execute(
            """
            SELECT COUNT(DISTINCT player_id) FROM player_match_features
            WHERE feature_version = ?
            """,
            [version],
        ).fetchone()[0]

    print("FEATURE-01 deterministic build complete")
    print(f"feature_version: {version}")
    print(f"raw_source_type: {raw_source_type}")
    print(f"feature definitions: {len(expected_feature_names)}")
    print(f"player_match rows: {player_match_rows}")
    print(f"feature rows written: {feature_rows}")
    print(f"non-null feature values: {non_null_rows}")
    print(f"coverage: {distinct_matches} matches / {distinct_players} players")
    print("No ratings, percentiles, weights or expert thresholds were created.")


if __name__ == "__main__":
    main()
