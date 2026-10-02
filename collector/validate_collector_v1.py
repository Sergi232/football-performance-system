from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "collector" / "data_collector_futbol_v1.html"
ENTRY = ROOT / "collector" / "data_collector_futbol.html"
CATALOG = ROOT / "collector" / "event_catalog.json"


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> None:
    html = HTML.read_text(encoding="utf-8")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    required = [
        'lang="es"', 'Captura manual v1.1', 'collector_version:"1.1.0"',
        'opponentName', 'shirtNumber', 'starter', 'Titular', 'Suplente',
        "recordEvent('PASS','NORMAL','SUCCESS')", "recordEvent('PASS','LONG','FAIL')",
        "recordEvent('PASS','CROSS','SUCCESS')", "recordEvent('DRIBBLE',null,'FAIL')",
        "recordEvent('SHOT',null,'GOAL')", "recordEvent('SHOT',null,'ON_TARGET')",
        "recordEvent('SHOT',null,'BLOCKED')", "recordEvent('TACKLE',null,'SUCCESS')",
        "recordEvent('TACKLE',null,'FAIL')", "recordEvent('INTERCEPTION',null,null)",
        "recordEvent('BLOCK',null,null)", "recordEvent('CLEARANCE',null,null)",
        "beginFoul('RECEIVED')", "beginFoul('COMMITTED')", "recordEvent('CARD','YELLOW',null)",
        "recordEvent('CARD','RED',null)", "recordEvent('LOSS','OTHER',null)",
        "recordEvent('PENALTY','WON','GOAL')", "recordEvent('PENALTY','CONCEDED','MISSED')",
        "recordTeamSetPiece('CORNER','FOR')", "recordTeamSetPiece('CORNER','AGAINST')",
        "recordEvent('GK','SAVE',null)", "recordEvent('GK','GOAL_CONCEDED',null)",
        "tagLastPass('key_pass')", "tagLastPass('assist')", "second_yellow:true", "set_piece_result",
        "match_second", "video_second", "localStorage", "exportEventsCSV", "exportSummaryCSV",
        "downloadJSON", "undoLast", "recordRoleChange", "recordFormationChange",
        'e.outcome==="GOAL"||e.outcome==="ON_TARGET"', '@media(max-width:620px)', 'min-height:48px',
        'class="sr-only" for="${shirtId}"', 'id="${shirtId}" name="${shirtId}"',
        'id="${nameId}" name="${nameId}"', 'id="${statusId}" name="${statusId}"',
        'suspiciousStarterState=savedEvents.length===0&&starterCount>11',
    ]
    missing = [item for item in required if item not in html]
    if missing:
        fail("Collector V1.1 missing required fragments: " + ", ".join(missing))

    forbidden = [
        ">Passada", ">Llarga", ">Centre", ">AssistÃ¨ncia", ">Save<", ">Goal conceded<",
        "Clearance defensivo", "Tackle ganado/perdido", "falta_peligrosa",
        '.header-inner .optional-head{display:none}',
        '.header-inner>div:not(.brand):nth-of-type(n+4){display:none}',
        '<summary><span>Ãšltimas acciones</span><button',
        'function updateStarter(i,v){state.players[i].starter=v==="1";renderAll()}',
    ]
    present = [item for item in forbidden if item in html]
    if present:
        fail("Collector V1.1 contains forbidden/legacy fragments: " + ", ".join(present))

    if catalog.get("catalog_version") != "0.3.0":
        fail(f"Unexpected catalog version: {catalog.get('catalog_version')!r}")

    entry = ENTRY.read_text(encoding="utf-8")
    if "data_collector_futbol_v1.html" not in entry:
        fail("Official collector entrypoint does not point to V1.1 implementation")

    print("COLLECTOR V1.1 FINAL GATE: PASS")
    print("catalog_version=0.3.0")
    print("structured_opponent=PASS")
    print("editable_shirt_number=PASS")
    print("starter_substitute_explicit=PASS")
    print("starter_minutes_consistency_guard=PASS")
    print("shots_on_target_goal_plus_on_target=PASS")
    print("spanish_visible_labels=PASS")
    print("responsive_metadata_access=PASS")
    print("mobile_touch_targets=PASS")
    print("dynamic_form_ids_names_labels=PASS")
    print("summary_interactive_element_guard=PASS")
    print("event_taxonomy_unchanged=PASS")
    print("official_entrypoint=PASS")


if __name__ == "__main__":
    main()
