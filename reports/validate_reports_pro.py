"""Generate and validate professional TEAM / PLAYER / MATCH reports in demo mode."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("FPS_DEMO_MODE", "1")

from app.data_access import get_squad_summary, get_team_matches, list_teams  # noqa: E402
from app.presentation import demo_mode  # noqa: E402
from reports.data_builder import build_match_report_data, build_player_report_data, build_team_report_data  # noqa: E402
from reports.pdf_engine_elite_v2 import render_pdf_bytes  # noqa: E402
from reports.report_metrics import REPORT_METRIC_VERSION  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
OUTPUT_DIR = ROOT / "reports" / "output" / "professional_demo"
EXPECTED_SCHEMA = "0.6.0"


def _slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return text.strip("_") or "report"


def _write(name: str, payload: dict) -> tuple[Path, int]:
    pdf = render_pdf_bytes(payload)
    if not pdf.startswith(b"%PDF-"):
        raise AssertionError(f"{name}: output is not a PDF")
    if len(pdf) < 5000:
        raise AssertionError(f"{name}: PDF unexpectedly small ({len(pdf)} bytes)")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / name
    try:
        path.write_bytes(pdf)
    except PermissionError:
        fallback = OUTPUT_DIR / "_validation"
        fallback.mkdir(parents=True, exist_ok=True)
        path = fallback / name
        path.write_bytes(pdf)
    return path, len(pdf)


def _guardrails(payload: dict) -> None:
    guardrails = payload.get("guardrails") or {}
    for key in (
        "recommendation_policy_validated",
        "cross_player_ranking_allowed",
        "report_may_recalculate_critical_metrics",
        "report_may_issue_tactical_recommendation",
    ):
        if guardrails.get(key) is not False:
            raise AssertionError(f"Guardrail {key} must be False")


def _assert_absent(payloads: list[dict], raw_values: list[str]) -> None:
    text = json.dumps(payloads, ensure_ascii=False, default=str)
    leaked = sorted({value for value in raw_values if value and value in text})
    if leaked:
        raise AssertionError(f"Real identities leaked into demo payload: {leaked[:10]}")


def _assert_profile(payload: dict, key: str, minimum: int) -> None:
    profile = payload.get(key) or []
    if len(profile) < minimum:
        raise AssertionError(f"{payload.get('report_type')}: {key} has only {len(profile)} rows")
    for row in profile:
        if "label" not in row or "key" not in row:
            raise AssertionError(f"{payload.get('report_type')}: malformed technical profile row")


def main() -> None:
    if not demo_mode():
        raise SystemExit("REPORTS-PRO: FAIL - FPS_DEMO_MODE must be enabled")

    db_path = Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    teams = list_teams(db_path)
    if teams.empty:
        raise AssertionError("No team available")
    team_id = str(teams.iloc[0]["team_id"])
    raw_team = str(teams.iloc[0]["display_name"])

    squad = get_squad_summary(db_path, team_id)
    eligible = squad.loc[squad["appearances"] > 0]
    if eligible.empty:
        raise AssertionError("No player with appearance available")
    player_id = str(eligible.iloc[0]["player_id"])

    matches = get_team_matches(db_path, team_id)
    if matches.empty:
        raise AssertionError("No match available")
    match_id = str(matches.iloc[0]["match_id"])

    team_payload = build_team_report_data(db_path, team_id)
    player_payload = build_player_report_data(db_path, team_id, player_id)
    match_payload = build_match_report_data(db_path, team_id, match_id)
    payloads = [team_payload, player_payload, match_payload]

    for payload in payloads:
        _guardrails(payload)
        if payload.get("language") != "es":
            raise AssertionError("Report payload language must be es")
        if payload.get("demo_mode") is not True:
            raise AssertionError("Report payload must declare demo_mode=True")
        if payload.get("schema_version") != EXPECTED_SCHEMA:
            raise AssertionError(f"Unexpected schema: {payload.get('schema_version')}")
        if payload.get("report_metric_version") != REPORT_METRIC_VERSION:
            raise AssertionError(f"Unexpected report metric version: {payload.get('report_metric_version')}")

    if match_payload.get("match_summary") is None:
        raise AssertionError("Materialized match summary is required by the professional renderer")
    _assert_profile(team_payload, "technical_profile", 6)
    _assert_profile(player_payload, "technical_profile", 6)
    _assert_profile(match_payload, "technical_profile", 6)

    raw_players = squad["player"].astype(str).tolist() if "player" in squad.columns else []
    raw_opponents = matches["opponent"].astype(str).tolist() if "opponent" in matches.columns else []
    _assert_absent(payloads, [raw_team, *raw_players, *raw_opponents])

    outputs = [
        _write("team_professional_Equipo_Demo.pdf", team_payload),
        _write(f"player_professional_{_slug(player_payload['summary']['player'])}.pdf", player_payload),
        _write(f"match_professional_{_slug(match_payload['match']['opponent'])}.pdf", match_payload),
    ]

    print("REPORTS ELITE TECHNICAL GATE")
    print(f"schema={EXPECTED_SCHEMA}")
    print(f"report_metrics={REPORT_METRIC_VERSION}")
    print(f"team={team_payload['team']['display_name']}")
    print(f"player={player_payload['summary']['player']}")
    print(f"opponent={match_payload['match']['opponent']}")
    print("spanish=PASS")
    print("anonymization=PASS")
    print("technical_context=PASS")
    print("materialized_match_summary=PASS")
    print("critical_recalculation_guard=PASS")
    for path, size in outputs:
        print(f"PDF: {path} ({size} bytes)")
    print("REPORTS ELITE TECHNICAL GATE: PASS")


if __name__ == "__main__":
    main()
