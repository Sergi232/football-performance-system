"""Read-only access to the experimental performance score."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from app.access_control import assert_team_access, filter_authorized_teams

SCORE_VERSION = "performance_score_v0.2-experimental"


def connect_read_only(db_path: Path) -> duckdb.DuckDBPyConnection:
    db_path = Path(db_path).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    return duckdb.connect(str(db_path), read_only=True)


def list_score_teams(db_path: Path) -> pd.DataFrame:
    with connect_read_only(db_path) as con:
        frame = con.execute(
            """
            SELECT DISTINCT s.team_id, t.display_name
            FROM player_match_performance_score s
            JOIN teams t ON t.team_id = s.team_id
            WHERE s.score_version = ?
            ORDER BY t.display_name
            """,
            [SCORE_VERSION],
        ).df()
    return filter_authorized_teams(frame)


def list_team_players(db_path: Path, team_id: str) -> pd.DataFrame:
    assert_team_access(team_id)
    with connect_read_only(db_path) as con:
        return con.execute(
            """
            SELECT
                p.player_id,
                p.display_name AS player,
                COUNT(*) FILTER (WHERE s.performance_score IS NOT NULL) AS scored_matches,
                MAX(s.position_group) FILTER (WHERE s.performance_score IS NOT NULL) AS latest_position_group
            FROM player_match_performance_score s
            JOIN players p ON p.player_id = s.player_id
            WHERE s.score_version = ? AND s.team_id = ?
            GROUP BY p.player_id, p.display_name
            ORDER BY p.display_name
            """,
            [SCORE_VERSION, team_id],
        ).df()


def get_player_score_history(db_path: Path, team_id: str, player_id: str) -> pd.DataFrame:
    assert_team_access(team_id)
    with connect_read_only(db_path) as con:
        return con.execute(
            """
            SELECT
                m.match_date,
                s.match_id,
                s.primary_role,
                s.position_group,
                s.position_mapping_status,
                s.dimension_coverage_count,
                s.attacking_threat,
                s.creation_progression,
                s.defensive_contribution,
                s.finishing,
                s.discipline,
                s.performance_score,
                s.score_evidence_confidence,
                s.fallback_dimension_count,
                s.attacking_threat_evidence,
                s.creation_progression_evidence,
                s.defensive_contribution_evidence,
                s.finishing_evidence,
                s.discipline_evidence,
                s.score_status
            FROM player_match_performance_score s
            JOIN matches m ON m.match_id = s.match_id
            WHERE s.score_version = ?
              AND s.team_id = ?
              AND s.player_id = ?
            ORDER BY m.match_date, s.match_id
            """,
            [SCORE_VERSION, team_id, player_id],
        ).df()


def get_latest_player_score(db_path: Path, team_id: str, player_id: str) -> dict | None:
    history = get_player_score_history(db_path, team_id, player_id)
    eligible = history[history["performance_score"].notna()].copy()
    if eligible.empty:
        return None
    return eligible.iloc[-1].to_dict()


def get_team_score_snapshot(db_path: Path, team_id: str) -> pd.DataFrame:
    """Return one descriptive score snapshot row per squad player.

    trend_delta_5v5 is descriptive only: latest five eligible scores minus the
    preceding five eligible scores. No threshold or performance label is applied.
    """
    assert_team_access(team_id)
    with connect_read_only(db_path) as con:
        return con.execute(
            """
            WITH roster AS (
                SELECT DISTINCT pm.player_id, p.display_name AS player
                FROM player_match pm
                JOIN players p ON p.player_id = pm.player_id
                WHERE pm.team_id = ?
            ),
            eligible AS (
                SELECT
                    s.player_id,
                    s.match_id,
                    m.match_date,
                    s.position_group,
                    s.performance_score,
                    s.score_evidence_confidence,
                    s.fallback_dimension_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY s.player_id
                        ORDER BY m.match_date DESC, s.match_id DESC
                    ) AS rn
                FROM player_match_performance_score s
                JOIN matches m ON m.match_id = s.match_id
                WHERE s.score_version = ?
                  AND s.team_id = ?
                  AND s.position_group <> 'OTHER_OUTFIELD'
                  AND s.performance_score IS NOT NULL
            ),
            score_agg AS (
                SELECT
                    player_id,
                    COUNT(*) AS scored_matches,
                    MAX(CASE WHEN rn = 1 THEN match_date END) AS latest_score_date,
                    MAX(CASE WHEN rn = 1 THEN position_group END) AS position_group,
                    MAX(CASE WHEN rn = 1 THEN performance_score END) AS latest_score,
                    MAX(CASE WHEN rn = 1 THEN score_evidence_confidence END) AS latest_confidence,
                    MAX(CASE WHEN rn = 1 THEN fallback_dimension_count END) AS latest_fallback_dimensions,
                    AVG(CASE WHEN rn BETWEEN 1 AND 5 THEN performance_score END) AS avg_last5,
                    AVG(CASE WHEN rn BETWEEN 6 AND 10 THEN performance_score END) AS avg_previous5,
                    COUNT(*) FILTER (WHERE rn BETWEEN 1 AND 5) AS n_last5,
                    COUNT(*) FILTER (WHERE rn BETWEEN 6 AND 10) AS n_previous5
                FROM eligible
                GROUP BY player_id
            )
            SELECT
                r.player_id,
                r.player,
                a.scored_matches,
                a.latest_score_date,
                a.position_group,
                a.latest_score,
                a.latest_confidence,
                a.latest_fallback_dimensions,
                a.avg_last5,
                a.avg_previous5,
                CASE
                    WHEN a.n_last5 > 0 AND a.n_previous5 > 0
                    THEN a.avg_last5 - a.avg_previous5
                    ELSE NULL
                END AS trend_delta_5v5,
                COALESCE(a.n_last5, 0) AS n_last5,
                COALESCE(a.n_previous5, 0) AS n_previous5
            FROM roster r
            LEFT JOIN score_agg a ON a.player_id = r.player_id
            ORDER BY r.player
            """,
            [team_id, SCORE_VERSION, team_id],
        ).df()


def get_score_status(db_path: Path) -> dict:
    with connect_read_only(db_path) as con:
        row = con.execute(
            """
            SELECT
                COUNT(*) AS rows,
                COUNT(*) FILTER (WHERE position_group <> 'OTHER_OUTFIELD') AS observable_rows,
                COUNT(*) FILTER (
                    WHERE position_group <> 'OTHER_OUTFIELD' AND performance_score IS NOT NULL
                ) AS eligible_rows,
                COUNT(*) FILTER (
                    WHERE position_mapping_status = 'role_unavailable_source_semantics'
                ) AS role_unavailable_rows,
                COUNT(*) FILTER (
                    WHERE performance_score IS NOT NULL AND COALESCE(fallback_dimension_count, 0) > 0
                ) AS fallback_score_rows
            FROM player_match_performance_score
            WHERE score_version = ?
            """,
            [SCORE_VERSION],
        ).fetchone()
    keys = ["rows", "observable_rows", "eligible_rows", "role_unavailable_rows", "fallback_score_rows"]
    if row is None:
        return dict.fromkeys(keys, 0)
    return dict(zip(keys, row))
