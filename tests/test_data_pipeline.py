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


def build_fixture_source(input_dir: Path) -> list[str]:
    rows = []
    match_ids = []
    dates = pd.date_range("2025-08-15", periods=38, freq="7D")

    for index, match_date in enumerate(dates, start=1):
        match_id = f"MATCH_{index:03d}"
        opponent_id = f"OPP_{index:03d}"
        match_ids.append(match_id)
        is_home = index % 2 == 1
        rows.append(
            {
                "matchId": match_id,
                "matchDate": match_date,
                "homeTeamId": DEMO_TEAM_SOURCE_ID if is_home else opponent_id,
                "awayTeamId": opponent_id if is_home else DEMO_TEAM_SOURCE_ID,
                "homeTeamName": "Deportivo Alavés" if is_home else f"Opponent {index}",
                "awayTeamName": f"Opponent {index}" if is_home else "Deportivo Alavés",
                "homeScore": index % 4,
                "awayScore": (index + 1) % 3,
                "competition": "LaLiga",
                "season": "2025/26",
            }
        )

    write_parquet(input_dir / "opta_fixtures.parquet", pd.DataFrame(rows))
    return match_ids


def build_player_stats_source(input_dir: Path, match_ids: list[str]) -> None:
    rows = []
    for match_id in match_ids:
        rows.extend(
            [
                {
                    "matchId": match_id,
                    "contestantId": DEMO_TEAM_SOURCE_ID,
                    "playerId": "PLAYER_A",
                    "playerName": "Player A",
                    "minsPlayed": 90,
                    "position": "CB",
                    "isStarter": True,
                    "shirtNumber": 4,
                },
                {
                    "matchId": match_id,
                    "contestantId": DEMO_TEAM_SOURCE_ID,
                    "playerId": "PLAYER_B",
                    "playerName": "Player B",
                    "minsPlayed": 60,
                    "position": "CM",
                    "isStarter": True,
                    "shirtNumber": 8,
                },
                {
                    "matchId": match_id,
                    "contestantId": "OPP_NOT_DEMO",
                    "playerId": f"RIVAL_{match_id}",
                    "playerName": "Rival Player",
                    "minsPlayed": 90,
                    "position": "FW",
                    "isStarter": True,
                    "shirtNumber": 9,
                },
            ]
        )

    write_parquet(input_dir / "opta_player_stats.parquet", pd.DataFrame(rows))


def run_script(script: str, *args: str) -> None:
    subprocess.run(
        [sys.executable, str(DATA_DIR / script), *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_fixture_and_player_match_pipeline_is_idempotent(tmp_path: Path) -> None:
    input_dir = tmp_path / "pannadata"
    db_path = tmp_path / "football_performance.duckdb"
    validation_path = tmp_path / "validation.json"

    match_ids = build_fixture_source(input_dir)
    build_player_stats_source(input_dir, match_ids)

    run_script("init_database.py", "--db", str(db_path))

    for _ in range(2):
        run_script(
            "import_demo_fixtures.py",
            "--input-dir",
            str(input_dir),
            "--db",
            str(db_path),
        )
        run_script(
            "import_demo_player_match.py",
            "--input-dir",
            str(input_dir),
            "--db",
            str(db_path),
        )

    run_script(
        "validate_demo_database.py",
        "--db",
        str(db_path),
        "--output",
        str(validation_path),
    )

    demo_team_id = stable_id("team", DEMO_TEAM_SOURCE_ID)
    with duckdb.connect(str(db_path), read_only=True) as con:
        demo_matches = con.execute(
            "SELECT COUNT(*) FROM team_match WHERE team_id = ?",
            [demo_team_id],
        ).fetchone()[0]
        player_match_rows = con.execute(
            "SELECT COUNT(*) FROM player_match WHERE team_id = ?",
            [demo_team_id],
        ).fetchone()[0]
        covered_matches = con.execute(
            "SELECT COUNT(DISTINCT match_id) FROM player_match WHERE team_id = ?",
            [demo_team_id],
        ).fetchone()[0]
        distinct_players = con.execute(
            "SELECT COUNT(DISTINCT player_id) FROM player_match WHERE team_id = ?",
            [demo_team_id],
        ).fetchone()[0]

    assert demo_matches == 38
    assert player_match_rows == 76
    assert covered_matches == 38
    assert distinct_players == 2
    assert validation_path.exists()
