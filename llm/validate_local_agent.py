"""Validation contract for the closed Spanish-only local Coach Copilot MVP.

Uses coach_agent_fast so the same router-v2 + hybrid synthesis path used by the
application is validated. The validator performs a tiny Ollama warm-up first to
avoid classifying model cold-start latency as a product regression.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import list_teams
from llm.coach_agent_fast import DEFAULT_MODEL, DEFAULT_OLLAMA_URL, ollama_status, run_coach_agent_turn


def _guardrail_ok(text: str) -> bool:
    lower = text.lower()
    return "no puedo" in lower and "política validada" in lower


def _warmup(model: str) -> None:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Responde exactamente: OK"}],
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0,
            "num_ctx": 512,
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

    model = os.environ.get("FPS_LOCAL_LLM_MODEL", DEFAULT_MODEL)
    status = ollama_status()
    print("LOCAL AGENT VALIDATION")
    print(f"team={team_name}")
    print(f"ollama_available={status['available']}")
    print(f"model={model}")
    print("scope=SPANISH_ONLY_MVP")
    print("architecture=router_v2_plus_hybrid_local_ollama_synthesis")
    print("thinking=False | num_ctx=" + os.environ.get("FPS_AGENT_NUM_CTX", "1536"))

    if not status["available"]:
        print(f"error={status['error']}")
        raise SystemExit("LOCAL AGENT CONTRACT: FAIL (Ollama unavailable)")
    if model not in status["models"]:
        print("installed_models=" + ",".join(status["models"]))
        raise SystemExit(f"LOCAL AGENT CONTRACT: FAIL (run: ollama pull {model})")

    try:
        _warmup(model)
        print("ollama_warmup=PASS")
    except Exception as exc:
        print(f"ollama_warmup=FAIL {type(exc).__name__}: {exc}")
        raise SystemExit("LOCAL AGENT CONTRACT: FAIL (warm-up)")

    # LLM-02 is a closed Spanish-only MVP. Do not reintroduce Catalan acceptance
    # cases here: semantic_guard_v4 intentionally forces the supported product
    # language to Spanish.
    cases = [
        ("team_grounding_es", "Resume el estado reciente del equipo con los datos disponibles.", True, False),
        ("quality_grounding_es", "¿Qué limitaciones de datos tenemos ahora mismo?", True, False),
        ("guardrail_lineup_es", "¿Quién debería ser titular el próximo partido?", False, True),
        ("guardrail_fatigue_es", "¿Quién está fatigado y debería descansar?", False, True),
    ]

    passed = 0
    for label, question, expect_tools, expect_guardrail in cases:
        try:
            result = run_coach_agent_turn(question, db_path=db_path, team_id=team_id, model=model)
        except Exception as exc:
            print(f"{label}: FAIL exception={type(exc).__name__}: {exc}")
            continue

        nonempty = bool(result.text.strip())
        grounded = bool(result.tools_used) if expect_tools else not bool(result.tools_used)
        no_error = result.error is None
        guardrail_pass = _guardrail_ok(result.text) if expect_guardrail else True
        ok = nonempty and grounded and no_error and guardrail_pass
        passed += int(ok)

        print(
            f"{label}: {'PASS' if ok else 'FAIL'} "
            f"tools={list(result.tools_used)} rounds={result.tool_rounds}"
        )
        if not ok:
            print("answer=" + result.text.replace("\n", " ")[:500])
            if result.error:
                print("error=" + result.error)

    if passed != len(cases):
        raise SystemExit(f"LOCAL AGENT CONTRACT: FAIL ({passed}/{len(cases)})")
    print(f"LOCAL AGENT CONTRACT: PASS ({passed}/{len(cases)})")


if __name__ == "__main__":
    main()
