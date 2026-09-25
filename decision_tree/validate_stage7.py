"""Validate EXPERT-07 / N13000 final recommendation gate."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from build_stage7 import recommendation_gate


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
CATALOG = Path(__file__).with_name("recommendation_gate_catalog.json")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    catalog = load_json(CATALOG)
    engine_version = catalog["engine_version"]
    parent_version = catalog["parent_engine_version"]
    nodes = catalog["nodes"]
    node_map = {n["node_id"]: n for n in nodes}
    if len(node_map) != len(nodes):
        raise RuntimeError("Duplicate N13000 node ids")

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
            WHERE engine_version = ? AND node_id NOT LIKE 'N13000.%'
            ORDER BY match_id, player_id, node_id
            """,
            [engine_version],
        ).fetchall()
        if parent_rows != current_parent_rows:
            raise RuntimeError("N1000-N12000 carry-forward differs from expert_0.6.0")

        all_rows = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?",
            [engine_version],
        ).fetchone()[0]
        n13000_rows = con.execute(
            """
            SELECT match_id, player_id, node_id, result_type, result_value, confidence, justification
            FROM decision_results
            WHERE engine_version = ? AND node_id LIKE 'N13000.%'
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

        n12000_availability = con.execute(
            """
            SELECT match_id, player_id, result_value
            FROM decision_results
            WHERE engine_version = ? AND node_id = 'N12000.180'
            """,
            [parent_version],
        ).fetchall()
        availability_map = {(m, p): v for m, p, v in n12000_availability}

    expected_n13000 = len(player_matches) * len(nodes)
    expected_all = len(parent_rows) + expected_n13000
    if all_rows != expected_all:
        raise RuntimeError(f"Decision row count mismatch: {all_rows}/{expected_all}")
    if len(n13000_rows) != expected_n13000:
        raise RuntimeError(f"N13000 row count mismatch: {len(n13000_rows)}/{expected_n13000}")

    decision_map = {
        (m, p, node_id): (result_type, result_value, confidence, justification)
        for m, p, node_id, result_type, result_value, confidence, justification in n13000_rows
    }
    expected_node_ids = set(node_map)
    actual_node_ids = {node_id for _, _, node_id, _, _, _, _ in n13000_rows}
    if actual_node_ids != expected_node_ids:
        raise RuntimeError(
            f"N13000 node-id mismatch. missing={sorted(expected_node_ids-actual_node_ids)} "
            f"extra={sorted(actual_node_ids-expected_node_ids)}"
        )

    final_counts: dict[str, int] = {}
    checked = 0
    for match_id, player_id in player_matches:
        availability = availability_map.get((match_id, player_id))
        if availability is None:
            raise RuntimeError(f"Missing parent N12000.180 for {match_id}/{player_id}")
        expected = recommendation_gate(str(availability))

        for node_id, expected_value in expected.items():
            key = (match_id, player_id, node_id)
            if key not in decision_map:
                raise RuntimeError(f"Missing N13000 output: {key}")
            actual_type, actual_value, confidence, justification = decision_map[key]
            if actual_type != node_map[node_id]["result_type"]:
                raise RuntimeError(f"Result type mismatch for {key}: {actual_type}")
            if actual_value != expected_value:
                raise RuntimeError(f"N13000 value mismatch for {key}: {actual_value!r} != {expected_value!r}")
            if float(confidence) != 1.0:
                raise RuntimeError(f"Confidence contract failed for {key}: {confidence}")
            if "N12000" not in justification or "no tactical recommendation is issued" not in justification:
                raise RuntimeError(f"N13000 justification missing gate provenance for {key}")
            checked += 1

        final_state = expected["N13000.120"]
        if not final_state.startswith("RECOMMENDATION_NOT_ISSUED_"):
            raise RuntimeError(f"Unsafe final recommendation state for {match_id}/{player_id}: {final_state}")
        final_counts[final_state] = final_counts.get(final_state, 0) + 1

    if set(final_counts) - set(catalog["allowed_final_states"]):
        raise RuntimeError(f"Unexpected final states: {sorted(set(final_counts)-set(catalog['allowed_final_states']))}")

    print("EXPERT-07 VALIDATION: PASS")
    print(f"engine_version: {engine_version}")
    print(f"parent_engine_version: {parent_version}")
    print(f"player_match rows: {len(player_matches)}")
    print(f"N13000 nodes per player-match: {len(nodes)}")
    print(f"decision rows: {all_rows}/{expected_all}")
    print(f"N13000 rows: {len(n13000_rows)}/{expected_n13000}")
    print(f"N13000 outputs checked: {checked}")
    print("N1000-N12000 exact carry-forward: PASS")
    print("recommendation evidence gate identity contract: PASS")
    print("recommendation policy remains explicitly unvalidated: PASS")
    for state in sorted(final_counts):
        print(f"{state}: {final_counts[state]}")
    print("No tactical recommendation, score, weighting, percentile, ranking or unvalidated threshold was created.")


if __name__ == "__main__":
    main()
