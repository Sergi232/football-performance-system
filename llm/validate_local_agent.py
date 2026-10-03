"""End-to-end local validation for the Granite Coach Copilot runtime."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import get_squad_summary, get_team_matches, list_teams
from llm.coach_agent_fast import DEFAULT_MODEL, DEFAULT_OLLAMA_URL, ollama_status, run_coach_agent_turn


def _warmup(model: str) -> None:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Responde exactamente: OK"}],
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0,
            "num_ctx": int(os.environ.get("FPS_AGENT_NUM_CTX", "1536")),
            "num_predict": 8,
        },
    }
    req = urllib.request.Request(
        f"{DEFAULT_OLLAMA_URL.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        response.read()


def _ollama_executable() -> str | None:
    found = shutil.which("ollama")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidate = Path(local) / "Programs" / "Ollama" / "ollama.exe"
        if candidate.exists():
            return str(candidate)
    return None


def _wait_for_ollama() -> dict:
    status = ollama_status()
    if status.get("available"):
        return status
    executable = _ollama_executable()
    if executable:
        kwargs: dict[str, object] = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            subprocess.Popen([executable, "serve"], **kwargs)
        except Exception:
            pass
    last = status
    for _ in range(6):
        time.sleep(3)
        last = ollama_status()
        if last.get("available"):
            return last
    return last


def main() -> None:
    db_raw = os.environ.get("FPS_DB_PATH")
    if not db_raw:
        raise SystemExit("Set FPS_DB_PATH before running this validator.")
    db_path = Path(db_raw).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    teams = list_teams(db_path)
    if teams.empty:
        raise SystemExit("No teams available in database.")
    team_id = str(teams.iloc[0]["team_id"])
    team_name = str(teams.iloc[0]["display_name"])
    squad = get_squad_summary(db_path, team_id)
    matches = get_team_matches(db_path, team_id)
    if squad.empty or matches.empty:
        raise SystemExit("Need squad and match data for validation.")

    player = str(squad.iloc[0]["player"])
    opponent = str(matches.iloc[0]["opponent"])
    model = os.environ.get("FPS_LOCAL_LLM_MODEL", DEFAULT_MODEL)
    status = _wait_for_ollama()

    print("LOCAL AGENT VALIDATION V2")
    print(f"team={team_name}")
    print(f"model={model}")
    print("runtime=model-driven tools + read-only data + numeric guard")

    if not status.get("available"):
        raise SystemExit("LOCAL AGENT CONTRACT: FAIL (Ollama unavailable)")
    if model not in (status.get("models") or []):
        raise SystemExit(f"LOCAL AGENT CONTRACT: FAIL (run: ollama pull {model})")

    _warmup(model)
    cases = [
        ("max_goals", "¿Quién es el máximo goleador?", {"query_team_stats"}, None),
        ("max_assists", "¿Quién lleva más asistencias?", {"query_team_stats"}, None),
        ("player_evolution", f"¿Cómo ha evolucionado {player} últimamente?", {"get_player_profile"}, None),
        ("player_gps", f"Enséñame los datos GPS de {player}.", {"get_player_gps"}, None),
        ("match_detail", f"¿Qué pasó contra {opponent}?", {"get_match_detail"}, None),
        ("team_state", "Resume el estado reciente del equipo.", {"get_team_snapshot"}, None),
        ("quality", "¿Qué limitaciones de datos tenemos?", {"get_data_quality"}, None),
        ("fatigue", "¿Quién presenta más cansancio para el próximo partido?", set(), "no puedo determinar"),
        ("unknown", "Explícame la teoría de juegos.", set(), "no tengo una consulta validada"),
    ]

    passed = 0
    elapsed_values: list[float] = []
    for label, question, expected_tools, expected_text in cases:
        start = time.monotonic()
        try:
            result = run_coach_agent_turn(question, db_path=db_path, team_id=team_id, model=model)
        except Exception as exc:
            print(f"{label}: FAIL exception={type(exc).__name__}: {exc}")
            continue
        elapsed = time.monotonic() - start
        elapsed_values.append(elapsed)
        tools = set(result.tools_used)
        tool_ok = tools == expected_tools
        text_ok = bool(result.text.strip()) and (expected_text is None or expected_text in result.text.casefold())
        error_ok = result.error is None or str(result.error).startswith("SYNTHESIS_FALLBACK")
        ok = tool_ok and text_ok and error_ok
        passed += int(ok)
        print(f"{label}: {'PASS' if ok else 'FAIL'} elapsed={elapsed:.1f}s tools={sorted(tools)}")
        if not ok:
            print("answer=" + result.text.replace("\n", " ")[:500])
            if result.error:
                print("error=" + str(result.error)[:300])

    avg = sum(elapsed_values) / len(elapsed_values) if elapsed_values else 0.0
    print(f"average_elapsed={avg:.1f}s")
    print(f"LOCAL AGENT CONTRACT: {'PASS' if passed == len(cases) else 'FAIL'} ({passed}/{len(cases)})")
    if passed != len(cases):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
