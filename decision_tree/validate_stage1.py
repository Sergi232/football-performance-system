"""Validate EXPERT-01 N1000-N3000 outputs."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
BASE_CATALOG = ROOT / "features" / "catalog.json"
EXPERT_CATALOG = Path(__file__).with_name("catalog.json")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail_if(condition: bool, message: str) -> None:
    if condition:
        raise RuntimeError(message)


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    base = load_json(BASE_CATALOG)
    expert = load_json(EXPERT_CATALOG)
    engine_version = expert["engine_version"]
    features = [x["name"] for x in base["ratio_features"] + base["per90_features"]]

    with duckdb.connect(str(DB), read_only=True) as con:
        pm_count = con.execute("SELECT COUNT(*) FROM player_match").fetchone()[0]
        expected = pm_count * (2 + 2 * len(features))
        actual = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?",
            [engine_version],
        ).fetchone()[0]
        fail_if(actual != expected, f"Decision row count mismatch: {actual}/{expected}")

        duplicates = con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT match_id, player_id, node_id, COUNT(*) AS n
                FROM decision_results
                WHERE engine_version = ?
                GROUP BY 1,2,3 HAVING COUNT(*) > 1
            )
            """,
            [engine_version],
        ).fetchone()[0]
        fail_if(duplicates != 0, f"Duplicate node outputs: {duplicates}")

        family_counts = dict(
            con.execute(
                """
                SELECT substr(node_id, 1, 5), COUNT(*)
                FROM decision_results
                WHERE engine_version = ?
                GROUP BY 1 ORDER BY 1
                """,
                [engine_version],
            ).fetchall()
        )
        fail_if(family_counts.get("N1000") != pm_count, "N1000 coverage mismatch")
        fail_if(family_counts.get("N2000") != pm_count, "N2000 coverage mismatch")
        fail_if(family_counts.get("N3000") != pm_count * len(features) * 2, "N3000 coverage mismatch")

        bad_activity = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id = 'N1000.100'
              AND result_value NOT IN (
                'MINUTES_UNKNOWN','LISTED_NO_MINUTES','STARTER_ACTIVE',
                'SUBSTITUTE_ACTIVE','ACTIVE_START_STATUS_UNKNOWN'
              )
            """,
            [engine_version],
        ).fetchone()[0]
        fail_if(bad_activity != 0, f"Invalid N1000 states: {bad_activity}")

        bad_delta = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id LIKE 'N3000.%.DELTA_PRIOR_MEAN'
              AND result_value NOT IN (
                'CURRENT_VALUE_MISSING','HISTORY_COUNT_MISSING','NO_PRIOR_HISTORY',
                'DELTA_NOT_EVALUABLE','ABOVE_PRIOR_MEAN','BELOW_PRIOR_MEAN','EQUAL_PRIOR_MEAN'
              )
            """,
            [engine_version],
        ).fetchone()[0]
        fail_if(bad_delta != 0, f"Invalid N3000 delta states: {bad_delta}")

        bad_slope = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id LIKE 'N3000.%.PRIOR_SLOPE'
              AND result_value NOT IN (
                'HISTORY_COUNT_MISSING','INSUFFICIENT_PRIOR_HISTORY','SLOPE_NOT_EVALUABLE',
                'PRIOR_TREND_UP','PRIOR_TREND_DOWN','PRIOR_TREND_FLAT'
              )
            """,
            [engine_version],
        ).fetchone()[0]
        fail_if(bad_slope != 0, f"Invalid N3000 slope states: {bad_slope}")

        non_deterministic_confidence = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND (confidence IS NULL OR confidence <> 1.0)
            """,
            [engine_version],
        ).fetchone()[0]
        fail_if(non_deterministic_confidence != 0, "EXPERT-01 confidence contract violated")

        semantic_labels = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ?
              AND regexp_matches(upper(coalesce(result_value,'')), 'GOOD|BAD|IMPROV|DECLIN|RECOMMEND')
            """,
            [engine_version],
        ).fetchone()[0]
        fail_if(semantic_labels != 0, f"Premature semantic/recommendation labels found: {semantic_labels}")

    print("EXPERT-01 VALIDATION: PASS")
    print(f"engine_version: {engine_version}")
    print(f"player_match rows: {pm_count}")
    print(f"base features: {len(features)}")
    print(f"decision rows: {actual}/{expected}")
    print(f"family coverage: N1000={family_counts.get('N1000')}, N2000={family_counts.get('N2000')}, N3000={family_counts.get('N3000')}")
    print("duplicate node outputs: 0")
    print("deterministic confidence contract: PASS")
    print("no premature good/bad/improving/declining/recommendation labels: PASS")


if __name__ == "__main__":
    main()
