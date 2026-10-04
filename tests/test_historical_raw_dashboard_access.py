"""Dashboard aggregates must retain sourced historical raw statistics."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from app.data_access import get_team_matches
from data.init_database import initialize_database


def test_historical_raw_player_match_stats_feed_team_match_kpis(tmp_path: Path) -> None:
    db = tmp_path / "historical.duckdb"
    initialize_database(db)
    with duckdb.connect(str(db)) as con:
        con.executemany(
            "INSERT INTO teams (team_id, display_name) VALUES (?, ?)",
            [("T", "Equipo histórico"), ("O", "Rival histórico")],
        )
        con.execute(
            "INSERT INTO matches (match_id, match_date, home_team_id, away_team_id, source_type) "
            "VALUES ('M', '2026-01-01', 'T', 'O', 'PANNADATA_OPTA')"
        )
        con.execute(
            "INSERT INTO team_match VALUES ('M', 'T', 'O', true, NULL, 1, 0)"
        )
        con.executemany(
            "INSERT INTO players (player_id, display_name) VALUES (?, ?)",
            [("P1", "Jugador 01"), ("P2", "Jugador 02")],
        )
        con.executemany(
            "INSERT INTO player_match VALUES ('M', 'T', ?, true, 90, NULL, NULL)",
            [("P1",), ("P2",)],
        )
        con.executemany(
            """
            INSERT INTO player_match_raw_stats (
                match_id, team_id, player_id, source_type,
                shots_total, shots_on_target, passes_total, passes_completed,
                fouls_committed, fouls_received, yellow_cards, red_cards,
                penalties_won, penalties_conceded
            ) VALUES ('M', 'T', ?, 'opta_player_stats', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("P1", 3, 1, 20, 15, 2, 1, 1, 0, 1, 0),
                ("P2", 2, 2, 30, 25, 1, 2, 0, 1, 0, 1),
            ],
        )

    row = get_team_matches(db, "T").iloc[0]
    assert {
        "shots_total": int(row.shots_total),
        "shots_on_target": int(row.shots_on_target),
        "passes_total": int(row.passes_total),
        "passes_completed": int(row.passes_completed),
        "fouls_committed": int(row.fouls_committed),
        "fouls_received": int(row.fouls_received),
        "yellow_cards": int(row.yellow_cards),
        "red_cards": int(row.red_cards),
        "penalties_won": int(row.penalties_won),
        "penalties_conceded": int(row.penalties_conceded),
    } == {
        "shots_total": 5,
        "shots_on_target": 3,
        "passes_total": 50,
        "passes_completed": 40,
        "fouls_committed": 3,
        "fouls_received": 3,
        "yellow_cards": 1,
        "red_cards": 1,
        "penalties_won": 1,
        "penalties_conceded": 1,
    }
    assert pd.isna(row.corners_for)
    assert pd.isna(row.starting_formation)
