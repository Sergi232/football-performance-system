"""EXPERT-03: N8000 team context + N9000 optional physical-data gate."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
CATALOG = Path(__file__).with_name("context_catalog.json")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def decision_id(engine_version: str, match_id: str, player_id: str, node_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:decision:{engine_version}:{match_id}:{player_id}:{node_id}"))


def classify_venue(is_home: bool | None) -> str:
    if is_home is True:
        return "HOME"
    if is_home is False:
        return "AWAY"
    return "VENUE_UNKNOWN"


def classify_result(score_for: int | None, score_against: int | None) -> str:
    if score_for is None or score_against is None:
        return "RESULT_UNKNOWN"
    if int(score_for) > int(score_against):
        return "WIN"
    if int(score_for) < int(score_against):
        return "LOSS"
    return "DRAW"


def classify_goal_difference(score_for: int | None, score_against: int | None) -> str:
    if score_for is None or score_against is None:
        return "GOAL_DIFFERENCE_UNKNOWN"
    diff = int(score_for) - int(score_against)
    if diff > 0:
        return "POSITIVE"
    if diff < 0:
        return "NEGATIVE"
    return "ZERO"


def classify_formation(starting_formation: str | None) -> str:
    if starting_formation is None or not str(starting_formation).strip():
        return "FORMATION_UNKNOWN"
    return str(starting_formation).strip()


def classify_gps(observation_count: int | None) -> str:
    return "GPS_OBSERVED" if int(observation_count or 0) > 0 else "GPS_NOT_AVAILABLE"


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    catalog = load_json(CATALOG)
    engine_version = catalog["engine_version"]
    parent_version = catalog["parent_engine_version"]
    nodes = {n["node_id"]: n for n in catalog["nodes"]}

    with duckdb.connect(str(DB)) as con:
        player_matches = con.execute(
            """
            SELECT pm.match_id, pm.team_id, pm.player_id,
                   tm.is_home, tm.starting_formation, tm.score_for, tm.score_against
            FROM player_match pm
            LEFT JOIN team_match tm
              ON tm.match_id = pm.match_id AND tm.team_id = pm.team_id
            ORDER BY pm.match_id, pm.player_id
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
            raise RuntimeError(f"EXPERT-03 requires validated parent engine {parent_version}")

        # N9000 is an evidence gate for observed GPS only. Synthetic demo rows are
        # deliberately excluded so demo data can never become expert evidence.
        gps_counts = dict(
            ((m, p), n)
            for m, p, n in con.execute(
                """
                SELECT go.match_id, go.player_id, COUNT(*)
                FROM gps_observations go
                JOIN gps_imports gi ON gi.gps_import_id = go.gps_import_id
                WHERE lower(coalesce(gi.provider, '')) <> 'fps synthetic demo'
                  AND lower(coalesce(gi.source_format, '')) <> 'synthetic_demo'
                GROUP BY 1,2
                """
            ).fetchall()
        )

        rows: list[tuple] = []
        for match_id, player_id, node_id, result_type, result_value, confidence, justification in parent_rows:
            rows.append((
                decision_id(engine_version, match_id, player_id, node_id), match_id, player_id,
                node_id, result_type, result_value, float(confidence), justification, engine_version,
            ))

        for match_id, team_id, player_id, is_home, formation, score_for, score_against in player_matches:
            context = [
                ("N8000.100", classify_venue(is_home),
                 f"Observed own-team venue context from team_match.is_home={is_home}. No opponent analytics used."),
                ("N8000.110", classify_result(score_for, score_against),
                 f"Observed own-team match result from score_for={score_for}, score_against={score_against}. This is factual match context, not a player-performance judgement."),
                ("N8000.120", classify_goal_difference(score_for, score_against),
                 f"Observed own-team goal-difference sign from score_for={score_for}, score_against={score_against}. No threshold beyond exact sign."),
                ("N8000.130", classify_formation(formation),
                 f"Observed starting_formation={formation if formation is not None else 'NULL'}. Missing formation remains explicit; no formation is inferred."),
            ]
            for node_id, value, justification in context:
                node = nodes[node_id]
                rows.append((
                    decision_id(engine_version, match_id, player_id, node_id), match_id, player_id,
                    node_id, node["result_type"], value, 1.0, justification, engine_version,
                ))

            gps_n = int(gps_counts.get((match_id, player_id), 0))
            node_id = "N9000.100"
            node = nodes[node_id]
            rows.append((
                decision_id(engine_version, match_id, player_id, node_id), match_id, player_id,
                node_id, node["result_type"], classify_gps(gps_n), 1.0,
                f"Observed non-synthetic normalized gps_observations for this player-match={gps_n}. Synthetic demo GPS is excluded from expert evidence. No physical value is estimated when observed GPS is absent; no sprint/HIE/load threshold is applied.",
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
        con.register("_expert_stage3_rows", frame)
        con.execute(
            """
            INSERT INTO decision_results (
                decision_id, match_id, player_id, node_id, result_type,
                result_value, confidence, justification, engine_version
            )
            SELECT decision_id, match_id, player_id, node_id, result_type,
                   result_value, confidence, justification, engine_version
            FROM _expert_stage3_rows
            """
        )
        con.unregister("_expert_stage3_rows")

        written = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?", [engine_version]
        ).fetchone()[0]
        families = con.execute(
            """
            SELECT regexp_extract(node_id, '^(N[0-9]+)', 1) AS family, COUNT(*)
            FROM decision_results WHERE engine_version = ?
            GROUP BY 1 ORDER BY 1
            """, [engine_version]
        ).fetchall()
        gps_observed = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id = 'N9000.100' AND result_value = 'GPS_OBSERVED'
            """, [engine_version]
        ).fetchone()[0]

    print("EXPERT-03 build complete")
    print(f"engine_version: {engine_version}")
    print(f"parent_engine_version: {parent_version}")
    print(f"player_match rows: {len(player_matches)}")
    print(f"new nodes per player-match: {len(nodes)}")
    print(f"decision rows written: {written}")
    print("family rows: " + ", ".join(f"{name}={count}" for name, count in families))
    print(f"player-match rows with observed non-synthetic GPS: {gps_observed}")
    print("N8000 uses own-team context only; N9000 degrades explicitly when observed GPS is absent and ignores synthetic demo GPS.")


if __name__ == "__main__":
    main()
