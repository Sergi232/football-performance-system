"""Deterministic post-match observations from already collected player-match data.

These are descriptive facts, not tactical recommendations. No LLM is used and no
missing value is silently converted into an observed zero.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


def _connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    path = Path(db_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")
    return duckdb.connect(str(path), read_only=True)


def get_match_observed_player_stats(db_path: Path, team_id: str, match_id: str) -> pd.DataFrame:
    with _connect(db_path) as con:
        return con.execute(
            """
            SELECT
                p.display_name AS player,
                pm.player_id,
                pm.minutes_played AS minutes,
                pm.started,
                pm.primary_role,
                rs.passes_total,
                rs.passes_completed,
                rs.assists,
                rs.shots_total,
                rs.goals,
                rs.tackles_total,
                rs.tackles_won,
                rs.interceptions,
                rs.blocked_passes,
                rs.clearances,
                rs.turnovers,
                rs.dispossessed
            FROM player_match pm
            JOIN players p ON p.player_id=pm.player_id
            LEFT JOIN player_match_raw_stats rs
              ON rs.match_id=pm.match_id
             AND rs.player_id=pm.player_id
             AND rs.team_id=pm.team_id
            WHERE pm.team_id=? AND pm.match_id=? AND pm.minutes_played > 0
            ORDER BY pm.started DESC, pm.minutes_played DESC, p.display_name
            """,
            [team_id, match_id],
        ).df()


def _leader(frame: pd.DataFrame, column: str) -> dict | None:
    if column not in frame.columns:
        return None
    values = pd.to_numeric(frame[column], errors="coerce")
    valid = frame.loc[values.notna(), ["player", column]].copy()
    if valid.empty:
        return None
    valid[column] = pd.to_numeric(valid[column], errors="coerce")
    best = valid[column].max()
    leaders = valid.loc[valid[column] == best, "player"].astype(str).tolist()
    return {"players": leaders, "value": float(best)}


def get_match_observations(db_path: Path, team_id: str, match_id: str) -> dict:
    frame = get_match_observed_player_stats(db_path, team_id, match_id)
    if frame.empty:
        return {"players": 0, "goal_scorers": [], "assist_providers": [], "leaders": {}}

    goals = pd.to_numeric(frame.get("goals"), errors="coerce")
    assists = pd.to_numeric(frame.get("assists"), errors="coerce")

    goal_rows = frame.loc[goals.fillna(0) > 0, ["player", "goals"]].copy()
    assist_rows = frame.loc[assists.fillna(0) > 0, ["player", "assists"]].copy()

    goal_scorers = [
        {"player": str(r.player), "goals": int(r.goals)}
        for r in goal_rows.itertuples(index=False)
    ]
    assist_providers = [
        {"player": str(r.player), "assists": int(r.assists)}
        for r in assist_rows.itertuples(index=False)
    ]

    return {
        "players": int(len(frame)),
        "goal_scorers": goal_scorers,
        "assist_providers": assist_providers,
        "leaders": {
            "shots_total": _leader(frame, "shots_total"),
            "passes_completed": _leader(frame, "passes_completed"),
            "tackles_won": _leader(frame, "tackles_won"),
            "interceptions": _leader(frame, "interceptions"),
        },
    }
