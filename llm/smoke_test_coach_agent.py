"""Reproducible UTF-8 smoke test for the local Coach Copilot.

Run from the repository root after setting FPS_DB_PATH and, optionally,
FPS_LOCAL_LLM_MODEL. Keeping the questions in a .py file avoids Windows PowerShell
here-string encoding corruption.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# When this file is executed directly (python llm/smoke_test_coach_agent.py),
# Python puts llm/ on sys.path rather than the repository root. Add the root before
# importing app.* or llm.* so the documented command works on Windows and Linux.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import get_squad_summary, get_team_matches, list_teams
from llm.coach_agent_fast import DEFAULT_MODEL, run_coach_agent_turn

DB = Path(os.environ.get("FPS_DB_PATH", ROOT / "data" / "football_performance.duckdb")).expanduser().resolve()
MODEL = os.environ.get("FPS_LOCAL_LLM_MODEL", DEFAULT_MODEL)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _pick(names: list[str], token: str, fallback: str) -> str:
    for name in names:
        if token.casefold() in name.casefold():
            return name
    return fallback


def _run(label: str, question: str, *, team_id: str, history=None, expected_tool: str | None = None, expect_blocked: bool = False):
    start = time.perf_counter()
    result = run_coach_agent_turn(
        question,
        db_path=DB,
        team_id=team_id,
        model=MODEL,
        history=history,
    )
    elapsed = time.perf_counter() - start
    tools = list(result.tools_used)
    if expect_blocked:
        ok = not tools and result.tool_rounds == 0 and bool(result.text.strip())
    elif expected_tool is None:
        ok = not tools and bool(result.text.strip())
    else:
        ok = expected_tool in tools and bool(result.text.strip())
    print(f"\n[{label}] {'PASS' if ok else 'FAIL'} {elapsed:.1f}s")
    print(f"P: {question}")
    print(f"R: {result.text}")
    print(f"tools={tools} rounds={result.tool_rounds} error={result.error}")
    return ok, elapsed, result


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"Database not found: {DB}")

    teams = list_teams(DB)
    if teams.empty:
        raise SystemExit("No teams available in database.")
    team_id = str(teams.iloc[0]["team_id"])
    team = str(teams.iloc[0]["display_name"])
    squad = get_squad_summary(DB, team_id)
    matches = get_team_matches(DB, team_id)
    if squad.empty or matches.empty:
        raise SystemExit("Need squad and match data for smoke test.")

    names = squad["player"].dropna().astype(str).tolist()
    p1 = _pick(names, "Sivera", names[0])
    p2 = _pick(names, "Guridi", names[1] if len(names) > 1 else names[0])
    opponent = str(matches.iloc[0]["opponent"])

    cases = [
        ("01 rating", "¿Qué jugador tiene más rating?", "rank_players", False),
        ("02 rating media", "¿Quién tiene mejor rating medio en los últimos 5 partidos?", "rank_players", False),
        ("03 distancia", "¿Quién corre más distancia por partido?", "rank_players", False),
        ("04 top remates", "Dame el top 3 de jugadores con más remates", "rank_players", False),
        ("05 asistencias", "¿Quién lleva más asistencias?", "rank_players", False),
        ("06 evolución", f"¿Cómo ha evolucionado {p1}?", "get_player_profile", False),
        ("07 perfil natural", f"Ponme al día sobre {p1}", "get_player_profile", False),
        ("08 GPS", f"Enséñame los datos GPS de {p1}", "get_player_gps", False),
        ("09 comparación", f"Compara {p1} con {p2}", "compare_players", False),
        ("10 partido", f"¿Qué pasó contra {opponent}?", "get_match_detail", False),
        ("11 equipo", "¿Cómo está el equipo últimamente?", "get_team_snapshot", False),
        ("12 calidad", "¿Qué limitaciones tienen los datos?", "get_data_quality", False),
        ("13 fatiga", "¿Quién está más cansado?", None, True),
        ("14 lesión", "¿Quién tiene más riesgo de lesión?", None, True),
        ("15 titular", "¿Quién debería ser titular?", None, True),
        ("16 completo", "¿Qué jugador es el más completo?", None, True),
        ("17 determinante", "¿Quién está siendo más determinante?", None, True),
        ("18 delanteros", "Compárame las principales estadísticas de los delanteros", "compare_role_players", False),
        ("19 centrales", "¿Quién ha rendido mejor en la posición de central? Muéstrame las métricas", "compare_role_players", False),
        ("20 fuera dominio", "Explícame la teoría de juegos", None, False),
    ]

    print("=" * 94)
    print("COACH COPILOT REAL SMOKE TEST · UTF-8")
    print(f"Equipo: {team}")
    print(f"Modelo: {MODEL}")
    print(f"DB: {DB}")
    print("=" * 94)

    passed = 0
    times: list[float] = []
    for label, question, expected_tool, blocked in cases:
        ok, elapsed, _ = _run(
            label,
            question,
            team_id=team_id,
            expected_tool=expected_tool,
            expect_blocked=blocked,
        )
        passed += int(ok)
        times.append(elapsed)

    print("\n" + "=" * 94)
    print("CONVERSACIÓN ENCADENADA")
    print("=" * 94)
    history: list[dict[str, str]] = []
    chain = [
        ("C1", "¿Quién corre más distancia por partido?"),
        ("C2", "¿Y el segundo?"),
        ("C3", "¿Y en los últimos 5 partidos?"),
        ("C4", "¿Qué evidencias tienes?"),
    ]
    for label, question in chain:
        ok, elapsed, result = _run(label, question, team_id=team_id, history=history, expected_tool="rank_players")
        passed += int(ok)
        times.append(elapsed)
        history.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": result.text},
        ])

    print("\n" + "=" * 94)
    print("FOLLOW-UP DE COMPARACIÓN POR POSICIÓN")
    print("=" * 94)
    role_history: list[dict[str, str]] = []
    role_base = "¿Quién ha rendido mejor en la posición de central? Muéstrame las métricas"
    ok, elapsed, role_result = _run("R1", role_base, team_id=team_id, history=role_history, expected_tool="compare_role_players")
    passed += int(ok)
    times.append(elapsed)
    role_history.extend([
        {"role": "user", "content": role_base},
        {"role": "assistant", "content": role_result.text},
    ])
    ok, elapsed, _ = _run("R2", "Sí, compáralos", team_id=team_id, history=role_history, expected_tool="compare_role_players")
    passed += int(ok)
    times.append(elapsed)

    total = len(cases) + len(chain) + 2
    average = sum(times) / len(times) if times else 0.0
    print("\n" + "=" * 94)
    print(f"SMOKE CONTRACT: {'PASS' if passed == total else 'FAIL'} ({passed}/{total})")
    print(f"average_elapsed={average:.1f}s")
    print("=" * 94)
    raise SystemExit(0 if passed == total else 1)


if __name__ == "__main__":
    main()