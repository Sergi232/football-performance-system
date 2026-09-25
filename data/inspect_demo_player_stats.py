"""Inspect approved/candidate player-match aggregate stats in the real PannaData source.

DATA-04 inspection only. This script does not write to the normalized database.
It filters the 38 validated demo matches and the demo team, then reports which
source columns actually exist for the variables considered useful for the
Football Performance System MVP.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

from import_demo_events import (
    EXPECTED_MATCHES,
    DEFAULT_DB,
    DEFAULT_INPUT,
    DEFAULT_TEAM_SOURCE_ID,
    sql_literal,
    sql_path,
    stable_id,
)


CANDIDATES: dict[str, list[str]] = {
    "minutes": ["minsPlayed", "minutes_played"],
    "passes_total": ["totalPass"],
    "passes_completed": ["accuratePass"],
    "key_passes": ["keyPass", "totalKeyPass", "keyPasses"],
    "assists": ["goalAssist", "assists"],
    "long_balls_total": ["totalLongBalls"],
    "long_balls_completed": ["accurateLongBalls"],
    "crosses_total": ["totalCross"],
    "crosses_completed": ["accurateCross"],
    "dribbles_total": ["totalContest"],
    "dribbles_won": ["wonContest"],
    "turnovers": ["turnover"],
    "dispossessed": ["dispossessed"],
    "shots_total": ["totalScoringAtt"],
    "shots_blocked": ["blockedScoringAtt"],
    "goals": ["goals"],
    "tackles_total": ["totalTackle"],
    "tackles_won": ["wonTackle"],
    "interceptions": ["interception"],
    "blocked_passes": ["blockedPass"],
    "clearances": ["totalClearance"],
    "fouls_committed": ["fouls"],
    "fouls_received": ["wasFouled"],
    "yellow_cards": ["yellowCard"],
    "red_cards": ["redCard"],
    "penalties_conceded": ["penaltyConceded"],
    "penalties_won": ["penaltyWon"],
    "saves": ["saves"],
    "diving_saves": ["divingSave"],
    "goals_conceded": ["goalsConceded"],
}

SEARCH_HINTS = {
    "pass": ["pass", "key"],
    "cross": ["cross"],
    "long": ["long"],
    "dribble": ["contest", "drib"],
    "loss": ["turnover", "disposs", "loss"],
    "defense": ["tackle", "intercept", "block", "clear"],
    "foul": ["foul"],
    "card": ["card", "yellow", "red"],
    "penalty": ["penalty"],
    "keeper": ["save", "conced"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect DATA-04 player stats candidates")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--team-source-id", default=DEFAULT_TEAM_SOURCE_ID)
    return parser.parse_args()


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.expanduser().resolve()
    db_path = args.db.expanduser().resolve()
    source_path = input_dir / "opta_player_stats.parquet"

    if not source_path.exists():
        raise FileNotFoundError(f"Missing source: {source_path}")
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}. Run DATA-01/DATA-02 first.")

    demo_team_id = stable_id("team", args.team_source_id)

    with duckdb.connect(str(db_path)) as con:
        fixture_rows = con.execute(
            """
            SELECT m.source_match_id
            FROM matches m
            JOIN team_match tm ON tm.match_id = m.match_id
            WHERE tm.team_id = ?
            ORDER BY m.source_match_id
            """,
            [demo_team_id],
        ).fetchall()
        if len(fixture_rows) != EXPECTED_MATCHES:
            raise RuntimeError(
                f"Expected {EXPECTED_MATCHES} validated demo fixtures, found {len(fixture_rows)}"
            )

        match_ids = [str(row[0]) for row in fixture_rows]
        in_list = ", ".join(sql_literal(value) for value in match_ids)
        team_literal = sql_literal(args.team_source_id)

        schema = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{sql_path(source_path)}')"
        ).fetchdf()
        available = {str(name): str(dtype) for name, dtype in schema[["column_name", "column_type"]].itertuples(index=False, name=None)}
        lower_map = {name.lower(): name for name in available}

        selected = ["match_id", "team_id", "player_id", "player_name"]
        resolved: dict[str, str | None] = {}
        for logical, aliases in CANDIDATES.items():
            source_col = next((lower_map[a.lower()] for a in aliases if a.lower() in lower_map), None)
            resolved[logical] = source_col
            if source_col and source_col not in selected:
                selected.append(source_col)

        select_sql = ", ".join(qident(col) for col in selected)
        demo = con.execute(
            f"""
            SELECT {select_sql}
            FROM read_parquet('{sql_path(source_path)}')
            WHERE team_id = {team_literal}
              AND match_id IN ({in_list})
            """
        ).fetchdf()

    print("=" * 96)
    print("DATA-04 — REAL opta_player_stats CANDIDATE INSPECTION")
    print("=" * 96)
    print(f"Source: {source_path}")
    print(f"Demo rows: {len(demo)}")
    print(f"Covered matches: {demo['match_id'].nunique()}/{EXPECTED_MATCHES}")
    print(f"Distinct players: {demo['player_id'].nunique()}")
    print()

    print("CANDIDATE MAPPING:")
    for logical, source_col in resolved.items():
        dtype = available.get(source_col, "-") if source_col else "-"
        print(f"  {logical:<26} -> {str(source_col):<24} {dtype}")

    print("\nCANDIDATE DIAGNOSTICS:")
    for logical, source_col in resolved.items():
        if not source_col:
            print(f"  {logical:<26} MISSING")
            continue
        series = demo[source_col]
        non_null = int(series.notna().sum())
        unique = int(series.nunique(dropna=True))
        numeric = pd.to_numeric(series, errors="coerce")
        numeric_non_null = int(numeric.notna().sum())
        if numeric_non_null:
            zero = int((numeric.fillna(0) == 0).sum())
            total = float(numeric.fillna(0).sum())
            min_value = float(numeric.min()) if numeric.notna().any() else float("nan")
            max_value = float(numeric.max()) if numeric.notna().any() else float("nan")
            print(
                f"  {logical:<26} col={source_col:<22} non_null={non_null:>4}/{len(demo)} "
                f"unique={unique:<4} zero={zero:<4} sum={total:g} min={min_value:g} max={max_value:g}"
            )
        else:
            top = series.dropna().astype(str).value_counts().head(5)
            top_text = "; ".join(f"{idx} ({count})" for idx, count in top.items())
            print(
                f"  {logical:<26} col={source_col:<22} non_null={non_null:>4}/{len(demo)} "
                f"unique={unique:<4} top={top_text}"
            )

    missing = [logical for logical, source_col in resolved.items() if source_col is None]
    if missing:
        print("\nMISSING-CANDIDATE SEARCH HINTS:")
        all_columns = list(available)
        for label, needles in SEARCH_HINTS.items():
            hits = [
                col for col in all_columns
                if any(needle.lower() in col.lower() for needle in needles)
            ]
            if hits:
                print(f"  {label:<12}: {', '.join(hits[:30])}")

    print("\nEND DATA-04 INSPECTION")


if __name__ == "__main__":
    main()
