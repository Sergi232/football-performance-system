import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "collector" / "event_catalog.json"
HTML = ROOT / "collector" / "data_collector_futbol_v1.html"


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def load_html():
    return HTML.read_text(encoding="utf-8")


def test_catalog_version_and_required_actions():
    catalog = load_catalog()
    assert catalog["catalog_version"] == "0.3.0"

    actions = {
        (e["action_type"], e.get("subtype"), tuple(e.get("outcomes", [])))
        for e in catalog["events"]
    }

    required = {
        ("PASS", "NORMAL", ("SUCCESS", "FAIL")),
        ("PASS", "LONG", ("SUCCESS", "FAIL")),
        ("PASS", "CROSS", ("SUCCESS", "FAIL")),
        ("DRIBBLE", None, ("SUCCESS", "FAIL")),
        ("SHOT", None, ("GOAL", "ON_TARGET", "OFF_TARGET", "BLOCKED")),
        ("TACKLE", None, ("SUCCESS", "FAIL")),
        ("INTERCEPTION", None, ()),
        ("BLOCK", None, ()),
        ("CLEARANCE", None, ()),
        ("FOUL", "COMMITTED", ()),
        ("FOUL", "RECEIVED", ()),
        ("CARD", "YELLOW", ()),
        ("CARD", "RED", ()),
        ("LOSS", "OTHER", ()),
        ("PENALTY", "WON", ("GOAL", "MISSED")),
        ("PENALTY", "CONCEDED", ("GOAL", "MISSED")),
        ("CORNER", "FOR", ()),
        ("CORNER", "AGAINST", ()),
        ("GK", "SAVE", ()),
        ("GK", "GOAL_CONCEDED", ()),
    }
    assert required <= actions


def test_collector_implements_catalog_contract():
    html = load_html()

    required_fragments = [
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
        "video_second",
        "match_second",
        "localStorage",
        "exportEventsCSV",
        "exportSummaryCSV",
        "downloadJSON",
        "undoLast",
        "loadBulkNames",
        "recordRoleChange",
        "recordFormationChange",
    ]
    for fragment in required_fragments:
        assert fragment in html, fragment


def test_collector_avoids_old_double_counting_actions():
    html = load_html()
    forbidden = [
        "record('gol_penalti')",
        "record('asistencia')",
        "record('pase_completado')",
        "record('regate_no_completado')",
        "Pérdida manual",
        "falta_peligrosa",
    ]
    for fragment in forbidden:
        assert fragment not in html, fragment


def test_set_piece_result_values_are_auditable():
    catalog = load_catalog()
    qualifier = next(q for q in catalog["qualifiers"] if q["name"] == "set_piece_result")
    assert qualifier["allowed_values"] == [
        "DIRECT_SHOT",
        "SHOT_AFTER_RESTART",
        "GOAL",
        "NO_SHOT",
    ]
