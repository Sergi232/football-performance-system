"""FEATURE-02: build leakage-safe temporal features from FEATURE-01.

For every base feature, all temporal baselines are computed using only matches
with match_date strictly earlier than the current match. Matches with the same
match_date never inform one another.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
BASE_CATALOG = Path(__file__).with_name("catalog.json")
TEMPORAL_CATALOG = Path(__file__).with_name("temporal_catalog.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FEATURE-02 temporal features")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def base_feature_names() -> list[str]:
    catalog = load_json(BASE_CATALOG)
    return [f["name"] for f in catalog["ratio_features"] + catalog["per90_features"]]


def ols_slope(values: list[float]) -> float | None:
    n = len(values)
    if n < 2:
        return None
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return None
    return numerator / denominator


def prior_stats(history: list[float]) -> dict[str, float | None]:
    n = len(history)
    if n == 0:
        return {
            "history_n": 0.0,
            "prev": None,
            "prior_mean": None,
            "prior_std": None,
            "prior_slope": None,
        }
    mean = sum(history) / n
    std = None
    if n >= 2:
        variance = sum((v - mean) ** 2 for v in history) / n
        std = math.sqrt(variance)
    return {
        "history_n": float(n),
        "prev": history[-1],
        "prior_mean": mean,
        "prior_std": std,
        "prior_slope": ols_slope(history),
    }


def compute_temporal_frame(base: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    required = {"match_id", "player_id", "feature_name", "feature_value", "match_date"}
    missing = required - set(base.columns)
    if missing:
        raise ValueError(f"Missing columns for temporal build: {sorted(missing)}")
    if base["match_date"].isna().any():
        raise ValueError("FEATURE-02 requires non-null match_date for every base feature row")

    rows: list[dict] = []
    base = base[base["feature_name"].isin(feature_names)].copy()
    base = base.sort_values(["player_id", "feature_name", "match_date", "match_id"])

    for (player_id, feature_name), group in base.groupby(
        ["player_id", "feature_name"], sort=False
    ):
        history: list[float] = []
        for match_date, same_date in group.groupby("match_date", sort=True):
            stats = prior_stats(history)
            same_date = same_date.sort_values("match_id")

            for row in same_date.itertuples(index=False):
                current = None if pd.isna(row.feature_value) else float(row.feature_value)
                values = {
                    "history_n": stats["history_n"],
                    "prev": stats["prev"],
                    "prior_mean": stats["prior_mean"],
                    "prior_std": stats["prior_std"],
                    "delta_prev": None,
                    "delta_prior_mean": None,
                    "prior_slope": stats["prior_slope"],
                }
                if current is not None and stats["prev"] is not None:
                    values["delta_prev"] = current - float(stats["prev"])
                if current is not None and stats["prior_mean"] is not None:
                    values["delta_prior_mean"] = current - float(stats["prior_mean"])

                for operator, value in values.items():
                    rows.append(
                        {
                            "match_id": row.match_id,
                            "player_id": player_id,
                            "feature_name": f"{feature_name}__{operator}",
                            "feature_value": value,
                        }
                    )

            # Same-date rows enter history only after every row on that date has
            # been calculated, so they cannot leak into one another.
            for row in same_date.itertuples(index=False):
                if not pd.isna(row.feature_value):
                    history.append(float(row.feature_value))

    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    base_catalog = load_json(BASE_CATALOG)
    temporal_catalog = load_json(TEMPORAL_CATALOG)
    base_version = temporal_catalog["base_feature_version"]
    version = temporal_catalog["feature_version"]
    names = base_feature_names()
    operators = [o["name"] for o in temporal_catalog["operators"]]

    if base_catalog["feature_version"] != base_version:
        raise RuntimeError("Base catalog version does not match temporal contract")
    if len(names) != len(set(names)):
        raise RuntimeError("Duplicate base feature names")

    with duckdb.connect(str(db_path)) as con:
        base = con.execute(
            """
            SELECT f.match_id, f.player_id, f.feature_name, f.feature_value, m.match_date
            FROM player_match_features f
            JOIN matches m ON m.match_id = f.match_id
            WHERE f.feature_version = ?
            ORDER BY f.player_id, f.feature_name, m.match_date, f.match_id
            """,
            [base_version],
        ).fetchdf()

        expected_base_rows = con.execute(
            "SELECT COUNT(*) FROM player_match WHERE 1=1"
        ).fetchone()[0] * len(names)
        if len(base) != expected_base_rows:
            raise RuntimeError(
                f"Expected {expected_base_rows} FEATURE-01 rows, found {len(base)}. "
                "Run features/run_stage1.py first."
            )

        temporal = compute_temporal_frame(base, names)
        expected_temporal_rows = len(base) * len(operators)
        if len(temporal) != expected_temporal_rows:
            raise RuntimeError(
                f"Expected {expected_temporal_rows} temporal rows, built {len(temporal)}"
            )

        temporal["feature_text"] = None
        temporal["feature_version"] = version

        con.execute("DELETE FROM player_match_features WHERE feature_version = ?", [version])
        con.register("temporal_df", temporal)
        con.execute(
            """
            INSERT INTO player_match_features (
                match_id, player_id, feature_name, feature_value,
                feature_text, feature_version
            )
            SELECT match_id, player_id, feature_name, feature_value,
                   feature_text, feature_version
            FROM temporal_df
            """
        )
        con.unregister("temporal_df")

        written = con.execute(
            "SELECT COUNT(*) FROM player_match_features WHERE feature_version = ?",
            [version],
        ).fetchone()[0]
        non_null = con.execute(
            """
            SELECT COUNT(*) FROM player_match_features
            WHERE feature_version = ? AND feature_value IS NOT NULL
            """,
            [version],
        ).fetchone()[0]
        matches = con.execute(
            "SELECT COUNT(DISTINCT match_id) FROM player_match_features WHERE feature_version = ?",
            [version],
        ).fetchone()[0]
        players = con.execute(
            "SELECT COUNT(DISTINCT player_id) FROM player_match_features WHERE feature_version = ?",
            [version],
        ).fetchone()[0]

    print("FEATURE-02 temporal build complete")
    print(f"feature_version: {version}")
    print(f"base feature definitions: {len(names)}")
    print(f"temporal operators: {len(operators)}")
    print(f"feature rows written: {written}")
    print(f"non-null feature values: {non_null}")
    print(f"coverage: {matches} matches / {players} players")
    print("Strict-past contract: same-date and future matches never inform the current row.")
    print("No arbitrary recent-match windows, ratings, weights or expert thresholds were created.")


if __name__ == "__main__":
    main()
