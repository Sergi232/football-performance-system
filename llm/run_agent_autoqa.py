"""Unattended, zero-cost QA for the local Coach Copilot.

This is NOT model training. It automatically calibrates a few local Ollama runtime
profiles, then stress-tests routing, tools, guardrails and answer generation. If
Ollama synthesis is still too slow, it continues with router/tool QA instead of
wasting hours on repeated timeouts.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import get_squad_summary, get_team_matches, list_teams
from llm.coach_agent_fast import DEFAULT_MODEL, ollama_status, run_coach_agent_turn
from llm.coach_agent_hybrid import _plan_tools


PROFILES = [
    {"name": "ultra_fast", "ctx": 1024, "predict": 80, "timeout": 12, "lines": 18, "chars": 1800},
    {"name": "fast", "ctx": 1536, "predict": 112, "timeout": 18, "lines": 24, "chars": 2400},
    {"name": "balanced", "ctx": 2048, "predict": 144, "timeout": 25, "lines": 30, "chars": 3200},
]

TEAM_CASES = [
    ("team", "Resumeix l'estat recent de l'equip.", {"get_team_snapshot"}),
    ("team", "Què ha canviat en la forma recent de l'equip?", {"get_team_snapshot"}),
    ("team", "Qui presenta el canvi recent més gran i amb quina mostra?", {"get_team_snapshot"}),
    ("quality", "Quines limitacions de dades tenim ara mateix?", {"get_data_quality"}),
    ("quality", "Tenim prou dades GPS per parlar de fatiga?", {"get_data_quality"}),
    ("guardrail", "Qui hauria de ser titular el proper partit?", set()),
    ("guardrail", "Quin jugador té més risc de lesió?", set()),
]

PLAYER_TEMPLATES = [
    ("player", "Explica'm el rendiment recent de {player}.", {"get_player_profile"}),
    ("player", "Com ha evolucionat {player} en els últims partits?", {"get_player_profile", "get_player_match_stats"}),
    ("player", "Per què {player} té aquesta nota recent?", {"get_player_profile", "get_player_match_stats"}),
    ("player", "Quin rol ha tingut {player}?", {"get_player_profile"}),
    ("gps", "Quines dades GPS tenim de {player}?", {"get_player_gps"}),
]

COMPARE_TEMPLATES = [
    "Compara descriptivament {p1} i {p2} en forma recent.",
    "Quines diferències observables hi ha entre {p1} i {p2}?",
]

MATCH_TEMPLATES = [
    "Resumeix l'últim partit.",
    "Què sabem del partit contra {opponent}?",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def choose_team(db_path: Path, explicit: str | None) -> tuple[str, str]:
    teams = list_teams(db_path)
    if teams.empty:
        raise RuntimeError("No teams available.")
    if explicit:
        row = teams.loc[teams["team_id"].astype(str) == str(explicit)]
        if row.empty:
            raise RuntimeError(f"Unknown team_id: {explicit}")
        return str(row.iloc[0]["team_id"]), str(row.iloc[0]["display_name"])
    row = teams.iloc[0]
    return str(row["team_id"]), str(row["display_name"])


def set_profile(profile: dict) -> None:
    os.environ["FPS_AGENT_NUM_CTX"] = str(profile["ctx"])
    os.environ["FPS_AGENT_NUM_PREDICT"] = str(profile["predict"])
    os.environ["FPS_AGENT_TIMEOUT"] = str(profile["timeout"])
    os.environ["FPS_AGENT_EVIDENCE_LINES"] = str(profile["lines"])
    os.environ["FPS_AGENT_EVIDENCE_CHARS"] = str(profile["chars"])


def calibrate(db_path: Path, team_id: str, model: str) -> tuple[dict | None, list[dict]]:
    probes = [
        "Resumeix l'estat recent de l'equip.",
        "Quines limitacions de dades tenim ara mateix?",
    ]
    rows: list[dict] = []
    best: dict | None = None
    for profile in PROFILES:
        set_profile(profile)
        passes = 0
        elapsed_total = 0.0
        for question in probes:
            start = time.monotonic()
            try:
                result = run_coach_agent_turn(question, db_path=db_path, team_id=team_id, model=model)
                elapsed = time.monotonic() - start
                ok = bool(result.text.strip()) and result.error is None and bool(result.tools_used)
                err = result.error
            except Exception as exc:
                elapsed = time.monotonic() - start
                ok = False
                err = f"{type(exc).__name__}: {exc}"
            passes += int(ok)
            elapsed_total += elapsed
            rows.append({
                "profile": profile["name"], "question": question, "pass": ok,
                "elapsed_s": round(elapsed, 3), "error": err,
            })
        candidate = dict(profile)
        candidate["passes"] = passes
        candidate["avg_elapsed_s"] = elapsed_total / len(probes)
        if best is None or (candidate["passes"], -candidate["avg_elapsed_s"]) > (best["passes"], -best["avg_elapsed_s"]):
            best = candidate
        if passes == len(probes):
            return candidate, rows
    if best and best["passes"] > 0:
        return best, rows
    return None, rows


def build_cases(db_path: Path, team_id: str, rng: random.Random) -> list[dict]:
    cases = [
        {"category": cat, "question": q, "expected": sorted(expected)}
        for cat, q, expected in TEAM_CASES
    ]
    squad = get_squad_summary(db_path, team_id)
    players = squad.loc[
        pd.to_numeric(squad.get("appearances"), errors="coerce").fillna(0) >= 3,
        "player",
    ].dropna().astype(str).tolist()
    rng.shuffle(players)
    players = players[:16]
    for player in players:
        for cat, template, expected in PLAYER_TEMPLATES:
            cases.append({"category": cat, "question": template.format(player=player), "expected": sorted(expected)})
    for i in range(0, len(players) - 1, 2):
        cases.append({
            "category": "compare",
            "question": rng.choice(COMPARE_TEMPLATES).format(p1=players[i], p2=players[i + 1]),
            "expected": ["compare_players"],
        })
    matches = get_team_matches(db_path, team_id).head(12)
    if not matches.empty:
        cases.append({"category": "match", "question": "Resumeix l'últim partit.", "expected": ["get_match_detail"]})
    for row in matches.itertuples(index=False):
        opponent = str(getattr(row, "opponent", "") or "")
        if opponent:
            cases.append({
                "category": "match",
                "question": MATCH_TEMPLATES[1].format(opponent=opponent),
                "expected": ["get_match_detail"],
            })
    rng.shuffle(cases)
    return cases


def classify_error(error: str | None, tools: list[str], expected: list[str], answer: str) -> str:
    if error:
        low = error.lower()
        if "timeout" in low:
            return "SYNTHESIS_TIMEOUT"
        if "model_not_installed" in low:
            return "MODEL_NOT_INSTALLED"
        return "RUNTIME_ERROR"
    if expected and not set(expected).issubset(set(tools)):
        return "ROUTING_MISS"
    if not answer.strip():
        return "EMPTY_ANSWER"
    return "OK"


def router_only_case(question: str, expected: list[str], db_path: Path, team_id: str) -> tuple[list[str], bool, str | None]:
    plan, guardrail = _plan_tools(question, db_path=db_path, team_id=team_id, history=None)
    tools = [name for name, _ in plan]
    if guardrail:
        ok = not expected
    else:
        ok = set(expected).issubset(set(tools))
    return tools, ok, guardrail


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("FPS_DB_PATH"))
    parser.add_argument("--team-id", default=None)
    parser.add_argument("--model", default=os.environ.get("FPS_LOCAL_LLM_MODEL", DEFAULT_MODEL))
    parser.add_argument("--hours", type=float, default=8.0)
    parser.add_argument("--max-cases", type=int, default=240)
    parser.add_argument("--seed", type=int, default=20260926)
    parser.add_argument("--output", default="outputs/agent_eval")
    args = parser.parse_args()

    if not args.db:
        raise SystemExit("Set FPS_DB_PATH or pass --db.")
    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")
    status = ollama_status()
    if not status.get("available"):
        raise SystemExit(f"Ollama unavailable: {status.get('error')}")
    if args.model not in (status.get("models") or []):
        raise SystemExit(f"Model not installed: {args.model}")

    team_id, team_name = choose_team(db_path, args.team_id)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    cases_path = output / f"autoqa_{run_id}_cases.csv"
    summary_path = output / f"autoqa_{run_id}_summary.json"
    calibration_path = output / f"autoqa_{run_id}_calibration.csv"

    print("=" * 88)
    print("COACH COPILOT AUTO-QA · LOCAL ONLY · ZERO PAID API")
    print(f"team={team_name} model={args.model}")
    print("This does not train model weights. It calibrates runtime + tests agent behaviour.")
    print("=" * 88)

    profile, calibration = calibrate(db_path, team_id, args.model)
    pd.DataFrame(calibration).to_csv(calibration_path, index=False, encoding="utf-8-sig")
    if profile:
        set_profile(profile)
        print(f"selected_profile={profile['name']} calibration_passes={profile['passes']}/2 avg={profile['avg_elapsed_s']:.1f}s")
        mode = "FULL_AGENT_QA"
    else:
        print("No synthesis profile passed. Switching to ROUTER_TOOL_QA so unattended time is not wasted.")
        mode = "ROUTER_TOOL_QA"

    rng = random.Random(args.seed)
    cases = build_cases(db_path, team_id, rng)
    deadline = time.monotonic() + max(0.01, args.hours) * 3600
    rows: list[dict] = []
    index = 0
    consecutive_timeouts = 0

    while len(rows) < args.max_cases and time.monotonic() < deadline:
        case = cases[index % len(cases)]
        index += 1
        start = time.monotonic()
        question = case["question"]
        expected = case["expected"]

        if mode == "ROUTER_TOOL_QA":
            tools, ok, guardrail = router_only_case(question, expected, db_path, team_id)
            answer = guardrail or "ROUTER_ONLY"
            error = None if ok else "ROUTING_MISS"
            elapsed = time.monotonic() - start
            classification = "OK" if ok else "ROUTING_MISS"
        else:
            try:
                result = run_coach_agent_turn(question, db_path=db_path, team_id=team_id, model=args.model)
                tools = list(result.tools_used)
                answer = result.text
                error = result.error
            except Exception as exc:
                tools = []
                answer = ""
                error = f"{type(exc).__name__}: {exc}"
            elapsed = time.monotonic() - start
            classification = classify_error(error, tools, expected, answer)
            ok = classification == "OK"
            if classification == "SYNTHESIS_TIMEOUT":
                consecutive_timeouts += 1
            else:
                consecutive_timeouts = 0
            if consecutive_timeouts >= 3:
                print("3 consecutive synthesis timeouts -> switching remaining run to ROUTER_TOOL_QA")
                mode = "ROUTER_TOOL_QA"

        row = {
            "case": len(rows) + 1,
            "category": case["category"],
            "question": question,
            "expected_tools": ",".join(expected),
            "tools_used": ",".join(tools),
            "pass": bool(ok),
            "classification": classification,
            "elapsed_s": round(elapsed, 3),
            "answer": answer,
            "error": error,
            "mode": mode,
            "timestamp": now_iso(),
        }
        rows.append(row)
        print(f"[{len(rows):03d}/{args.max_cases}] {'PASS' if ok else 'FAIL'} {case['category']:<9} {classification:<18} {elapsed:>5.1f}s")

        if len(rows) % 10 == 0:
            pd.DataFrame(rows).to_csv(cases_path, index=False, encoding="utf-8-sig")

        # Once all unique cases have been covered twice, repetition adds little value.
        if index >= len(cases) * 2:
            break

    frame = pd.DataFrame(rows)
    frame.to_csv(cases_path, index=False, encoding="utf-8-sig")
    classifications = Counter(frame["classification"].tolist()) if not frame.empty else Counter()
    categories = {}
    if not frame.empty:
        for category, group in frame.groupby("category"):
            categories[str(category)] = {
                "cases": int(len(group)),
                "passes": int(group["pass"].astype(bool).sum()),
                "pass_rate": float(group["pass"].astype(bool).mean()),
                "avg_elapsed_s": float(group["elapsed_s"].mean()),
            }

    summary = {
        "run_id": run_id,
        "team": team_name,
        "team_id": team_id,
        "provider": "ollama_local_only",
        "model": args.model,
        "training_performed": False,
        "selected_profile": profile,
        "final_mode": mode,
        "cases": int(len(frame)),
        "passes": int(frame["pass"].astype(bool).sum()) if not frame.empty else 0,
        "pass_rate": float(frame["pass"].astype(bool).mean()) if not frame.empty else None,
        "classifications": dict(classifications),
        "by_category": categories,
        "calibration_csv": str(calibration_path),
        "cases_csv": str(cases_path),
        "finished_at": now_iso(),
        "notes": [
            "No OpenAI or paid external API is called.",
            "The model is not fine-tuned and its weights are not modified.",
            "Runtime profile selection is automatic and reversible.",
            "If repeated synthesis timeouts occur, QA switches to deterministic router/tool validation instead of wasting the run.",
        ],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=" * 88)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
