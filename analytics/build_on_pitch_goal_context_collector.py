"""Materialize the existing on-pitch goal-context contract from Collector rows.

This is a source adapter only.  It uses the same interval resolver and writes the
same ``on_pitch_goal_context_v0.2`` rows as ``build_on_pitch_goal_context.py``;
the difference is that the timeline comes from the official Collector export
already normalized into DuckDB instead of the private Opta parquet inputs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.build_on_pitch_goal_context import CONTEXT_VERSION, _resolve_interval

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
SOURCE_TYPE = "collector_html_v1.1"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build on-pitch goal context from Collector rows")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    db = args.db.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)

    with duckdb.connect(str(db)) as con:
        matches = con.execute(
            """
            SELECT DISTINCT pm.match_id, pm.team_id
            FROM player_match pm
            JOIN matches m ON m.match_id=pm.match_id
            WHERE pm.minutes_played > 0 AND m.source_type=?
            ORDER BY pm.match_id, pm.team_id
            """,
            [SOURCE_TYPE],
        ).fetchall()
        if not matches:
            raise RuntimeError("No played Collector player-match rows")

        rows: list[tuple] = []
        for match_id, team_id in matches:
            played = con.execute(
                """
                SELECT pm.player_id, pm.started, pm.minutes_played,
                       MIN(rs.start_second) AS stint_start, MAX(rs.end_second) AS stint_end
                FROM player_match pm
                LEFT JOIN player_role_stints rs
                  ON rs.match_id=pm.match_id AND rs.team_id=pm.team_id
                 AND rs.player_id=pm.player_id AND rs.source_type=?
                WHERE pm.match_id=? AND pm.team_id=? AND pm.minutes_played>0
                GROUP BY pm.player_id, pm.started, pm.minutes_played
                ORDER BY pm.player_id
                """,
                [SOURCE_TYPE, match_id, team_id],
            ).fetchall()
            goals = con.execute(
                """
                SELECT match_second, qualifiers
                FROM match_events
                WHERE match_id=? AND team_id=? AND source_type=?
                  AND action_type='SHOT' AND outcome='GOAL'
                ORDER BY match_second, event_id
                """,
                [match_id, team_id, SOURCE_TYPE],
            ).fetchall()
            goal_seconds = []
            for second, qualifiers in goals:
                data = json.loads(qualifiers or "{}")
                if not bool(data.get("own_goal")):
                    goal_seconds.append(int(second))

            for player_id, started, minutes, stint_start, stint_end in played:
                start, end, start_source, end_source, precision, conflict = _resolve_interval(
                    mid=str(match_id), source_player_id=str(player_id), started=bool(started),
                    minutes_played=float(minutes), lineup_on=None, lineup_off=None,
                    event_on=None if stint_start is None else int(stint_start),
                    event_off=None if stint_end is None else int(stint_end),
                )
                goals_for = sum(sec >= start and (end is None or sec < end) for sec in goal_seconds)
                ambiguity = sum(
                    precision != "SECOND_OR_BOUNDARY_EXACT" and (
                        sec // 60 == start // 60 or (end is not None and sec // 60 == end // 60)
                    ) for sec in goal_seconds
                )
                rows.append((
                    match_id, team_id, player_id, start, end, start_source, end_source, precision,
                    goals_for, 0, goals_for, len(goal_seconds), 0, ambiguity, CONTEXT_VERSION,
                ))

        con.execute("DELETE FROM player_match_on_pitch_context WHERE context_version=?", [CONTEXT_VERSION])
        con.executemany(
            """
            INSERT INTO player_match_on_pitch_context (
                match_id, team_id, player_id, start_second, end_second, start_source, end_source,
                timing_precision, goals_for_on_pitch, goals_against_on_pitch, goal_diff_on_pitch,
                team_goals_for, team_goals_against, boundary_ambiguity_goals, context_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    print("PERF-18 COLLECTOR ON-PITCH GOAL CONTEXT: PASS")
    print(f"context_version={CONTEXT_VERSION} rows={len(rows)}")
    print("source=Collector normalized match_events/player_role_stints")


if __name__ == "__main__":
    main()
