"""Deterministic candidate evaluator for Coach Copilot auto-correction.

Each invocation runs in a fresh Python interpreter so source-code candidates are
actually re-imported. It evaluates the functional Golden Set with strict routing
contracts and, optionally, full local-Ollama synthesis contracts.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm import coach_agent_router_v2  # noqa: F401,E402
from app.data_access import get_squad_summary, get_team_matches, list_teams  # noqa: E402
from llm.coach_agent_fast import DEFAULT_MODEL, ollama_status  # noqa: E402
from llm.run_agent_self_improve import (  # noqa: E402
    PROFILES,
    build_golden_set,
    evaluate_synthesis,
    failure_classification,
    router_contract,
)
# Must load after run_agent_self_improve so QA hooks can rebind its captured compact
# adapter to the exact V6 adapter used by the product runtime.
from llm import coach_agent_semantic_guard_v4  # noqa: F401,E402


def choose_team(db_path: Path, explicit: str | None) -> tuple[str, str]:
    teams = list_teams(db_path)
    if teams.empty:
        raise RuntimeError("No teams available")
    if explicit:
        selected = teams.loc[teams["team_id"].astype(str) == str(explicit)]
        if selected.empty:
            raise RuntimeError(f"Unknown team_id: {explicit}")
        row = selected.iloc[0]
    else:
        row = teams.iloc[0]
    return str(row["team_id"]), str(row["display_name"])


def set_profile(name: str) -> dict[str, Any]:
    by_name = {p["name"]: p for p in PROFILES}
    if name not in by_name:
        raise RuntimeError(f"Unknown profile {name}; expected one of {sorted(by_name)}")
    p = by_name[name]
    os.environ["FPS_AGENT_NUM_CTX"] = str(p["ctx"])
    os.environ["FPS_AGENT_NUM_PREDICT"] = str(p["predict"])
    os.environ["FPS_AGENT_TIMEOUT"] = str(p["timeout"])
    os.environ["FPS_AGENT_EVIDENCE_LINES"] = str(p["lines"])
    os.environ["FPS_AGENT_EVIDENCE_CHARS"] = str(p["chars"])
    return p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("FPS_DB_PATH"))
    ap.add_argument("--team-id", default=None)
    ap.add_argument("--model", default=os.environ.get("FPS_LOCAL_LLM_MODEL", DEFAULT_MODEL))
    ap.add_argument("--mode", choices=("router", "full"), default="full")
    ap.add_argument("--profile", default="balanced")
    ap.add_argument("--seed", type=int, default=20260930)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    if not args.db:
        raise SystemExit("Set FPS_DB_PATH or pass --db")
    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    if args.mode == "full":
        status = ollama_status()
        if not status.get("available"):
            raise SystemExit(f"Ollama unavailable: {status.get('error')}")
        if args.model not in (status.get("models") or []):
            raise SystemExit(f"Model not installed: {args.model}")

    profile = set_profile(args.profile)
    team_id, team_name = choose_team(db_path, args.team_id)
    squad = get_squad_summary(db_path, team_id)
    appearances = pd.to_numeric(squad.get("appearances"), errors="coerce").fillna(0)
    players = squad.loc[appearances >= 3, "player"].dropna().astype(str).tolist()
    matches = get_team_matches(db_path, team_id).head(20)
    opponents = matches.get("opponent", pd.Series(dtype=str)).dropna().astype(str).tolist()
    golden = build_golden_set(players, opponents, args.seed)

    rows: list[dict[str, Any]] = []
    classes: Counter[str] = Counter()
    started_all = time.monotonic()

    for spec in golden:
        question = str(spec["question"])
        started = time.monotonic()
        router = router_contract(question, spec, db_path, team_id)
        synth: dict[str, Any] | None = None
        if args.mode == "full" and router["pass"]:
            synth = evaluate_synthesis(
                question=question,
                spec=spec,
                db_path=db_path,
                team_id=team_id,
                model=args.model,
            )
        classification = failure_classification(router, synth)
        passed = bool(router["pass"]) if args.mode == "router" else bool(router["pass"] and synth is not None and synth["pass"])
        classes[classification] += 1
        rows.append({
            "id": spec["id"],
            "category": spec["category"],
            "language": spec["language"],
            "question": question,
            "pass": passed,
            "classification": classification,
            "router_pass": bool(router["pass"]),
            "router_tools": router["tools"],
            "router_missing": router["missing_tools"],
            "router_extra": router["extra_tools"],
            "wrong_guardrail": bool(router["wrong_guardrail"]),
            "synthesis_pass": None if synth is None else bool(synth["pass"]),
            "synthesis_failures": [] if synth is None else synth["failures"],
            "runtime_error": "" if synth is None else synth["runtime_error"],
            "numeric_grounding_pass": None if synth is None else synth["numeric_grounding_pass"],
            "policy_safety_pass": None if synth is None else synth["policy_safety_pass"],
            "language_pass": None if synth is None else synth["language_pass"],
            "sentence_limit_pass": None if synth is None else synth["sentence_limit_pass"],
            "subject_pass": None if synth is None else synth["subject_pass"],
            "fallback_absent": None if synth is None else synth["fallback_absent"],
            "answer": "" if synth is None else synth["answer"],
            "elapsed_s": round(time.monotonic() - started, 3),
        })

    total = len(rows)
    pass_count = sum(int(r["pass"]) for r in rows)
    router_pass_count = sum(int(r["router_pass"]) for r in rows)
    runtime_failures = sum(int("RUNTIME_ERROR" in r["synthesis_failures"] or "FALLBACK" in r["synthesis_failures"]) for r in rows)
    safety_failures = sum(int(r["wrong_guardrail"] or r["policy_safety_pass"] is False or r["language_pass"] is False) for r in rows)
    elapsed_total = time.monotonic() - started_all
    payload = {
        "mode": args.mode,
        "team": team_name,
        "team_id": team_id,
        "model": args.model,
        "profile": profile,
        "cases": total,
        "passes": pass_count,
        "pass_rate": pass_count / total if total else 0.0,
        "router_passes": router_pass_count,
        "router_pass_rate": router_pass_count / total if total else 0.0,
        "runtime_failures": runtime_failures,
        "safety_failures": safety_failures,
        "classifications": dict(classes),
        "elapsed_total_s": round(elapsed_total, 3),
        "avg_case_s": round(elapsed_total / total, 3) if total else 0.0,
        "rows": rows,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("mode", "profile", "cases", "passes", "pass_rate", "router_passes", "runtime_failures", "safety_failures", "avg_case_s")}, ensure_ascii=False))
    print(f"output={out}")


if __name__ == "__main__":
    main()
