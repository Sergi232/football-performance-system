"""Adaptive unattended QA for the local Coach Copilot.

Designed for long local runs (for example 10 hours) without paid APIs.
It does NOT fine-tune or alter model weights and does NOT rewrite product code.
Instead it learns from failures during the run by:
- increasing sampling of weak categories;
- replaying failed questions with controlled Spanish/Catalan variants;
- testing multi-turn follow-ups;
- automatically exploring several bounded Ollama synthesis profiles;
- reducing expensive synthesis probes when they are clearly unproductive;
- saving checkpoints, failure clusters and before/after metrics.

Critical football analytics remain read-only and outside the LLM.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
import time
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Install the approved router patch before any hybrid routing call.
from llm import coach_agent_router_v2  # noqa: F401
from app.data_access import get_squad_summary, get_team_matches, list_teams
from llm.coach_agent_fast import DEFAULT_MODEL, ollama_status, run_coach_agent_turn
from llm.coach_agent_hybrid import _plan_tools
from llm.run_agent_continuous import build_question


BASE_CATEGORY_WEIGHTS = {
    "player": 24.0,
    "team": 12.0,
    "match": 12.0,
    "compare": 12.0,
    "quality": 16.0,
    "gps": 14.0,
    "guardrail": 10.0,
}

SYNTHESIS_PROFILES = [
    {"name": "tiny", "ctx": 1024, "predict": 64, "timeout": 12, "lines": 10, "chars": 1100},
    {"name": "compact", "ctx": 1280, "predict": 80, "timeout": 15, "lines": 14, "chars": 1500},
    {"name": "fast", "ctx": 1536, "predict": 96, "timeout": 18, "lines": 18, "chars": 1900},
    {"name": "balanced", "ctx": 2048, "predict": 128, "timeout": 25, "lines": 24, "chars": 2600},
]

ES_PREFIXES = [
    "Con los datos actuales, ",
    "Según la evidencia disponible, ",
    "Para el cuerpo técnico: ",
    "Sin inventar información, ",
    "De forma breve, ",
    "",
]
CA_PREFIXES = [
    "Amb les dades actuals, ",
    "Segons l'evidència disponible, ",
    "Per al cos tècnic: ",
    "Sense inventar informació, ",
    "De forma breu, ",
    "",
]
ES_SUFFIXES = ["", " Sé preciso.", " Indica las limitaciones.", " Usa solo datos disponibles."]
CA_SUFFIXES = ["", " Sigues precís.", " Indica les limitacions.", " Usa només dades disponibles."]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def choose_team(db_path: Path, explicit: str | None) -> tuple[str, str]:
    teams = list_teams(db_path)
    if teams.empty:
        raise RuntimeError("No teams available")
    if explicit:
        row = teams.loc[teams["team_id"].astype(str) == str(explicit)]
        if row.empty:
            raise RuntimeError(f"Unknown team_id: {explicit}")
        return str(row.iloc[0]["team_id"]), str(row.iloc[0]["display_name"])
    row = teams.iloc[0]
    return str(row["team_id"]), str(row["display_name"])


def set_profile(profile: dict[str, Any]) -> None:
    os.environ["FPS_AGENT_NUM_CTX"] = str(profile["ctx"])
    os.environ["FPS_AGENT_NUM_PREDICT"] = str(profile["predict"])
    os.environ["FPS_AGENT_TIMEOUT"] = str(profile["timeout"])
    os.environ["FPS_AGENT_EVIDENCE_LINES"] = str(profile["lines"])
    os.environ["FPS_AGENT_EVIDENCE_CHARS"] = str(profile["chars"])


def profile_score(stats: Counter) -> float:
    attempts = stats["attempts"]
    if not attempts:
        return -1e9
    success_rate = stats["success"] / attempts
    avg_elapsed = stats["elapsed_ms"] / max(1, attempts) / 1000.0
    # Reliability dominates; latency breaks ties.
    return (success_rate * 100.0) - min(avg_elapsed, 60.0) * 1.2


def select_profile(rng: random.Random, profile_stats: dict[str, Counter]) -> dict[str, Any]:
    # Explore every profile twice before exploiting.
    for profile in SYNTHESIS_PROFILES:
        if profile_stats[profile["name"]]["attempts"] < 2:
            return profile
    # 15% exploration prevents locking onto an early lucky profile.
    if rng.random() < 0.15:
        return rng.choice(SYNTHESIS_PROFILES)
    return max(SYNTHESIS_PROFILES, key=lambda p: profile_score(profile_stats[p["name"]]))


def recent_failure_rate(recent: deque[tuple[str, bool]], category: str) -> tuple[float, int]:
    values = [ok for cat, ok in recent if cat == category]
    if not values:
        return 0.0, 0
    failures = sum(1 for ok in values if not ok)
    return failures / len(values), len(values)


def adaptive_weights(recent: deque[tuple[str, bool]]) -> tuple[list[str], list[float]]:
    categories = list(BASE_CATEGORY_WEIGHTS)
    weights: list[float] = []
    for category in categories:
        failure_rate, n = recent_failure_rate(recent, category)
        confidence = min(1.0, n / 12.0)
        # Weak categories can receive up to ~4x their base sampling weight.
        multiplier = 1.0 + (3.0 * failure_rate * confidence)
        weights.append(BASE_CATEGORY_WEIGHTS[category] * multiplier)
    return categories, weights


def target_case(
    rng: random.Random,
    target: str,
    lang: str,
    players: list[str],
    opponents: list[str],
) -> tuple[str, str, set[str]]:
    # Reuse the curated bilingual generator but rejection-sample the desired category.
    for _ in range(80):
        category, question, expected = build_question(rng, lang, players, opponents)
        if category == target:
            return category, question, expected
    return build_question(rng, lang, players, opponents)


def mutate_question(rng: random.Random, question: str, lang: str) -> str:
    prefixes = ES_PREFIXES if lang == "es" else CA_PREFIXES
    suffixes = ES_SUFFIXES if lang == "es" else CA_SUFFIXES
    q = question.strip()
    mutation = rng.randrange(5)
    if mutation == 0:
        return rng.choice(prefixes) + q
    if mutation == 1:
        return q.rstrip("?.") + rng.choice(suffixes)
    if mutation == 2:
        return rng.choice(prefixes) + q.rstrip("?.") + rng.choice(suffixes)
    if mutation == 3:
        return q.replace("¿", "").replace("?", "")
    return q


def build_followup_case(rng: random.Random, lang: str, players: list[str]) -> dict[str, Any] | None:
    if not players:
        return None
    player = rng.choice(players)
    if lang == "es":
        history = [
            {"role": "user", "content": f"Explícame el rendimiento reciente de {player}."},
            {"role": "assistant", "content": f"Resumen previo sobre {player}."},
        ]
        question = rng.choice([
            "¿Y cómo ha evolucionado en los últimos partidos?",
            "¿Y qué muestra sostiene esa evolución?",
            "¿Puedes separar su nota de sus acciones recientes?",
        ])
    else:
        history = [
            {"role": "user", "content": f"Explica'm el rendiment recent de {player}."},
            {"role": "assistant", "content": f"Resum previ sobre {player}."},
        ]
        question = rng.choice([
            "I com ha evolucionat en els últims partits?",
            "I quina mostra sosté aquesta evolució?",
            "Pots separar la seva nota de les accions recents?",
        ])
    return {
        "category": "followup",
        "question": question,
        "expected": {"get_player_profile", "get_player_match_stats"},
        "history": history,
        "language": lang,
    }


def router_check(
    question: str,
    expected: set[str],
    db_path: Path,
    team_id: str,
    history: list[dict[str, str]] | None,
) -> tuple[bool, list[str], str | None]:
    plan, guardrail = _plan_tools(question, db_path=db_path, team_id=team_id, history=history)
    tools = [name for name, _ in plan]
    if guardrail:
        return (not expected), tools, guardrail
    return expected.issubset(set(tools)), tools, None


def is_synthesis_success(result: Any, expected: set[str]) -> bool:
    if result.error is not None:
        return False
    if not str(result.text or "").strip():
        return False
    if expected and not expected.issubset(set(result.tools_used)):
        return False
    low = str(result.text).lower()
    if "síntesi local no disponible" in low or "sintesis local no disponible" in low:
        return False
    return True


def synthesis_interval(profile_stats: dict[str, Counter]) -> int:
    attempts = sum(v["attempts"] for v in profile_stats.values())
    successes = sum(v["success"] for v in profile_stats.values())
    if attempts < 8:
        return 12
    rate = successes / max(1, attempts)
    if rate >= 0.75:
        return 15
    if rate >= 0.40:
        return 30
    if rate >= 0.15:
        return 60
    return 120


def write_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("FPS_DB_PATH"))
    parser.add_argument("--team-id", default=None)
    parser.add_argument("--model", default=os.environ.get("FPS_LOCAL_LLM_MODEL", DEFAULT_MODEL))
    parser.add_argument("--hours", type=float, default=10.0)
    parser.add_argument("--max-cases", type=int, default=100000)
    parser.add_argument("--spanish-ratio", type=float, default=0.80)
    parser.add_argument("--seed", type=int, default=20260926)
    parser.add_argument("--output", default="outputs/agent_eval")
    args = parser.parse_args()

    if not args.db:
        raise SystemExit("Set FPS_DB_PATH or pass --db")
    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    status = ollama_status()
    if not status.get("available"):
        raise SystemExit(f"Ollama unavailable: {status.get('error')}")
    if args.model not in (status.get("models") or []):
        raise SystemExit(f"Model not installed: {args.model}")

    team_id, team_name = choose_team(db_path, args.team_id)
    squad = get_squad_summary(db_path, team_id)
    players = squad.loc[
        pd.to_numeric(squad.get("appearances"), errors="coerce").fillna(0) >= 3,
        "player",
    ].dropna().astype(str).tolist()
    matches = get_team_matches(db_path, team_id).head(24)
    opponents = matches.get("opponent", pd.Series(dtype=str)).dropna().astype(str).tolist()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    cases_jsonl = output / f"adaptive10h_{run_id}_cases.jsonl"
    failures_jsonl = output / f"adaptive10h_{run_id}_failures.jsonl"
    checkpoints_jsonl = output / f"adaptive10h_{run_id}_checkpoints.jsonl"
    summary_path = output / f"adaptive10h_{run_id}_summary.json"
    failures_csv = output / f"adaptive10h_{run_id}_failures.csv"

    rng = random.Random(args.seed)
    deadline = time.monotonic() + max(0.01, args.hours) * 3600.0

    recent: deque[tuple[str, bool]] = deque(maxlen=600)
    replay_queue: deque[dict[str, Any]] = deque(maxlen=500)
    counters = Counter()
    category_stats: dict[str, Counter] = defaultdict(Counter)
    profile_stats: dict[str, Counter] = {p["name"]: Counter() for p in SYNTHESIS_PROFILES}
    failure_rows: list[dict[str, Any]] = []
    window_stats = Counter()
    case_no = 0

    print("=" * 96)
    print("COACH COPILOT ADAPTIVE 10H QA · LOCAL ONLY · ZERO PAID API")
    print(f"team={team_name} model={args.model} spanish_ratio={args.spanish_ratio:.0%}")
    print("Adaptive feedback: weak-category oversampling + failure replay + synthesis profile bandit")
    print("Model weights are NOT trained. Product analytics/code are NOT mutated during the run.")
    print("Ctrl+C stops safely and writes the final summary.")
    print("=" * 96)

    try:
        while case_no < args.max_cases and time.monotonic() < deadline:
            case_no += 1
            lang = "es" if rng.random() < args.spanish_ratio else "ca"

            # About 35% of traffic after a failure is targeted replay with a mutation.
            if replay_queue and rng.random() < 0.35:
                prior = replay_queue.popleft()
                case = dict(prior)
                case["question"] = mutate_question(rng, str(prior["question"]), str(prior["language"]))
                case["source"] = "failure_replay"
            elif rng.random() < 0.10:
                followup = build_followup_case(rng, lang, players)
                if followup is None:
                    categories, weights = adaptive_weights(recent)
                    target = rng.choices(categories, weights=weights, k=1)[0]
                    category, question, expected = target_case(rng, target, lang, players, opponents)
                    case = {"category": category, "question": question, "expected": expected, "history": None, "language": lang, "source": "adaptive"}
                else:
                    case = {**followup, "source": "followup"}
            else:
                categories, weights = adaptive_weights(recent)
                target = rng.choices(categories, weights=weights, k=1)[0]
                category, question, expected = target_case(rng, target, lang, players, opponents)
                case = {
                    "category": category,
                    "question": mutate_question(rng, question, lang),
                    "expected": expected,
                    "history": None,
                    "language": lang,
                    "source": "adaptive",
                }

            category = str(case["category"])
            expected = set(case["expected"])
            question = str(case["question"])
            history = case.get("history")

            started = time.monotonic()
            router_ok, router_tools, guardrail = router_check(question, expected, db_path, team_id, history)
            elapsed_router = time.monotonic() - started

            do_synthesis = (
                router_ok
                and category != "guardrail"
                and case_no % synthesis_interval(profile_stats) == 0
            )
            synthesis_ok: bool | None = None
            synthesis_error: str | None = None
            synthesis_text = guardrail or ""
            profile_name: str | None = None
            tools_used = list(router_tools)

            if do_synthesis:
                profile = select_profile(rng, profile_stats)
                set_profile(profile)
                profile_name = str(profile["name"])
                synthesis_started = time.monotonic()
                try:
                    result = run_coach_agent_turn(
                        question,
                        db_path=db_path,
                        team_id=team_id,
                        history=history,
                        model=args.model,
                    )
                    synthesis_elapsed = time.monotonic() - synthesis_started
                    synthesis_ok = is_synthesis_success(result, expected)
                    synthesis_error = result.error
                    synthesis_text = result.text
                    tools_used = list(result.tools_used)
                except Exception as exc:
                    synthesis_elapsed = time.monotonic() - synthesis_started
                    synthesis_ok = False
                    synthesis_error = f"{type(exc).__name__}: {exc}"

                ps = profile_stats[profile_name]
                ps["attempts"] += 1
                ps["success"] += int(bool(synthesis_ok))
                ps["fail"] += int(not bool(synthesis_ok))
                ps["elapsed_ms"] += int(synthesis_elapsed * 1000)

            ok = router_ok and (synthesis_ok is not False)
            if not router_ok:
                classification = "ROUTING_MISS"
            elif synthesis_ok is False:
                classification = "SYNTHESIS_FAIL"
            elif do_synthesis:
                classification = "FULL_PASS"
            else:
                classification = "ROUTER_PASS"

            recent.append((category, ok))
            counters[classification] += 1
            category_stats[category]["cases"] += 1
            category_stats[category]["passes"] += int(ok)
            window_stats["cases"] += 1
            window_stats["passes"] += int(ok)

            elapsed_total = time.monotonic() - started
            row = {
                "case": case_no,
                "language": case["language"],
                "category": category,
                "source": case["source"],
                "question": question,
                "history": history,
                "expected_tools": sorted(expected),
                "router_tools": router_tools,
                "tools_used": tools_used,
                "router_pass": router_ok,
                "synthesis_attempted": do_synthesis,
                "synthesis_pass": synthesis_ok,
                "synthesis_profile": profile_name,
                "classification": classification,
                "pass": ok,
                "elapsed_router_s": round(elapsed_router, 3),
                "elapsed_total_s": round(elapsed_total, 3),
                "error": synthesis_error,
                "answer_preview": str(synthesis_text or "")[:600],
                "timestamp": now_iso(),
            }
            write_jsonl(cases_jsonl, row)

            if not ok:
                failure_rows.append(row)
                write_jsonl(failures_jsonl, row)
                # Replay the failure several times with controlled variants.
                for _ in range(4):
                    replay_queue.append({
                        "category": category,
                        "question": question,
                        "expected": expected,
                        "history": history,
                        "language": case["language"],
                    })

            if case_no % 25 == 0 or not ok:
                interval = synthesis_interval(profile_stats)
                print(
                    f"[{case_no:06d}] {'PASS' if ok else 'FAIL'} {case['language']} "
                    f"{category:<9} {classification:<15} {elapsed_total:>5.1f}s "
                    f"replay={len(replay_queue)} synth_every={interval}"
                )

            if case_no % 250 == 0:
                cat_snapshot = {}
                for cat in BASE_CATEGORY_WEIGHTS:
                    fail_rate, n = recent_failure_rate(recent, cat)
                    cat_snapshot[cat] = {"recent_n": n, "recent_failure_rate": round(fail_rate, 4)}
                profile_snapshot = {
                    name: {
                        "attempts": int(st["attempts"]),
                        "successes": int(st["success"]),
                        "success_rate": (st["success"] / st["attempts"]) if st["attempts"] else None,
                        "avg_elapsed_s": (st["elapsed_ms"] / st["attempts"] / 1000.0) if st["attempts"] else None,
                        "score": profile_score(st) if st["attempts"] else None,
                    }
                    for name, st in profile_stats.items()
                }
                checkpoint = {
                    "case": case_no,
                    "elapsed_hours": round((args.hours * 3600 - max(0.0, deadline - time.monotonic())) / 3600, 3),
                    "overall_pass_rate": counters["ROUTER_PASS"] + counters["FULL_PASS"],
                    "classifications": dict(counters),
                    "recent_categories": cat_snapshot,
                    "profiles": profile_snapshot,
                    "replay_queue": len(replay_queue),
                    "timestamp": now_iso(),
                }
                denominator = max(1, sum(counters.values()))
                checkpoint["overall_pass_rate"] = round((counters["ROUTER_PASS"] + counters["FULL_PASS"]) / denominator, 5)
                write_jsonl(checkpoints_jsonl, checkpoint)
                window_stats.clear()

    except KeyboardInterrupt:
        print("Interrupted by user; saving final state...")

    if failure_rows:
        flat = []
        for row in failure_rows:
            copied = dict(row)
            copied["history"] = json.dumps(copied.get("history"), ensure_ascii=False)
            copied["expected_tools"] = ",".join(copied.get("expected_tools") or [])
            copied["router_tools"] = ",".join(copied.get("router_tools") or [])
            copied["tools_used"] = ",".join(copied.get("tools_used") or [])
            flat.append(copied)
        pd.DataFrame(flat).to_csv(failures_csv, index=False, encoding="utf-8-sig")

    total = max(1, sum(counters.values()))
    by_category = {
        cat: {
            "cases": int(st["cases"]),
            "passes": int(st["passes"]),
            "pass_rate": (st["passes"] / st["cases"]) if st["cases"] else None,
        }
        for cat, st in category_stats.items()
    }
    profile_summary = {
        name: {
            "attempts": int(st["attempts"]),
            "successes": int(st["success"]),
            "failures": int(st["fail"]),
            "success_rate": (st["success"] / st["attempts"]) if st["attempts"] else None,
            "avg_elapsed_s": (st["elapsed_ms"] / st["attempts"] / 1000.0) if st["attempts"] else None,
            "score": profile_score(st) if st["attempts"] else None,
        }
        for name, st in profile_stats.items()
    }
    attempted_profiles = [p for p in SYNTHESIS_PROFILES if profile_stats[p["name"]]["attempts"]]
    best_profile = None
    if attempted_profiles:
        best_profile = max(attempted_profiles, key=lambda p: profile_score(profile_stats[p["name"]]))["name"]

    summary = {
        "run_id": run_id,
        "team": team_name,
        "provider": "ollama_local_only",
        "model": args.model,
        "hours_requested": args.hours,
        "cases": case_no,
        "spanish_ratio_target": args.spanish_ratio,
        "training_performed": False,
        "self_modifying_code": False,
        "adaptive_feedback": {
            "weak_category_oversampling": True,
            "failure_replay": True,
            "multiturn_followups": True,
            "synthesis_profile_exploration": True,
            "dynamic_synthesis_frequency": True,
        },
        "overall_pass_rate": (counters["ROUTER_PASS"] + counters["FULL_PASS"]) / total,
        "classifications": dict(counters),
        "by_category": by_category,
        "synthesis_profiles": profile_summary,
        "best_synthesis_profile": best_profile,
        "remaining_replay_queue": len(replay_queue),
        "failures_recorded": len(failure_rows),
        "cases_jsonl": str(cases_jsonl),
        "failures_jsonl": str(failures_jsonl),
        "failures_csv": str(failures_csv) if failure_rows else None,
        "checkpoints_jsonl": str(checkpoints_jsonl),
        "finished_at": now_iso(),
        "notes": [
            "No paid/external LLM API is used.",
            "Model weights are not trained or modified.",
            "Feedback changes test allocation and safe runtime parameters only.",
            "Failures are replayed with controlled variants instead of being silently accepted.",
            "Critical analytics and Match Rating are never recalculated by the LLM.",
        ],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 96)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
