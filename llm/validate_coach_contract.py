"""Reproducible deterministic Coach Copilot query-space validation.

This gate intentionally avoids LLM-dependent cases. It validates the common product
contract, follow-ups, guardrails, non-domain preflight and demo identity boundary on
a reproducible DuckDB.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.assistant_identity import build_assistant_identity_context
from app.data_access import get_squad_summary, get_team_matches, list_teams
from app.presentation import display_team_name
from llm.coach_agent_fast import run_coach_agent_turn

DEFAULT_DB = ROOT / "data" / "football_performance_synthetic_demo.duckdb"
MODEL = "qwen3.5:4b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate deterministic Coach Copilot contract")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    return parser.parse_args()


def _run(question: str, *, db: Path, team_id: str, expected_tool: str | None, history=None, blocked: bool = False):
    result = run_coach_agent_turn(question, db_path=db, team_id=team_id, model=MODEL, history=history)
    tools = list(result.tools_used)
    if blocked:
        ok = not tools and result.tool_rounds == 0 and bool(result.text.strip())
    else:
        ok = expected_tool in tools and result.tool_rounds == 0 and bool(result.text.strip())
    return ok, result


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    if not db.exists():
        raise SystemExit(f"Database not found: {db}")

    os.environ["FPS_DEMO_MODE"] = "1"
    teams = list_teams(db)
    if teams.empty:
        raise SystemExit("No teams in validation DB")
    team_id = str(teams.iloc[0]["team_id"])
    raw_team_name = str(teams.iloc[0]["display_name"])
    team_alias = display_team_name(raw_team_name, 1)
    squad = get_squad_summary(db, team_id)
    matches = get_team_matches(db, team_id)
    if squad.empty or matches.empty:
        raise SystemExit("Validation DB needs squad and matches")

    players = squad["player"].dropna().astype(str).tolist()
    p1, p2 = players[0], players[1]
    opponent = str(matches.iloc[0]["opponent"])
    identity = build_assistant_identity_context(squad, matches, raw_team_name=raw_team_name, team_alias=team_alias)

    cases = [
        ("rating", "¿Qué jugador tiene más rating?", "rank_players"),
        ("rating_l5", "¿Quién tiene mejor rating medio en los últimos 5 partidos?", "rank_players"),
        ("goals", "¿Quién tiene más goles?", "rank_players"),
        ("assists", "¿Quién lleva más asistencias?", "rank_players"),
        ("shots", "Dame el top 3 de jugadores con más remates", "rank_players"),
        ("passes", "¿Quién tiene más pases completados?", "rank_players"),
        ("tackles", "¿Quién tiene más entradas ganadas?", "rank_players"),
        ("interceptions", "¿Quién tiene más intercepciones?", "rank_players"),
        ("minutes", "¿Quién ha jugado más minutos?", "rank_players"),
        ("distance", "¿Quién corre más distancia por partido?", "rank_players"),
        ("speed", "¿Quién tiene mayor velocidad máxima?", "rank_players"),
        ("profile", f"¿Cómo ha evolucionado {p1}?", "get_player_profile"),
        ("profile_natural", f"Ponme al día sobre {p1}", "get_player_profile"),
        ("gps", f"Enséñame los datos GPS de {p1}", "get_player_gps"),
        ("compare", f"Compara {p1} con {p2}", "compare_players"),
        ("match", f"¿Qué pasó contra {opponent}?", "get_match_detail"),
        ("team", "¿Cómo está el equipo últimamente?", "get_team_snapshot"),
        ("quality", "¿Qué limitaciones tienen los datos?", "get_data_quality"),
        ("role_st", "Compárame las principales estadísticas de los delanteros", "compare_role_players"),
        ("role_cb", "¿Quién ha rendido mejor en la posición de central? Muéstrame las métricas", "compare_role_players"),
        ("role_fb", "Compara las métricas de los laterales", "compare_role_players"),
        ("role_dm", "¿Cómo están rindiendo los mediocentros defensivos?", "compare_role_players"),
        ("role_cm", "Compárame a los interiores", "compare_role_players"),
        ("role_am", "Muéstrame las métricas de los mediapuntas", "compare_role_players"),
        ("role_w", "Compara las estadísticas de los extremos", "compare_role_players"),
        ("role_gk", "¿Quién ha rendido mejor entre los porteros?", "compare_role_players"),
        ("role_window", "¿Quién ha rendido mejor como delantero en los últimos 5 partidos?", "compare_role_players"),
    ]

    failures: list[str] = []
    print("=" * 88)
    print("COACH COPILOT QUERY-SPACE CONTRACT")
    print(f"team={team_alias} db={db.name}")
    print("=" * 88)

    for label, question, tool in cases:
        ok, result = _run(question, db=db, team_id=team_id, expected_tool=tool)
        print(f"{label:18} {'PASS' if ok else 'FAIL'} tools={list(result.tools_used)} rounds={result.tool_rounds}")
        if not ok:
            failures.append(label)

    blocked_cases = [
        ("fatigue", "¿Quién está más cansado?"),
        ("injury", "¿Quién tiene más riesgo de lesión?"),
        ("lineup", "¿Quién debería ser titular?"),
        ("best_general", "¿Quién es el mejor jugador del equipo?"),
        ("complete", "¿Quién es el jugador más completo?"),
        ("decisive", "¿Quién es el más determinante?"),
        ("garbage", "sss"),
        ("meta_help", "no puedes hacer nada"),
        ("out_domain", "Explícame la teoría de juegos"),
    ]
    for label, question in blocked_cases:
        ok, result = _run(question, db=db, team_id=team_id, expected_tool=None, blocked=True)
        print(f"{label:18} {'PASS' if ok else 'FAIL'} tools={list(result.tools_used)} rounds={result.tool_rounds}")
        if not ok:
            failures.append(label)

    history: list[dict[str, str]] = []
    chain = [
        ("follow_base", "¿Quién corre más distancia por partido?"),
        ("follow_second", "¿Y el segundo?"),
        ("follow_window", "¿Y en los últimos 5 partidos?"),
        ("follow_evidence", "¿Qué evidencias tienes?"),
    ]
    for label, question in chain:
        ok, result = _run(question, db=db, team_id=team_id, expected_tool="rank_players", history=history)
        print(f"{label:18} {'PASS' if ok else 'FAIL'} tools={list(result.tools_used)} rounds={result.tool_rounds}")
        if not ok:
            failures.append(label)
        history.extend([{"role": "user", "content": question}, {"role": "assistant", "content": result.text}])

    role_history = [
        {"role": "user", "content": "Compárame las principales estadísticas de los centrales"},
        {"role": "assistant", "content": "comparación previa"},
        {"role": "user", "content": "no puedes hacer nada"},
        {"role": "assistant", "content": "limitación"},
    ]
    ok, role_follow = _run("Sí, compáralos", db=db, team_id=team_id, expected_tool="compare_role_players", history=role_history)
    print(f"{'role_followup':18} {'PASS' if ok else 'FAIL'} tools={list(role_follow.tools_used)} rounds={role_follow.tool_rounds}")
    if not ok:
        failures.append("role_followup")

    player_aliases = sorted(alias for alias in identity.alias_to_runtime if alias.startswith("Jugador "))
    opponent_aliases = sorted(alias for alias in identity.alias_to_runtime if alias.startswith("Rival "))
    if not player_aliases or not opponent_aliases:
        failures.append("identity_maps_missing")
    else:
        alias = player_aliases[0]
        runtime_question = identity.to_runtime(f"¿Cómo ha evolucionado {alias}?")
        ok, alias_result = _run(runtime_question, db=db, team_id=team_id, expected_tool="get_player_profile")
        display_answer = identity.to_display(alias_result.text)
        privacy_ok = ok and alias in display_answer and not identity.leaked_runtime_identities(display_answer)
        print(f"{'identity_player':18} {'PASS' if privacy_ok else 'FAIL'} alias={alias}")
        if not privacy_ok:
            failures.append("identity_player")

        opp_alias = opponent_aliases[0]
        runtime_question = identity.to_runtime(f"¿Qué pasó contra {opp_alias}?")
        ok, opp_result = _run(runtime_question, db=db, team_id=team_id, expected_tool="get_match_detail")
        display_answer = identity.to_display(opp_result.text)
        privacy_ok = ok and opp_alias in display_answer and not identity.leaked_runtime_identities(display_answer)
        print(f"{'identity_opponent':18} {'PASS' if privacy_ok else 'FAIL'} alias={opp_alias}")
        if not privacy_ok:
            failures.append("identity_opponent")

    _, raw_role = _run("Compárame las principales estadísticas de los delanteros", db=db, team_id=team_id, expected_tool="compare_role_players")
    display_role = identity.to_display(raw_role.text)
    privacy_ok = not identity.leaked_runtime_identities(display_role)
    print(f"{'identity_role':18} {'PASS' if privacy_ok else 'FAIL'}")
    if not privacy_ok:
        failures.append("identity_role")

    print("=" * 88)
    if failures:
        print("COACH COPILOT CONTRACT: FAIL")
        print("Failures: " + ", ".join(failures))
        raise SystemExit(1)
    print("COACH COPILOT CONTRACT: PASS")
    print("Core queries, follow-ups, guardrails, preflight and demo identities validated without LLM use.")
    print("=" * 88)


if __name__ == "__main__":
    main()
