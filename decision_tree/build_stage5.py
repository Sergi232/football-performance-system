"""EXPERT-05: N11000 strict-past consistency/trend evidence.

This stage carries N1000-N10000 forward unchanged from expert_0.4.0 and adds
exact prior_std and prior_slope evidence from FEATURE-02. It deliberately avoids
high/low consistency labels, improving/declining labels, scores and rankings.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
CATALOG = Path(__file__).with_name("consistency_trend_catalog.json")
BASE_CATALOG = ROOT / "features" / "catalog.json"
TEMPORAL_CATALOG = ROOT / "features" / "temporal_catalog.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def decision_id(engine_version: str, match_id: str, player_id: str, node_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:decision:{engine_version}:{match_id}:{player_id}:{node_id}"))


def feature_names(base_catalog: dict) -> list[str]:
    return [f["name"] for f in base_catalog["ratio_features"] + base_catalog["per90_features"]]


def encode_temporal_numeric(
    history_n: float | None,
    value: float | None,
    missing_value_state: str,
) -> str:
    if history_n is None:
        return "HISTORY_COUNT_MISSING"
    if float(history_n) < 2.0:
        return "INSUFFICIENT_PRIOR_HISTORY"
    if value is None:
        return missing_value_state
    return format(float(value), ".17g")


def fmt(value: object) -> str:
    return "NULL" if value is None else str(value)


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    catalog = load_json(CATALOG)
    base_catalog = load_json(BASE_CATALOG)
    temporal_catalog = load_json(TEMPORAL_CATALOG)

    engine_version = catalog["engine_version"]
    parent_version = catalog["parent_engine_version"]
    base_version = catalog["base_feature_version"]
    temporal_version = catalog["temporal_feature_version"]
    patterns = catalog["node_patterns"]
    names = feature_names(base_catalog)

    if base_catalog["feature_version"] != base_version:
        raise RuntimeError("EXPERT-05 base feature version mismatch")
    if temporal_catalog["feature_version"] != temporal_version:
        raise RuntimeError("EXPERT-05 temporal feature version mismatch")
    if temporal_catalog["base_feature_version"] != base_version:
        raise RuntimeError("EXPERT-05 temporal/base feature contract mismatch")
    if len(names) != len(set(names)):
        raise RuntimeError("Duplicate base feature names")

    generated_nodes: list[tuple[str, str, str, str]] = []
    for idx, feature in enumerate(names, start=1):
        for pattern in patterns:
            node_id = f"N11000.{idx:03d}.{pattern['suffix']}"
            generated_nodes.append((node_id, feature, pattern["operator"], pattern["result_type"]))
    if len({n[0] for n in generated_nodes}) != len(generated_nodes):
        raise RuntimeError("Duplicate N11000 node ids")

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
            raise RuntimeError(f"EXPERT-05 requires validated parent engine {parent_version}")

        temporal_rows = con.execute(
            """
            SELECT match_id, player_id, feature_name, feature_value
            FROM player_match_features
            WHERE feature_version = ?
              AND (
                feature_name LIKE '%__history_n'
                OR feature_name LIKE '%__prior_std'
                OR feature_name LIKE '%__prior_slope'
              )
            """,
            [temporal_version],
        ).fetchall()
        temporal_map = {(m, p, f): v for m, p, f, v in temporal_rows}

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
            for node_id, feature, operator, result_type in generated_nodes:
                history_n = temporal_map.get((match_id, player_id, f"{feature}__history_n"))
                value = temporal_map.get((match_id, player_id, f"{feature}__{operator}"))
                missing_state = (
                    "PRIOR_STD_NOT_EVALUABLE"
                    if operator == "prior_std"
                    else "PRIOR_SLOPE_NOT_EVALUABLE"
                )
                result_value = encode_temporal_numeric(history_n, value, missing_state)
                rows.append((
                    decision_id(engine_version, match_id, player_id, node_id),
                    match_id,
                    player_id,
                    node_id,
                    result_type,
                    result_value,
                    1.0,
                    (
                        f"feature={feature}; strict_past_history_n={fmt(history_n)}; "
                        f"{operator}={fmt(value)}. "
                        "The exact strict-past value is exposed when mathematically evaluable. "
                        "No high/low consistency label, improving/declining label, score, weight, "
                        "percentile, ranking, practical-significance cutoff or recommendation is applied."
                    ),
                    engine_version,
                ))

        expected = len(parent_rows) + len(player_matches) * len(generated_nodes)
        if len(rows) != expected:
            raise RuntimeError(f"Expected {expected} decision rows, built {len(rows)}")

        frame = pd.DataFrame(rows, columns=[
            "decision_id", "match_id", "player_id", "node_id", "result_type",
            "result_value", "confidence", "justification", "engine_version",
        ])

        con.execute("DELETE FROM decision_results WHERE engine_version = ?", [engine_version])
        con.register("_expert_stage5_rows", frame)
        con.execute(
            """
            INSERT INTO decision_results (
                decision_id, match_id, player_id, node_id, result_type,
                result_value, confidence, justification, engine_version
            )
            SELECT decision_id, match_id, player_id, node_id, result_type,
                   result_value, confidence, justification, engine_version
            FROM _expert_stage5_rows
            """
        )
        con.unregister("_expert_stage5_rows")

        written = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?",
            [engine_version],
        ).fetchone()[0]
        n11000 = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id LIKE 'N11000.%'
            """,
            [engine_version],
        ).fetchone()[0]

    print("EXPERT-05 build complete")
    print(f"engine_version: {engine_version}")
    print(f"parent_engine_version: {parent_version}")
    print(f"player_match rows: {len(player_matches)}")
    print(f"base features: {len(names)}")
    print(f"N11000 nodes per player-match: {len(generated_nodes)}")
    print(f"decision rows written: {written}")
    print(f"N11000 rows: {n11000}")
    print("N11000 exposes exact strict-past prior_std/prior_slope evidence only; no evaluative thresholds or recommendations were created.")


if __name__ == "__main__":
    main()
