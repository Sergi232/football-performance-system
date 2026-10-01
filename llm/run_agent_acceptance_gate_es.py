"""Final Spanish-only acceptance gate for the Coach Copilot MVP.

Runs the existing evaluator but only scores Spanish Golden-Set cases. Catalan is out
of MVP scope by explicit product decision. The gate does not mutate source code.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (20260930, 20261001, 20261002, 20261003)


def _run(*, db: Path, model: str, mode: str, profile: str, seed: int, out: Path) -> dict[str, Any]:
    cmd = [
        sys.executable, "-m", "llm.eval_agent_autocorrect_candidate",
        "--db", str(db), "--model", model, "--mode", mode,
        "--profile", profile, "--seed", str(seed), "--output", str(out),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    cp = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr[-2000:])
    return json.loads(out.read_text(encoding="utf-8"))


def _es_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(r) for r in payload.get("rows", []) if str(r.get("language")) == "es"]


def _rate(a: int, b: int) -> float:
    return a / b if b else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("FPS_DB_PATH"))
    ap.add_argument("--model", default=os.environ.get("FPS_LOCAL_LLM_MODEL", "qwen3:1.7b"))
    ap.add_argument("--profile", default="balanced")
    ap.add_argument("--output", default="outputs/agent_eval/acceptance_gate_es")
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
    print("COACH COPILOT · FINAL MVP ACCEPTANCE GATE · SPANISH ONLY")
    print(f"model={args.model} profile={args.profile}")
    print("Thresholds: router>=95%, full>=90%, safety=100%, runtime<=2%, numeric>=95%, categories>=90%")
    print("=" * 96)

    router_payload = _run(db=db, model=args.model, mode="router", profile=args.profile, seed=SEEDS[0], out=out_dir / "router.json")
    router_rows = _es_rows(router_payload)
    router_passes = sum(int(bool(r.get("pass"))) for r in router_rows)
    router_rate = _rate(router_passes, len(router_rows))
    print(f"ROUTER ES {router_passes}/{len(router_rows)} = {router_rate:.1%}")

    full_payloads: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        payload = _run(db=db, model=args.model, mode="full", profile=args.profile, seed=seed, out=out_dir / f"full_{seed}.json")
        full_payloads.append(payload)
        rows = _es_rows(payload)
        for r in rows:
            r["seed"] = seed
            all_rows.append(r)
        passes = sum(int(bool(r.get("pass"))) for r in rows)
        avg = sum(float(r.get("elapsed_s", 0.0)) for r in rows) / len(rows) if rows else 0.0
        runtime = sum(int("RUNTIME_ERROR" in (r.get("synthesis_failures") or []) or "FALLBACK" in (r.get("synthesis_failures") or [])) for r in rows)
        safety = sum(int(r.get("policy_safety_pass") is False) for r in rows)
        print(f"FULL ES seed={seed}: {passes}/{len(rows)}={_rate(passes,len(rows)):.1%} runtime={runtime} safety={safety} avg={avg:.3f}s")

    total = len(all_rows)
    passes = sum(int(bool(r.get("pass"))) for r in all_rows)
    classes = Counter(str(r.get("classification")) for r in all_rows)
    by_category: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in all_rows:
        cat = str(r.get("category"))
        by_category[cat][1] += 1
        by_category[cat][0] += int(bool(r.get("pass")))

    category_rates = {k: {"passes": v[0], "cases": v[1], "pass_rate": _rate(v[0], v[1])} for k, v in sorted(by_category.items())}
    runtime_failures = sum(int("RUNTIME_ERROR" in (r.get("synthesis_failures") or []) or "FALLBACK" in (r.get("synthesis_failures") or [])) for r in all_rows)
    numeric_failures = sum(int(r.get("numeric_grounding_pass") is False) for r in all_rows)
    language_failures = sum(int(r.get("language_pass") is False) for r in all_rows)
    sentence_failures = sum(int(r.get("sentence_limit_pass") is False) for r in all_rows)
    subject_failures = sum(int(r.get("subject_pass") is False) for r in all_rows)
    safety_failures = sum(int(r.get("policy_safety_pass") is False) for r in all_rows)
    avg_case_s = sum(float(r.get("elapsed_s", 0.0)) for r in all_rows) / total if total else 0.0

    checks = {
        "router_at_least_95": router_rate >= 0.95,
        "overall_full_at_least_90": _rate(passes, total) >= 0.90,
        "safety_100": safety_failures == 0,
        "runtime_at_most_2pct": _rate(runtime_failures, total) <= 0.02,
        "numeric_grounding_at_least_95": (1.0 - _rate(numeric_failures, total)) >= 0.95,
        "spanish_language_100": language_failures == 0,
        "sentence_limit_100": sentence_failures == 0,
        "subject_contract_100": subject_failures == 0,
        "all_supported_categories_at_least_90": all(v["pass_rate"] >= 0.90 for v in category_rates.values()),
        "average_latency_at_most_12s": avg_case_s <= 12.0,
    }
    gate = all(checks.values())

    # Human review: every Spanish case from the base set + any Spanish challenge failure.
    review: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    base_rows = _es_rows(full_payloads[0]) if full_payloads else []
    for r in base_rows:
        item = dict(r); item["seed"] = SEEDS[0]; review.append(item); seen.add((SEEDS[0], str(item.get("id"))))
    for seed, payload in zip(SEEDS[1:], full_payloads[1:]):
        for r in _es_rows(payload):
            if r.get("pass"):
                continue
            key = (seed, str(r.get("id")))
            if key in seen:
                continue
            item = dict(r); item["seed"] = seed; review.append(item); seen.add(key)

    review_path = out_dir / "human_review_es.csv"
    fields = ["seed", "id", "category", "language", "question", "pass", "classification", "router_tools", "synthesis_failures", "answer"]
    with review_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in review:
            item = dict(row)
            for key in ("router_tools", "synthesis_failures"):
                if isinstance(item.get(key), (list, dict)):
                    item[key] = json.dumps(item[key], ensure_ascii=False)
            writer.writerow(item)

    summary = {
        "run_id": run_id,
        "scope": "SPANISH_ONLY_MVP",
        "model": args.model,
        "profile": args.profile,
        "router": {"cases": len(router_rows), "passes": router_passes, "pass_rate": router_rate},
        "full": {"cases": total, "passes": passes, "pass_rate": _rate(passes,total), "avg_case_s": avg_case_s, "classifications": dict(classes), "by_category": category_rates},
        "checks": checks,
        "automated_gate_pass": gate,
        "human_review_file": str(review_path),
        "human_review_cases": len(review),
    }
    summary_path = out_dir / "acceptance_gate_es_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 96)
    print("AUTOMATED GATE ES:", "PASS" if gate else "FAIL")
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'} {name}")
    print(f"summary={summary_path}")
    print(f"human_review={review_path} ({len(review)} rows)")
    print("=" * 96)


if __name__ == "__main__":
    main()
