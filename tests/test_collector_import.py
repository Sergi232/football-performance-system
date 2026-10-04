from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data"))
from import_collector_export import SOURCE_TYPE, import_collector_export  # noqa: E402
from init_database import initialize_database  # noqa: E402

FIXTURE = ROOT / "collector" / "fixtures" / "collector_export_v1_1.json"


def prepared_db(tmp_path: Path) -> Path:
    db = tmp_path / "collector.duckdb"
    initialize_database(db)
    return db


def test_collector_json_import_is_idempotent_and_preserves_events(tmp_path: Path) -> None:
    db = prepared_db(tmp_path)
    first = import_collector_export(FIXTURE, db)
    second = import_collector_export(FIXTURE, db)
    assert first["match_id"] == second["match_id"]
    with duckdb.connect(str(db), read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM player_match").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM match_events WHERE source_type=?", [SOURCE_TYPE]).fetchone()[0] == 6
        raw = con.execute("SELECT passes_total, passes_completed, turnovers, tackles_total, fouls_committed FROM player_match_raw_stats WHERE source_player_id='P01'").fetchone()
        assert raw == (2, 1, 1, 1, 1)
        assert con.execute("SELECT COUNT(*) FROM player_role_stints WHERE source_type=?", [SOURCE_TYPE]).fetchone()[0] == 3


def test_collector_json_rejects_catalog_mismatch(tmp_path: Path) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["catalog_version"] = "broken"
    export = tmp_path / "invalid.json"
    export.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="catalog_version"):
        import_collector_export(export, prepared_db(tmp_path))


def test_collector_import_reaches_feature_engine(tmp_path: Path) -> None:
    db = prepared_db(tmp_path)
    import_collector_export(FIXTURE, db)
    subprocess.run([sys.executable, str(ROOT / "features" / "build_player_match_features.py"), "--db", str(db), "--raw-source-type", SOURCE_TYPE], check=True, cwd=ROOT)
    with duckdb.connect(str(db), read_only=True) as con:
        value = con.execute("SELECT feature_value FROM player_match_features f JOIN player_match_raw_stats r USING(match_id, player_id) WHERE r.source_player_id='P01' AND f.feature_name='pass_completion_rate'").fetchone()[0]
        assert value == pytest.approx(0.5)


def test_collector_presentation_queries_keep_raw_event_and_role_trace(tmp_path: Path) -> None:
    """The dashboard queries expose imported Collector facts without new metrics."""
    db = prepared_db(tmp_path)
    result = import_collector_export(FIXTURE, db)

    from app.data_access import get_match_event_log, get_match_lineup, get_team_matches

    team_id, match_id = str(result["team_id"]), str(result["match_id"])
    matches = get_team_matches(db, team_id)
    assert len(matches) == 1
    assert matches.iloc[0]["corners_for"] == 1
    assert matches.iloc[0]["fouls_committed"] == 1

    lineup = get_match_lineup(db, team_id, match_id)
    p01 = lineup.loc[lineup["player"] == "Jugador 01"].iloc[0]
    assert p01["passes_total"] == 2
    assert p01["long_balls_total"] == 1
    assert p01["fouls_committed"] == 1
    assert "Central" in str(p01["observed_role_stints"])
    assert "Mediocentro" in str(p01["observed_role_stints"])

    events = get_match_event_log(db, team_id, match_id)
    assert len(events) == 6
    foul = events.loc[events["action_type"] == "FOUL"].iloc[0]
    assert (foul["x"], foul["y"]) == (80.0, 20.0)
    assert "NO_SHOT" in str(foul["qualifiers"])
    corner = events.loc[events["action_type"] == "CORNER"].iloc[0]
    assert "SHOT_AFTER_RESTART" in str(corner["qualifiers"])
