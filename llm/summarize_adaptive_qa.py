"""Summarize adaptive Coach Copilot QA without conflating router and synthesis.

The adaptive runner logs router/tool decisions for every case and only samples full
LLM synthesis on a subset. This post-processor reports those layers separately.

Important: ``synthesis_pass`` in the current runner is an *execution/contract*
check (no runtime error, non-empty answer, expected tools present, no fallback
message). It is NOT a semantic judge of factual correctness, grounding, language
quality or coaching usefulness.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _rate(num: int, den: int) -> float | None:
    return (num / den) if den else None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            if not isinstance(payload, dict):
                raise SystemExit(f"Expected JSON object at {path}:{line_no}")
            rows.append(payload)
    return rows


def _latest_cases(output_dir: Path) -> Path:
    candidates = sorted(
        output_dir.glob("adaptive10h_*_cases.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise SystemExit(
            f"No adaptive10h_*_cases.jsonl found under {output_dir}. "
            "Pass --cases explicitly."
        )
    return candidates[0]


def summarize(rows: list[dict[str, Any]], source: Path) -> dict[str, Any]:
    total = len(rows)
    router_passes = sum(bool(row.get("router_pass")) for row in rows)

    synth_rows = [row for row in rows if bool(row.get("synthesis_attempted"))]
    synth_attempts = len(synth_rows)
    synth_passes = sum(row.get("synthesis_pass") is True for row in synth_rows)
    synth_failures = sum(row.get("synthesis_pass") is False for row in synth_rows)
    synth_unknown = synth_attempts - synth_passes - synth_failures

    e2e_passes = sum(
        bool(row.get("router_pass")) and row.get("synthesis_pass") is True
        for row in synth_rows
    )

    classifications = Counter(str(row.get("classification") or "UNKNOWN") for row in rows)

    category_acc: dict[str, Counter] = defaultdict(Counter)
    profile_acc: dict[str, Counter] = defaultdict(Counter)

    for row in rows:
        category = str(row.get("category") or "UNKNOWN")
        cat = category_acc[category]
        cat["cases"] += 1
        cat["router_passes"] += int(bool(row.get("router_pass")))

        if bool(row.get("synthesis_attempted")):
            cat["synthesis_attempts"] += 1
            cat["synthesis_passes"] += int(row.get("synthesis_pass") is True)
            cat["synthesis_failures"] += int(row.get("synthesis_pass") is False)

            profile = str(row.get("synthesis_profile") or "UNKNOWN")
            prof = profile_acc[profile]
            prof["attempts"] += 1
            prof["passes"] += int(row.get("synthesis_pass") is True)
            prof["failures"] += int(row.get("synthesis_pass") is False)
            try:
                prof["elapsed_ms"] += int(float(row.get("elapsed_total_s") or 0.0) * 1000)
            except (TypeError, ValueError):
                pass

    by_category: dict[str, dict[str, Any]] = {}
    for category, st in sorted(category_acc.items()):
        cases = int(st["cases"])
        synth_n = int(st["synthesis_attempts"])
        by_category[category] = {
            "cases": cases,
            "router_passes": int(st["router_passes"]),
            "router_pass_rate": _rate(int(st["router_passes"]), cases),
            "synthesis_attempts": synth_n,
            "synthesis_execution_passes": int(st["synthesis_passes"]),
            "synthesis_execution_failures": int(st["synthesis_failures"]),
            "synthesis_execution_success_rate": _rate(int(st["synthesis_passes"]), synth_n),
            "synthesis_coverage": _rate(synth_n, cases),
        }

    by_profile: dict[str, dict[str, Any]] = {}
    for profile, st in sorted(profile_acc.items()):
        attempts = int(st["attempts"])
        by_profile[profile] = {
            "attempts": attempts,
            "passes": int(st["passes"]),
            "failures": int(st["failures"]),
            "execution_success_rate": _rate(int(st["passes"]), attempts),
            "avg_total_elapsed_s": (
                st["elapsed_ms"] / attempts / 1000.0 if attempts else None
            ),
        }

    return {
        "source_cases_jsonl": str(source),
        "cases": total,
        "router_tools": {
            "cases": total,
            "passes": router_passes,
            "failures": total - router_passes,
            "pass_rate": _rate(router_passes, total),
        },
        "synthesis_execution": {
            "attempts": synth_attempts,
            "passes": synth_passes,
            "failures": synth_failures,
            "unknown": synth_unknown,
            "success_rate": _rate(synth_passes, synth_attempts),
            "coverage_of_all_cases": _rate(synth_attempts, total),
        },
        "end_to_end_on_synthesis_cases": {
            "eligible_cases": synth_attempts,
            "passes": e2e_passes,
            "pass_rate": _rate(e2e_passes, synth_attempts),
        },
        "classifications": dict(classifications),
        "by_category": by_category,
        "by_synthesis_profile": by_profile,
        "semantic_synthesis_quality": {
            "evaluated": False,
            "reason": (
                "Current synthesis_pass validates runtime/contract success only; "
                "it does not judge factual correctness, grounding, unsupported claims, "
                "language quality or coaching usefulness."
            ),
        },
        "interpretation_notes": [
            "Do not report the router pass rate as overall Coach Copilot answer quality.",
            "Synthesis coverage can be intentionally low because the adaptive runner samples expensive LLM calls.",
            "A production-ready synthesis claim requires a separate semantic evaluation layer or reviewed benchmark set.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=None, help="Path to adaptive10h_*_cases.jsonl")
    parser.add_argument("--output-dir", default="outputs/agent_eval")
    parser.add_argument("--out", default=None, help="Optional output JSON path")
    args = parser.parse_args()

    cases_path = Path(args.cases).expanduser().resolve() if args.cases else _latest_cases(Path(args.output_dir))
    if not cases_path.exists():
        raise SystemExit(f"Cases file not found: {cases_path}")

    rows = _load_jsonl(cases_path)
    if not rows:
        raise SystemExit(f"No cases found in: {cases_path}")

    summary = summarize(rows, cases_path)

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
    else:
        stem = cases_path.name.replace("_cases.jsonl", "_split_metrics.json")
        out_path = cases_path.with_name(stem)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"split_metrics={out_path}")


if __name__ == "__main__":
    main()
