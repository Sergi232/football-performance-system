"""Validate descriptive GPS physical summary logic without requiring real GPS data."""
from __future__ import annotations

import argparse
import math
import sys
import tempfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
ANALYTICS = ROOT / "analytics"
if str(ANALYTICS) not in sys.path:
    sys.path.insert(0, str(ANALYTICS))

from build_gps_physical_summary import SUMMARY_VERSION, materialize  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"


def build_fixture(db: Path) -> None:
    """Create one player-match with an older real import and a newer synthetic import."""
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE TABLE matches(match_id VARCHAR, match_date TIMESTAMP)")
        con.execute("CREATE TABLE player_match(match_id VARCHAR, team_id VARCHAR, player_id VARCHAR)")
        con.execute(
            """
            CREATE TABLE gps_imports(
                gps_import_id VARCHAR,
                provider VARCHAR,
                source_format VARCHAR,
                source_filename VARCHAR,
                imported_at TIMESTAMP
            )
            """
        )
        con.execute(
            """
            CREATE TABLE gps_observations(
                gps_import_id VARCHAR, match_id VARCHAR, player_id VARCHAR,
                timestamp_ms BIGINT, distance_m DOUBLE, speed_m_s DOUBLE,
                acceleration_m_s2 DOUBLE, quality_flags JSON
            )
            """
        )
        con.execute("INSERT INTO matches VALUES ('M1', '2026-01-01 18:00:00')")
        con.execute("INSERT INTO player_match VALUES ('M1','T1','P1')")
        con.execute(
            """
            INSERT INTO gps_imports VALUES
            ('I_REAL','Fixture Provider','fixture_csv','real.csv','2026-01-01 19:00:00'),
            ('I_SYN','FPS Synthetic Demo','synthetic_demo','synthetic.csv','2026-01-01 20:00:00')
            """
        )
        con.execute(
            """
            INSERT INTO gps_observations VALUES
            ('I_REAL','M1','P1',0,NULL,0.0,0.0,NULL),
            ('I_REAL','M1','P1',1000,5.0,5.0,1.0,NULL),
            ('I_REAL','M1','P1',2000,6.0,6.0,-2.0,'["CHECK"]'),
            ('I_SYN','M1','P1',0,50.0,8.0,2.0,NULL),
            ('I_SYN','M1','P1',1000,50.0,9.0,-3.0,NULL)
            """
        )


def validate_fixture() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "gps_fixture.duckdb"
        build_fixture(db)
        summary = materialize(db)
        assert summary == {"summary_rows": 2, "latest_rows": 1, "matches": 1, "players": 1, "imports": 2}

        with duckdb.connect(str(db), read_only=True) as con:
            row = con.execute(
                """
                SELECT provider, source_format, source_priority, import_rank,
                       sample_count, distance_sample_count, speed_sample_count,
                       acceleration_sample_count, total_distance_m, peak_speed_m_s,
                       max_acceleration_m_s2, min_acceleration_m_s2,
                       observation_duration_s, distance_coverage_pct,
                       quality_metadata_sample_count, summary_version
                FROM player_match_gps_summary
                WHERE import_rank=1
                """
            ).fetchone()
            ranks = con.execute(
                """
                SELECT provider, source_priority, import_rank
                FROM player_match_gps_summary
                ORDER BY import_rank
                """
            ).fetchall()

        assert row[0] == "Fixture Provider"
        assert row[1] == "fixture_csv"
        assert row[2] == 0
        assert row[3] == 1
        assert row[4:8] == (3, 2, 3, 3)
        assert math.isclose(row[8], 11.0)
        assert math.isclose(row[9], 6.0)
        assert math.isclose(row[10], 1.0)
        assert math.isclose(row[11], -2.0)
        assert math.isclose(row[12], 2.0)
        assert math.isclose(row[13], 100.0 * 2 / 3)
        assert row[14] == 1
        assert row[15] == SUMMARY_VERSION
        assert ranks == [
            ("Fixture Provider", 0, 1),
            ("FPS Synthetic Demo", 1, 2),
        ]


def validate_database(db: Path) -> dict[str, int]:
    with duckdb.connect(str(db), read_only=True) as con:
        tables = {
            r[0]
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
        }
        if "player_match_gps_summary" not in tables:
            raise RuntimeError("player_match_gps_summary missing. Run analytics/build_gps_physical_summary.py first.")
        obs = int(con.execute("SELECT COUNT(*) FROM gps_observations").fetchone()[0])
        rows = int(
            con.execute(
                "SELECT COUNT(*) FROM player_match_gps_summary WHERE summary_version=?",
                [SUMMARY_VERSION],
            ).fetchone()[0]
        )
        latest = int(
            con.execute(
                "SELECT COUNT(*) FROM player_match_gps_summary WHERE summary_version=? AND import_rank=1",
                [SUMMARY_VERSION],
            ).fetchone()[0]
        )
        dup = int(
            con.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT match_id, player_id, COUNT(*) AS n
                    FROM player_match_gps_summary
                    WHERE summary_version=? AND import_rank=1
                    GROUP BY match_id, player_id
                    HAVING COUNT(*) > 1
                )
                """,
                [SUMMARY_VERSION],
            ).fetchone()[0]
        )
        if obs > 0 and rows == 0:
            raise RuntimeError("GPS observations exist but no descriptive summaries were materialized")
        if dup != 0:
            raise RuntimeError(f"Duplicate latest GPS summaries detected: {dup}")
    return {"gps_observations": obs, "summary_rows": rows, "latest_rows": latest}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate descriptive GPS physical summary")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(f"Database not found: {db}")
    validate_fixture()
    status = validate_database(db)
    print("GPS PHYSICAL SUMMARY CONTRACT: PASS")
    print(f"summary_version={SUMMARY_VERSION}")
    print("source_precedence_fixture=REAL_OVER_SYNTHETIC:PASS")
    print("fixture_selected_total_distance_m=11.0")
    print("fixture_selected_peak_speed_m_s=6.0")
    print("fixture_selected_max_acceleration_m_s2=1.0")
    print("fixture_selected_min_acceleration_m_s2=-2.0")
    print(f"db_gps_observations={status['gps_observations']}")
    print(f"db_summary_rows={status['summary_rows']}")
    print(f"db_latest_rows={status['latest_rows']}")
    print("GPS remains optional; zero database rows is a valid product state.")
    print("No HSR/sprint/workload/fatigue threshold was introduced.")


if __name__ == "__main__":
    main()
