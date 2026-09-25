"""EXPERT-01: deterministic auditable foundation for N1000-N3000."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
BASE_CATALOG = ROOT / "features" / "catalog.json"
TEMPORAL_CATALOG = ROOT / "features" / "temporal_catalog.json"
EXPERT_CATALOG = Path(__file__).with_name("catalog.json")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_feature_names() -> list[str]:
    catalog = load_json(BASE_CATALOG)
    return [x["name"] for x in catalog["ratio_features"] + catalog["per90_features"]]


def decision_id(engine_version: str, match_id: str, player_id: str, node_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:decision:{engine_version}:{match_id}:{player_id}:{node_id}"))


def classify_activity(started: bool | None, minutes: float | None) -> str:
    if minutes is None:
        return "MINUTES_UNKNOWN"
    if float(minutes) == 0.0:
        return "LISTED_NO_MINUTES"
    if started is True:
        return "STARTER_ACTIVE"
    if started is False:
        return "SUBSTITUTE_ACTIVE"
    return "ACTIVE_START_STATUS_UNKNOWN"


def classify_role(role: str | None) -> str:
    if role is None or not str(role).strip():
        return "ROLE_UNKNOWN"
    return str(role).strip()


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


def fmt(value: object) -> str:
    return "NULL" if value is None else str(value)


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    base_catalog = load_json(BASE_CATALOG)
    temporal_catalog = load_json(TEMPORAL_CATALOG)
    expert_catalog = load_json(EXPERT_CATALOG)
    feature_names = load_feature_names()

    base_version = expert_catalog["dependencies"]["feature_base_version"]
    temporal_version = expert_catalog["dependencies"]["feature_temporal_version"]
    engine_version = expert_catalog["engine_version"]

    if base_catalog["feature_version"] != base_version:
        raise RuntimeError("EXPERT-01 base feature version does not match features/catalog.json")
    if temporal_catalog["feature_version"] != temporal_version:
        raise RuntimeError("EXPERT-01 temporal feature version does not match temporal_catalog.json")

    with duckdb.connect(str(DB)) as con:
        player_matches = con.execute(
            """
            SELECT match_id, player_id, started, minutes_played, primary_role
            FROM player_match
            ORDER BY match_id, player_id
            """
        ).fetchall()

        base_rows = con.execute(
            """
            SELECT match_id, player_id, feature_name, feature_value
            FROM player_match_features
            WHERE feature_version = ?
            """,
            [base_version],
        ).fetchall()
        expected_base = len(player_matches) * len(feature_names)
        if len(base_rows) != expected_base:
            raise RuntimeError(
                f"EXPERT-01 requires complete FEATURE-01: expected {expected_base} rows, found {len(base_rows)}"
            )
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
        valid_ops = {"history_n", "delta_prior_mean", "prior_slope"}
        for match_id, player_id, feature_name, value in temporal_rows:
            if "__" not in feature_name:
                continue
            base_name, operator = feature_name.rsplit("__", 1)
            if operator in valid_ops:
                temporal_map[(match_id, player_id, base_name, operator)] = value

        rows: list[tuple] = []
        for match_id, player_id, started, minutes, role in player_matches:
            activity = classify_activity(started, minutes)
            node_id = "N1000.100"
            rows.append(
                (
                    decision_id(engine_version, match_id, player_id, node_id),
                    match_id,
                    player_id,
                    node_id,
                    "availability_activity_observed",
                    activity,
                    1.0,
                    f"Deterministic observed state from minutes_played={fmt(minutes)}, started={fmt(started)}. "
                    "No injury, medical availability or fitness is inferred.",
                    engine_version,
                )
            )

            role_state = classify_role(role)
            node_id = "N2000.100"
            rows.append(
                (
                    decision_id(engine_version, match_id, player_id, node_id),
                    match_id,
                    player_id,
                    node_id,
                    "structural_role_observed",
                    role_state,
                    1.0,
                    f"Observed primary_role={fmt(role)}. No archetype, role-fit score or tactical recommendation is inferred.",
                    engine_version,
                )
            )

            for index, feature_name in enumerate(feature_names, start=1):
                current = current_map.get((match_id, player_id, feature_name))
                history_n = temporal_map.get((match_id, player_id, feature_name, "history_n"))
                delta = temporal_map.get((match_id, player_id, feature_name, "delta_prior_mean"))
                slope = temporal_map.get((match_id, player_id, feature_name, "prior_slope"))

                delta_state = classify_delta(current, history_n, delta)
                node_id = f"N3000.{index:03d}.DELTA_PRIOR_MEAN"
                rows.append(
                    (
                        decision_id(engine_version, match_id, player_id, node_id),
                        match_id,
                        player_id,
                        node_id,
                        "form_relative_prior_mean",
                        delta_state,
                        1.0,
                        f"feature={feature_name}; current={fmt(current)}; strict_past_history_n={fmt(history_n)}; "
                        f"delta_prior_mean={fmt(delta)}. Sign is descriptive only and is not a good/bad judgement.",
                        engine_version,
                    )
                )

                slope_state = classify_slope(history_n, slope)
                node_id = f"N3000.{index:03d}.PRIOR_SLOPE"
                rows.append(
                    (
                        decision_id(engine_version, match_id, player_id, node_id),
                        match_id,
                        player_id,
                        node_id,
                        "strict_past_trend_direction",
                        slope_state,
                        1.0,
                        f"feature={feature_name}; strict_past_history_n={fmt(history_n)}; prior_slope={fmt(slope)}. "
                        "Direction is mathematical only; no practical-significance threshold is applied.",
                        engine_version,
                    )
                )

        expected = len(player_matches) * (2 + 2 * len(feature_names))
        if len(rows) != expected:
            raise RuntimeError(f"Expected {expected} decision rows, built {len(rows)}")

        con.execute("DELETE FROM decision_results WHERE engine_version = ?", [engine_version])
        con.executemany(
            """
            INSERT INTO decision_results (
                decision_id, match_id, player_id, node_id, result_type,
                result_value, confidence, justification, engine_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        written = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?",
            [engine_version],
        ).fetchone()[0]
        families = con.execute(
            """
            SELECT substr(node_id, 1, 5) AS family, COUNT(*)
            FROM decision_results
            WHERE engine_version = ?
            GROUP BY 1 ORDER BY 1
            """,
            [engine_version],
        ).fetchall()

    print("EXPERT-01 build complete")
    print(f"engine_version: {engine_version}")
    print(f"player_match rows: {len(player_matches)}")
    print(f"base features: {len(feature_names)}")
    print(f"decision rows written: {written}")
    print("family rows: " + ", ".join(f"{name}={count}" for name, count in families))
    print("No ratings, arbitrary thresholds, good/bad labels or recommendations were created.")


if __name__ == "__main__":
    main()
