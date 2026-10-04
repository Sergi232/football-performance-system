"""Read-only data access for DASHBOARD-01.

The dashboard reads validated database layers only. It does not calculate critical
metrics itself and it never upgrades a descriptive signal into a recommendation.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from app.access_control import assert_team_access, filter_authorized_teams


BASE_FEATURE_VERSION = "0.1.0"
FINAL_ENGINE_VERSION = "expert_0.7.0"


def connect_read_only(db_path: Path) -> duckdb.DuckDBPyConnection:
    db_path = Path(db_path).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    return duckdb.connect(str(db_path), read_only=True)


def list_teams(db_path: Path) -> pd.DataFrame:
    with connect_read_only(db_path) as con:
        frame = con.execute(
            """
            SELECT
                t.team_id,
                t.display_name,
                COUNT(DISTINCT pm.match_id) AS matches,
                COUNT(DISTINCT pm.player_id) AS players
            FROM teams t
            JOIN player_match pm ON pm.team_id = t.team_id
            GROUP BY t.team_id, t.display_name
            ORDER BY matches DESC, t.display_name
            """
        ).df()
    return filter_authorized_teams(frame)


def get_team_overview(db_path: Path, team_id: str) -> dict:
    assert_team_access(team_id)
    with connect_read_only(db_path) as con:
        row = con.execute(
            """
            SELECT
                COUNT(DISTINCT pm.match_id) AS matches,
                COUNT(DISTINCT pm.player_id) AS players,
                SUM(pm.minutes_played) AS player_minutes,
                SUM(rs.goals) AS goals,
                SUM(rs.assists) AS assists
            FROM player_match pm
            LEFT JOIN player_match_raw_stats rs
              ON rs.match_id = pm.match_id
             AND rs.player_id = pm.player_id
             AND rs.team_id = pm.team_id
            WHERE pm.team_id = ?
            """,
            [team_id],
        ).fetchone()
        if row is None:
            return {"matches": 0, "players": 0, "player_minutes": None, "goals": None, "assists": None}
        keys = ["matches", "players", "player_minutes", "goals", "assists"]
        return dict(zip(keys, row))


def get_team_matches(db_path: Path, team_id: str) -> pd.DataFrame:
    assert_team_access(team_id)
    with connect_read_only(db_path) as con:
        return con.execute(
            """
            SELECT
                m.match_id,
                m.match_date,
                CASE WHEN tm.is_home THEN 'H' ELSE 'A' END AS venue,
                opp.display_name AS opponent,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.goals_for ELSE tm.score_for END AS score_for,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.goals_against ELSE tm.score_against END AS score_against,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.corners_for END AS corners_for,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.corners_against END AS corners_against,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.fouls_received ELSE raw.fouls_received END AS fouls_received,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.fouls_committed ELSE raw.fouls_committed END AS fouls_committed,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.yellow_cards ELSE raw.yellow_cards END AS yellow_cards,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.red_cards ELSE raw.red_cards END AS red_cards,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.penalties_won ELSE raw.penalties_won END AS penalties_won,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.penalties_conceded ELSE raw.penalties_conceded END AS penalties_conceded,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.shots_total ELSE raw.shots_total END AS shots_total,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.shots_on_target ELSE raw.shots_on_target END AS shots_on_target,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.passes_total ELSE raw.passes_total END AS passes_total,
                CASE WHEN m.source_type='collector_html_v1.1' THEN ev.passes_completed ELSE raw.passes_completed END AS passes_completed,
                tm.starting_formation
            FROM team_match tm
            JOIN matches m ON m.match_id = tm.match_id
            LEFT JOIN teams opp ON opp.team_id = tm.opponent_team_id
            LEFT JOIN (
                SELECT match_id, team_id,
                  COUNT(*) FILTER (WHERE action_type='SHOT' AND outcome='GOAL') AS goals_for,
                  COUNT(*) FILTER (WHERE action_type='GK' AND subtype='GOAL_CONCEDED') AS goals_against,
                  COUNT(*) FILTER (WHERE action_type='CORNER' AND subtype='FOR') AS corners_for,
                  COUNT(*) FILTER (WHERE action_type='CORNER' AND subtype='AGAINST') AS corners_against,
                  COUNT(*) FILTER (WHERE action_type='FOUL' AND subtype='RECEIVED') AS fouls_received,
                  COUNT(*) FILTER (WHERE action_type='FOUL' AND subtype='COMMITTED') AS fouls_committed,
                  COUNT(*) FILTER (WHERE action_type='CARD' AND subtype='YELLOW') AS yellow_cards,
                  COUNT(*) FILTER (WHERE action_type='CARD' AND subtype='RED') AS red_cards,
                  COUNT(*) FILTER (WHERE action_type='PENALTY' AND subtype='WON') AS penalties_won,
                  COUNT(*) FILTER (WHERE action_type='PENALTY' AND subtype='CONCEDED') AS penalties_conceded,
                  COUNT(*) FILTER (WHERE action_type='SHOT') AS shots_total,
                  COUNT(*) FILTER (WHERE action_type='SHOT' AND outcome IN ('GOAL','ON_TARGET')) AS shots_on_target,
                  COUNT(*) FILTER (WHERE action_type='PASS') AS passes_total,
                  COUNT(*) FILTER (WHERE action_type='PASS' AND outcome='SUCCESS') AS passes_completed
                FROM match_events GROUP BY match_id, team_id
            ) ev ON ev.match_id=tm.match_id AND ev.team_id=tm.team_id
            LEFT JOIN (
                SELECT
                  match_id, team_id,
                  SUM(shots_total) AS shots_total,
                  SUM(shots_on_target) AS shots_on_target,
                  SUM(passes_total) AS passes_total,
                  SUM(passes_completed) AS passes_completed,
                  SUM(fouls_committed) AS fouls_committed,
                  SUM(fouls_received) AS fouls_received,
                  SUM(yellow_cards) AS yellow_cards,
                  SUM(red_cards) AS red_cards,
                  SUM(penalties_won) AS penalties_won,
                  SUM(penalties_conceded) AS penalties_conceded
                FROM player_match_raw_stats
                GROUP BY match_id, team_id
            ) raw ON raw.match_id=tm.match_id AND raw.team_id=tm.team_id
            WHERE tm.team_id = ?
            ORDER BY m.match_date DESC, m.match_id
            """,
            [team_id],
        ).df()


def get_squad_summary(db_path: Path, team_id: str) -> pd.DataFrame:
    assert_team_access(team_id)
    with connect_read_only(db_path) as con:
        return con.execute(
            """
            SELECT
                p.player_id,
                p.display_name AS player,
                COUNT(*) FILTER (WHERE pm.minutes_played > 0) AS appearances,
                SUM(CASE WHEN pm.started THEN 1 ELSE 0 END) AS starts,
                SUM(pm.minutes_played) AS minutes,
                SUM(rs.goals) AS goals,
                SUM(rs.assists) AS assists,
                string_agg(DISTINCT pm.primary_role, ', ' ORDER BY pm.primary_role)
                    FILTER (WHERE pm.primary_role IS NOT NULL) AS observed_roles
            FROM player_match pm
            JOIN players p ON p.player_id = pm.player_id
            LEFT JOIN player_match_raw_stats rs
              ON rs.match_id = pm.match_id
             AND rs.player_id = pm.player_id
             AND rs.team_id = pm.team_id
            WHERE pm.team_id = ?
            GROUP BY p.player_id, p.display_name
            ORDER BY minutes DESC NULLS LAST, p.display_name
            """,
            [team_id],
        ).df()


def get_player_match_history(db_path: Path, team_id: str, player_id: str) -> pd.DataFrame:
    assert_team_access(team_id)
    with connect_read_only(db_path) as con:
        return con.execute(
            """
            SELECT
                m.match_id,
                m.match_date,
                CASE WHEN tm.is_home THEN 'H' ELSE 'A' END AS venue,
                opp.display_name AS opponent,
                pm.started,
                pm.minutes_played AS minutes,
                pm.primary_role,
                (
                    SELECT string_agg(
                        concat_ws(' · ', prs.role, prs.side, concat(CAST(prs.start_second / 60 AS INTEGER), '''')),
                        ' → ' ORDER BY prs.start_second
                    )
                    FROM player_role_stints prs
                    WHERE prs.match_id=pm.match_id AND prs.team_id=pm.team_id AND prs.player_id=pm.player_id
                ) AS observed_role_stints,
                rs.passes_total,
                rs.passes_completed,
                (
                    SELECT COUNT(*) FROM match_events me
                    WHERE me.match_id=pm.match_id AND me.team_id=pm.team_id AND me.player_id=pm.player_id
                      AND me.action_type='PASS' AND CAST(json_extract(me.qualifiers, '$.key_pass') AS VARCHAR) = 'true'
                ) AS key_passes,
                rs.long_balls_total,
                rs.long_balls_completed,
                rs.crosses_total,
                rs.crosses_completed,
                rs.assists,
                rs.dribbles_total,
                rs.dribbles_won,
                rs.shots_total,
                rs.shots_on_target,
                rs.shots_blocked,
                rs.goals,
                rs.tackles_total,
                rs.tackles_won,
                rs.interceptions,
                rs.blocked_passes,
                rs.clearances,
                rs.turnovers,
                rs.dispossessed,
                rs.fouls_committed,
                rs.fouls_received,
                rs.yellow_cards,
                rs.red_cards,
                rs.penalties_won,
                rs.penalties_conceded,
                rs.saves,
                rs.goals_conceded
            FROM player_match pm
            JOIN matches m ON m.match_id = pm.match_id
            JOIN team_match tm ON tm.match_id = pm.match_id AND tm.team_id = pm.team_id
            LEFT JOIN teams opp ON opp.team_id = tm.opponent_team_id
            LEFT JOIN player_match_raw_stats rs
              ON rs.match_id = pm.match_id
             AND rs.player_id = pm.player_id
             AND rs.team_id = pm.team_id
            WHERE pm.team_id = ? AND pm.player_id = ?
            ORDER BY m.match_date DESC, m.match_id
            """,
            [team_id, player_id],
        ).df()


def get_player_primary_position(db_path: Path, team_id: str, player_id: str) -> dict | None:
    """Describe the most frequent reliable observed position; never infer one."""
    assert_team_access(team_id)
    with connect_read_only(db_path) as con:
        row = con.execute(
            """
            WITH observed AS (
                SELECT r.position_group
                FROM player_match pm
                JOIN player_match_rating r
                  ON r.match_id=pm.match_id AND r.player_id=pm.player_id AND r.team_id=pm.team_id
                WHERE pm.team_id=? AND pm.player_id=? AND pm.minutes_played > 0
                  AND r.match_rating_version='match_rating_v0.5-candidate'
                  AND r.position_group IS NOT NULL AND r.position_group <> 'OTHER_OUTFIELD'
                  AND r.rating_path <> 'OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2'
                  AND pm.primary_role IS NOT NULL AND trim(pm.primary_role) <> ''
                  AND lower(trim(pm.primary_role)) <> 'substitute'
            ), ranked AS (
                SELECT position_group, COUNT(*) AS appearances,
                       SUM(COUNT(*)) OVER () AS reliable_appearances,
                       ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC, position_group) AS rn
                FROM observed GROUP BY position_group
            )
            SELECT position_group, appearances, reliable_appearances,
                   appearances::DOUBLE / reliable_appearances AS share
            FROM ranked WHERE rn=1
            """,
            [team_id, player_id],
        ).fetchone()
    if row is None:
        return None
    return dict(zip(["position_group", "appearances", "reliable_appearances", "share"], row))


def list_base_features(db_path: Path, player_id: str | None = None) -> list[str]:
    with connect_read_only(db_path) as con:
        if player_id is None:
            rows = con.execute(
                """
                SELECT DISTINCT feature_name
                FROM player_match_features
                WHERE feature_version = ?
                ORDER BY feature_name
                """,
                [BASE_FEATURE_VERSION],
            ).fetchall()
        else:
            rows = con.execute(
                """
                SELECT DISTINCT feature_name
                FROM player_match_features
                WHERE feature_version = ? AND player_id = ?
                ORDER BY feature_name
                """,
                [BASE_FEATURE_VERSION, player_id],
            ).fetchall()
    return [row[0] for row in rows]


def get_player_feature_history(db_path: Path, player_id: str, feature_name: str) -> pd.DataFrame:
    with connect_read_only(db_path) as con:
        return con.execute(
            """
            SELECT
                m.match_date,
                opp.display_name AS opponent,
                pm.primary_role,
                pm.minutes_played AS minutes,
                f.feature_value
            FROM player_match_features f
            JOIN player_match pm
              ON pm.match_id = f.match_id AND pm.player_id = f.player_id
            JOIN matches m ON m.match_id = f.match_id
            JOIN team_match tm ON tm.match_id = pm.match_id AND tm.team_id = pm.team_id
            LEFT JOIN teams opp ON opp.team_id = tm.opponent_team_id
            WHERE f.player_id = ?
              AND f.feature_version = ?
              AND f.feature_name = ?
            ORDER BY m.match_date, f.match_id
            """,
            [player_id, BASE_FEATURE_VERSION, feature_name],
        ).df()


def get_latest_player_gate(db_path: Path, team_id: str, player_id: str) -> dict | None:
    """Return the latest played-match N12000/N13000 state from the validated final engine."""
    assert_team_access(team_id)
    with connect_read_only(db_path) as con:
        row = con.execute(
            """
            SELECT
                m.match_date,
                MAX(CASE WHEN dr.node_id = 'N12000.100' THEN dr.result_value END) AS observed_role,
                MAX(CASE WHEN dr.node_id = 'N12000.110' THEN dr.result_value END) AS same_role_history,
                MAX(CASE WHEN dr.node_id = 'N12000.120' THEN dr.result_value END) AS evaluable_signals,
                MAX(CASE WHEN dr.node_id = 'N12000.170' THEN dr.result_value END) AS evidence_coverage,
                MAX(CASE WHEN dr.node_id = 'N12000.180' THEN dr.result_value END) AS evidence_availability,
                MAX(CASE WHEN dr.node_id = 'N13000.100' THEN dr.result_value END) AS recommendation_gate,
                MAX(CASE WHEN dr.node_id = 'N13000.110' THEN dr.result_value END) AS policy_status,
                MAX(CASE WHEN dr.node_id = 'N13000.120' THEN dr.result_value END) AS final_status
            FROM decision_results dr
            JOIN matches m ON m.match_id = dr.match_id
            JOIN player_match pm
              ON pm.match_id = dr.match_id
             AND pm.player_id = dr.player_id
            WHERE dr.engine_version = ?
              AND dr.player_id = ?
              AND pm.team_id = ?
              AND pm.minutes_played > 0
              AND dr.node_id IN (
                'N12000.100','N12000.110','N12000.120','N12000.170','N12000.180',
                'N13000.100','N13000.110','N13000.120'
              )
            GROUP BY dr.match_id, m.match_date
            ORDER BY m.match_date DESC, dr.match_id DESC
            LIMIT 1
            """,
            [FINAL_ENGINE_VERSION, player_id, team_id],
        ).fetchone()
    if row is None:
        return None
    keys = [
        "match_date", "observed_role", "same_role_history", "evaluable_signals",
        "evidence_coverage", "evidence_availability", "recommendation_gate",
        "policy_status", "final_status",
    ]
    return dict(zip(keys, row))


def get_latest_player_expert_trace(db_path: Path, team_id: str, player_id: str) -> pd.DataFrame:
    """Expose the already materialized N12000/N13000 audit trail for the latest match.

    Decision conditions are not stored as executable expressions per result row.
    The caller must therefore show the stored justification as the rule evidence,
    rather than reconstructing or inventing a condition.
    """
    assert_team_access(team_id)
    with connect_read_only(db_path) as con:
        return con.execute(
            """
            WITH latest AS (
                SELECT dr.match_id
                FROM decision_results dr
                JOIN matches m ON m.match_id=dr.match_id
                JOIN player_match pm ON pm.match_id=dr.match_id AND pm.player_id=dr.player_id
                WHERE dr.engine_version=? AND dr.player_id=? AND pm.team_id=? AND pm.minutes_played > 0
                ORDER BY m.match_date DESC, dr.match_id DESC LIMIT 1
            )
            SELECT dr.node_id, dr.result_value, dr.confidence, dr.justification
            FROM decision_results dr JOIN latest l ON l.match_id=dr.match_id
            WHERE dr.engine_version=? AND dr.player_id=?
              AND (dr.node_id LIKE 'N12000.%' OR dr.node_id LIKE 'N13000.%')
            ORDER BY dr.node_id
            """,
            [FINAL_ENGINE_VERSION, player_id, team_id, FINAL_ENGINE_VERSION, player_id],
        ).df()


def get_match_lineup(db_path: Path, team_id: str, match_id: str) -> pd.DataFrame:
    assert_team_access(team_id)
    with connect_read_only(db_path) as con:
        return con.execute(
            """
            SELECT
                p.display_name AS player,
                pm.shirt_number,
                pm.started,
                pm.minutes_played AS minutes,
                pm.primary_role,
                (
                    SELECT string_agg(
                        concat_ws(' · ', prs.role, prs.side, concat(CAST(prs.start_second / 60 AS INTEGER), '''')),
                        ' → ' ORDER BY prs.start_second
                    )
                    FROM player_role_stints prs
                    WHERE prs.match_id=pm.match_id AND prs.team_id=pm.team_id AND prs.player_id=pm.player_id
                ) AS observed_role_stints,
                rs.passes_total,
                rs.passes_completed,
                (
                    SELECT COUNT(*) FROM match_events me
                    WHERE me.match_id=pm.match_id AND me.team_id=pm.team_id AND me.player_id=pm.player_id
                      AND me.action_type='PASS' AND CAST(json_extract(me.qualifiers, '$.key_pass') AS VARCHAR) = 'true'
                ) AS key_passes,
                rs.long_balls_total,
                rs.long_balls_completed,
                rs.crosses_total,
                rs.crosses_completed,
                rs.assists,
                rs.dribbles_total,
                rs.dribbles_won,
                rs.shots_total,
                rs.shots_on_target,
                rs.shots_blocked,
                rs.goals,
                rs.tackles_total,
                rs.tackles_won,
                rs.interceptions,
                rs.blocked_passes,
                rs.clearances,
                rs.turnovers,
                rs.dispossessed,
                rs.fouls_committed,
                rs.fouls_received,
                rs.yellow_cards,
                rs.red_cards,
                rs.penalties_won,
                rs.penalties_conceded,
                rs.saves,
                rs.goals_conceded
            FROM player_match pm
            JOIN players p ON p.player_id = pm.player_id
            LEFT JOIN player_match_raw_stats rs
              ON rs.match_id = pm.match_id
             AND rs.player_id = pm.player_id
             AND rs.team_id = pm.team_id
            WHERE pm.team_id = ? AND pm.match_id = ?
            ORDER BY pm.started DESC, pm.minutes_played DESC NULLS LAST, pm.shirt_number NULLS LAST, p.display_name
            """,
            [team_id, match_id],
        ).df()


def get_match_event_log(db_path: Path, team_id: str, match_id: str) -> pd.DataFrame:
    """Expose Collector raw events as imported, without producing new metrics."""
    assert_team_access(team_id)
    with connect_read_only(db_path) as con:
        return con.execute(
            """
            SELECT
                me.event_id,
                p.display_name AS player,
                me.period,
                me.match_second,
                me.action_type,
                me.subtype,
                me.outcome,
                me.x,
                me.y,
                CAST(me.qualifiers AS VARCHAR) AS qualifiers
            FROM match_events me
            LEFT JOIN players p ON p.player_id=me.player_id
            WHERE me.match_id=? AND me.team_id=?
            ORDER BY me.period NULLS LAST, me.match_second NULLS LAST, me.event_id
            """,
            [match_id, team_id],
        ).df()


def get_engine_status(db_path: Path) -> dict:
    with connect_read_only(db_path) as con:
        player_match_rows = con.execute("SELECT COUNT(*) FROM player_match").fetchone()[0]
        engine_rows = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?",
            [FINAL_ENGINE_VERSION],
        ).fetchone()[0]
        n13000_rows = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id LIKE 'N13000.%'
            """,
            [FINAL_ENGINE_VERSION],
        ).fetchone()[0]
        unsafe = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id = 'N13000.120'
              AND result_value NOT LIKE 'RECOMMENDATION_NOT_ISSUED_%'
            """,
            [FINAL_ENGINE_VERSION],
        ).fetchone()[0]
    return {
        "player_match_rows": player_match_rows,
        "engine_rows": engine_rows,
        "n13000_rows": n13000_rows,
        "unsafe_final_states": unsafe,
    }
