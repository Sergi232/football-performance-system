"""Final non-destructive delivery audit for the TFM repository.

This checker does not rebuild analytics or modify files. It verifies that the main
academic/product documents are present, that canonical Coach Copilot results are
synchronized, and that the expected final screenshots exist when requested.

Usage:
    python -m publication.final_delivery_check --allow-missing-screenshots
    python -m publication.final_delivery_check
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "README.md",
    "PROJECT_STATE.md",
    "docs/FINAL_RELEASE_GATE.md",
    "docs/ARCHITECTURE.md",
    "docs/DECISIONS.md",
    "docs/WORKFLOW.md",
    "docs/TFM_MANUSCRIPT_DRAFT.md",
    "docs/TFM_METHODOLOGY_DRAFT.md",
    "docs/TFM_RESULTS_DRAFT.md",
    "docs/TFM_DISCUSSION_CONCLUSIONS_DRAFT.md",
    "docs/TFM_EVIDENCE_MATRIX.md",
    "docs/TFM_TABLES_RESULTS.md",
    "docs/TFM_ANNEXES_DRAFT.md",
    "docs/TFM_DEFENSE_OUTLINE.md",
    "docs/TFM_SCREENSHOT_CHECKLIST.md",
    "docs/TFM_SUBMISSION_CHECKLIST.md",
    "llm/COACH_COPILOT_CONTRACT.md",
    "llm/validate_coach_contract.py",
    "llm/smoke_test_coach_agent.py",
    "run_final_demo.ps1",
)

CANONICAL_COACH_DOCS = (
    "README.md",
    "PROJECT_STATE.md",
    "docs/FINAL_RELEASE_GATE.md",
    "docs/TFM_MANUSCRIPT_DRAFT.md",
    "docs/TFM_METHODOLOGY_DRAFT.md",
    "docs/TFM_RESULTS_DRAFT.md",
    "docs/TFM_EVIDENCE_MATRIX.md",
    "docs/TFM_TABLES_RESULTS.md",
    "docs/TFM_ANNEXES_DRAFT.md",
    "docs/TFM_DEFENSE_OUTLINE.md",
)

SCREENSHOTS = (
    "docs/screenshots/01_collector.png",
    "docs/screenshots/02_team_mode.png",
    "docs/screenshots/03_player_mode.png",
    "docs/screenshots/04_match_mode.png",
    "docs/screenshots/05_gps.png",
    "docs/screenshots/06_attention.png",
    "docs/screenshots/07_coach_copilot.png",
    "docs/screenshots/08_pdf_team.png",
    "docs/screenshots/09_pdf_player.png",
    "docs/screenshots/10_pdf_match.png",
)

FORBIDDEN_CURRENT_MARKERS = (
    "SMOKE CONTRACT: PASS (22/22)",
    "SMOKE CONTRACT = PASS (22/22)",
    "Smoke real | 22 / 22 PASS",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-missing-screenshots",
        action="store_true",
        help="Do not fail while the final screenshot pack is still being produced.",
    )
    args = parser.parse_args()

    failures: list[str] = []
    warnings: list[str] = []

    print("=" * 72)
    print("FOOTBALL PERFORMANCE SYSTEM · FINAL DELIVERY CHECK")
    print("=" * 72)

    for relative in REQUIRED_FILES:
        exists = (ROOT / relative).is_file()
        print(f"{'PASS' if exists else 'FAIL'} required file: {relative}")
        if not exists:
            failures.append(f"missing required file: {relative}")

    for relative in CANONICAL_COACH_DOCS:
        path = ROOT / relative
        if not path.is_file():
            continue
        text = _read(relative)
        has_final = "28/28" in text or "28 / 28" in text
        print(f"{'PASS' if has_final else 'FAIL'} final Coach metric present: {relative}")
        if not has_final:
            failures.append(f"final 28/28 metric missing: {relative}")
        for marker in FORBIDDEN_CURRENT_MARKERS:
            if marker in text:
                failures.append(f"stale Coach marker in {relative}: {marker}")
                print(f"FAIL stale marker: {relative} -> {marker}")

    screenshot_missing = [relative for relative in SCREENSHOTS if not (ROOT / relative).is_file()]
    for relative in SCREENSHOTS:
        exists = (ROOT / relative).is_file()
        status = "PASS" if exists else ("WARN" if args.allow_missing_screenshots else "FAIL")
        print(f"{status} screenshot: {relative}")

    if screenshot_missing:
        message = f"missing screenshots: {len(screenshot_missing)}/{len(SCREENSHOTS)}"
        if args.allow_missing_screenshots:
            warnings.append(message)
        else:
            failures.append(message)

    print("-" * 72)
    if warnings:
        for item in warnings:
            print(f"WARN: {item}")
    if failures:
        for item in failures:
            print(f"FAIL: {item}")
        print("FINAL DELIVERY CHECK: FAIL")
        return 1

    print("FINAL DELIVERY CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
