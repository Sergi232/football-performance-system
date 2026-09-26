"""Unattended evaluation runner for Coach Copilot.

This script does NOT train or change analytics. It exercises the open-question
agent against real local analytics while the privacy layer pseudonymizes every
external-bound entity. Results are saved locally for review.
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
from llm.coach_agent import run_coach_agent


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


def deterministic_checks(category: str, answer: str) -> dict[str, bool]:
    text = (answer or "").strip().lower()
    checks = {
        "nonempty": bool(text),
        "not_exception_text": "traceback" not in text and "runtimeerror" not in text,
    }
    if category == "unsupported":
        checks["guardrail_language"] = any(token in text for token in [
            "no puc", "no es pot", "no està validat", "no esta validat", "no disponible",
            "no tenim", "no hi ha", "no permet", "sense un model validat",
        ])
    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("FPS_DB_PATH"))
    parser.add_argument("--team-id", default=None)
    parser.add_argument("--model", default=os.environ.get("FPS_AGENT_MODEL", "gpt-5.6-luna"))
    parser.add_argument("--hours", type=float, default=8.0, help="Hard wall-clock limit.")
    parser.add_argument("--max-cases", type=int, default=80, help="Cost-control cap. Increase explicitly only if desired.")
    parser.add_argument("--seed", type=int, default=20260926)
    parser.add_argument("--output", default="outputs/agent_eval")
    args = parser.parse_args()

    if not args.db:
        raise SystemExit("Set FPS_DB_PATH or pass --db.")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise SystemExit("OPENAI_API_KEY is not set. No external model call was made.")

    db_path = Path(args.db).expanduser().resolve()
    team_id, team_name = choose_team(db_path, args.team_id)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = output_dir / f"coach_agent_eval_{run_id}.jsonl"
    summary_path = output_dir / f"coach_agent_eval_{run_id}_summary.json"
    csv_path = output_dir / f"coach_agent_eval_{run_id}.csv"

    rng = random.Random(args.seed)
    questions = build_questions(db_path, team_id, rng)
    if not questions:
        raise RuntimeError("No evaluation questions could be generated.")

    deadline = time.monotonic() + max(0.01, args.hours) * 3600
    rows: list[dict] = []
    case = 0
    q_index = 0

    print("=" * 88)
    print("COACH COPILOT OVERNIGHT EVALUATION")
    print(f"team={team_name} model={args.model} max_cases={args.max_cases} hard_limit_hours={args.hours}")
    print("Privacy: local pseudonymization ON | OpenAI response storage OFF | Agents tracing OFF")
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
            answer = run_coach_agent(
                question,
                db_path=db_path,
                team_id=team_id,
                session_id=f"eval-{run_id}-{case}",
                model=args.model,
            )
            checks = deterministic_checks(category, answer)
            record.update({
                "answer": answer,
                "checks": checks,
                "pass": all(checks.values()),
                "error": None,
            })
        except Exception as exc:
            record.update({
                "answer": None,
                "checks": {"nonempty": False, "not_exception_text": False},
                "pass": False,
                "error": f"{type(exc).__name__}: {exc}",
            })
        record["elapsed_s"] = round(time.monotonic() - started, 3)
        rows.append(record)
        with jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        status = "PASS" if record["pass"] else "FAIL"
        print(f"[{case:03d}/{args.max_cases}] {status} {category:<11} {record['elapsed_s']:>6.1f}s | {question[:70]}")

    frame = pd.DataFrame(rows)
    frame.to_csv(csv_path, index=False, encoding="utf-8-sig")
    failures = int((~frame["pass"].astype(bool)).sum()) if not frame.empty else 0
    summary = {
        "run_id": run_id,
        "team_id": team_id,
        "team_name": team_name,
        "model": args.model,
        "cases": len(rows),
        "passes": len(rows) - failures,
        "failures": failures,
        "pass_rate": None if not rows else (len(rows) - failures) / len(rows),
        "jsonl": str(jsonl_path),
        "csv": str(csv_path),
        "finished_at": utc_now(),
        "notes": [
            "Deterministic checks validate runtime/guardrail basics, not semantic truth of every prose claim.",
            "All real entity names/IDs are pseudonymized before external model calls and restored locally for saved answers.",
            "No analytics/model version is modified by this runner.",
        ],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=" * 88)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
