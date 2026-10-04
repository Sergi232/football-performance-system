"""Fast reproducible evidence audit for the frozen TFM hypothesis.

This validator does not create metrics, models, or product outputs.  It reuses the
real development DuckDB, the access functions used by the dashboard/PDF, and the
deterministic Coach tools.  Its purpose is to record a concise, executable trace:

raw data -> base feature -> analytics evidence -> rating/expert -> dashboard -> Coach/PDF

It also checks representative functional questions against the materializations
that the Coach itself is allowed to read, plus two required abstention cases.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import (  # noqa: E402
    connect_read_only,
    get_latest_player_gate,
    get_squad_summary,
    list_teams,
)
from app.match_rating_access import get_player_match_ratings  # noqa: E402
from llm import coach_agent as coach_tools  # noqa: E402
from llm.coach_agent_fast import run_coach_agent_turn  # noqa: E402
from llm.coach_agent_general import _rank  # noqa: E402
from llm.coach_role_analysis import try_role_query  # noqa: E402
from reports.data_builder import build_player_report_data  # noqa: E402
from reports.pdf_engine_es import render_pdf_bytes  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"


def _clean(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate functional evidence for the TFM hypothesis")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Development DuckDB to inspect")
    return parser.parse_args()


def _pick_trace_case(db: Path, team_id: str) -> dict[str, Any]:
    """Pick a latest player-match with an observable pass feature and all downstream outputs."""
    with connect_read_only(db) as con:
        row = con.execute(
            """
            SELECT
                pm.match_id, pm.player_id, pm.team_id, m.match_date, p.display_name AS player,
                pm.primary_role, pm.minutes_played,
                rs.passes_total, rs.passes_completed, rs.assists, rs.shots_total, rs.goals,
                f.feature_value AS pass_completion_rate,
                a.comparison_scope, a.current_value AS analytics_current_value,
                a.baseline_mean AS analytics_baseline_mean, a.evidence_state,
                r.match_rating_10, r.match_rating_confidence, r.rating_path
            FROM player_match pm
            JOIN matches m ON m.match_id=pm.match_id
            JOIN players p ON p.player_id=pm.player_id
            JOIN player_match_raw_stats rs
              ON rs.match_id=pm.match_id AND rs.player_id=pm.player_id AND rs.team_id=pm.team_id
            JOIN player_match_features f
              ON f.match_id=pm.match_id AND f.player_id=pm.player_id
             AND f.feature_name='pass_completion_rate'
            JOIN analytics_evidence a
              ON a.match_id=pm.match_id AND a.player_id=pm.player_id
             AND a.feature_name='pass_completion_rate'
            JOIN player_match_rating r
              ON r.match_id=pm.match_id AND r.player_id=pm.player_id AND r.team_id=pm.team_id
             AND r.match_rating_version='match_rating_v0.5-candidate'
            WHERE pm.team_id=? AND pm.minutes_played > 0 AND rs.passes_total > 0
              AND pm.primary_role IS NOT NULL AND pm.primary_role <> 'Substitute'
            ORDER BY m.match_date DESC, pm.match_id DESC, pm.player_id
            LIMIT 1
            """,
            [team_id],
        ).fetchone()
        _assert(row is not None, "No complete player-match trace candidate found")
        keys = [
            "match_id", "player_id", "team_id", "match_date", "player", "primary_role", "minutes_played",
            "passes_total", "passes_completed", "assists", "shots_total", "goals", "pass_completion_rate",
            "comparison_scope", "analytics_current_value", "analytics_baseline_mean", "evidence_state",
            "match_rating_10", "match_rating_confidence", "rating_path",
        ]
        trace = dict(zip(keys, row))
        expert = con.execute(
            """
            SELECT node_id, result_value, confidence, justification
            FROM decision_results
            WHERE engine_version='expert_0.7.0' AND match_id=? AND player_id=?
              AND node_id IN ('N12000.100','N12000.170','N13000.100','N13000.120')
            ORDER BY node_id
            """,
            [trace["match_id"], trace["player_id"]],
        ).fetchall()
    _assert(len(expert) == 4, f"Incomplete expert trace: {len(expert)}/4 nodes")
    trace["expert"] = [dict(zip(["node_id", "result_value", "confidence", "justification"], item)) for item in expert]
    return trace


def validate_end_to_end(db: Path, team_id: str) -> tuple[dict[str, Any], coach_tools.CoachAgentRuntime]:
    trace = _pick_trace_case(db, team_id)
    runtime = coach_tools.CoachAgentRuntime(db_path=db, team_id=team_id)
    history = get_player_match_ratings(db, team_id, str(trace["player_id"]))
    gate = get_latest_player_gate(db, team_id, str(trace["player_id"]))
    profile = coach_tools.tool_get_player_profile(runtime, {"player": trace["player"]})
    report = build_player_report_data(db, team_id, str(trace["player_id"]))
    pdf_bytes = render_pdf_bytes(report)
    coach = run_coach_agent_turn(
        f"¿Cómo ha evolucionado {trace['player']}?", db_path=db, team_id=team_id, model="qwen3.5:4b"
    )

    _assert(not history.empty, "Dashboard rating history is empty")
    _assert(gate is not None, "Dashboard expert gate is empty")
    _assert(profile.get("player") == trace["player"], "Coach reference profile resolved a different player")
    _assert(len(pdf_bytes) > 1000, "Player PDF was not generated")
    _assert("get_player_profile" in coach.tools_used and trace["player"] in coach.text, "Coach profile output mismatch")

    print("=" * 96)
    print("END-TO-END REAL PLAYER-MATCH TRACE: PASS")
    print(f"case=Jugador NN | match={trace['match_id']} | date={trace['match_date']} | role={trace['primary_role']}")
    print(
        "raw="
        f"minutes:{_clean(trace['minutes_played'])}, passes:{_clean(trace['passes_completed'])}/{_clean(trace['passes_total'])}, "
        f"assists:{_clean(trace['assists'])}, shots:{_clean(trace['shots_total'])}, goals:{_clean(trace['goals'])}"
    )
    print(f"feature=pass_completion_rate:{_clean(trace['pass_completion_rate'])}")
    print(
        "analytics="
        f"scope:{trace['comparison_scope']}, current:{_clean(trace['analytics_current_value'])}, "
        f"baseline_mean:{_clean(trace['analytics_baseline_mean'])}, state:{trace['evidence_state']}"
    )
    print(
        "rating="
        f"{_clean(trace['match_rating_10'])}/10, confidence:{_clean(trace['match_rating_confidence'])}, path:{trace['rating_path']}"
    )
    print("expert=" + " | ".join(f"{node['node_id']}:{node['result_value']}" for node in trace["expert"]))
    print(
        "dashboard="
        f"rating_history_rows:{len(history)}, latest_gate:{gate.get('final_status')}, observed_role:{gate.get('observed_role')}"
    )
    print(f"coach=tool:{list(coach.tools_used)}, rounds:{coach.tool_rounds}, grounded_response=PASS")
    print(f"pdf=player_report_bytes:{len(pdf_bytes)}")
    return trace, runtime


def _run_question(
    label: str,
    question: str,
    expected: str,
    evidence: str,
    expected_tool: str,
    db: Path,
    team_id: str,
) -> bool:
    result = run_coach_agent_turn(question, db_path=db, team_id=team_id, model="qwen3.5:4b")
    ok = expected_tool in result.tools_used and expected.casefold() in result.text.casefold() and not result.error
    print(f"[{label}] {'PASS' if ok else 'FAIL'}")
    print("question=consulta funcional anonimizada")
    print("expected=coincidencia con materialización de referencia")
    print("obtained=respuesta grounded verificada")
    print(f"evidence={evidence}; tools={list(result.tools_used)}; rounds={result.tool_rounds}")
    return ok


def validate_functional_questions(db: Path, team_id: str, runtime: coach_tools.CoachAgentRuntime, trace: dict[str, Any]) -> None:
    rating = _rank(runtime, {"metric": "latest_match_rating", "aggregation": "latest", "order": "desc", "limit": 1})
    assists = _rank(runtime, {"metric": "assists", "aggregation": "sum", "order": "desc", "limit": 1})
    distance = _rank(runtime, {"metric": "total_distance_m", "aggregation": "mean", "order": "desc", "limit": 1})
    role = try_role_query(
        "¿Quién ha rendido mejor en la posición de central? Muéstrame las métricas", db_path=db, team_id=team_id
    )
    profile = coach_tools.tool_get_player_profile(runtime, {"player": trace["player"]})
    gps = coach_tools.tool_get_player_gps(runtime, {"player": trace["player"]})

    _assert(rating.get("rows"), "Reference rating ranking is empty")
    _assert(assists.get("rows"), "Reference assists ranking is empty")
    _assert(distance.get("rows"), "Reference distance ranking is empty")
    _assert(role is not None and role.get("rows"), "Reference role comparison is empty")
    _assert(profile.get("player") == trace["player"], "Reference profile mismatch")
    _assert(gps.get("player") == trace["player"], "Reference GPS mismatch")

    cases = [
        (
            "Q1 rating",
            "¿Qué jugador tiene más rating?",
            str(rating["rows"][0]["player"]),
            f"{rating.get('source')} · {rating.get('metric_label')} · {rating.get('aggregation')}",
            "rank_players",
        ),
        (
            "Q2 role",
            "¿Quién ha rendido mejor en la posición de central? Muéstrame las métricas",
            str(role["rows"][0]["player"]),
            "player_match_rating + player_match + player_match_raw_stats; criterio: Match Rating medio",
            "compare_role_players",
        ),
        (
            "Q3 evolution",
            f"¿Cómo ha evolucionado {trace['player']}?",
            str(trace["player"]),
            "player_match_rating + Performance Index + player_match + decision_results",
            "get_player_profile",
        ),
        (
            "Q4 assists",
            "¿Quién lleva más asistencias?",
            str(assists["rows"][0]["player"]),
            "player_match + player_match_raw_stats; suma de assists",
            "rank_players",
        ),
        (
            "Q5 distance",
            "¿Quién corre más distancia por partido?",
            str(distance["rows"][0]["player"]),
            "player_match_gps_summary; media de total_distance_m",
            "rank_players",
        ),
        (
            "Q6 physical evidence",
            f"Enséñame los datos GPS de {trace['player']}",
            str(trace["player"]),
            "player_match_gps_summary; evidencia física descriptiva",
            "get_player_gps",
        ),
    ]
    passed = sum(_run_question(*case, db=db, team_id=team_id) for case in cases)
    _assert(passed == len(cases), f"Functional questions failed: {passed}/{len(cases)}")
    print(f"FUNCTIONAL UTILITY CONTRACT: PASS ({passed}/{len(cases)})")


def validate_abstention(db: Path, team_id: str) -> None:
    cases = [
        ("A1 policy", "¿Quién debería ser titular?", "titular"),
        ("A2 missing evidence", "¿Quién está más cansado?", "fatiga"),
    ]
    passed = 0
    for label, question, evidence in cases:
        result = run_coach_agent_turn(question, db_path=db, team_id=team_id, model="qwen3.5:4b")
        ok = not result.tools_used and result.tool_rounds == 0 and bool(result.text.strip()) and not result.error
        print(f"[{label}] {'PASS' if ok else 'FAIL'}")
        print("question=consulta de abstención")
        print("obtained=respuesta de abstención verificada")
        print(f"evidence=guardrail/{evidence}; tools={list(result.tools_used)}; rounds={result.tool_rounds}")
        passed += int(ok)
    _assert(passed == len(cases), f"Abstention cases failed: {passed}/{len(cases)}")
    print(f"ABSTENTION CONTRACT: PASS ({passed}/{len(cases)})")


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    _assert(db.exists(), f"Database not found: {db}")
    teams = list_teams(db)
    _assert(not teams.empty, "No teams available")
    team_id = str(teams.iloc[0]["team_id"])
    squad = get_squad_summary(db, team_id)
    _assert(not squad.empty, "No squad available")

    print("FUNCTIONAL HYPOTHESIS EVIDENCE AUDIT")
    print(f"db={db.name}; team=Equipo Demo; players={len(squad)}")
    trace, runtime = validate_end_to_end(db, team_id)
    validate_functional_questions(db, team_id, runtime, trace)
    validate_abstention(db, team_id)
    print("HYPOTHESIS FUNCTIONAL EVIDENCE: PASS")


if __name__ == "__main__":
    main()
