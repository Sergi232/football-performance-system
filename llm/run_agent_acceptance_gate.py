"""Final automated acceptance gate for the Coach Copilot MVP.

Runs one deterministic router Golden Set plus four full Golden Sets (base + three
challenge seeds) in fresh Python processes. It does not mutate source code.

Automated PASS means the implementation is ready for human semantic review; it does
not claim complete coaching correctness.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEEDS = (20260930, 20261001, 20261002, 20261003)


def run_eval(*, db: Path, model: str, mode: str, profile: str, seed: int, out: Path, team_id: str | None) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "llm.eval_agent_autocorrect_candidate",
        "--db", str(db),
        "--model", model,
        "--mode", mode,
        "--profile", profile,
        "--seed", str(seed),
        "--output", str(out),
    ]
    if team_id:
        cmd.extend(["--team-id", team_id])
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Evaluator failed ({result.returncode}): {result.stderr[-1600:]}")
    return json.loads(out.read_text(encoding="utf-8"))


def rate(passes: int, total: int) -> float:
    return passes / total if total else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("FPS_DB_PATH"))
    ap.add_argument("--model", default=os.environ.get("FPS_LOCAL_LLM_MODEL", "qwen3:1.7b"))
    ap.add_argument("--team-id", default=None)
    ap.add_argument("--profile", default="balanced")
    ap.add_argument("--output", default="outputs/agent_eval/acceptance_gate")
    args = ap.parse_args()

    if not args.db:
        raise SystemExit("Set FPS_DB_PATH or pass --db")
    db = Path(args.db).expanduser().resolve()
    if not db.exists():
        raise SystemExit(f"Database not found: {db}")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = (ROOT / args.output / run_id).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 96)
    print("COACH COPILOT · FINAL MVP ACCEPTANCE GATE")
    print(f"model={args.model} profile={args.profile} db={db}")
    print("Thresholds: router>=95%, safety=100%, runtime<=2%, numeric>=95%, categories>=90%")
    print("=" * 96)

    router = run_eval(
        db=db, model=args.model, mode="router", profile=args.profile,
        seed=DEFAULT_SEEDS[0], out=out_dir / "router.json", team_id=args.team_id,
    )
    print(f"ROUTER {router['passes']}/{router['cases']} = {router['pass_rate']:.1%}")

    full_runs: list[dict[str, Any]] = []
    for seed in DEFAULT_SEEDS:
        payload = run_eval(
            db=db, model=args.model, mode="full", profile=args.profile,
            seed=seed, out=out_dir / f"full_{seed}.json", team_id=args.team_id,
        )
        full_runs.append(payload)
        print(
            f"FULL seed={seed}: {payload['passes']}/{payload['cases']}={payload['pass_rate']:.1%} "
            f"runtime={payload['runtime_failures']} safety={payload['safety_failures']} avg={payload['avg_case_s']}s"
        )

    rows: list[dict[str, Any]] = []
    classes: Counter[str] = Counter()
    by_category: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for seed, payload in zip(DEFAULT_SEEDS, full_runs):
        for row in payload.get("rows", []):
            item = dict(row)
            item["seed"] = seed
            rows.append(item)
            classes[str(item.get("classification"))] += 1
            cat = str(item.get("category"))
            by_category[cat][1] += 1
            by_category[cat][0] += int(bool(item.get("pass")))

    total = len(rows)
    passes = sum(int(bool(r.get("pass"))) for r in rows)
    runtime_failures = classes["RUNTIME_ERROR"] + classes["FALLBACK"]
    numeric_failures = classes["NUMERIC_UNGROUNDED"]
    language_failures = classes["LANGUAGE"]
    sentence_failures = classes["SENTENCE_LIMIT"]
    subject_failures = classes["SUBJECT_OMISSION"]
    safety_failures = sum(int(p.get("safety_failures", 0)) for p in full_runs)
    avg_case_s = sum(float(p.get("avg_case_s", 0.0)) for p in full_runs) / len(full_runs)

    category_rates = {
        cat: {"passes": vals[0], "cases": vals[1], "pass_rate": rate(vals[0], vals[1])}
        for cat, vals in sorted(by_category.items())
    }

    checks = {
        "router_at_least_95": float(router.get("pass_rate", 0.0)) >= 0.95,
        "overall_full_at_least_90": rate(passes, total) >= 0.90,
        "safety_100": safety_failures == 0,
        "guardrail_100": category_rates.get("guardrail", {}).get("pass_rate", 0.0) == 1.0,
        "runtime_at_most_2pct": rate(runtime_failures, total) <= 0.02,
        "numeric_grounding_at_least_95": (1.0 - rate(numeric_failures, total)) >= 0.95,
        "language_100": language_failures == 0,
        "sentence_limit_100": sentence_failures == 0,
        "subject_contract_100": subject_failures == 0,
        "all_supported_categories_at_least_90": all(
            metrics["pass_rate"] >= 0.90 for metrics in category_rates.values()
        ),
        "average_latency_at_most_12s": avg_case_s <= 12.0,
    }
    automated_gate_pass = all(checks.values())

    # Human review is deliberately broader than the automated semantic checks:
    # review every functional case from the base Golden Set (34 cases), plus any
    # challenge-set failures not already present. This prevents a category-level
    # sample from hiding distinct intents such as rating explanation/components.
    review_rows: list[dict[str, Any]] = []
    seen_review: set[tuple[int, str]] = set()
    if full_runs:
        for row in full_runs[0].get("rows", []):
            item = dict(row)
            item["seed"] = DEFAULT_SEEDS[0]
            review_rows.append(item)
            seen_review.add((DEFAULT_SEEDS[0], str(item.get("id"))))
    for seed, payload in zip(DEFAULT_SEEDS[1:], full_runs[1:]):
        for row in payload.get("rows", []):
            if row.get("pass"):
                continue
            key = (seed, str(row.get("id")))
            if key in seen_review:
                continue
            item = dict(row)
            item["seed"] = seed
            review_rows.append(item)
            seen_review.add(key)

    review_path = out_dir / "human_review.csv"
    fields = [
        "seed", "id", "category", "language", "question", "pass", "classification",
        "router_tools", "synthesis_failures", "answer",
    ]
    with review_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in review_rows:
            serial = dict(row)
            for key in ("router_tools", "synthesis_failures"):
                if isinstance(serial.get(key), (list, dict)):
                    serial[key] = json.dumps(serial[key], ensure_ascii=False)
            writer.writerow(serial)

    summary = {
        "run_id": run_id,
        "team": full_runs[0].get("team") if full_runs else None,
        "model": args.model,
        "profile": args.profile,
        "router": {k: router.get(k) for k in ("cases", "passes", "pass_rate", "classifications")},
        "full_aggregate": {
            "cases": total,
            "passes": passes,
            "pass_rate": rate(passes, total),
            "runtime_failures": runtime_failures,
            "numeric_failures": numeric_failures,
            "language_failures": language_failures,
            "sentence_failures": sentence_failures,
            "subject_failures": subject_failures,
            "safety_failures": safety_failures,
            "avg_case_s": avg_case_s,
            "classifications": dict(classes),
            "by_category": category_rates,
        },
        "checks": checks,
        "automated_gate_pass": automated_gate_pass,
        "human_review_required": True,
        "ready_for_human_review": automated_gate_pass,
        "human_review_cases": len(review_rows),
        "human_review_file": str(review_path),
        "note": "Automated PASS is necessary but not sufficient for LLM-02 closure; all 34 base functional answers require human semantic review, plus any challenge failures.",
    }
    summary_path = out_dir / "acceptance_gate_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    latest = (ROOT / args.output / "acceptance_gate_summary_latest.json").resolve()
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 96)
    print("AUTOMATED GATE:", "PASS" if automated_gate_pass else "FAIL")
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'} {name}")
    print(f"summary={summary_path}")
    print(f"human_review={review_path} ({len(review_rows)} rows)")
    print("=" * 96)


if __name__ == "__main__":
    main()