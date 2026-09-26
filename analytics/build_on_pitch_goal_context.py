"""Build validated player-match on-pitch goal context for PERF-17.

Uses source lineup substitution context plus goal events to count team goals for/against
while each player was actually on the pitch. This is team context, not an individual
causal attribution.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
CONTEXT_VERSION = "on_pitch_goal_context_v0.1"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build on-pitch goal context")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--input-dir", type=Path, default=None)
    return p.parse_args()


def _norm_id(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        head = text[:-2]
        if head.isdigit():
            text = head
    return text or None


def _truthy(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y"}
    return bool(value)


def _event_second(minute: Any, second: Any) -> int | None:
    if minute is None or pd.isna(minute):
        return None
    m = int(float(minute))
    s = 0 if second is None or pd.isna(second) else int(float(second))
    return m * 60 + s


def discover_input_dir(explicit: Path | None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    env = os.environ.get("FPS_INPUT_DIR")
    if env:
        candidates.append(Path(env))
    candidates.extend([
        Path(r"D:\Data\Sergi\Desktop\analisi_futbol\input\pannadata"),
        Path(r"C:\Users\sergi\Desktop\analisi_futbol\input\pannadata"),
        Path(r"D:\Data\Sergi\Desktop\analisi_futbol\pannadata"),
        Path(r"C:\Users\sergi\Desktop\analisi_futbol\pannadata"),
    ])
    needed = {"opta_lineups.parquet", "opta_events.parquet", "opta_shot_events.parquet"}
    for candidate in candidates:
        path = candidate.expanduser().resolve()
        if path.exists() and all((path / name).exists() for name in needed):
            return path
    checked = "\n".join(str(p) for p in candidates)
    raise FileNotFoundError(
        "Could not find PannaData input directory with lineups/events/shot_events. Checked:\n" + checked
    )


def _sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)
    input_dir = discover_input_dir(args.input_dir)

    with duckdb.connect(str(db)) as con:
        tables = {r[0] for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()}
        if "player_match_on_pitch_context" not in tables:
            raise RuntimeError("Missing player_match_on_pitch_context. Run data/init_database.py --db <db> first.")

        main_team = con.execute(
            """
            SELECT team_id, COUNT(*) AS n
            FROM player_match
            WHERE minutes_played > 0
            GROUP BY team_id
            ORDER BY n DESC, team_id
            LIMIT 1
            """
        ).fetchone()
        if main_team is None:
            raise RuntimeError("No played player_match rows")
        team_id = str(main_team[0])

        team_row = con.execute(
            "SELECT source_team_id FROM teams WHERE team_id=?", [team_id]
        ).fetchone()
        if not team_row or team_row[0] is None:
            raise RuntimeError("Main team source_team_id unavailable")
        source_team_id = str(team_row[0])

        match_meta = con.execute(
            """
            SELECT
                m.match_id, m.source_match_id,
                home.source_team_id AS home_source_team_id,
                away.source_team_id AS away_source_team_id,
                tm.score_for, tm.score_against
            FROM team_match tm
            JOIN matches m ON m.match_id=tm.match_id
            LEFT JOIN teams home ON home.team_id=m.home_team_id
            LEFT JOIN teams away ON away.team_id=m.away_team_id
            WHERE tm.team_id=?
            ORDER BY m.match_date, m.match_id
            """,
            [team_id],
        ).df()
        if match_meta.empty:
            raise RuntimeError("No team matches found")
        if match_meta[["source_match_id", "home_source_team_id", "away_source_team_id"]].isna().any().any():
            raise RuntimeError("Source match/team identifiers incomplete")

        player_map = {
            str(source_id): str(player_id)
            for source_id, player_id in con.execute(
                "SELECT source_player_id, player_id FROM players WHERE source_player_id IS NOT NULL"
            ).fetchall()
        }

        source_matches = match_meta["source_match_id"].astype(str).tolist()
        match_map = dict(zip(match_meta["source_match_id"].astype(str), match_meta["match_id"].astype(str)))
        meta_by_source = {
            str(r.source_match_id): r for r in match_meta.itertuples(index=False)
        }
        in_list = ", ".join("'" + x.replace("'", "''") + "'" for x in source_matches)
        team_literal = "'" + source_team_id.replace("'", "''") + "'"

        lineups_path = input_dir / "opta_lineups.parquet"
        events_path = input_dir / "opta_events.parquet"
        shots_path = input_dir / "opta_shot_events.parquet"

        lineups = con.execute(
            f"""
            SELECT match_id, player_id, is_starter, minutes_played,
                   sub_on_minute, sub_off_minute
            FROM read_parquet('{_sql_path(lineups_path)}')
            WHERE team_id={team_literal} AND match_id IN ({in_list})
            """
        ).df()
        lineups["minutes_played"] = pd.to_numeric(lineups["minutes_played"], errors="coerce")
        played = lineups[lineups["minutes_played"].fillna(0) > 0].copy()

        summary = con.execute(
            f"""
            SELECT match_id, minute, second, player_on_id, player_off_id
            FROM read_parquet('{_sql_path(events_path)}')
            WHERE team_id={team_literal} AND match_id IN ({in_list})
              AND (player_on_id IS NOT NULL OR player_off_id IS NOT NULL)
            """
        ).df()

        sub_on: dict[tuple[str, str], int] = {}
        sub_off: dict[tuple[str, str], int] = {}
        for row in summary.itertuples(index=False):
            sec = _event_second(row.minute, row.second)
            if sec is None:
                continue
            mid = str(row.match_id)
            on_id = _norm_id(row.player_on_id)
            off_id = _norm_id(row.player_off_id)
            if on_id:
                sub_on[(mid, on_id)] = min(sec, sub_on.get((mid, on_id), sec))
            if off_id:
                sub_off[(mid, off_id)] = min(sec, sub_off.get((mid, off_id), sec))

        shots = con.execute(
            f"""
            SELECT match_id, team_id, minute, second, type_id, is_goal, is_own_goal
            FROM read_parquet('{_sql_path(shots_path)}')
            WHERE match_id IN ({in_list})
            """
        ).df()

        goals_by_match: dict[str, list[tuple[int, str]]] = {mid: [] for mid in source_matches}
        for row in shots.itertuples(index=False):
            own_goal = _truthy(row.is_own_goal)
            try:
                type_id = int(float(row.type_id)) if row.type_id is not None and not pd.isna(row.type_id) else None
            except (TypeError, ValueError):
                type_id = None
            is_goal = _truthy(row.is_goal) or own_goal or type_id == 16
            if not is_goal:
                continue
            sec = _event_second(row.minute, row.second)
            if sec is None:
                raise RuntimeError(f"Goal without timestamp in source match {row.match_id}")
            mid = str(row.match_id)
            meta = meta_by_source[mid]
            event_team = str(row.team_id)
            if own_goal:
                home = str(meta.home_source_team_id)
                away = str(meta.away_source_team_id)
                if event_team == home:
                    scoring_team = away
                elif event_team == away:
                    scoring_team = home
                else:
                    raise RuntimeError(f"Own-goal team not in fixture: {mid} / {event_team}")
            else:
                scoring_team = event_team
            goals_by_match[mid].append((sec, scoring_team))

        # Validate reconstructed score before using goal timing anywhere downstream.
        score_errors: list[str] = []
        for mid, meta in meta_by_source.items():
            goals = goals_by_match[mid]
            gf = sum(1 for _, scoring in goals if scoring == source_team_id)
            ga = sum(1 for _, scoring in goals if scoring != source_team_id)
            if gf != int(meta.score_for) or ga != int(meta.score_against):
                score_errors.append(f"{mid}: reconstructed={gf}-{ga} expected={int(meta.score_for)}-{int(meta.score_against)}")
        if score_errors:
            raise RuntimeError("Goal timeline does not reconcile to final scores:\n" + "\n".join(score_errors[:20]))

        rows: list[tuple] = []
        minute_fallback_rows = 0
        exact_timing_rows = 0
        boundary_ambiguity_total = 0

        for row in played.itertuples(index=False):
            mid = str(row.match_id)
            source_player_id = _norm_id(row.player_id)
            if not source_player_id or source_player_id not in player_map:
                raise RuntimeError(f"Played lineup player not mapped: {mid} / {row.player_id}")
            player_id = player_map[source_player_id]
            started = _truthy(row.is_starter)

            if started:
                start_second = 0
                start_source = "STARTER"
            elif (mid, source_player_id) in sub_on:
                start_second = sub_on[(mid, source_player_id)]
                start_source = "EVENT_SECOND"
            elif row.sub_on_minute is not None and not pd.isna(row.sub_on_minute):
                start_second = int(float(row.sub_on_minute)) * 60
                start_source = "LINEUP_MINUTE"
            else:
                raise RuntimeError(f"Played substitute without sub-on time: {mid} / {source_player_id}")

            if (mid, source_player_id) in sub_off:
                end_second = sub_off[(mid, source_player_id)]
                end_source = "EVENT_SECOND"
            elif row.sub_off_minute is not None and not pd.isna(row.sub_off_minute):
                end_second = int(float(row.sub_off_minute)) * 60
                end_source = "LINEUP_MINUTE"
            else:
                end_second = None
                end_source = "MATCH_END"

            if end_second is not None and end_second < start_second:
                raise RuntimeError(f"Invalid on-pitch interval: {mid} / {source_player_id}")

            minute_fallback = start_source == "LINEUP_MINUTE" or end_source == "LINEUP_MINUTE"
            timing_precision = "MINUTE_FALLBACK" if minute_fallback else "SECOND_OR_BOUNDARY_EXACT"
            if minute_fallback:
                minute_fallback_rows += 1
            else:
                exact_timing_rows += 1

            gf = ga = ambiguous = 0
            for sec, scoring in goals_by_match[mid]:
                if sec < start_second:
                    continue
                if end_second is not None and sec >= end_second:
                    continue
                if scoring == source_team_id:
                    gf += 1
                else:
                    ga += 1
                if minute_fallback:
                    if start_source == "LINEUP_MINUTE" and sec // 60 == start_second // 60:
                        ambiguous += 1
                    if end_source == "LINEUP_MINUTE" and end_second is not None and sec // 60 == end_second // 60:
                        ambiguous += 1

            boundary_ambiguity_total += ambiguous
            meta = meta_by_source[mid]
            rows.append((
                match_map[mid], team_id, player_id,
                int(start_second), None if end_second is None else int(end_second),
                start_source, end_source, timing_precision,
                int(gf), int(ga), int(gf - ga),
                int(meta.score_for), int(meta.score_against), int(ambiguous), CONTEXT_VERSION,
            ))

        played_db = con.execute(
            "SELECT COUNT(*) FROM player_match WHERE team_id=? AND minutes_played>0", [team_id]
        ).fetchone()[0]
        if len(rows) != played_db:
            raise RuntimeError(f"On-pitch context coverage mismatch: {len(rows)}/{played_db}")

        con.execute("DELETE FROM player_match_on_pitch_context WHERE context_version=?", [CONTEXT_VERSION])
        con.executemany(
            """
            INSERT INTO player_match_on_pitch_context (
                match_id, team_id, player_id, start_second, end_second,
                start_source, end_source, timing_precision,
                goals_for_on_pitch, goals_against_on_pitch, goal_diff_on_pitch,
                team_goals_for, team_goals_against, boundary_ambiguity_goals,
                context_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    print("PERF-17 ON-PITCH GOAL CONTEXT: PASS")
    print(f"context_version={CONTEXT_VERSION}")
    print(f"input_dir={input_dir}")
    print(f"rows={len(rows)}")
    print(f"exact_timing_rows={exact_timing_rows}")
    print(f"minute_fallback_rows={minute_fallback_rows}")
    print(f"boundary_ambiguity_goals={boundary_ambiguity_total}")
    print("goal_timeline_vs_final_score=PASS")
    print("Interpretation: team context while player was on pitch; not individual causal responsibility.")


if __name__ == "__main__":
    main()
