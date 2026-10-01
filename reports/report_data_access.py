"""Read-only descriptive data access used only by professional PDF reports.

This module exposes simple team-match aggregates from already normalised raw stats.
It does not calculate Match Rating, Performance Index, expert decisions or tactical
recommendations.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.access_control import assert_team_access
from app.data_access import connect_read_only


def get_team_match_technical_history(db_path: Path, team_id: str) -> pd.DataFrame:
    """Return one auditable technical row per team-match.

    All values are direct sums of player-match raw stats, except pass completion %, which
    is a transparent ratio of completed / attempted passes for that same team-match.
    """
    assert_team_access(team_id)
    with connect_read_only(db_path) as con:
        return con.execute(
            """
            SELECT
                m.match_id,
                m.match_date,
                CASE WHEN tm.is_home THEN 'H' ELSE 'A' END AS venue,
                opp.display_name AS opponent,
                tm.score_for,
                tm.score_against,
                COUNT(*) FILTER (WHERE pm.minutes_played > 0) AS players_used,
                SUM(COALESCE(rs.passes_total, 0)) AS passes_total,
                SUM(COALESCE(rs.passes_completed, 0)) AS passes_completed,
                CASE
                    WHEN SUM(COALESCE(rs.passes_total, 0)) > 0
                    THEN 100.0 * SUM(COALESCE(rs.passes_completed, 0))
                               / SUM(COALESCE(rs.passes_total, 0))
                    ELSE NULL
                END AS pass_completion_pct,
                SUM(COALESCE(rs.shots_total, 0)) AS shots_total,
                SUM(COALESCE(rs.goals, 0)) AS goals,
                SUM(COALESCE(rs.assists, 0)) AS assists,
                SUM(COALESCE(rs.tackles_total, 0)) AS tackles_total,
                SUM(COALESCE(rs.tackles_won, 0)) AS tackles_won,
                SUM(COALESCE(rs.interceptions, 0)) AS interceptions,
                SUM(COALESCE(rs.turnovers, 0)) AS turnovers,
                SUM(COALESCE(rs.dispossessed, 0)) AS dispossessed
            FROM player_match pm
            JOIN matches m ON m.match_id = pm.match_id
            JOIN team_match tm ON tm.match_id = pm.match_id AND tm.team_id = pm.team_id
            LEFT JOIN teams opp ON opp.team_id = tm.opponent_team_id
            LEFT JOIN player_match_raw_stats rs
              ON rs.match_id = pm.match_id
             AND rs.player_id = pm.player_id
             AND rs.team_id = pm.team_id
            WHERE pm.team_id = ?
            GROUP BY
                m.match_id, m.match_date, tm.is_home, opp.display_name,
                tm.score_for, tm.score_against
            ORDER BY m.match_date DESC, m.match_id DESC
            """,
            [team_id],
        ).df()
