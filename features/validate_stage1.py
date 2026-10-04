"""Validate FEATURE-01 deterministic player-match features."""
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
    parser = argparse.ArgumentParser(description="Validate FEATURE-01")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--raw-source-type", default=RAW_SOURCE_TYPE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    raw_source_type = str(args.raw_source_type).strip()
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    version = catalog["feature_version"]
    ratios = catalog["ratio_features"]
    per90 = catalog["per90_features"]
    feature_names = [f["name"] for f in ratios + per90]

    with duckdb.connect(str(db_path)) as con:
        pm_rows = con.execute("SELECT COUNT(*) FROM player_match").fetchone()[0]
        expected_rows = pm_rows * len(feature_names)
        actual_rows = con.execute(
            "SELECT COUNT(*) FROM player_match_features WHERE feature_version = ?",
            [version],
        ).fetchone()[0]
        if actual_rows != expected_rows:
            raise RuntimeError(
                f"Feature row count mismatch: actual={actual_rows}, expected={expected_rows}"
            )

        distinct_names = {
            r[0]
            for r in con.execute(
                "SELECT DISTINCT feature_name FROM player_match_features WHERE feature_version = ?",
                [version],
            ).fetchall()
        }
        if distinct_names != set(feature_names):
            raise RuntimeError(
                f"Feature name mismatch: missing={sorted(set(feature_names)-distinct_names)}, "
                f"extra={sorted(distinct_names-set(feature_names))}"
            )

        duplicates = con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT match_id, player_id, feature_name, feature_version, COUNT(*) n
                FROM player_match_features
                WHERE feature_version = ?
                GROUP BY ALL
                HAVING COUNT(*) > 1
            )
            """,
            [version],
        ).fetchone()[0]
        if duplicates:
            raise RuntimeError(f"Duplicate feature keys: {duplicates}")

        ratio_names = [f["name"] for f in ratios]
        placeholders = ",".join("?" for _ in ratio_names)
        ratio_out_of_range = con.execute(
            f"""
            SELECT COUNT(*)
            FROM player_match_features
            WHERE feature_version = ?
              AND feature_name IN ({placeholders})
              AND feature_value IS NOT NULL
              AND (feature_value < -1e-12 OR feature_value > 1.000000000001)
            """,
            [version, *ratio_names],
        ).fetchone()[0]
        if ratio_out_of_range:
            raise RuntimeError(f"Ratio features outside [0,1]: {ratio_out_of_range}")

        per90_names = [f["name"] for f in per90]
        placeholders = ",".join("?" for _ in per90_names)
        negative_per90 = con.execute(
            f"""
            SELECT COUNT(*)
            FROM player_match_features
            WHERE feature_version = ?
              AND feature_name IN ({placeholders})
              AND feature_value < 0
            """,
            [version, *per90_names],
        ).fetchone()[0]
        if negative_per90:
            raise RuntimeError(f"Negative per-90 features: {negative_per90}")

        zero_minute_per90 = con.execute(
            f"""
            SELECT COUNT(*)
            FROM player_match_features f
            JOIN player_match pm
              ON pm.match_id=f.match_id AND pm.player_id=f.player_id
            WHERE f.feature_version = ?
              AND f.feature_name IN ({placeholders})
              AND COALESCE(pm.minutes_played, 0) <= 0
              AND f.feature_value IS NOT NULL
            """,
            [version, *per90_names],
        ).fetchone()[0]
        if zero_minute_per90:
            raise RuntimeError(
                f"Per-90 values found on zero-minute rows: {zero_minute_per90}"
            )

        semantic_errors = 0
        for feature in ratios:
            num = feature["numerator"]
            den = feature["denominator"]
            semantic_errors += con.execute(
                f"""
                SELECT COUNT(*)
                FROM player_match_features f
                JOIN player_match pm
                  ON pm.match_id=f.match_id AND pm.player_id=f.player_id
                LEFT JOIN player_match_raw_stats r
                  ON r.match_id=pm.match_id
                 AND r.player_id=pm.player_id
                 AND r.source_type=?
                WHERE f.feature_version=? AND f.feature_name=?
                  AND (
                    ((r.{num} IS NULL OR r.{den} IS NULL OR r.{den} <= 0)
                      AND f.feature_value IS NOT NULL)
                    OR
                    ((r.{num} IS NOT NULL AND r.{den} IS NOT NULL AND r.{den} > 0)
                      AND f.feature_value IS NULL)
                  )
                """,
                [raw_source_type, version, feature["name"]],
            ).fetchone()[0]

        for feature in per90:
            src = feature["source"]
            semantic_errors += con.execute(
                f"""
                SELECT COUNT(*)
                FROM player_match_features f
                JOIN player_match pm
                  ON pm.match_id=f.match_id AND pm.player_id=f.player_id
                LEFT JOIN player_match_raw_stats r
                  ON r.match_id=pm.match_id
                 AND r.player_id=pm.player_id
                 AND r.source_type=?
                WHERE f.feature_version=? AND f.feature_name=?
                  AND (
                    ((pm.minutes_played IS NULL OR pm.minutes_played <= 0 OR r.{src} IS NULL)
                      AND f.feature_value IS NOT NULL)
                    OR
                    ((pm.minutes_played > 0 AND r.{src} IS NOT NULL)
                      AND f.feature_value IS NULL)
                  )
                """,
                [raw_source_type, version, feature["name"]],
            ).fetchone()[0]

        if semantic_errors:
            raise RuntimeError(f"NULL/provenance semantic mismatches: {semantic_errors}")

        match_count = con.execute(
            "SELECT COUNT(DISTINCT match_id) FROM player_match_features WHERE feature_version=?",
            [version],
        ).fetchone()[0]
        player_count = con.execute(
            "SELECT COUNT(DISTINCT player_id) FROM player_match_features WHERE feature_version=?",
            [version],
        ).fetchone()[0]
        non_null = con.execute(
            "SELECT COUNT(*) FROM player_match_features WHERE feature_version=? AND feature_value IS NOT NULL",
            [version],
        ).fetchone()[0]

    print("FEATURE-01 VALIDATION: PASS")
    print(f"feature_version: {version}")
    print(f"feature definitions: {len(feature_names)}")
    print(f"feature rows: {actual_rows}/{expected_rows}")
    print(f"non-null values: {non_null}")
    print(f"coverage: {match_count} matches / {player_count} players")
    print("ratio domains [0,1]: PASS")
    print("per-90 non-negative + zero-minute NULL contract: PASS")
    print("raw NULL preservation contract: PASS")
    print("No ratings/weights/percentiles/expert thresholds validated or created.")


if __name__ == "__main__":
    main()
