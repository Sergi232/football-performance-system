"""Read-only access to the immediate post-match rating layer."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

MATCH_RATING_VERSION = "match_rating_v0.1-experimental"


def _connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    path = Path(db_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")
    return duckdb.connect(str(path), read_only=True)


def get_player_match_ratings(db_path: Path, team_id: str, player_id: str) -> pd.DataFrame:
    with _connect(db_path) as con:
        return con.execute(
            """
            SELECT
                r.match_id, r.match_date, tm.opponent_team_id,
                opp.display_name AS opponent,
                CASE WHEN tm.is_home THEN 'H' ELSE 'A' END AS venue,
                r.minutes_played, r.started, r.primary_role, r.position_group,
                r.attacking_threat, r.creation_progression, r.defensive_contribution,
                r.finishing, r.discipline, r.match_rating_100, r.match_rating_10,
                r.match_rating_confidence, r.match_rating_dimensions_used,
                r.match_rating_context, r.match_rating_status, r.rating_path
            FROM player_match_rating r
            JOIN team_match tm ON tm.match_id=r.match_id AND tm.team_id=r.team_id
            LEFT JOIN teams opp ON opp.team_id=tm.opponent_team_id
            WHERE r.match_rating_version=? AND r.team_id=? AND r.player_id=?
            ORDER BY r.match_date, r.match_id
            """,
            [MATCH_RATING_VERSION, team_id, player_id],
        ).df()


def get_latest_player_match_rating(db_path: Path, team_id: str, player_id: str) -> dict | None:
    frame = get_player_match_ratings(db_path, team_id, player_id)
    if frame.empty:
        return None
    return frame.iloc[-1].to_dict()


def get_match_ratings(db_path: Path, team_id: str, match_id: str) -> pd.DataFrame:
    with _connect(db_path) as con:
        return con.execute(
            """
            SELECT
                p.display_name AS player,
                r.player_id, r.minutes_played, r.started, r.primary_role,
                r.position_group, r.match_rating_10, r.match_rating_100,
                r.match_rating_confidence, r.match_rating_dimensions_used,
                r.match_rating_context, r.match_rating_status, r.rating_path,
                r.attacking_threat, r.creation_progression, r.defensive_contribution,
                r.finishing, r.discipline
            FROM player_match_rating r
            JOIN players p ON p.player_id=r.player_id
            WHERE r.match_rating_version=? AND r.team_id=? AND r.match_id=?
            ORDER BY r.started DESC, r.minutes_played DESC, p.display_name
            """,
            [MATCH_RATING_VERSION, team_id, match_id],
        ).df()


def get_latest_team_match_ratings(db_path: Path, team_id: str) -> pd.DataFrame:
    with _connect(db_path) as con:
        row = con.execute(
            """
            SELECT match_id
            FROM player_match_rating
            WHERE match_rating_version=? AND team_id=?
            ORDER BY match_date DESC, match_id DESC
            LIMIT 1
            """,
            [MATCH_RATING_VERSION, team_id],
        ).fetchone()
    if row is None:
        return pd.DataFrame()
    return get_match_ratings(db_path, team_id, row[0])


def get_match_rating_status(db_path: Path) -> dict:
    with _connect(db_path) as con:
        row = con.execute(
            """
            SELECT
                COUNT(*) AS rows,
                COUNT(*) FILTER (WHERE match_rating_10 IS NOT NULL) AS rated_rows,
                COUNT(*) FILTER (WHERE rating_path='GOALKEEPER') AS goalkeeper_rows,
                COUNT(*) FILTER (WHERE match_rating_context='GENERIC_ROLE_UNAVAILABLE') AS generic_role_rows,
                COUNT(*) FILTER (WHERE match_rating_status LIKE 'NEUTRAL_%') AS neutral_rows,
                COUNT(DISTINCT match_id) AS matches
            FROM player_match_rating
            WHERE match_rating_version=?
            """,
            [MATCH_RATING_VERSION],
        ).fetchone()
    keys = ["rows", "rated_rows", "goalkeeper_rows", "generic_role_rows", "neutral_rows", "matches"]
    return dict(zip(keys, row or [0] * len(keys)))
