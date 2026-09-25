"""Validate EXPERT-04 N10000 role-conditioned evidence layer."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
CATALOG = Path(__file__).with_name("role_fit_catalog.json")
ROLE_FEATURE_CATALOG = ROOT / "features" / "role_temporal_catalog.json"

FORBIDDEN_TOKENS = (
    "GOOD", "BAD", "BEST", "WORST", "RECOMMEND", "SUITABLE", "UNSUITABLE",
    "FIT_SCORE", "HIGH_FIT", "LOW_FIT",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    catalog = load_json(CATALOG)
    role_feature_catalog = load_json(ROLE_FEATURE_CATALOG)
    engine_version = catalog["engine_version"]
    parent_version = catalog["parent_engine_version"]
    role_feature_version = catalog["role_feature_version"]
    context_nodes = catalog["context_nodes"]
    evidence_nodes = catalog["evidence_nodes"]
    all_nodes = context_nodes + evidence_nodes

    if role_feature_catalog["feature_version"] != role_feature_version:
        raise RuntimeError("EXPERT-04 role feature version mismatch")
    if len({n["node_id"] for n in all_nodes}) != len(all_nodes):
        raise RuntimeError("Duplicate N10000 node IDs")

    with duckdb.connect(str(DB), read_only=True) as con:
        pm_count = con.execute("SELECT COUNT(*) FROM player_match").fetchone()[0]
        observed_role_count = con.execute(
            """
            SELECT COUNT(*) FROM player_match
            WHERE primary_role IS NOT NULL AND TRIM(primary_role) <> ''
            """
        ).fetchone()[0]
        parent_count = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?",
            [parent_version],
        ).fetchone()[0]
        if parent_count == 0:
            raise RuntimeError(f"Missing parent engine {parent_version}")

        expected_n10000 = pm_count * len(all_nodes)
        expected_total = parent_count + expected_n10000
        total = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?",
            [engine_version],
        ).fetchone()[0]
        if total != expected_total:
            raise RuntimeError(f"decision rows mismatch: {total}/{expected_total}")

        n10000_count = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id LIKE 'N10000.%'
            """,
            [engine_version],
        ).fetchone()[0]
        if n10000_count != expected_n10000:
            raise RuntimeError(f"N10000 rows mismatch: {n10000_count}/{expected_n10000}")

        duplicate_count = con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT match_id, player_id, node_id, COUNT(*) AS n
                FROM decision_results
                WHERE engine_version = ?
                GROUP BY 1,2,3
                HAVING COUNT(*) > 1
            )
            """,
            [engine_version],
        ).fetchone()[0]
        if duplicate_count:
            raise RuntimeError(f"duplicate node outputs: {duplicate_count}")

        confidence_bad = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND (confidence IS NULL OR confidence <> 1.0)
            """,
            [engine_version],
        ).fetchone()[0]
        if confidence_bad:
            raise RuntimeError(f"deterministic confidence violations: {confidence_bad}")

        child_minus_parent = con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT match_id, player_id, node_id, result_type, result_value, confidence, justification
                FROM decision_results
                WHERE engine_version = ? AND node_id NOT LIKE 'N10000.%'
                EXCEPT
                SELECT match_id, player_id, node_id, result_type, result_value, confidence, justification
                FROM decision_results
                WHERE engine_version = ?
            )
            """,
            [engine_version, parent_version],
        ).fetchone()[0]
        parent_minus_child = con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT match_id, player_id, node_id, result_type, result_value, confidence, justification
                FROM decision_results
                WHERE engine_version = ?
                EXCEPT
                SELECT match_id, player_id, node_id, result_type, result_value, confidence, justification
                FROM decision_results
                WHERE engine_version = ? AND node_id NOT LIKE 'N10000.%'
            )
            """,
            [parent_version, engine_version],
        ).fetchone()[0]
        if child_minus_parent or parent_minus_child:
            raise RuntimeError(
                f"N1000-N9000 carry-forward mismatch: child_minus_parent={child_minus_parent}, "
                f"parent_minus_child={parent_minus_child}"
            )

        role_identity_bad = con.execute(
            """
            SELECT COUNT(*)
            FROM decision_results d
            JOIN player_match pm
              ON pm.match_id = d.match_id AND pm.player_id = d.player_id
            WHERE d.engine_version = ? AND d.node_id = 'N10000.100'
              AND d.result_value IS DISTINCT FROM
                  CASE
                    WHEN pm.primary_role IS NULL OR TRIM(pm.primary_role) = '' THEN 'ROLE_UNKNOWN'
                    ELSE TRIM(pm.primary_role)
                  END
            """,
            [engine_version],
        ).fetchone()[0]
        if role_identity_bad:
            raise RuntimeError(f"observed-role identity violations: {role_identity_bad}")

        observed_role_outputs = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id = 'N10000.100' AND result_value <> 'ROLE_UNKNOWN'
            """,
            [engine_version],
        ).fetchone()[0]
        if observed_role_outputs != observed_role_count:
            raise RuntimeError(
                f"observed role coverage mismatch: {observed_role_outputs}/{observed_role_count}"
            )

        evidence_count = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND result_type = 'role_conditioned_relative_signal'
            """,
            [engine_version],
        ).fetchone()[0]
        expected_evidence = pm_count * len(evidence_nodes)
        if evidence_count != expected_evidence:
            raise RuntimeError(f"role evidence rows mismatch: {evidence_count}/{expected_evidence}")

        bad_justification = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ?
              AND result_type = 'role_conditioned_relative_signal'
              AND (
                justification NOT LIKE '%observed_role=%'
                OR justification NOT LIKE '%feature=%'
                OR justification NOT LIKE '%same_role_history_n=%'
                OR justification NOT LIKE '%delta_same_role_prior_mean=%'
              )
            """,
            [engine_version],
        ).fetchone()[0]
        if bad_justification:
            raise RuntimeError(f"role evidence justification violations: {bad_justification}")

        values = [
            str(row[0]).upper()
            for row in con.execute(
                "SELECT result_value FROM decision_results WHERE engine_version = ? AND node_id LIKE 'N10000.%'",
                [engine_version],
            ).fetchall()
        ]
        forbidden_hits = sorted(
            {token for token in FORBIDDEN_TOKENS if any(token in value for value in values)}
        )
        if forbidden_hits:
            raise RuntimeError(f"premature evaluative/fit labels found: {forbidden_hits}")

        role_feature_rows = con.execute(
            "SELECT COUNT(*) FROM player_match_features WHERE feature_version = ?",
            [role_feature_version],
        ).fetchone()[0]
        if role_feature_rows == 0:
            raise RuntimeError(f"Missing FEATURE-03 version {role_feature_version}")

    print("EXPERT-04 VALIDATION: PASS")
    print(f"engine_version: {engine_version}")
    print(f"parent_engine_version: {parent_version}")
    print(f"player_match rows: {pm_count}")
    print(f"N10000 nodes per player-match: {len(all_nodes)}")
    print(f"decision rows: {total}/{expected_total}")
    print(f"N10000 rows: {n10000_count}/{expected_n10000}")
    print(f"role-conditioned evidence rows: {evidence_count}/{expected_evidence}")
    print(f"observed-role player-match rows: {observed_role_outputs}/{pm_count}")
    print("N1000-N9000 exact carry-forward: PASS")
    print("observed role identity contract: PASS")
    print("same-role evidence justification contract: PASS")
    print("deterministic confidence contract: PASS")
    print("No fit score, minimum-sample threshold, weight, percentile, ranking or recommendation was validated or created.")


if __name__ == "__main__":
    main()
