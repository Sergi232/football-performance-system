"""Validate EXPERT-06 / N12000 player-fit evidence synthesis."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from decision_tree.build_stage6 import summarize_role_evidence


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
CATALOG = Path(__file__).with_name("player_fit_evidence_catalog.json")
ROLE_CATALOG = Path(__file__).with_name("role_fit_catalog.json")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    catalog = load_json(CATALOG)
    role_catalog = load_json(ROLE_CATALOG)
    engine_version = catalog["engine_version"]
    parent_version = catalog["parent_engine_version"]
    nodes = catalog["nodes"]
    node_map = {n["node_id"]: n for n in nodes}
    if len(node_map) != len(nodes):
        raise RuntimeError("Duplicate N12000 node ids")

    evidence_nodes = role_catalog["evidence_nodes"]
    source_family_by_node = {n["node_id"]: n["source_family"] for n in evidence_nodes}
    if len(source_family_by_node) != 24:
        raise RuntimeError(f"Expected 24 N10000 evidence nodes, found {len(source_family_by_node)}")

    with duckdb.connect(str(DB)) as con:
        player_matches = con.execute(
            "SELECT match_id, player_id FROM player_match ORDER BY match_id, player_id"
        ).fetchall()

        parent_rows = con.execute(
            """
            SELECT match_id, player_id, node_id, result_type, result_value, confidence, justification
            FROM decision_results
            WHERE engine_version = ?
            ORDER BY match_id, player_id, node_id
            """,
            [parent_version],
        ).fetchall()
        current_parent_rows = con.execute(
            """
            SELECT match_id, player_id, node_id, result_type, result_value, confidence, justification
            FROM decision_results
            WHERE engine_version = ? AND node_id NOT LIKE 'N12000.%'
            ORDER BY match_id, player_id, node_id
            """,
            [engine_version],
        ).fetchall()
        if parent_rows != current_parent_rows:
            raise RuntimeError("N1000-N11000 carry-forward differs from expert_0.5.0")

        all_rows = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?",
            [engine_version],
        ).fetchone()[0]
        n12000_rows = con.execute(
            """
            SELECT match_id, player_id, node_id, result_type, result_value, confidence, justification
            FROM decision_results
            WHERE engine_version = ? AND node_id LIKE 'N12000.%'
            ORDER BY match_id, player_id, node_id
            """,
            [engine_version],
        ).fetchall()

        duplicate_nodes = con.execute(
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
        if duplicate_nodes != 0:
            raise RuntimeError(f"Duplicate decision outputs: {duplicate_nodes}")

        n10000_rows = con.execute(
            """
            SELECT match_id, player_id, node_id, result_value
            FROM decision_results
            WHERE engine_version = ? AND node_id LIKE 'N10000.%'
            """,
            [parent_version],
        ).fetchall()
        n10000_map = {(m, p, node_id): value for m, p, node_id, value in n10000_rows}

    expected_n12000 = len(player_matches) * len(nodes)
    expected_all = len(parent_rows) + expected_n12000
    if all_rows != expected_all:
        raise RuntimeError(f"Decision row count mismatch: {all_rows}/{expected_all}")
    if len(n12000_rows) != expected_n12000:
        raise RuntimeError(f"N12000 row count mismatch: {len(n12000_rows)}/{expected_n12000}")

    decision_map = {
        (m, p, node_id): (result_type, result_value, confidence, justification)
        for m, p, node_id, result_type, result_value, confidence, justification in n12000_rows
    }
    expected_node_ids = set(node_map)
    actual_node_ids = {node_id for _, _, node_id, _, _, _, _ in n12000_rows}
    if actual_node_ids != expected_node_ids:
        missing = sorted(expected_node_ids - actual_node_ids)
        extra = sorted(actual_node_ids - expected_node_ids)
        raise RuntimeError(f"N12000 node-id mismatch. missing={missing} extra={extra}")

    forbidden_tokens = ("GOOD", "BAD", "BEST", "WORST", "RECOMMEND", "RANK", "HIGH_FIT", "LOW_FIT")
    checked = 0
    available = 0

    for match_id, player_id in player_matches:
        role_value = n10000_map.get((match_id, player_id, "N10000.100"))
        history_value = n10000_map.get((match_id, player_id, "N10000.110"))
        if role_value is None or history_value is None:
            raise RuntimeError(f"Missing N10000 context for {match_id}/{player_id}")

        evidence_values: dict[str, str] = {}
        for node_id in source_family_by_node:
            value = n10000_map.get((match_id, player_id, node_id))
            if value is None:
                raise RuntimeError(f"Missing N10000 evidence {node_id} for {match_id}/{player_id}")
            evidence_values[node_id] = value

        expected = summarize_role_evidence(
            role_value,
            history_value,
            evidence_values,
            source_family_by_node,
        )

        evaluable = int(expected["N12000.120"])
        unavailable = int(expected["N12000.130"])
        above = int(expected["N12000.140"])
        below = int(expected["N12000.150"])
        equal = int(expected["N12000.160"])
        domain_total = sum(int(expected[node_id]) for node_id in ("N12000.400", "N12000.500", "N12000.600", "N12000.700"))
        if evaluable + unavailable != len(source_family_by_node):
            raise RuntimeError(f"N12000 evaluable/unavailable partition failed for {match_id}/{player_id}")
        if above + below + equal != evaluable:
            raise RuntimeError(f"N12000 direction partition failed for {match_id}/{player_id}")
        if domain_total != evaluable:
            raise RuntimeError(f"N12000 domain partition failed for {match_id}/{player_id}")

        coverage = float(expected["N12000.170"])
        if not 0.0 <= coverage <= 1.0:
            raise RuntimeError(f"N12000 coverage outside [0,1] for {match_id}/{player_id}: {coverage}")
        if expected["N12000.180"] == "ROLE_EVIDENCE_AVAILABLE":
            available += 1

        for node_id, expected_value in expected.items():
            key = (match_id, player_id, node_id)
            if key not in decision_map:
                raise RuntimeError(f"Missing N12000 output: {key}")
            actual_type, actual_value, confidence, justification = decision_map[key]
            if actual_type != node_map[node_id]["result_type"]:
                raise RuntimeError(f"Result type mismatch for {key}: {actual_type}")
            if actual_value != expected_value:
                raise RuntimeError(f"N12000 value mismatch for {key}: {actual_value!r} != {expected_value!r}")
            if float(confidence) != 1.0:
                raise RuntimeError(f"Confidence contract failed for {key}: {confidence}")
            if "N10000" not in justification or "source_signal_count=24" not in justification:
                raise RuntimeError(f"N12000 justification missing provenance for {key}")
            upper = str(actual_value).upper()
            if any(token in upper for token in forbidden_tokens):
                raise RuntimeError(f"Premature evaluative/recommendation label in {key}: {actual_value}")
            checked += 1

    print("EXPERT-06 VALIDATION: PASS")
    print(f"engine_version: {engine_version}")
    print(f"parent_engine_version: {parent_version}")
    print(f"player_match rows: {len(player_matches)}")
    print(f"N12000 nodes per player-match: {len(nodes)}")
    print(f"decision rows: {all_rows}/{expected_all}")
    print(f"N12000 rows: {len(n12000_rows)}/{expected_n12000}")
    print(f"N12000 outputs checked: {checked}")
    print(f"player-match rows with evaluable same-role evidence: {available}")
    print("N1000-N11000 exact carry-forward: PASS")
    print("N10000 evidence partition + coverage identity contract: PASS")
    print("deterministic confidence contract: PASS")
    print("No fit score, weighting, percentile, ranking, minimum-sample cutoff or recommendation was validated or created.")


if __name__ == "__main__":
    main()
