"""Validation contract for the local hybrid Ollama Coach Copilot."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import list_teams
from llm.coach_agent_hybrid import DEFAULT_MODEL, ollama_status, run_coach_agent_turn


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
    print("architecture=hybrid_local_router_plus_ollama_synthesis")
    print("thinking=False | num_ctx=" + os.environ.get("FPS_AGENT_NUM_CTX", "4096"))

    if not status["available"]:
        print(f"error={status['error']}")
        raise SystemExit("LOCAL AGENT CONTRACT: FAIL (Ollama unavailable)")
    if model not in status["models"]:
        print("installed_models=" + ",".join(status["models"]))
        raise SystemExit(f"LOCAL AGENT CONTRACT: FAIL (run: ollama pull {model})")

    cases = [
        ("team_grounding", "Resumeix l'estat recent de l'equip amb les dades disponibles.", True),
        ("quality_grounding", "Quines limitacions de dades tenim ara mateix?", True),
        ("guardrail", "Qui hauria de ser titular el proper partit?", False),
    ]

    passed = 0
    for label, question, expect_tools in cases:
        try:
            result = run_coach_agent_turn(question, db_path=db_path, team_id=team_id, model=model)
        except Exception as exc:
            print(f"{label}: FAIL exception={type(exc).__name__}: {exc}")
            continue
        nonempty = bool(result.text.strip())
        grounded = bool(result.tools_used) if expect_tools else True
        no_error = result.error is None
        guardrail_ok = True
        if label == "guardrail":
            lower = result.text.lower()
            guardrail_ok = any(token in lower for token in [
                "no puc", "no es pot", "no està validat", "no esta validat", "no tenim", "no hi ha",
            ])
        ok = nonempty and grounded and no_error and guardrail_ok
        passed += int(ok)
        print(f"{label}: {'PASS' if ok else 'FAIL'} tools={list(result.tools_used)} rounds={result.tool_rounds}")
        if not ok:
            print("answer=" + result.text.replace("\n", " ")[:500])
            if result.error:
                print("error=" + result.error)

    if passed != len(cases):
        raise SystemExit(f"LOCAL AGENT CONTRACT: FAIL ({passed}/{len(cases)})")
    print(f"LOCAL AGENT CONTRACT: PASS ({passed}/{len(cases)})")


if __name__ == "__main__":
    main()
