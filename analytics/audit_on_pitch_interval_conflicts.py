"""Audit conflicting on-pitch intervals before PERF-17 V3 context materialization."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit lineup/event substitution timing conflicts")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--input-dir", type=Path, default=None)
    return p.parse_args()


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
    for candidate in candidates:
        path = candidate.expanduser().resolve()
        if (path / "opta_lineups.parquet").exists() and (path / "opta_events.parquet").exists():
            return path
    raise FileNotFoundError("PannaData input directory not found")


def sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def norm(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text or None


def truthy(value) -> bool:
    """Match build_on_pitch_goal_context starter parsing exactly."""
    if value is None or pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y"}
    return bool(value)


def event_second(minute, second) -> int | None:
    if minute is None or pd.isna(minute):
        return None
    return int(float(minute)) * 60 + (0 if second is None or pd.isna(second) else int(float(second)))


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    input_dir = discover_input_dir(args.input_dir)
    with duckdb.connect(str(db), read_only=True) as con:
        main_team = con.execute(
            "SELECT team_id, COUNT(*) n FROM player_match WHERE minutes_played>0 GROUP BY team_id ORDER BY n DESC LIMIT 1"
        ).fetchone()
        team_id = str(main_team[0])
        source_team_id = str(con.execute("SELECT source_team_id FROM teams WHERE team_id=?", [team_id]).fetchone()[0])
        source_matches = [str(r[0]) for r in con.execute(
            "SELECT m.source_match_id FROM team_match tm JOIN matches m ON m.match_id=tm.match_id WHERE tm.team_id=?",
            [team_id],
        ).fetchall()]

    in_list = ", ".join("'" + x.replace("'", "''") + "'" for x in source_matches)
    team_literal = "'" + source_team_id.replace("'", "''") + "'"
    with duckdb.connect() as con:
        lineups = con.execute(f"""
            SELECT match_id, player_id, player_name, is_starter, minutes_played, sub_on_minute, sub_off_minute
            FROM read_parquet('{sql_path(input_dir / 'opta_lineups.parquet')}')
            WHERE team_id={team_literal} AND match_id IN ({in_list}) AND minutes_played>0
        """).df()
        events = con.execute(f"""
            SELECT match_id, event_type, minute, second, player_id, player_on_id, player_off_id
            FROM read_parquet('{sql_path(input_dir / 'opta_events.parquet')}')
            WHERE team_id={team_literal} AND match_id IN ({in_list})
              AND (player_on_id IS NOT NULL OR player_off_id IS NOT NULL)
            ORDER BY match_id, minute, second
        """).df()

    on_times: dict[tuple[str, str], list[int]] = {}
    off_times: dict[tuple[str, str], list[int]] = {}
    for r in events.itertuples(index=False):
        sec = event_second(r.minute, r.second)
        if sec is None:
            continue
        mid = str(r.match_id)
        on = norm(r.player_on_id)
        off = norm(r.player_off_id)
        if on:
            on_times.setdefault((mid, on), []).append(sec)
        if off:
            off_times.setdefault((mid, off), []).append(sec)

    conflicts = []
    for r in lineups.itertuples(index=False):
        mid = str(r.match_id)
        pid = norm(r.player_id)
        ons = on_times.get((mid, pid), [])
        offs = off_times.get((mid, pid), [])
        started = truthy(r.is_starter)
        start = 0 if started else (min(ons) if ons else None)
        end = min(offs) if offs else None
        if start is not None and end is not None and end < start:
            conflicts.append((mid, pid, r.player_name, started, r.minutes_played, r.sub_on_minute, r.sub_off_minute, ons, offs))

    print("ON-PITCH INTERVAL CONFLICT AUDIT")
    print(f"conflicts={len(conflicts)}")
    for c in conflicts:
        mid, pid, name, starter, mins, lineup_on, lineup_off, ons, offs = c
        print("---")
        print(f"match_id={mid}")
        print(f"player_id={pid}")
        print(f"player={name}")
        print(f"starter={starter} minutes_played={mins}")
        print(f"lineup_sub_on_minute={lineup_on} lineup_sub_off_minute={lineup_off}")
        print(f"event_sub_on_seconds={ons}")
        print(f"event_sub_off_seconds={offs}")
        sample = events[(events['match_id'].astype(str)==mid) & (
            events['player_on_id'].astype(str).str.contains(pid, na=False) |
            events['player_off_id'].astype(str).str.contains(pid, na=False)
        )]
        print(sample.to_string(index=False))


if __name__ == "__main__":
    main()
