"""Validate FEATURE-03 role-conditioned strict-past features."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
BASE_CATALOG = ROOT / "features" / "catalog.json"
ROLE_CATALOG = ROOT / "features" / "role_temporal_catalog.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    base_catalog = load_json(BASE_CATALOG)
    role_catalog = load_json(ROLE_CATALOG)
    version = role_catalog["feature_version"]
    base_version = role_catalog["base_feature_version"]
    base_names = [
        x["name"] for x in base_catalog["ratio_features"] + base_catalog["per90_features"]
    ]
    operators = [x["name"] for x in role_catalog["metric_operators"]]

    if base_catalog["feature_version"] != base_version:
        raise RuntimeError("FEATURE-03 base version mismatch")

    with duckdb.connect(str(DB), read_only=True) as con:
        pm_count = con.execute("SELECT COUNT(*) FROM player_match").fetchone()[0]
        expected = pm_count * len(base_names) * len(operators) + pm_count
        total = con.execute(
            "SELECT COUNT(*) FROM player_match_features WHERE feature_version = ?",
            [version],
        ).fetchone()[0]
        if total != expected:
            raise RuntimeError(f"FEATURE-03 row mismatch: {total}/{expected}")

        duplicate_count = con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT match_id, player_id, feature_name, COUNT(*) n
                FROM player_match_features
                WHERE feature_version = ?
                GROUP BY 1,2,3
                HAVING COUNT(*) > 1
            )
            """,
            [version],
        ).fetchone()[0]
        if duplicate_count:
            raise RuntimeError(f"Duplicate FEATURE-03 rows: {duplicate_count}")

        role_pm = con.execute(
            """
            SELECT COUNT(*) FROM player_match
            WHERE primary_role IS NOT NULL AND TRIM(primary_role) <> ''
            """
        ).fetchone()[0]
        distinct_roles = con.execute(
            """
            SELECT COUNT(DISTINCT primary_role) FROM player_match
            WHERE primary_role IS NOT NULL AND TRIM(primary_role) <> ''
            """
        ).fetchone()[0]

        text_mismatch = con.execute(
            """
            SELECT COUNT(*)
            FROM player_match_features f
            JOIN player_match pm
              ON pm.match_id = f.match_id AND pm.player_id = f.player_id
            WHERE f.feature_version = ?
              AND (
                (pm.primary_role IS NULL OR TRIM(pm.primary_role) = '')
                    AND f.feature_text IS NOT NULL
                OR
                (pm.primary_role IS NOT NULL AND TRIM(pm.primary_role) <> '')
                    AND f.feature_text <> TRIM(pm.primary_role)
              )
            """,
            [version],
        ).fetchone()[0]
        if text_mismatch:
            raise RuntimeError(f"Role text/source mismatches: {text_mismatch}")

        missing_role_non_null = con.execute(
            """
            SELECT COUNT(*)
            FROM player_match_features f
            JOIN player_match pm
              ON pm.match_id = f.match_id AND pm.player_id = f.player_id
            WHERE f.feature_version = ?
              AND (pm.primary_role IS NULL OR TRIM(pm.primary_role) = '')
              AND f.feature_value IS NOT NULL
            """,
            [version],
        ).fetchone()[0]
        if missing_role_non_null:
            raise RuntimeError(
                f"Missing roles generated synthetic FEATURE-03 values: {missing_role_non_null}"
            )

        bad_history_n = con.execute(
            """
            SELECT COUNT(*)
            FROM player_match_features f
            JOIN player_match pm
              ON pm.match_id = f.match_id AND pm.player_id = f.player_id
            WHERE f.feature_version = ?
              AND pm.primary_role IS NOT NULL AND TRIM(pm.primary_role) <> ''
              AND (
                f.feature_name = 'role_match_history_n'
                OR f.feature_name LIKE '%__role_history_n'
              )
              AND (
                f.feature_value IS NULL
                OR f.feature_value < 0
                OR f.feature_value <> FLOOR(f.feature_value)
              )
            """,
            [version],
        ).fetchone()[0]
        if bad_history_n:
            raise RuntimeError(f"Invalid role history counts: {bad_history_n}")

        bad_std = con.execute(
            """
            SELECT COUNT(*) FROM player_match_features
            WHERE feature_version = ?
              AND feature_name LIKE '%__role_prior_std'
              AND feature_value < 0
            """,
            [version],
        ).fetchone()[0]
        if bad_std:
            raise RuntimeError(f"Negative role_prior_std values: {bad_std}")

        # Earliest dated observation for every player/role/metric must have
        # zero prior metric history. This directly tests strict-past behavior.
        first_metric_bad = con.execute(
            """
            WITH x AS (
                SELECT f.match_id, f.player_id,
                       REPLACE(f.feature_name, '__role_history_n', '') AS base_feature,
                       f.feature_value,
                       f.feature_text AS role,
                       m.match_date,
                       ROW_NUMBER() OVER (
                           PARTITION BY f.player_id, f.feature_text,
                                        REPLACE(f.feature_name, '__role_history_n', '')
                           ORDER BY m.match_date, f.match_id
                       ) AS rn
                FROM player_match_features f
                JOIN matches m ON m.match_id = f.match_id
                WHERE f.feature_version = ?
                  AND f.feature_name LIKE '%__role_history_n'
                  AND f.feature_text IS NOT NULL
            )
            SELECT COUNT(*) FROM x WHERE rn = 1 AND feature_value <> 0
            """,
            [version],
        ).fetchone()[0]
        if first_metric_bad:
            raise RuntimeError(
                f"First same-role metric observations contain prior history: {first_metric_bad}"
            )

        # Earliest role observation must have zero prior played matches in role.
        first_role_bad = con.execute(
            """
            WITH x AS (
                SELECT f.match_id, f.player_id, f.feature_text AS role,
                       f.feature_value, m.match_date,
                       ROW_NUMBER() OVER (
                           PARTITION BY f.player_id, f.feature_text
                           ORDER BY m.match_date, f.match_id
                       ) AS rn
                FROM player_match_features f
                JOIN matches m ON m.match_id = f.match_id
                WHERE f.feature_version = ?
                  AND f.feature_name = 'role_match_history_n'
                  AND f.feature_text IS NOT NULL
            )
            SELECT COUNT(*) FROM x WHERE rn = 1 AND feature_value <> 0
            """,
            [version],
        ).fetchone()[0]
        if first_role_bad:
            raise RuntimeError(
                f"First role observations contain prior match history: {first_role_bad}"
            )

        non_null = con.execute(
            """
            SELECT COUNT(*) FROM player_match_features
            WHERE feature_version = ? AND feature_value IS NOT NULL
            """,
            [version],
        ).fetchone()[0]

    print("FEATURE-03 VALIDATION: PASS")
    print(f"feature_version: {version}")
    print(f"base features: {len(base_names)}")
    print(f"role metric operators: {len(operators)}")
    print(f"feature rows: {total}/{expected}")
    print(f"non-null values: {non_null}")
    print(f"player_match rows with observed role: {role_pm}/{pm_count}")
    print(f"distinct observed role labels: {distinct_roles}")
    print("role source identity contract: PASS")
    print("missing-role NULL contract: PASS")
    print("strict-past first-observation contract: PASS")
    print("role history count + std domains: PASS")
    print("No role inference, score, percentile, weight, minimum-sample threshold or fit judgement was validated or created.")


if __name__ == "__main__":
    main()
