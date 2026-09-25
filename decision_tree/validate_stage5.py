"""Validate EXPERT-05 / N11000 strict-past consistency and trend evidence."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
CATALOG = Path(__file__).with_name("consistency_trend_catalog.json")
BASE_CATALOG = ROOT / "features" / "catalog.json"
TEMPORAL_CATALOG = ROOT / "features" / "temporal_catalog.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    catalog = load_json(CATALOG)
    base_catalog = load_json(BASE_CATALOG)
    temporal_catalog = load_json(TEMPORAL_CATALOG)

    engine_version = catalog["engine_version"]
    parent_version = catalog["parent_engine_version"]
    temporal_version = catalog["temporal_feature_version"]
    patterns = catalog["node_patterns"]
    names = feature_names(base_catalog)

    generated_nodes: list[tuple[str, str, str, str]] = []
    for idx, feature in enumerate(names, start=1):
        for pattern in patterns:
            generated_nodes.append((
                f"N11000.{idx:03d}.{pattern['suffix']}",
                feature,
                pattern["operator"],
                pattern["result_type"],
            ))

    if base_catalog["feature_version"] != catalog["base_feature_version"]:
        raise RuntimeError("EXPERT-05 base version mismatch")
    if temporal_catalog["feature_version"] != temporal_version:
        raise RuntimeError("EXPERT-05 temporal version mismatch")

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
            WHERE engine_version = ? AND node_id NOT LIKE 'N11000.%'
            ORDER BY match_id, player_id, node_id
            """,
            [engine_version],
        ).fetchall()

        if parent_rows != current_parent_rows:
            raise RuntimeError("N1000-N10000 carry-forward differs from expert_0.4.0")

        all_rows = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?",
            [engine_version],
        ).fetchone()[0]
        n11000_rows = con.execute(
            """
            SELECT match_id, player_id, node_id, result_type, result_value, confidence, justification
            FROM decision_results
            WHERE engine_version = ? AND node_id LIKE 'N11000.%'
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

    expected_n11000 = len(player_matches) * len(generated_nodes)
    expected_all = len(parent_rows) + expected_n11000
    if all_rows != expected_all:
        raise RuntimeError(f"Decision row count mismatch: {all_rows}/{expected_all}")
    if len(n11000_rows) != expected_n11000:
        raise RuntimeError(f"N11000 row count mismatch: {len(n11000_rows)}/{expected_n11000}")

    decision_map = {
        (m, p, node_id): (result_type, result_value, confidence, justification)
        for m, p, node_id, result_type, result_value, confidence, justification in n11000_rows
    }

    expected_node_ids = {node_id for node_id, _, _, _ in generated_nodes}
    actual_node_ids = {node_id for _, _, node_id, _, _, _, _ in n11000_rows}
    if actual_node_ids != expected_node_ids:
        missing = sorted(expected_node_ids - actual_node_ids)
        extra = sorted(actual_node_ids - expected_node_ids)
        raise RuntimeError(f"N11000 node-id mismatch. missing={missing[:5]} extra={extra[:5]}")

    forbidden_tokens = (
        "HIGH_CONSISTENCY", "LOW_CONSISTENCY", "GOOD", "BAD",
        "IMPROVING", "DECLINING", "RECOMMEND", "RANK",
    )

    checked = 0
    for match_id, player_id in player_matches:
        for node_id, feature, operator, result_type in generated_nodes:
            key = (match_id, player_id, node_id)
            if key not in decision_map:
                raise RuntimeError(f"Missing N11000 output: {key}")
            actual_type, actual_value, confidence, justification = decision_map[key]
            if actual_type != result_type:
                raise RuntimeError(f"Result type mismatch for {key}: {actual_type} != {result_type}")
            if float(confidence) != 1.0:
                raise RuntimeError(f"Confidence contract failed for {key}: {confidence}")

            history_n = temporal_map.get((match_id, player_id, f"{feature}__history_n"))
            value = temporal_map.get((match_id, player_id, f"{feature}__{operator}"))
            missing_state = (
                "PRIOR_STD_NOT_EVALUABLE"
                if operator == "prior_std"
                else "PRIOR_SLOPE_NOT_EVALUABLE"
            )
            expected_value = encode_temporal_numeric(history_n, value, missing_state)
            if actual_value != expected_value:
                raise RuntimeError(
                    f"N11000 evidence mismatch for {key}: {actual_value!r} != {expected_value!r}"
                )
            if f"feature={feature}" not in justification or f"{operator}=" not in justification:
                raise RuntimeError(f"N11000 justification missing provenance for {key}")
            upper = str(actual_value).upper()
            if any(token in upper for token in forbidden_tokens):
                raise RuntimeError(f"Premature evaluative label in {key}: {actual_value}")
            checked += 1

    print("EXPERT-05 VALIDATION: PASS")
    print(f"engine_version: {engine_version}")
    print(f"parent_engine_version: {parent_version}")
    print(f"player_match rows: {len(player_matches)}")
    print(f"base features: {len(names)}")
    print(f"N11000 nodes per player-match: {len(generated_nodes)}")
    print(f"decision rows: {all_rows}/{expected_all}")
    print(f"N11000 rows: {len(n11000_rows)}/{expected_n11000}")
    print(f"N11000 evidence outputs checked: {checked}")
    print("N1000-N10000 exact carry-forward: PASS")
    print("strict-past prior_std/prior_slope identity contract: PASS")
    print("deterministic confidence contract: PASS")
    print("No high/low consistency, improving/declining, score, weight, percentile, ranking or recommendation was validated or created.")


if __name__ == "__main__":
    main()
