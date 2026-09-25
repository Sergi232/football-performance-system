"""EXPERT-07: N13000 auditable final recommendation gate.

This stage carries N1000-N12000 forward unchanged from expert_0.6.0 and adds
an explicit gate for the final recommendation. Because no recommendation
policy, weights, practical-significance thresholds or minimum-sample rules have
been validated yet, this stage deliberately refuses to issue a tactical
recommendation.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
CATALOG = Path(__file__).with_name("recommendation_gate_catalog.json")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def decision_id(engine_version: str, match_id: str, player_id: str, node_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:decision:{engine_version}:{match_id}:{player_id}:{node_id}"))


def recommendation_gate(evidence_availability: str) -> dict[str, str]:
    """Map N12000 evidence availability to a non-recommendation gate state."""
    if evidence_availability == "ROLE_UNKNOWN":
        evidence_gate = "ROLE_UNKNOWN"
        final_state = "RECOMMENDATION_NOT_ISSUED_ROLE_UNKNOWN"
    elif evidence_availability == "NO_EVALUABLE_ROLE_EVIDENCE":
        evidence_gate = "NO_EVALUABLE_ROLE_EVIDENCE"
        final_state = "RECOMMENDATION_NOT_ISSUED_NO_EVIDENCE"
    elif evidence_availability == "ROLE_EVIDENCE_AVAILABLE":
        evidence_gate = "EVIDENCE_AVAILABLE"
        final_state = "RECOMMENDATION_NOT_ISSUED_POLICY_UNVALIDATED"
    else:
        raise ValueError(f"Unexpected N12000 evidence availability: {evidence_availability!r}")

    return {
        "N13000.100": evidence_gate,
        "N13000.110": "RECOMMENDATION_POLICY_NOT_VALIDATED",
        "N13000.120": final_state,
    }


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
        if not parent_rows:
            raise RuntimeError(f"EXPERT-07 requires validated parent engine {parent_version}")

        n12000_rows = con.execute(
            """
            SELECT match_id, player_id, node_id, result_value
            FROM decision_results
            WHERE engine_version = ?
              AND node_id IN ('N12000.100','N12000.110','N12000.120','N12000.130','N12000.170','N12000.180')
            """,
            [parent_version],
        ).fetchall()
        n12000_map = {(m, p, node_id): value for m, p, node_id, value in n12000_rows}

        rows: list[tuple] = []
        for match_id, player_id, node_id, result_type, result_value, confidence, justification in parent_rows:
            rows.append((
                decision_id(engine_version, match_id, player_id, node_id),
                match_id,
                player_id,
                node_id,
                result_type,
                result_value,
                float(confidence),
                justification,
                engine_version,
            ))

        final_state_counts: dict[str, int] = {}

        for match_id, player_id in player_matches:
            role = n12000_map.get((match_id, player_id, "N12000.100"))
            role_history = n12000_map.get((match_id, player_id, "N12000.110"))
            evaluable = n12000_map.get((match_id, player_id, "N12000.120"))
            unavailable = n12000_map.get((match_id, player_id, "N12000.130"))
            coverage = n12000_map.get((match_id, player_id, "N12000.170"))
            availability = n12000_map.get((match_id, player_id, "N12000.180"))
            if availability is None:
                raise RuntimeError(f"Missing N12000.180 for {match_id}/{player_id}")

            gate = recommendation_gate(str(availability))
            final_state_counts[gate["N13000.120"]] = final_state_counts.get(gate["N13000.120"], 0) + 1

            provenance = (
                f"N12000 observed_role={role}; same_role_match_history={role_history}; "
                f"evaluable_signals={evaluable}; unavailable_signals={unavailable}; "
                f"evidence_coverage={coverage}; evidence_availability={availability}. "
                "N13000 is a deterministic recommendation gate. The project currently has no validated "
                "recommendation policy, weights, minimum-sample rule or practical-significance threshold, "
                "so no tactical recommendation is issued."
            )

            for node in nodes:
                node_id = node["node_id"]
                rows.append((
                    decision_id(engine_version, match_id, player_id, node_id),
                    match_id,
                    player_id,
                    node_id,
                    node["result_type"],
                    gate[node_id],
                    1.0,
                    provenance,
                    engine_version,
                ))

        expected = len(parent_rows) + len(player_matches) * len(nodes)
        if len(rows) != expected:
            raise RuntimeError(f"Expected {expected} decision rows, built {len(rows)}")

        frame = pd.DataFrame(rows, columns=[
            "decision_id", "match_id", "player_id", "node_id", "result_type",
            "result_value", "confidence", "justification", "engine_version",
        ])
        con.execute("DELETE FROM decision_results WHERE engine_version = ?", [engine_version])
        con.register("_expert_stage7_rows", frame)
        con.execute(
            """
            INSERT INTO decision_results (
                decision_id, match_id, player_id, node_id, result_type,
                result_value, confidence, justification, engine_version
            )
            SELECT decision_id, match_id, player_id, node_id, result_type,
                   result_value, confidence, justification, engine_version
            FROM _expert_stage7_rows
            """
        )
        con.unregister("_expert_stage7_rows")

        written = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?", [engine_version]
        ).fetchone()[0]
        n13000 = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id LIKE 'N13000.%'
            """,
            [engine_version],
        ).fetchone()[0]

    print("EXPERT-07 build complete")
    print(f"engine_version: {engine_version}")
    print(f"parent_engine_version: {parent_version}")
    print(f"player_match rows: {len(player_matches)}")
    print(f"N13000 nodes per player-match: {len(nodes)}")
    print(f"decision rows written: {written}")
    print(f"N13000 rows: {n13000}")
    for state in sorted(final_state_counts):
        print(f"{state}: {final_state_counts[state]}")
    print("N13000 is a safe recommendation gate: no unvalidated tactical recommendation was created.")


if __name__ == "__main__":
    main()
