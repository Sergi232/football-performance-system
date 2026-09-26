"""DB-free Product Spiral Lab.

Uses the real GitHub UI/PDF code plus deterministic synthetic fixtures that reproduce
production field shapes. This is designed for a second/work PC that must not download
private data or large local models.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from collections import Counter, deque
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import run_product_spiral as spiral  # noqa: E402
from product.synthetic_fixtures import mutated_payload, scenario_payloads  # noqa: E402
from reports.pdf_engine import render_pdf_bytes  # noqa: E402


def _ensure_git_identity() -> None:
    """Set repository-local identity only when absent; never changes global Git config."""
    ok_name, _, name = spiral._run(["git", "config", "--local", "user.name"], timeout=20)
    ok_mail, _, mail = spiral._run(["git", "config", "--local", "user.email"], timeout=20)
    if not ok_name or not name.strip():
        spiral._run(["git", "config", "--local", "user.name", "Product Spiral Lab"], timeout=20)
    if not ok_mail or not mail.strip():
        spiral._run(["git", "config", "--local", "user.email", "product-spiral@local.invalid"], timeout=20)


def _probe(label: str, payload: dict) -> dict:
    started = time.perf_counter()
    guardrails = payload.get("guardrails") or {}
    unsafe = any(
        guardrails.get(key) is not False
        for key in (
            "recommendation_policy_validated",
            "cross_player_ranking_allowed",
            "report_may_recalculate_critical_metrics",
            "report_may_issue_tactical_recommendation",
        )
    )
    try:
        pdf = render_pdf_bytes(payload)
        pdf_ok = pdf.startswith(b"%PDF-") and len(pdf) >= 1000
        approx_pages = max(1, len(re.findall(rb"/Type\s*/Page\b", pdf))) if pdf_ok else 0
        error = ""
    except Exception as exc:  # stress harness must record and continue
        pdf = b""
        pdf_ok = False
        approx_pages = 0
        error = repr(exc)
    elapsed = time.perf_counter() - started
    return {
        "timestamp": spiral._utc_now(),
        "kind": payload.get("report_type", "unknown"),
        "team_id": "SYNTHETIC",
        "entity_id": label,
        "label": label,
        "pass": bool(pdf_ok and not unsafe),
        "classification": "OK" if pdf_ok and not unsafe else ("GUARDRAIL_FAIL" if unsafe else "PDF_RENDER_FAIL"),
        "pdf_bytes": len(pdf),
        "approx_pages": approx_pages,
        "elapsed_s": round(elapsed, 3),
        "unsafe_guardrail": unsafe,
        "match_rating_version": payload.get("match_rating_version"),
        "engine_version": payload.get("engine_version"),
        "error": error,
    }


def _static_web_audit() -> dict:
    """Code-level product audit usable without starting Streamlit or opening a private DB."""
    app = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    ui = (ROOT / "app" / "ui_theme.py").read_text(encoding="utf-8")
    coach = (ROOT / "app" / "coach_ui.py").read_text(encoding="utf-8")
    pages = sorted((ROOT / "app" / "pages").glob("*.py"))
    page_text = "\n".join(p.read_text(encoding="utf-8") for p in pages)
    checks = {
        "command_center_present": "Coach Command Center" in app or "Centre de comandament" in app,
        "shared_theme": "apply_professional_theme" in ui,
        "shared_navigation": "sidebar_navigation" in ui,
        "responsive_css": "@media (max-width:" in ui,
        "page_header_component": "def page_header" in coach,
        "metric_component": "def metric_card" in coach,
        "insight_component": "def insight_card" in coach,
        "plotly_shared_layout": "def _base_layout" in coach,
        "seven_product_pages": len(pages) >= 7,
        "pdf_downloads_present": "download_button" in page_text.lower(),
        "match_rating_visible": "Match Rating" in page_text,
    }
    passed = sum(checks.values())
    return {"pass": passed == len(checks), "score": round(100 * passed / len(checks), 2), "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=10.0)
    parser.add_argument("--max-cases", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=26092026)
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = spiral.OUTPUT_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    protected_dirty = spiral._protected_dirty_paths()
    if protected_dirty:
        raise SystemExit("Protected files are modified locally; refusing product spiral: " + ", ".join(protected_dirty))

    _ensure_git_identity()
    branch = spiral._ensure_local_branch(run_id)

    baseline = spiral.audit_repository()
    bootstrap = spiral.run_contract_gates(False)
    web_audit = _static_web_audit()
    if not bootstrap["all_pass"]:
        spiral._write_json(run_dir / "bootstrap_failure.json", bootstrap)
        raise SystemExit(f"Bootstrap contracts failed. See {run_dir / 'bootstrap_failure.json'}")

    print("=" * 96)
    print("FOOTBALL PERFORMANCE SYSTEM · PRODUCT SPIRAL LAB · DB-FREE")
    print(f"branch={branch}")
    print(f"hours={args.hours:g} synthetic_product_fixtures=True private_db_download=False")
    print(f"baseline_product_quality={baseline['score']:.2f}/100 web_source_audit={web_audit['score']:.2f}/100")
    print("Uses real GitHub UI/PDF code + synthetic contract-compatible fixtures. No Ollama/model/data download.")
    print("Analytics, ratings, expert thresholds, LLM and production DB remain protected.")
    print("=" * 96)

    recipe_log = []
    for recipe in spiral.RECIPES:
        result = spiral.apply_recipe(recipe, False)
        recipe_log.append(result)
        print(f"RECIPE {recipe.name}: {result.get('status')} score={result.get('after_score', result.get('before_score', '—'))}")
        spiral._write_json(run_dir / "recipes.json", recipe_log)

    base_cases = scenario_payloads(args.seed)
    queue: deque[tuple[str, dict]] = deque(base_cases)
    failures: Counter[str] = Counter()
    cases_done = 0
    passes = 0
    deadline = time.monotonic() + max(0.0, args.hours) * 3600.0
    next_gate = time.monotonic() + 15 * 60
    next_checkpoint = time.monotonic()
    case_csv = run_dir / "cases.csv"

    while cases_done < args.max_cases and time.monotonic() < deadline:
        if queue and rng.random() < 0.70:
            label, payload = queue.popleft()
        else:
            label, payload = rng.choice(base_cases)
            label, payload = mutated_payload(label, payload, args.seed + cases_done)

        row = _probe(label, payload)
        cases_done += 1
        if row["pass"]:
            passes += 1
        else:
            failures[row["classification"]] += 1
            # Failure replay: test the exact case repeatedly and nearby bounded mutations.
            queue.appendleft((label, payload))
            mlabel, mpayload = mutated_payload(label, payload, args.seed + cases_done * 17)
            queue.appendleft((mlabel, mpayload))

        spiral._append_csv(case_csv, row)
        if not row["pass"] or cases_done % 50 == 0:
            print(
                f"[{cases_done:06d}] {'PASS' if row['pass'] else 'FAIL'} {row['kind']:<6} "
                f"{row['classification']:<18} {row['elapsed_s']:.2f}s queue={len(queue)}"
            )

        now = time.monotonic()
        if now >= next_gate:
            gates = spiral.run_contract_gates(False)
            web_audit = _static_web_audit()
            spiral._write_json(run_dir / "latest_gates.json", {"contracts": gates, "web_audit": web_audit})
            if not gates["all_pass"]:
                failures["REGRESSION_GATE_FAIL"] += 1
                print("REGRESSION GATE FAIL — stopping safely; diagnostics saved.")
                break
            next_gate = now + 15 * 60

        if now >= next_checkpoint:
            checkpoint = {
                "run_id": run_id,
                "updated_at": spiral._utc_now(),
                "mode": "DB_FREE_SYNTHETIC",
                "branch": branch,
                "baseline_quality": baseline,
                "current_quality": spiral.audit_repository(),
                "web_source_audit": _static_web_audit(),
                "recipes": recipe_log,
                "cases": cases_done,
                "passes": passes,
                "pass_rate": passes / cases_done if cases_done else None,
                "failures": dict(failures),
                "private_db_downloaded": False,
                "ollama_or_model_downloaded": False,
            }
            spiral._write_json(run_dir / "checkpoint.json", checkpoint)
            next_checkpoint = now + 5 * 60

    final_gates = spiral.run_contract_gates(False)
    final = {
        "run_id": run_id,
        "finished_at": spiral._utc_now(),
        "mode": "DB_FREE_SYNTHETIC",
        "branch": branch,
        "baseline_quality": baseline,
        "final_quality": spiral.audit_repository(),
        "web_source_audit": _static_web_audit(),
        "recipes": recipe_log,
        "cases": cases_done,
        "passes": passes,
        "pass_rate": passes / cases_done if cases_done else None,
        "failures": dict(failures),
        "final_gates": final_gates,
        "case_csv": str(case_csv),
        "private_db_downloaded": False,
        "ollama_or_model_downloaded": False,
        "note": "Synthetic contract QA is not a replacement for the final visual/data gate on the real DB.",
    }
    spiral._write_json(run_dir / "final_summary.json", final)

    print("=" * 96)
    print("PRODUCT SPIRAL COMPLETE · DB-FREE")
    print(f"quality: {baseline['score']:.2f} -> {final['final_quality']['score']:.2f}")
    print(f"cases={cases_done} passes={passes} pass_rate={(passes / cases_done):.3f}" if cases_done else "cases=0")
    print(f"final_contracts={'PASS' if final_gates['all_pass'] else 'FAIL'}")
    print(f"summary={run_dir / 'final_summary.json'}")


if __name__ == "__main__":
    main()
