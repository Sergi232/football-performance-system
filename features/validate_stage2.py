from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
BASE_CATALOG = Path(__file__).with_name("catalog.json")
TEMPORAL_CATALOG = Path(__file__).with_name("temporal_catalog.json")


def parse_args():
    p = argparse.ArgumentParser(description="Validate FEATURE-02 temporal features")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    return p.parse_args()


def main():
    args = parse_args()
    db = args.db.expanduser().resolve()
    base_catalog = json.loads(BASE_CATALOG.read_text(encoding="utf-8"))
    temporal_catalog = json.loads(TEMPORAL_CATALOG.read_text(encoding="utf-8"))
    base_names = [f["name"] for f in base_catalog["ratio_features"] + base_catalog["per90_features"]]
    ops = [o["name"] for o in temporal_catalog["operators"]]
    version = temporal_catalog["feature_version"]

    with duckdb.connect(str(db)) as con:
        pm_rows = con.execute("SELECT COUNT(*) FROM player_match").fetchone()[0]
        expected = pm_rows * len(base_names) * len(ops)
        actual = con.execute(
            "SELECT COUNT(*) FROM player_match_features WHERE feature_version=?",
            [version],
        ).fetchone()[0]
        if actual != expected:
            raise RuntimeError(f"FEATURE-02 row count mismatch: {actual} != {expected}")

        dup = con.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT match_id, player_id, feature_name, COUNT(*) n
              FROM player_match_features
              WHERE feature_version=?
              GROUP BY 1,2,3 HAVING COUNT(*)>1
            )
            """,
            [version],
        ).fetchone()[0]
        if dup:
            raise RuntimeError(f"Duplicate temporal feature keys: {dup}")

        bad_hist = con.execute(
            """
            SELECT COUNT(*) FROM player_match_features
            WHERE feature_version=?
              AND feature_name LIKE '%__history_n'
              AND (feature_value < 0 OR feature_value <> FLOOR(feature_value))
            """,
            [version],
        ).fetchone()[0]
        if bad_hist:
            raise RuntimeError(f"Invalid history_n values: {bad_hist}")

        bad_std = con.execute(
            """
            SELECT COUNT(*) FROM player_match_features
            WHERE feature_version=?
              AND feature_name LIKE '%__prior_std'
              AND feature_value < 0
            """,
            [version],
        ).fetchone()[0]
        if bad_std:
            raise RuntimeError(f"Negative prior_std values: {bad_std}")

        first_date_leak = con.execute(
            """
            WITH first_dates AS (
              SELECT pm.player_id, MIN(m.match_date) first_date
              FROM player_match pm JOIN matches m ON m.match_id=pm.match_id
              GROUP BY pm.player_id
            )
            SELECT COUNT(*)
            FROM player_match_features f
            JOIN matches m ON m.match_id=f.match_id
            JOIN first_dates d ON d.player_id=f.player_id AND d.first_date=m.match_date
            WHERE f.feature_version=?
              AND (
                (f.feature_name LIKE '%__history_n' AND COALESCE(f.feature_value, -1) <> 0)
                OR (f.feature_name NOT LIKE '%__history_n' AND f.feature_value IS NOT NULL)
              )
            """,
            [version],
        ).fetchone()[0]
        if first_date_leak:
            raise RuntimeError(f"First-date leakage contract failed: {first_date_leak}")

        matches, players = con.execute(
            """
            SELECT COUNT(DISTINCT match_id), COUNT(DISTINCT player_id)
            FROM player_match_features WHERE feature_version=?
            """,
            [version],
        ).fetchone()

    print("FEATURE-02 VALIDATION: PASS")
    print(f"feature_version: {version}")
    print(f"base features: {len(base_names)}")
    print(f"temporal operators: {len(ops)}")
    print(f"feature rows: {actual}/{expected}")
    print(f"coverage: {matches} matches / {players} players")
    print("history_n integer/non-negative: PASS")
    print("prior_std non-negative: PASS")
    print("first-date strict-past contract: PASS")
    print("No ratings/weights/recent-window thresholds created.")


if __name__ == "__main__":
    main()
