"""EXPERT-02: auditable domain evidence layer for N4000-N7000.

This stage carries N1000-N3000 forward unchanged from expert_0.1.0 and adds
semantic domain nodes over already-approved FEATURE-01/FEATURE-02 inputs.
No score, percentile, weight, role-fit recommendation or practical-significance
threshold is introduced here.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
BASE_CATALOG = ROOT / "features" / "catalog.json"
TEMPORAL_CATALOG = ROOT / "features" / "temporal_catalog.json"
STAGE1_CATALOG = ROOT / "decision_tree" / "catalog.json"
DOMAIN_CATALOG = Path(__file__).with_name("domain_catalog.json")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_base_feature_names() -> list[str]:
    catalog = load_json(BASE_CATALOG)
    return [x["name"] for x in catalog["ratio_features"] + catalog["per90_features"]]


def decision_id(engine_version: str, match_id: str, player_id: str, node_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:decision:{engine_version}:{match_id}:{player_id}:{node_id}"))


def classify_delta(current: float | None, history_n: float | None, delta: float | None) -> str:
    if current is None:
        return "CURRENT_VALUE_MISSING"
    if history_n is None:
        return "HISTORY_COUNT_MISSING"
    if float(history_n) < 1.0:
        return "NO_PRIOR_HISTORY"
    if delta is None:
        return "DELTA_NOT_EVALUABLE"
    if float(delta) > 0.0:
        return "ABOVE_PRIOR_MEAN"
    if float(delta) < 0.0:
        return "BELOW_PRIOR_MEAN"
    return "EQUAL_PRIOR_MEAN"


def classify_slope(history_n: float | None, slope: float | None) -> str:
    if history_n is None:
        return "HISTORY_COUNT_MISSING"
    if float(history_n) < 2.0:
        return "INSUFFICIENT_PRIOR_HISTORY"
    if slope is None:
        return "SLOPE_NOT_EVALUABLE"
    if float(slope) > 0.0:
        return "PRIOR_TREND_UP"
    if float(slope) < 0.0:
        return "PRIOR_TREND_DOWN"
    return "PRIOR_TREND_FLAT"


def compose_domain_state(
    current: float | None,
    history_n: float | None,
    delta: float | None,
    slope: float | None,
) -> str:
    level = classify_delta(current, history_n, delta)
    if level in {"CURRENT_VALUE_MISSING", "HISTORY_COUNT_MISSING", "NO_PRIOR_HISTORY"}:
        return level
    trend = classify_slope(history_n, slope)
    return f"{level}__{trend}"


def fmt(value: object) -> str:
    return "NULL" if value is None else str(value)


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    base_catalog = load_json(BASE_CATALOG)
    temporal_catalog = load_json(TEMPORAL_CATALOG)
    stage1_catalog = load_json(STAGE1_CATALOG)
    domain_catalog = load_json(DOMAIN_CATALOG)

    engine_version = domain_catalog["engine_version"]
    parent_version = domain_catalog["parent_engine_version"]
    base_version = domain_catalog["dependencies"]["feature_base_version"]
    temporal_version = domain_catalog["dependencies"]["feature_temporal_version"]
    domain_nodes = domain_catalog["domain_nodes"]
    feature_names = load_base_feature_names()

    if stage1_catalog["engine_version"] != parent_version:
        raise RuntimeError("EXPERT-02 parent engine version does not match decision_tree/catalog.json")
    if base_catalog["feature_version"] != base_version:
        raise RuntimeError("EXPERT-02 base feature version mismatch")
    if temporal_catalog["feature_version"] != temporal_version:
        raise RuntimeError("EXPERT-02 temporal feature version mismatch")

    node_ids = [node["node_id"] for node in domain_nodes]
    if len(node_ids) != len(set(node_ids)):
        raise RuntimeError("Duplicate domain node_id in domain_catalog.json")

    allowed_features = set(feature_names)
    missing_catalog_features = sorted({node["feature"] for node in domain_nodes} - allowed_features)
    if missing_catalog_features:
        raise RuntimeError(f"Domain catalog references unknown base features: {missing_catalog_features}")

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
        expected_parent = len(player_matches) * (2 + 2 * len(feature_names))
        if len(parent_rows) != expected_parent:
            raise RuntimeError(
                f"EXPERT-02 requires validated {parent_version}: expected {expected_parent} rows, found {len(parent_rows)}"
            )

        base_rows = con.execute(
            """
            SELECT match_id, player_id, feature_name, feature_value
            FROM player_match_features
            WHERE feature_version = ?
            """,
            [base_version],
        ).fetchall()
        current_map = {(m, p, f): v for m, p, f, v in base_rows}

        temporal_rows = con.execute(
            """
            SELECT match_id, player_id, feature_name, feature_value
            FROM player_match_features
            WHERE feature_version = ?
            """,
            [temporal_version],
        ).fetchall()
        temporal_map: dict[tuple[str, str, str, str], float | None] = {}
        needed_ops = {"history_n", "delta_prior_mean", "prior_slope"}
        for match_id, player_id, feature_name, value in temporal_rows:
            if "__" not in feature_name:
                continue
            base_name, operator = feature_name.rsplit("__", 1)
            if operator in needed_ops:
                temporal_map[(match_id, player_id, base_name, operator)] = value

        rows: list[tuple] = []

        # Carry the already-validated N1000-N3000 layer forward exactly.
        for match_id, player_id, node_id, result_type, result_value, confidence, justification in parent_rows:
            rows.append(
                (
                    decision_id(engine_version, match_id, player_id, node_id),
                    match_id,
                    player_id,
                    node_id,
                    result_type,
                    result_value,
                    float(confidence),
                    justification,
                    engine_version,
                )
            )

        # Add domain evidence. Every state is descriptive relative to the same
        # player's strict-past baseline; it is not a cross-player judgement.
        for match_id, player_id in player_matches:
            for node in domain_nodes:
                feature = node["feature"]
                current = current_map.get((match_id, player_id, feature))
                history_n = temporal_map.get((match_id, player_id, feature, "history_n"))
                delta = temporal_map.get((match_id, player_id, feature, "delta_prior_mean"))
                slope = temporal_map.get((match_id, player_id, feature, "prior_slope"))
                result_value = compose_domain_state(current, history_n, delta, slope)
                node_id = node["node_id"]
                rows.append(
                    (
                        decision_id(engine_version, match_id, player_id, node_id),
                        match_id,
                        player_id,
                        node_id,
                        "domain_relative_signal",
                        result_value,
                        1.0,
                        (
                            f"family={node['family']}; label={node['label']}; feature={feature}; "
                            f"metric_role={node['metric_role']}; current={fmt(current)}; "
                            f"strict_past_history_n={fmt(history_n)}; delta_prior_mean={fmt(delta)}; "
                            f"prior_slope={fmt(slope)}. Relative direction is descriptive only; "
                            "no practical-significance threshold, percentile, role adjustment, score, weight or recommendation is applied."
                        ),
                        engine_version,
                    )
                )

        expected = expected_parent + len(player_matches) * len(domain_nodes)
        if len(rows) != expected:
            raise RuntimeError(f"Expected {expected} decision rows, built {len(rows)}")

        frame = pd.DataFrame(
            rows,
            columns=[
                "decision_id", "match_id", "player_id", "node_id", "result_type",
                "result_value", "confidence", "justification", "engine_version",
            ],
        )

        con.execute("DELETE FROM decision_results WHERE engine_version = ?", [engine_version])
        con.register("_expert_stage2_rows", frame)
        con.execute(
            """
            INSERT INTO decision_results (
                decision_id, match_id, player_id, node_id, result_type,
                result_value, confidence, justification, engine_version
            )
            SELECT
                decision_id, match_id, player_id, node_id, result_type,
                result_value, confidence, justification, engine_version
            FROM _expert_stage2_rows
            """
        )
        con.unregister("_expert_stage2_rows")

        written = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?",
            [engine_version],
        ).fetchone()[0]
        families = con.execute(
            """
            SELECT regexp_extract(node_id, '^(N[0-9]+)', 1) AS family, COUNT(*)
            FROM decision_results
            WHERE engine_version = ?
            GROUP BY 1 ORDER BY 1
            """,
            [engine_version],
        ).fetchall()

    print("EXPERT-02 build complete")
    print(f"engine_version: {engine_version}")
    print(f"parent_engine_version: {parent_version}")
    print(f"player_match rows: {len(player_matches)}")
    print(f"domain nodes per player-match: {len(domain_nodes)}")
    print(f"decision rows written: {written}")
    print("family rows: " + ", ".join(f"{name}={count}" for name, count in families))
    print("N4000-N7000 are descriptive own-history evidence only; no scores, weights, percentiles or recommendations were created.")


if __name__ == "__main__":
    main()
