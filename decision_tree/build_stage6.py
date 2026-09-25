"""EXPERT-06: N12000 auditable player-fit evidence synthesis.

This stage carries N1000-N11000 forward unchanged from expert_0.5.0 and
summarizes the already validated N10000 same-role evidence. It deliberately
stops before a fit score, weighted ranking or tactical recommendation.
"""
from __future__ import annotations

import json
import uuid
from collections import Counter
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
CATALOG = Path(__file__).with_name("player_fit_evidence_catalog.json")
ROLE_CATALOG = Path(__file__).with_name("role_fit_catalog.json")

EVALUABLE_STATES = {
    "ABOVE_ROLE_PRIOR_MEAN",
    "BELOW_ROLE_PRIOR_MEAN",
    "EQUAL_ROLE_PRIOR_MEAN",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def decision_id(engine_version: str, match_id: str, player_id: str, node_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:decision:{engine_version}:{match_id}:{player_id}:{node_id}"))


def summarize_role_evidence(
    role_value: str,
    history_value: str,
    evidence_values: dict[str, str],
    source_family_by_node: dict[str, str],
) -> dict[str, str]:
    total = len(source_family_by_node)
    if set(evidence_values) != set(source_family_by_node):
        missing = sorted(set(source_family_by_node) - set(evidence_values))
        extra = sorted(set(evidence_values) - set(source_family_by_node))
        raise ValueError(f"N12000 evidence node mismatch. missing={missing} extra={extra}")

    counts = Counter(evidence_values.values())
    evaluable = sum(counts[state] for state in EVALUABLE_STATES)
    unavailable = total - evaluable
    above = counts["ABOVE_ROLE_PRIOR_MEAN"]
    below = counts["BELOW_ROLE_PRIOR_MEAN"]
    equal = counts["EQUAL_ROLE_PRIOR_MEAN"]

    domain_counts: dict[str, int] = {"N4000": 0, "N5000": 0, "N6000": 0, "N7000": 0}
    for node_id, value in evidence_values.items():
        family = source_family_by_node[node_id]
        if family not in domain_counts:
            raise ValueError(f"Unexpected N12000 source family: {family}")
        if value in EVALUABLE_STATES:
            domain_counts[family] += 1

    if role_value == "ROLE_UNKNOWN":
        availability = "ROLE_UNKNOWN"
    elif evaluable == 0:
        availability = "NO_EVALUABLE_ROLE_EVIDENCE"
    else:
        availability = "ROLE_EVIDENCE_AVAILABLE"

    coverage = 0.0 if total == 0 else evaluable / total
    return {
        "N12000.100": role_value,
        "N12000.110": history_value,
        "N12000.120": str(evaluable),
        "N12000.130": str(unavailable),
        "N12000.140": str(above),
        "N12000.150": str(below),
        "N12000.160": str(equal),
        "N12000.170": format(float(coverage), ".17g"),
        "N12000.180": availability,
        "N12000.400": str(domain_counts["N4000"]),
        "N12000.500": str(domain_counts["N5000"]),
        "N12000.600": str(domain_counts["N6000"]),
        "N12000.700": str(domain_counts["N7000"]),
    }


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
        raise RuntimeError(f"EXPERT-06 expects 24 N10000 evidence nodes, found {len(source_family_by_node)}")

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
            raise RuntimeError(f"EXPERT-06 requires validated parent engine {parent_version}")

        n10000_rows = con.execute(
            """
            SELECT match_id, player_id, node_id, result_value
            FROM decision_results
            WHERE engine_version = ? AND node_id LIKE 'N10000.%'
            """,
            [parent_version],
        ).fetchall()

        n10000_map = {(m, p, node_id): value for m, p, node_id, value in n10000_rows}

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

            summary = summarize_role_evidence(
                role_value,
                history_value,
                evidence_values,
                source_family_by_node,
            )

            evaluable = int(summary["N12000.120"])
            unavailable = int(summary["N12000.130"])
            above = int(summary["N12000.140"])
            below = int(summary["N12000.150"])
            equal = int(summary["N12000.160"])
            coverage = summary["N12000.170"]

            for node in nodes:
                node_id = node["node_id"]
                value = summary[node_id]
                rows.append((
                    decision_id(engine_version, match_id, player_id, node_id),
                    match_id,
                    player_id,
                    node_id,
                    node["result_type"],
                    value,
                    1.0,
                    (
                        f"N10000 observed_role={role_value}; same_role_match_history={history_value}; "
                        f"evaluable_signals={evaluable}; unavailable_signals={unavailable}; "
                        f"above={above}; below={below}; equal={equal}; coverage={coverage}; "
                        f"source_signal_count={len(source_family_by_node)}. "
                        "N12000 is a deterministic evidence synthesis only. Direction counts are not "
                        "weighted or interpreted as favourable/unfavourable, and no fit score, percentile, "
                        "cross-player ranking, minimum-sample cutoff or tactical recommendation is applied."
                    ),
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
        con.register("_expert_stage6_rows", frame)
        con.execute(
            """
            INSERT INTO decision_results (
                decision_id, match_id, player_id, node_id, result_type,
                result_value, confidence, justification, engine_version
            )
            SELECT decision_id, match_id, player_id, node_id, result_type,
                   result_value, confidence, justification, engine_version
            FROM _expert_stage6_rows
            """
        )
        con.unregister("_expert_stage6_rows")

        written = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?", [engine_version]
        ).fetchone()[0]
        n12000 = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id LIKE 'N12000.%'
            """,
            [engine_version],
        ).fetchone()[0]
        available = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id = 'N12000.180'
              AND result_value = 'ROLE_EVIDENCE_AVAILABLE'
            """,
            [engine_version],
        ).fetchone()[0]

    print("EXPERT-06 build complete")
    print(f"engine_version: {engine_version}")
    print(f"parent_engine_version: {parent_version}")
    print(f"player_match rows: {len(player_matches)}")
    print(f"N12000 nodes per player-match: {len(nodes)}")
    print(f"decision rows written: {written}")
    print(f"N12000 rows: {n12000}")
    print(f"player-match rows with evaluable same-role evidence: {available}")
    print("N12000 summarizes exact same-role evidence counts only; no fit score, weighting, ranking or recommendation was created.")


if __name__ == "__main__":
    main()
