"""Validate Spanish + anonymized Team / Player / Match PDF exports."""
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
from reports.pdf_engine_es import render_pdf_bytes  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
OUTPUT_DIR = ROOT / "reports" / "output" / "demo_es"


def _slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return text.strip("_") or "report"


def _write(name: str, payload: dict) -> tuple[Path, int]:
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
        fallback_dir = OUTPUT_DIR / "_validation"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        original = Path(name)
        path = fallback_dir / f"{original.stem}_{os.getpid()}{original.suffix}"
        path.write_bytes(pdf)
    return path, len(pdf)


def _guardrails(payload: dict) -> None:
    expected_false = (
        "recommendation_policy_validated",
        "cross_player_ranking_allowed",
        "report_may_recalculate_critical_metrics",
        "report_may_issue_tactical_recommendation",
    )
    guardrails = payload.get("guardrails") or {}
    for key in expected_false:
        if guardrails.get(key) is not False:
            raise AssertionError(f"Guardrail {key} must be False")


def _assert_absent(payloads: list[dict], raw_values: list[str]) -> None:
    text = json.dumps(payloads, ensure_ascii=False, default=str)
    leaked = sorted({value for value in raw_values if value and value in text})
    if leaked:
        raise AssertionError(f"Real identities leaked into demo payload: {leaked[:10]}")


def main() -> None:
    if not demo_mode():
        raise SystemExit("REPORTS-02: FAIL — FPS_DEMO_MODE must be enabled")

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

    if not str(team_payload["team"]["display_name"]).startswith("Equipo Demo"):
        raise AssertionError("Team identity is not anonymized")
    if not str(player_payload["summary"].get("player", "")).startswith("Jugador "):
        raise AssertionError("Player identity is not anonymized")
    if not str(match_payload["match"].get("opponent", "")).startswith("Rival "):
        raise AssertionError("Opponent identity is not anonymized")

    raw_players = squad.get("player", []).astype(str).tolist() if "player" in squad.columns else []
    raw_opponents = matches.get("opponent", []).astype(str).tolist() if "opponent" in matches.columns else []
    _assert_absent(payloads, [raw_team, *raw_players, *raw_opponents])

    outputs = [
        _write("team_Equipo_Demo.pdf", team_payload),
        _write(f"player_{_slug(player_payload['summary']['player'])}.pdf", player_payload),
        _write(f"match_{_slug(match_payload['match']['opponent'])}.pdf", match_payload),
    ]

    print("REPORTS-02 SPANISH DEMO CONTRACT")
    print(f"schema={team_payload.get('schema_version')}")
    print(f"team={team_payload['team']['display_name']}")
    print(f"player={player_payload['summary']['player']}")
    print(f"opponent={match_payload['match']['opponent']}")
    print("language_es=PASS")
    print("anonymization=PASS")
    print("real_identity_leak_payload=0")
    print("guardrails=PASS")
    for path, size in outputs:
        print(f"PDF: {path} ({size} bytes)")
    print("REPORTS-02 PDF CONTRACT: PASS")


if __name__ == "__main__":
    main()
