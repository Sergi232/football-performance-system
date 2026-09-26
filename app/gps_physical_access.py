"""Read-only access to descriptive GPS physical summaries."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

PHYSICAL_SUMMARY_VERSION = "gps_physical_summary_v0.1-descriptive"


def _connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    path = Path(db_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")
    return duckdb.connect(str(path), read_only=True)


def summary_table_available(db_path: Path) -> bool:
    with _connect(db_path) as con:
        row = con.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema='main' AND table_name='player_match_gps_summary'
            """
        ).fetchone()
    return bool(row and row[0])


def get_gps_summary_status(db_path: Path) -> dict:
    if not summary_table_available(db_path):
        return {"table_available": False, "rows": 0, "matches": 0, "players": 0, "imports": 0}
    with _connect(db_path) as con:
        row = con.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE import_rank=1) AS rows,
                COUNT(DISTINCT match_id) FILTER (WHERE import_rank=1) AS matches,
                COUNT(DISTINCT player_id) FILTER (WHERE import_rank=1) AS players,
                COUNT(DISTINCT gps_import_id) AS imports
            FROM player_match_gps_summary
            WHERE summary_version=?
            """,
            [PHYSICAL_SUMMARY_VERSION],
        ).fetchone()
    keys = ["rows", "matches", "players", "imports"]
    return {"table_available": True, **dict(zip(keys, [int(v or 0) for v in row]))}


def get_player_gps_history(db_path: Path, team_id: str, player_id: str) -> pd.DataFrame:
    if not summary_table_available(db_path):
        return pd.DataFrame()
    with _connect(db_path) as con:
        return con.execute(
            """
            SELECT
                g.match_id, g.match_date,
                opp.display_name AS opponent,
                CASE WHEN tm.is_home THEN 'H' ELSE 'A' END AS venue,
                g.provider, g.source_filename,
                g.sample_count, g.total_distance_m, g.peak_speed_m_s,
                g.max_acceleration_m_s2, g.min_acceleration_m_s2,
                g.observation_duration_s,
                g.distance_coverage_pct, g.speed_coverage_pct, g.acceleration_coverage_pct,
                g.quality_metadata_sample_count
            FROM player_match_gps_summary g
            JOIN team_match tm ON tm.match_id=g.match_id AND tm.team_id=g.team_id
            LEFT JOIN teams opp ON opp.team_id=tm.opponent_team_id
            WHERE g.summary_version=? AND g.import_rank=1
              AND g.team_id=? AND g.player_id=?
            ORDER BY g.match_date, g.match_id
            """,
            [PHYSICAL_SUMMARY_VERSION, team_id, player_id],
        ).df()


def get_latest_player_gps(db_path: Path, team_id: str, player_id: str) -> dict | None:
    frame = get_player_gps_history(db_path, team_id, player_id)
    if frame.empty:
        return None
    return frame.iloc[-1].to_dict()


def get_match_gps_summary(db_path: Path, team_id: str, match_id: str) -> pd.DataFrame:
    if not summary_table_available(db_path):
        return pd.DataFrame()
    with _connect(db_path) as con:
        return con.execute(
            """
            SELECT
                p.display_name AS player,
                g.player_id, g.provider,
                g.sample_count, g.total_distance_m, g.peak_speed_m_s,
                g.max_acceleration_m_s2, g.min_acceleration_m_s2,
                g.observation_duration_s,
                g.distance_coverage_pct, g.speed_coverage_pct, g.acceleration_coverage_pct,
                g.quality_metadata_sample_count
            FROM player_match_gps_summary g
            JOIN players p ON p.player_id=g.player_id
            WHERE g.summary_version=? AND g.import_rank=1
              AND g.team_id=? AND g.match_id=?
            ORDER BY p.display_name
            """,
            [PHYSICAL_SUMMARY_VERSION, team_id, match_id],
        ).df()


def get_team_gps_match_coverage(db_path: Path, team_id: str) -> pd.DataFrame:
    if not summary_table_available(db_path):
        return pd.DataFrame()
    with _connect(db_path) as con:
        return con.execute(
            """
            WITH played AS (
                SELECT match_id, COUNT(*) FILTER (WHERE minutes_played > 0) AS played_players
                FROM player_match
                WHERE team_id=?
                GROUP BY match_id
            ), gps AS (
                SELECT match_id, COUNT(DISTINCT player_id) AS gps_players
                FROM player_match_gps_summary
                WHERE summary_version=? AND import_rank=1 AND team_id=?
                GROUP BY match_id
            )
            SELECT
                m.match_id, m.match_date,
                opp.display_name AS opponent,
                CASE WHEN tm.is_home THEN 'H' ELSE 'A' END AS venue,
                p.played_players,
                COALESCE(g.gps_players, 0) AS gps_players,
                CASE WHEN p.played_players > 0 THEN 100.0 * COALESCE(g.gps_players,0) / p.played_players ELSE NULL END AS gps_player_coverage_pct
            FROM team_match tm
            JOIN matches m ON m.match_id=tm.match_id
            LEFT JOIN teams opp ON opp.team_id=tm.opponent_team_id
            JOIN played p ON p.match_id=tm.match_id
            LEFT JOIN gps g ON g.match_id=tm.match_id
            WHERE tm.team_id=?
            ORDER BY m.match_date DESC, m.match_id DESC
            """,
            [team_id, PHYSICAL_SUMMARY_VERSION, team_id, team_id],
        ).df()


def get_team_latest_gps_snapshot(db_path: Path, team_id: str) -> pd.DataFrame:
    if not summary_table_available(db_path):
        return pd.DataFrame()
    with _connect(db_path) as con:
        return con.execute(
            """
            WITH ranked AS (
                SELECT
                    g.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY g.player_id
                        ORDER BY g.match_date DESC, g.match_id DESC
                    ) AS rn
                FROM player_match_gps_summary g
                WHERE g.summary_version=? AND g.import_rank=1 AND g.team_id=?
            )
            SELECT
                p.display_name AS player,
                r.player_id, r.match_id, r.match_date,
                r.total_distance_m, r.peak_speed_m_s,
                r.max_acceleration_m_s2, r.min_acceleration_m_s2,
                r.observation_duration_s,
                r.distance_coverage_pct, r.speed_coverage_pct, r.acceleration_coverage_pct
            FROM ranked r
            JOIN players p ON p.player_id=r.player_id
            WHERE r.rn=1
            ORDER BY p.display_name
            """,
            [PHYSICAL_SUMMARY_VERSION, team_id],
        ).df()
