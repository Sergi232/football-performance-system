"""REPORTS-01 local validation + demo PDF generation."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import get_squad_summary, get_team_matches, list_teams  # noqa: E402
from reports.data_builder import (  # noqa: E402
    build_match_report_data,
    build_player_report_data,
    build_team_report_data,
)
from reports.pdf_engine import render_pdf_bytes  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
OUTPUT_DIR = ROOT / "reports" / "output"


def _slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return text.strip("_") or "report"


def _write_pdf(name: str, payload: dict) -> tuple[Path, int]:
    pdf = render_pdf_bytes(payload)
    if not pdf.startswith(b"%PDF-"):
        raise AssertionError(f"{name}: output is not a PDF")
    if len(pdf) < 1000:
        raise AssertionError(f"{name}: PDF unexpectedly small ({len(pdf)} bytes)")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / name
    try:
        path.write_bytes(pdf)
    except PermissionError:
        # Windows locks a PDF that is open in some viewers. Validation must not fail
        # merely because an earlier report is being inspected by the user.
        fallback_dir = OUTPUT_DIR / "_validation"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        original = Path(name)
        path = fallback_dir / f"{original.stem}_{os.getpid()}{original.suffix}"
        path.write_bytes(pdf)
    return path, len(pdf)


def _validate_guardrails(payload: dict) -> None:
    guardrails = payload.get("guardrails") or {}
    expected_false = [
        "recommendation_policy_validated",
        "cross_player_ranking_allowed",
        "report_may_recalculate_critical_metrics",
        "report_may_issue_tactical_recommendation",
    ]
    for key in expected_false:
        if guardrails.get(key) is not False:
            raise AssertionError(f"Guardrail {key} must be False")


def main() -> None:
    db_path = Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    teams = list_teams(db_path)
    if teams.empty:
        raise AssertionError("No team available")
    team_id = str(teams.iloc[0]["team_id"])
    team_name = str(teams.iloc[0]["display_name"])

    squad = get_squad_summary(db_path, team_id)
    eligible = squad.loc[squad["appearances"] > 0]
    if eligible.empty:
        raise AssertionError("No player with an appearance available")
    player_id = str(eligible.iloc[0]["player_id"])
    player_name = str(eligible.iloc[0]["player"])

    matches = get_team_matches(db_path, team_id)
    if matches.empty:
        raise AssertionError("No match available")
    match_id = str(matches.iloc[0]["match_id"])
    opponent = str(matches.iloc[0]["opponent"])

    team_payload = build_team_report_data(db_path, team_id)
    player_payload = build_player_report_data(db_path, team_id, player_id)
    match_payload = build_match_report_data(db_path, team_id, match_id)

    for payload in (team_payload, player_payload, match_payload):
        _validate_guardrails(payload)

    gate = player_payload.get("latest_role_fit_gate") or {}
    final_status = gate.get("final_status")
    if final_status and not str(final_status).startswith("RECOMMENDATION_NOT_ISSUED_"):
        raise AssertionError(f"Unsafe final recommendation state in report payload: {final_status}")

    outputs = [
        _write_pdf(f"team_{_slug(team_name)}.pdf", team_payload),
        _write_pdf(f"player_{_slug(player_name)}.pdf", player_payload),
        _write_pdf(f"match_{_slug(opponent)}.pdf", match_payload),
    ]

    print("REPORTS-01 PDF CONTRACT: PASS")
    print(f"team: {team_name}")
    print(f"player: {player_name}")
    print(f"match opponent: {opponent}")
    print(f"team payload matches: {len(team_payload['matches'])}")
    print(f"team payload squad: {len(team_payload['squad'])}")
    print(f"match lineup rows: {len(match_payload['lineup'])}")
    print("recommendation/report guardrails: PASS")
    for path, size in outputs:
        print(f"PDF: {path} ({size} bytes)")
    print("No critical metric, ranking, score or tactical recommendation was created by the report layer.")


if __name__ == "__main__":
    main()
