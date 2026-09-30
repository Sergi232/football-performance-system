"""Audit summary for Coach Copilot self-improvement runs.

Separates router/tool quality from synthesis quality so a large volume of cheap
router passes can never inflate the reported final-answer success rate.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows


def rate(num: int, den: int) -> float | None:
    return (num / den) if den else None


def metric_block(rows: list[dict[str, Any]]) -> dict[str, Any]:
    router_n = len(rows)
    router_pass = sum(bool(r.get("router_pass")) for r in rows)
    synth = [r for r in rows if bool(r.get("synthesis_attempted"))]
    synth_n = len(synth)
    synth_pass = sum(r.get("synthesis_pass") is True for r in synth)
    e2e_pass = sum(bool(r.get("router_pass")) and r.get("synthesis_pass") is True for r in synth)
    return {
        "router_tools": {
            "cases": router_n,
            "passes": router_pass,
            "pass_rate": rate(router_pass, router_n),
        },
        "synthesis": {
            "attempts": synth_n,
            "passes": synth_pass,
            "pass_rate": rate(synth_pass, synth_n),
            "coverage": rate(synth_n, router_n),
        },
        "end_to_end_on_synthesis_cases": {
            "cases": synth_n,
            "passes": e2e_pass,
            "pass_rate": rate(e2e_pass, synth_n),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=None)
    parser.add_argument("--dir", default="outputs/agent_eval/self_improve")
    args = parser.parse_args()

    root = Path(args.dir)
    if args.input:
        source = Path(args.input)
    else:
        candidates = sorted(root.glob("agent_self_improve_*_cases.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise SystemExit(f"No self-improvement cases found under {root}")
        source = candidates[0]

    rows = load_jsonl(source)
    if not rows:
        raise SystemExit(f"No valid rows in {source}")

    category_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    language_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    classifications = Counter()
    mutation_triggers = Counter()
    extra_tools = Counter()
    missing_tools = Counter()

    for row in rows:
        category_rows[str(row.get("category", "UNKNOWN"))].append(row)
        language_rows[str(row.get("language", "UNKNOWN"))].append(row)
        classifications[str(row.get("classification", "UNKNOWN"))] += 1
        if row.get("mutation_trigger"):
            mutation_triggers[f"{row.get('mutation_tag')}|{row.get('classification')}"] += 1
        for tool in row.get("router_extra") or []:
            extra_tools[str(tool)] += 1
        for tool in row.get("router_missing") or []:
            missing_tools[str(tool)] += 1

    audited = {
        "source": str(source),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metric_block(rows),
        "by_category": {k: metric_block(v) for k, v in sorted(category_rows.items())},
        "by_language": {k: metric_block(v) for k, v in sorted(language_rows.items())},
        "classifications": dict(classifications),
        "root_cause_signals": {
            "mutation_triggers": mutation_triggers.most_common(20),
            "extra_tools": extra_tools.most_common(20),
            "missing_tools": missing_tools.most_common(20),
        },
        "interpretation": {
            "router_tools_pass_rate": "Routing/tool contract only; does not measure answer quality.",
            "synthesis_pass_rate": "Deterministic grounding/safety/runtime contract on cases where synthesis was attempted; not full semantic/coaching quality.",
            "human_review_required": True,
        },
    }

    root.mkdir(parents=True, exist_ok=True)
    run_id = source.stem.replace("agent_self_improve_", "").replace("_cases", "")
    output = root / f"agent_self_improve_{run_id}_audited_summary.json"
    latest = root / "audited_summary_latest.json"
    text = json.dumps(audited, ensure_ascii=False, indent=2)
    output.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")

    # Small stratified sample for later human review. Failures first, then passes,
    # capped to keep the review practical.
    synth_rows = [r for r in rows if bool(r.get("synthesis_attempted"))]
    review = sorted(synth_rows, key=lambda r: (r.get("synthesis_pass") is True, str(r.get("category")), int(r.get("case_no", 0))))[:24]
    review_path = root / f"agent_self_improve_{run_id}_human_review.csv"
    fields = ["case_no", "golden_id", "category", "language", "mutation_tag", "question", "classification", "synthesis_profile", "elapsed_total_s", "answer_preview"]
    with review_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in review:
            writer.writerow({key: row.get(key, "") for key in fields})

    print(json.dumps(audited, ensure_ascii=False, indent=2))
    print(f"audited_summary={output}")
    print(f"human_review={review_path}")


if __name__ == "__main__":
    main()
