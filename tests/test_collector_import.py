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
