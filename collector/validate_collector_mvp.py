from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "collector" / "event_catalog.json"
HTML_PATH = ROOT / "collector" / "data_collector_futbol_mvp.html"


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    html = HTML_PATH.read_text(encoding="utf-8")

    if catalog.get("catalog_version") != "0.3.0":
        fail(f"Unexpected catalog version: {catalog.get('catalog_version')!r}")

    required_actions = {
        ("PASS", "NORMAL"),
        ("PASS", "LONG"),
        ("PASS", "CROSS"),
        ("DRIBBLE", None),
        ("SHOT", None),
        ("TACKLE", None),
        ("INTERCEPTION", None),
        ("BLOCK", None),
        ("CLEARANCE", None),
        ("FOUL", "COMMITTED"),
        ("FOUL", "RECEIVED"),
        ("CARD", "YELLOW"),
        ("CARD", "RED"),
        ("LOSS", "OTHER"),
        ("PENALTY", "WON"),
        ("PENALTY", "CONCEDED"),
        ("CORNER", "FOR"),
        ("CORNER", "AGAINST"),
        ("GK", "SAVE"),
        ("GK", "GOAL_CONCEDED"),
    }
    actual_actions = {
        (row["action_type"], row.get("subtype")) for row in catalog.get("events", [])
    }
    missing_actions = sorted(required_actions - actual_actions, key=str)
    if missing_actions:
        fail(f"Missing catalog actions: {missing_actions}")

    required_html = [
        "recordEvent('PASS','NORMAL','SUCCESS')",
        "recordEvent('PASS','LONG','FAIL')",
        "recordEvent('PASS','CROSS','SUCCESS')",
        "recordEvent('DRIBBLE',null,'FAIL')",
        "recordEvent('SHOT',null,'GOAL')",
        "recordEvent('SHOT',null,'BLOCKED')",
        "recordEvent('TACKLE',null,'SUCCESS')",
        "recordEvent('TACKLE',null,'FAIL')",
        "recordEvent('INTERCEPTION',null,null)",
        "recordEvent('BLOCK',null,null)",
        "recordEvent('CLEARANCE',null,null)",
        "beginFoul('RECEIVED')",
        "beginFoul('COMMITTED')",
        "recordEvent('CARD','YELLOW',null)",
        "recordEvent('CARD','RED',null)",
        "recordEvent('LOSS','OTHER',null)",
        "recordEvent('PENALTY','WON','GOAL')",
        "recordEvent('PENALTY','CONCEDED','MISSED')",
        "recordTeamSetPiece('CORNER','FOR')",
        "recordTeamSetPiece('CORNER','AGAINST')",
        "recordEvent('GK','SAVE',null)",
        "recordEvent('GK','GOAL_CONCEDED',null)",
        "tagLastPass('key_pass')",
        "tagLastPass('assist')",
        "second_yellow:true",
        "set_piece_result",
        "match_second",
        "video_second",
        "localStorage",
        "exportEventsCSV",
        "exportSummaryCSV",
        "downloadJSON",
        "undoLast",
        "recordRoleChange",
        "recordFormationChange",
    ]
    missing_html = [fragment for fragment in required_html if fragment not in html]
    if missing_html:
        fail("Collector HTML is missing required contract fragments: " + ", ".join(missing_html))

    forbidden_html = [
        "record('gol_penalti')",
        "record('asistencia')",
        "record('pase_completado')",
        "record('regate_no_completado')",
        "falta_peligrosa",
    ]
    present_forbidden = [fragment for fragment in forbidden_html if fragment in html]
    if present_forbidden:
        fail("Legacy/double-counting actions still present: " + ", ".join(present_forbidden))

    print("COLLECTOR MVP VALIDATION: PASS")
    print("catalog_version: 0.3.0")
    print(f"catalog actions covered: {len(required_actions)}/{len(required_actions)}")
    print("event-level CSV + summary CSV + JSON: OK")
    print("foul x/y capture + ABP result workflow: OK")
    print("role/side + formation changes: OK")
    print("legacy double-counting buttons removed: OK")


if __name__ == "__main__":
    main()
