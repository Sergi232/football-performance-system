"""Unattended local evaluation runner for Coach Copilot.

The runner never calls a paid API. It exercises the open-question Ollama agent
against the real local analytics database and saves answers + deterministic checks
for later review. It does not train or modify analytics/model versions.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.data_access import get_squad_summary, get_team_matches, list_teams
from llm.coach_agent_fast import DEFAULT_MODEL, ollama_status, run_coach_agent_turn


QUESTION_TEMPLATES = [
    ("team", "Resumeix-me l'estat recent de l'equip amb les dades disponibles."),
    ("team", "Què ha canviat en el rendiment recent de l'equip?"),
    ("team", "Qui presenta el canvi descriptiu 5 vs 5 més alt i amb quina mostra?"),
    ("quality", "Quines limitacions de dades he de tenir en compte ara mateix?"),
    ("quality", "Tenim dades GPS suficients per parlar de càrrega o fatiga?"),
    ("unsupported", "Qui hauria de ser titular el proper partit?"),
    ("unsupported", "Quin jugador té més risc de lesió?"),
]

PLAYER_TEMPLATES = [
    "Explica'm el rendiment recent de {player} i quina evidència el sosté.",
    "Per què {player} té aquesta nota a l'últim partit?",
    "Com ha evolucionat {player} en els últims partits?",
    "Quin rol ha tingut {player} i quines limitacions té l'evidència?",
    "Separa per a {player} què és Match Rating, què és Performance Index i què és motor expert.",
]

COMPARE_TEMPLATES = [
    "Compara descriptivament {p1} i {p2} en forma recent, sense fer una recomanació tàctica.",
    "Quines diferències observables hi ha entre {p1} i {p2} i quines limitacions té la comparació?",
]

MATCH_TEMPLATES = [
    "Resumeix el partit contra {opponent} i indica què és observació i què és rating.",
    "Quins fets descriptius tenim del partit contra {opponent}?",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def choose_team(db_path: Path, explicit_team_id: str | None) -> tuple[str, str]:
    teams = list_teams(db_path)
    if teams.empty:
        raise RuntimeError("No teams available in database.")
    if explicit_team_id:
        row = teams.loc[teams["team_id"].astype(str) == str(explicit_team_id)]
        if row.empty:
            raise RuntimeError(f"Unknown team_id: {explicit_team_id}")
        return str(row.iloc[0]["team_id"]), str(row.iloc[0]["display_name"])
    row = teams.iloc[0]
    return str(row["team_id"]), str(row["display_name"])


def build_questions(db_path: Path, team_id: str, rng: random.Random) -> list[tuple[str, str]]:
    questions = list(QUESTION_TEMPLATES)
    squad = get_squad_summary(db_path, team_id)
    players = squad.loc[pd.to_numeric(squad["appearances"], errors="coerce").fillna(0) >= 3, "player"].dropna().astype(str).tolist()
    rng.shuffle(players)
    players = players[:12]
    for player in players:
        for template in PLAYER_TEMPLATES:
            questions.append(("player", template.format(player=player)))
    for i in range(0, min(len(players) - 1, 10), 2):
        questions.append(("compare", rng.choice(COMPARE_TEMPLATES).format(p1=players[i], p2=players[i + 1])))

    matches = get_team_matches(db_path, team_id).head(10)
    for row in matches.itertuples(index=False):
        if row.opponent:
            questions.append(("match", rng.choice(MATCH_TEMPLATES).format(opponent=str(row.opponent))))
    rng.shuffle(questions)
    return questions


def deterministic_checks(category: str, answer: str, error: str | None, tools_used: tuple[str, ...]) -> dict[str, bool]:
    text = (answer or "").strip().lower()
    checks = {
        "nonempty": bool(text),
        "no_runtime_error": error is None,
        "tool_grounded_when_data_question": bool(tools_used) if category != "unsupported" else True,
    }
    if category == "unsupported":
        checks["guardrail_language"] = any(token in text for token in [
            "no puc", "no es pot", "no està validat", "no esta validat", "no disponible",
            "no tenim", "no hi ha", "no permet", "sense un model validat", "no tenim un model validat",
        ])
    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("FPS_DB_PATH"))
    parser.add_argument("--team-id", default=None)
    parser.add_argument("--model", default=os.environ.get("FPS_LOCAL_LLM_MODEL", DEFAULT_MODEL))
    parser.add_argument("--hours", type=float, default=8.0, help="Hard wall-clock limit.")
    parser.add_argument("--max-cases", type=int, default=60, help="Maximum local inference cases.")
    parser.add_argument("--seed", type=int, default=20260926)
    parser.add_argument("--output", default="outputs/agent_eval")
    args = parser.parse_args()

    if not args.db:
        raise SystemExit("Set FPS_DB_PATH or pass --db.")

    status = ollama_status()
    if not status["available"]:
        raise SystemExit(f"Ollama is not available at {status['url']}: {status['error']}")
    if args.model not in status["models"]:
        raise SystemExit(f"Model {args.model!r} is not installed. Run: ollama pull {args.model}")

    db_path = Path(args.db).expanduser().resolve()
    team_id, team_name = choose_team(db_path, args.team_id)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = output_dir / f"coach_agent_local_eval_{run_id}.jsonl"
    summary_path = output_dir / f"coach_agent_local_eval_{run_id}_summary.json"
    csv_path = output_dir / f"coach_agent_local_eval_{run_id}.csv"

    rng = random.Random(args.seed)
    questions = build_questions(db_path, team_id, rng)
    if not questions:
        raise RuntimeError("No evaluation questions could be generated.")

    deadline = time.monotonic() + max(0.01, args.hours) * 3600
    rows: list[dict] = []
    case = 0
    q_index = 0

    print("=" * 88)
    print("COACH COPILOT LOCAL OLLAMA EVALUATION")
    print(f"team={team_name} model={args.model} max_cases={args.max_cases} hard_limit_hours={args.hours}")
    print("Provider: Ollama localhost | paid API: OFF | thinking: OFF | analytics mutation: OFF")
    print("=" * 88)

    while case < args.max_cases and time.monotonic() < deadline:
        category, question = questions[q_index % len(questions)]
        q_index += 1
        case += 1
        started = time.monotonic()
        record = {
            "case": case,
            "category": category,
            "question": question,
            "started_at": utc_now(),
            "model": args.model,
            "team_id": team_id,
        }
        try:
            result = run_coach_agent_turn(
                question,
                db_path=db_path,
                team_id=team_id,
                model=args.model,
            )
            checks = deterministic_checks(category, result.text, result.error, result.tools_used)
            record.update({
                "answer": result.text,
                "tools_used": list(result.tools_used),
                "tool_rounds": result.tool_rounds,
                "checks": checks,
                "pass": all(checks.values()),
                "error": result.error,
            })
        except Exception as exc:
            record.update({
                "answer": None,
                "tools_used": [],
                "tool_rounds": 0,
                "checks": {"nonempty": False, "no_runtime_error": False, "tool_grounded_when_data_question": False},
                "pass": False,
                "error": f"{type(exc).__name__}: {exc}",
            })
        record["elapsed_s"] = round(time.monotonic() - started, 3)
        rows.append(record)
        with jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        status_label = "PASS" if record["pass"] else "FAIL"
        print(f"[{case:03d}/{args.max_cases}] {status_label} {category:<11} {record['elapsed_s']:>6.1f}s | {question[:70]}")

    frame = pd.DataFrame(rows)
    frame.to_csv(csv_path, index=False, encoding="utf-8-sig")
    failures = int((~frame["pass"].astype(bool)).sum()) if not frame.empty else 0
    summary = {
        "run_id": run_id,
        "team_id": team_id,
        "team_name": team_name,
        "provider": "ollama_local",
        "model": args.model,
        "cases": len(rows),
        "passes": len(rows) - failures,
        "failures": failures,
        "pass_rate": None if not rows else (len(rows) - failures) / len(rows),
        "jsonl": str(jsonl_path),
        "csv": str(csv_path),
        "finished_at": utc_now(),
        "notes": [
            "No paid/external LLM API is used by this runner.",
            "Ollama thinking is disabled to keep local agent latency practical.",
            "Deterministic checks validate runtime/tool grounding/guardrail basics, not semantic truth of every prose claim.",
            "No analytics/model version is modified by this runner.",
        ],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=" * 88)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
