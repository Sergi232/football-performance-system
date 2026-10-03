"""End-to-end local validation for the hybrid Qwen Coach Copilot runtime."""
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
            "num_ctx": int(os.environ.get("FPS_AGENT_ROUTER_CTX", "1024")),
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


def _run_case(label: str, question: str, *, db_path: Path, team_id: str, model: str, expected_tools: set[str], expected_text: str | None = None, history: list[dict] | None = None) -> tuple[bool, float, object]:
    start = time.monotonic()
    try:
        result = run_coach_agent_turn(question, db_path=db_path, team_id=team_id, history=history, model=model)
    except Exception as exc:
        elapsed = time.monotonic() - start
        print(f"{label}: FAIL elapsed={elapsed:.1f}s exception={type(exc).__name__}: {exc}")
        return False, elapsed, None
    elapsed = time.monotonic() - start
    tools = set(result.tools_used)
    tool_ok = tools == expected_tools
    text_ok = bool(result.text.strip()) and (expected_text is None or expected_text in result.text.casefold())
    error_ok = result.error is None
    ok = tool_ok and text_ok and error_ok
    print(f"{label}: {'PASS' if ok else 'FAIL'} elapsed={elapsed:.1f}s tools={sorted(tools)} rounds={result.tool_rounds}")
    if not ok:
        print("answer=" + result.text.replace("\n", " ")[:500])
        if result.error:
            print("error=" + str(result.error)[:300])
    return ok, elapsed, result


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
    player2 = str(squad.iloc[1]["player"]) if len(squad) > 1 else player
    opponent = str(matches.iloc[0]["opponent"])
    model = os.environ.get("FPS_LOCAL_LLM_MODEL", DEFAULT_MODEL)
    status = _wait_for_ollama()

    print("LOCAL AGENT VALIDATION V4")
    print(f"team={team_name}")
    print(f"model={model}")
    print("runtime=deterministic high-confidence router + Qwen semantic fallback + read-only tools + deterministic factual answers")

    if not status.get("available"):
        raise SystemExit("LOCAL AGENT CONTRACT: FAIL (Ollama unavailable)")
    if model not in (status.get("models") or []):
        raise SystemExit(f"LOCAL AGENT CONTRACT: FAIL (run: ollama pull {model})")

    _warmup(model)

    cases = [
        ("rating_rank", "que jugador tiene mas rating", {"rank_players"}, None),
        ("gps_distance_rank", "que jugador corre más distancia por partido", {"rank_players"}, None),
        ("max_goals", "quien tiene mas goles", {"rank_players"}, None),
        ("max_assists", "quien lleva mas asistencias", {"rank_players"}, None),
        ("player_evolution", f"como ha evolucionado {player}", {"get_player_profile"}, None),
        ("player_gps", f"enseñame el gps de {player}", {"get_player_gps"}, None),
        ("compare_players", f"compara {player} con {player2}", {"compare_players"}, None),
        ("match_detail", f"que paso contra {opponent}", {"get_match_detail"}, None),
        ("team_state", "como esta el equipo recientemente", {"get_team_snapshot"}, None),
        ("quality", "que limitaciones de datos tenemos", {"get_data_quality"}, None),
        ("fatigue", "quien esta mas cansado", set(), "no puedo determinar"),
        # This wording deliberately avoids deterministic cue words and therefore checks Qwen routing.
        ("semantic_qwen_profile", f"ponme al dia sobre {player}", {"get_player_profile"}, None),
        ("unknown", "explicame la teoria de juegos", set(), "no tengo una consulta validada"),
    ]

    passed = 0
    elapsed_values: list[float] = []
    for label, question, expected_tools, expected_text in cases:
        ok, elapsed, _ = _run_case(
            label,
            question,
            db_path=db_path,
            team_id=team_id,
            model=model,
            expected_tools=expected_tools,
            expected_text=expected_text,
        )
        passed += int(ok)
        elapsed_values.append(elapsed)

    # Conversation contract: a ranking must support ordinal and evidence follow-ups
    # without needing another semantic interpretation of the original question.
    base_question = "que jugador corre más distancia por partido"
    ok_base, elapsed, base = _run_case(
        "followup_base",
        base_question,
        db_path=db_path,
        team_id=team_id,
        model=model,
        expected_tools={"rank_players"},
    )
    passed += int(ok_base)
    elapsed_values.append(elapsed)

    if base is not None:
        history = [
            {"role": "user", "content": base_question},
            {"role": "assistant", "content": base.text},
        ]
        ok_second, elapsed, second = _run_case(
            "followup_second",
            "y el segundo?",
            db_path=db_path,
            team_id=team_id,
            model=model,
            expected_tools={"rank_players"},
            history=history,
        )
        passed += int(ok_second)
        elapsed_values.append(elapsed)
        history.extend([
            {"role": "user", "content": "y el segundo?"},
            {"role": "assistant", "content": second.text if second is not None else ""},
        ])
        ok_evidence, elapsed, _ = _run_case(
            "followup_evidence",
            "que evidencias tienes?",
            db_path=db_path,
            team_id=team_id,
            model=model,
            expected_tools={"rank_players"},
            expected_text="python/duckdb",
            history=history,
        )
        passed += int(ok_evidence)
        elapsed_values.append(elapsed)
    else:
        passed += 0
        elapsed_values.extend([0.0, 0.0])

    total = len(cases) + 3
    avg = sum(elapsed_values) / len(elapsed_values) if elapsed_values else 0.0
    print(f"average_elapsed={avg:.1f}s")
    print(f"LOCAL AGENT CONTRACT: {'PASS' if passed == total else 'FAIL'} ({passed}/{total})")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
