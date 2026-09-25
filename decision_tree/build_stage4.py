"""EXPERT-04: N10000 auditable role-conditioned tactical-fit evidence.

This stage carries N1000-N9000 forward unchanged from expert_0.3.0 and adds
same-role strict-past evidence from FEATURE-03. It deliberately stops before a
fit score, recommendation, minimum-sample threshold or cross-player ranking.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
CATALOG = Path(__file__).with_name("role_fit_catalog.json")
CONTEXT_CATALOG = Path(__file__).with_name("context_catalog.json")
BASE_CATALOG = ROOT / "features" / "catalog.json"
ROLE_FEATURE_CATALOG = ROOT / "features" / "role_temporal_catalog.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_role(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def decision_id(engine_version: str, match_id: str, player_id: str, node_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:decision:{engine_version}:{match_id}:{player_id}:{node_id}"))


def classify_role_relative(
    role: str | None,
    current: float | None,
    metric_role_history_n: float | None,
    delta_role_prior_mean: float | None,
) -> str:
    if clean_role(role) is None:
        return "ROLE_UNKNOWN"
    if current is None:
        return "CURRENT_VALUE_MISSING"
    if metric_role_history_n is None:
        return "ROLE_HISTORY_MISSING"
    if float(metric_role_history_n) < 1.0:
        return "NO_PRIOR_METRIC_HISTORY_IN_ROLE"
    if delta_role_prior_mean is None:
        return "ROLE_DELTA_NOT_EVALUABLE"
    if float(delta_role_prior_mean) > 0.0:
        return "ABOVE_ROLE_PRIOR_MEAN"
    if float(delta_role_prior_mean) < 0.0:
        return "BELOW_ROLE_PRIOR_MEAN"
    return "EQUAL_ROLE_PRIOR_MEAN"


def fmt(value: object) -> str:
    return "NULL" if value is None else str(value)


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    catalog = load_json(CATALOG)
    context_catalog = load_json(CONTEXT_CATALOG)
    base_catalog = load_json(BASE_CATALOG)
    role_feature_catalog = load_json(ROLE_FEATURE_CATALOG)

    engine_version = catalog["engine_version"]
    parent_version = catalog["parent_engine_version"]
    base_version = catalog["base_feature_version"]
    role_feature_version = catalog["role_feature_version"]
    context_nodes = catalog["context_nodes"]
    evidence_nodes = catalog["evidence_nodes"]

    if context_catalog["engine_version"] != parent_version:
        raise RuntimeError("EXPERT-04 parent engine version mismatch")
    if base_catalog["feature_version"] != base_version:
        raise RuntimeError("EXPERT-04 base feature version mismatch")
    if role_feature_catalog["feature_version"] != role_feature_version:
        raise RuntimeError("EXPERT-04 role feature version mismatch")

    all_nodes = context_nodes + evidence_nodes
    node_ids = [n["node_id"] for n in all_nodes]
    if len(node_ids) != len(set(node_ids)):
        raise RuntimeError("Duplicate N10000 node_id in role_fit_catalog.json")

    allowed_base = {
        f["name"] for f in base_catalog["ratio_features"] + base_catalog["per90_features"]
    }
    unknown = sorted({n["feature"] for n in evidence_nodes} - allowed_base)
    if unknown:
        raise RuntimeError(f"N10000 catalog references unknown base features: {unknown}")

    with duckdb.connect(str(DB)) as con:
        player_matches = con.execute(
            """
            SELECT match_id, player_id, primary_role
            FROM player_match
            ORDER BY match_id, player_id
            """
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
            raise RuntimeError(f"EXPERT-04 requires validated parent engine {parent_version}")

        base_rows = con.execute(
            """
            SELECT match_id, player_id, feature_name, feature_value
            FROM player_match_features
            WHERE feature_version = ?
            """,
            [base_version],
        ).fetchall()
        base_map = {(m, p, f): v for m, p, f, v in base_rows}

        role_rows = con.execute(
            """
            SELECT match_id, player_id, feature_name, feature_value, feature_text
            FROM player_match_features
            WHERE feature_version = ?
            """,
            [role_feature_version],
        ).fetchall()

        role_metric_map: dict[tuple[str, str, str, str], tuple[float | None, str | None]] = {}
        role_match_history: dict[tuple[str, str], tuple[float | None, str | None]] = {}
        needed_ops = {"role_history_n", "role_prior_mean", "role_delta_prior_mean"}
        for match_id, player_id, feature_name, value, feature_text in role_rows:
            if feature_name == "role_match_history_n":
                role_match_history[(match_id, player_id)] = (value, clean_role(feature_text))
                continue
            if "__" not in feature_name:
                continue
            base_name, operator = feature_name.rsplit("__", 1)
            if operator in needed_ops:
                role_metric_map[(match_id, player_id, base_name, operator)] = (
                    value,
                    clean_role(feature_text),
                )

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

        role_node = context_nodes[0]
        history_node = context_nodes[1]

        for match_id, player_id, raw_role in player_matches:
            role = clean_role(raw_role)
            role_value = role if role is not None else "ROLE_UNKNOWN"
            rows.append((
                decision_id(engine_version, match_id, player_id, role_node["node_id"]),
                match_id,
                player_id,
                role_node["node_id"],
                role_node["result_type"],
                role_value,
                1.0,
                f"Observed player_match.primary_role={role if role is not None else 'NULL'}. No role is inferred.",
                engine_version,
            ))

            role_match_n, role_match_text = role_match_history.get((match_id, player_id), (None, None))
            if role is not None and role_match_text is not None and role_match_text != role:
                raise RuntimeError(
                    f"FEATURE-03 role identity mismatch for {match_id}/{player_id}: {role_match_text!r} != {role!r}"
                )
            history_value = "ROLE_UNKNOWN" if role is None else ("NULL" if role_match_n is None else str(int(float(role_match_n))))
            rows.append((
                decision_id(engine_version, match_id, player_id, history_node["node_id"]),
                match_id,
                player_id,
                history_node["node_id"],
                history_node["result_type"],
                history_value,
                1.0,
                (
                    f"Observed role={role if role is not None else 'NULL'}; "
                    f"strict-past same-role played matches={fmt(role_match_n)}. "
                    "The count is exposed directly; no minimum-sample cutoff is applied."
                ),
                engine_version,
            ))

            for node in evidence_nodes:
                feature = node["feature"]
                current = base_map.get((match_id, player_id, feature))
                history_n, history_role = role_metric_map.get(
                    (match_id, player_id, feature, "role_history_n"), (None, None)
                )
                prior_mean, mean_role = role_metric_map.get(
                    (match_id, player_id, feature, "role_prior_mean"), (None, None)
                )
                delta, delta_role = role_metric_map.get(
                    (match_id, player_id, feature, "role_delta_prior_mean"), (None, None)
                )
                for stored_role in (history_role, mean_role, delta_role):
                    if role is not None and stored_role is not None and stored_role != role:
                        raise RuntimeError(
                            f"FEATURE-03 metric role mismatch for {match_id}/{player_id}/{feature}: "
                            f"{stored_role!r} != {role!r}"
                        )

                result_value = classify_role_relative(role, current, history_n, delta)
                rows.append((
                    decision_id(engine_version, match_id, player_id, node["node_id"]),
                    match_id,
                    player_id,
                    node["node_id"],
                    "role_conditioned_relative_signal",
                    result_value,
                    1.0,
                    (
                        f"observed_role={role if role is not None else 'NULL'}; "
                        f"source_family={node['source_family']}; feature={feature}; "
                        f"metric_role={node['metric_role']}; current={fmt(current)}; "
                        f"same_role_history_n={fmt(history_n)}; same_role_prior_mean={fmt(prior_mean)}; "
                        f"delta_same_role_prior_mean={fmt(delta)}. "
                        "Direction is descriptive same-player/same-role evidence only; no fit score, "
                        "minimum-sample threshold, percentile, weight or recommendation is applied."
                    ),
                    engine_version,
                ))

        expected = len(parent_rows) + len(player_matches) * len(all_nodes)
        if len(rows) != expected:
            raise RuntimeError(f"Expected {expected} decision rows, built {len(rows)}")

        frame = pd.DataFrame(rows, columns=[
            "decision_id", "match_id", "player_id", "node_id", "result_type",
            "result_value", "confidence", "justification", "engine_version",
        ])
        con.execute("DELETE FROM decision_results WHERE engine_version = ?", [engine_version])
        con.register("_expert_stage4_rows", frame)
        con.execute(
            """
            INSERT INTO decision_results (
                decision_id, match_id, player_id, node_id, result_type,
                result_value, confidence, justification, engine_version
            )
            SELECT decision_id, match_id, player_id, node_id, result_type,
                   result_value, confidence, justification, engine_version
            FROM _expert_stage4_rows
            """
        )
        con.unregister("_expert_stage4_rows")

        written = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?",
            [engine_version],
        ).fetchone()[0]
        n10000 = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id LIKE 'N10000.%'
            """,
            [engine_version],
        ).fetchone()[0]
        observed_roles = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id = 'N10000.100' AND result_value <> 'ROLE_UNKNOWN'
            """,
            [engine_version],
        ).fetchone()[0]

    print("EXPERT-04 build complete")
    print(f"engine_version: {engine_version}")
    print(f"parent_engine_version: {parent_version}")
    print(f"player_match rows: {len(player_matches)}")
    print(f"N10000 nodes per player-match: {len(all_nodes)}")
    print(f"decision rows written: {written}")
    print(f"N10000 rows: {n10000}")
    print(f"player-match rows with observed role: {observed_roles}")
    print("N10000 exposes same-role strict-past evidence only; no fit score, threshold, ranking or recommendation was created.")


if __name__ == "__main__":
    main()
