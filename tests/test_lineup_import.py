from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path

import duckdb
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
DEMO_TEAM_SOURCE_ID = "4dtdjgnpdq9uw4sdutti0vaar"


def stable_id(entity: str, source_id: object) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:{entity}:{source_id}"))


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect() as con:
        con.register("frame", frame)
        escaped = str(path.resolve()).replace("'", "''")
        con.execute(f"COPY frame TO '{escaped}' (FORMAT PARQUET)")


def run_script(script: str, *args: str) -> None:
    subprocess.run(
        [sys.executable, str(DATA_DIR / script), *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def build_sources(input_dir: Path) -> None:
    fixtures = []
    stats = []
    lineups = []
    dates = pd.date_range("2025-08-15", periods=38, freq="7D")

    for match_no, match_date in enumerate(dates, start=1):
        match_id = f"MATCH_{match_no:03d}"
        opponent_id = f"OPP_{match_no:03d}"
        is_home = match_no % 2 == 1
        fixtures.append(
            {
                "match_id": match_id,
                "match_date": match_date,
                "home_team_id": DEMO_TEAM_SOURCE_ID if is_home else opponent_id,
                "away_team_id": opponent_id if is_home else DEMO_TEAM_SOURCE_ID,
                "home_team": "Alavés" if is_home else "Opponent",
                "away_team": "Opponent" if is_home else "Alavés",
                "home_score": 1,
                "away_score": 0,
                "competition": "LaLiga",
                "season": "2025/26",
            }
        )

        for player_no in range(1, 12):
            player_id = f"STARTER_{player_no:02d}"
            position = "Goalkeeper" if player_no == 1 else "Defender"
            side = "Centre" if player_no == 1 else ("Left" if player_no % 2 else "Right")
            stats.append(
                {
                    "match_id": match_id,
                    "team_id": DEMO_TEAM_SOURCE_ID,
                    "player_id": player_id,
                    "player_name": player_id,
                    "minsPlayed": 90.0,
                    "position": position,
                    "shirt_number": player_no,
                }
            )
            lineups.append(
                {
                    "match_id": match_id,
                    "match_date": str(match_date.date()),
                    "player_id": player_id,
                    "player_name": player_id,
                    "team_id": DEMO_TEAM_SOURCE_ID,
                    "team_name": "Alavés",
                    "team_position": "home" if is_home else "away",
                    "position": position,
                    "position_side": side,
                    "formation_place": str(player_no),
                    "shirt_number": float(player_no),
                    "is_starter": True,
                    "minutes_played": 90.0,
                    "sub_on_minute": 0.0,
                    "sub_off_minute": 0.0,
                    "competition": "La_Liga",
                    "season": "2025-2026",
                }
            )

        sub_id = "SUB_USED"
        stats.append(
            {
                "match_id": match_id,
                "team_id": DEMO_TEAM_SOURCE_ID,
                "player_id": sub_id,
                "player_name": sub_id,
                "minsPlayed": 30.0,
                "position": "Midfielder",
                "shirt_number": 20,
            }
        )
        lineups.append(
            {
                "match_id": match_id,
                "match_date": str(match_date.date()),
                "player_id": sub_id,
                "player_name": sub_id,
                "team_id": DEMO_TEAM_SOURCE_ID,
                "team_name": "Alavés",
                "team_position": "home" if is_home else "away",
                "position": "Substitute",
                "position_side": "",
                "formation_place": "",
                "shirt_number": 20.0,
                "is_starter": False,
                "minutes_played": 30.0,
                "sub_on_minute": 60.0,
                "sub_off_minute": 0.0,
                "competition": "La_Liga",
                "season": "2025-2026",
            }
        )

        lineups.append(
            {
                "match_id": match_id,
                "match_date": str(match_date.date()),
                "player_id": "BENCH_UNUSED",
                "player_name": "Bench Unused",
                "team_id": DEMO_TEAM_SOURCE_ID,
                "team_name": "Alavés",
                "team_position": "home" if is_home else "away",
                "position": "Substitute",
                "position_side": "",
                "formation_place": "",
                "shirt_number": 30.0,
                "is_starter": False,
                "minutes_played": 0.0,
                "sub_on_minute": 0.0,
                "sub_off_minute": 0.0,
                "competition": "La_Liga",
                "season": "2025-2026",
            }
        )

    write_parquet(input_dir / "opta_fixtures.parquet", pd.DataFrame(fixtures))
    write_parquet(input_dir / "opta_player_stats.parquet", pd.DataFrame(stats))
    write_parquet(input_dir / "opta_lineups.parquet", pd.DataFrame(lineups))


def test_lineup_import_adds_zero_minute_bench_and_starter_roles(tmp_path: Path) -> None:
    input_dir = tmp_path / "pannadata"
    db_path = tmp_path / "football_performance.duckdb"
    build_sources(input_dir)

    run_script("init_database.py", "--db", str(db_path))
    run_script("import_demo_fixtures.py", "--input-dir", str(input_dir), "--db", str(db_path))
    run_script("import_demo_player_match.py", "--input-dir", str(input_dir), "--db", str(db_path))
    run_script("import_demo_lineups.py", "--input-dir", str(input_dir), "--db", str(db_path))

    demo_team_id = stable_id("team", DEMO_TEAM_SOURCE_ID)
    with duckdb.connect(str(db_path), read_only=True) as con:
        total_rows = con.execute(
            "SELECT COUNT(*) FROM player_match WHERE team_id = ?", [demo_team_id]
        ).fetchone()[0]
        starter_rows = con.execute(
            "SELECT COUNT(*) FROM player_match WHERE team_id = ? AND started = TRUE",
            [demo_team_id],
        ).fetchone()[0]
        zero_rows = con.execute(
            "SELECT COUNT(*) FROM player_match WHERE team_id = ? AND minutes_played = 0",
            [demo_team_id],
        ).fetchone()[0]
        starter_role = con.execute(
            """
            SELECT pm.primary_role
            FROM player_match pm
            JOIN players p ON p.player_id = pm.player_id
            WHERE pm.team_id = ? AND p.source_player_id = 'STARTER_02'
            LIMIT 1
            """,
            [demo_team_id],
        ).fetchone()[0]
        sub_role = con.execute(
            """
            SELECT pm.primary_role
            FROM player_match pm
            JOIN players p ON p.player_id = pm.player_id
            WHERE pm.team_id = ? AND p.source_player_id = 'SUB_USED'
            LIMIT 1
            """,
            [demo_team_id],
        ).fetchone()[0]
        formations = con.execute(
            "SELECT COUNT(*) FROM team_match WHERE team_id = ? AND starting_formation IS NOT NULL",
            [demo_team_id],
        ).fetchone()[0]

    assert total_rows == 38 * 13
    assert starter_rows == 38 * 11
    assert zero_rows == 38
    assert starter_role in {"Defender | Left", "Defender | Right"}
    assert sub_role == "Midfielder"
    assert formations == 0
