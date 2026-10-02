from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "collector" / "data_collector_futbol_v1.html"


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> None:
    html = HTML.read_text(encoding="utf-8")

    required = [
        'lang="es"',
        'opponentName',
        'shirtNumber',
        'starter',
        'Titular',
        'Suplente',
        "recordEvent('PASS','NORMAL','SUCCESS')",
        "recordEvent('PASS','LONG','FAIL')",
        "recordEvent('PASS','CROSS','SUCCESS')",
        "recordEvent('DRIBBLE',null,'FAIL')",
        "recordEvent('SHOT',null,'GOAL')",
        "recordEvent('SHOT',null,'ON_TARGET')",
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
        'e.outcome==="GOAL"||e.outcome==="ON_TARGET"',
        '@media(max-width:620px)',
        'min-height:48px',
    ]
    missing = [item for item in required if item not in html]
    if missing:
        fail("Collector V1 missing required fragments: " + ", ".join(missing))

    forbidden_visible = [
        ">Passada",
        ">Llarga",
        ">Centre",
        ">Assistència",
        ">Save<",
        ">Goal conceded<",
        "Clearance defensivo",
        "Tackle ganado/perdido",
        "falta_peligrosa",
    ]
    present = [item for item in forbidden_visible if item in html]
    if present:
        fail("Collector V1 still contains forbidden/legacy visible strings: " + ", ".join(present))

    print("COLLECTOR V1 CONTRACT: PASS")
    print("catalog_version=0.3.0")
    print("structured_opponent=PASS")
    print("editable_shirt_number=PASS")
    print("starter_substitute_explicit=PASS")
    print("shots_on_target_goal_plus_on_target=PASS")
    print("spanish_visible_labels=PASS")
    print("mobile_touch_targets=PASS")
    print("event_taxonomy_unchanged=PASS")


if __name__ == "__main__":
    main()
