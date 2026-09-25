"""Inspect the real PannaData lineup source for the validated 38-match demo case.

DATA-02 diagnostic only. This script does not modify the normalized database.
It prints the real opta_lineups schema and compact value/null diagnostics for
rows belonging to the validated Deportivo Alavés 2025/26 match set.

Usage from repository root:
    python data/inspect_demo_lineups.py
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import duckdb
import pandas as pd


HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = Path(r"C:\Users\sergi\Desktop\analisi_futbol\input\pannadata")
DEFAULT_DB = HERE / "football_performance.duckdb"
DEFAULT_TEAM_SOURCE_ID = "4dtdjgnpdq9uw4sdutti0vaar"

FIELD_CANDIDATES = {
    "match_id": ["match_id", "matchId", "game_id", "gameId", "fixture_id", "fixtureId", "opta_match_id"],
    "team_id": ["team_id", "teamId", "contestant_id", "contestantId", "club_id", "clubId"],
    "player_id": ["player_id", "playerId", "person_id", "personId", "athlete_id", "athleteId"],
    "player_name": ["player_name", "playerName", "full_name", "fullName", "name"],
    "started": ["started", "starter", "is_starter", "isStarter", "starting", "is_starting", "isStarting"],
    "position": ["position", "position_name", "positionName", "pos", "player_position", "playerPosition"],
    "shirt_number": ["shirt_number", "shirtNumber", "jersey_number", "jerseyNumber", "number"],
    "formation": ["formation", "formation_name", "formationName", "team_formation", "teamFormation", "starting_formation", "startingFormation"],
    "status": ["status", "lineup_status", "lineupStatus", "player_status", "playerStatus", "type"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect real demo lineups for DATA-02")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--team-source-id", default=DEFAULT_TEAM_SOURCE_ID)
    return parser.parse_args()


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def resolve_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized = {}
    for column in columns:
        normalized.setdefault(normalize_name(column), []).append(column)
    for candidate in candidates:
        if candidate in columns:
            return candidate
        matches = normalized.get(normalize_name(candidate), [])
        if len(matches) == 1:
            return matches[0]
    return None


def compact_values(series: pd.Series, limit: int = 8) -> str:
    values = series.dropna().astype(str).value_counts().head(limit)
    if values.empty:
        return "<no non-null values>"
    return "; ".join(f"{value} ({count})" for value, count in values.items())


def main() -> None:
    args = parse_args()
    source_path = args.input_dir.expanduser().resolve() / "opta_lineups.parquet"
    db_path = args.db.expanduser().resolve()

    if not source_path.exists():
        raise FileNotFoundError(f"Missing source: {source_path}")
    if not db_path.exists():
        raise FileNotFoundError(f"Missing normalized DB: {db_path}. Run Stage 2A first.")

    with duckdb.connect(str(db_path)) as con:
        fixture_ids = [
            str(row[0])
            for row in con.execute(
                """
                SELECT m.source_match_id
                FROM matches m
                JOIN team_match tm ON tm.match_id = m.match_id
                JOIN teams t ON t.team_id = tm.team_id
                WHERE t.source_team_id = ?
                ORDER BY m.source_match_id
                """,
                [str(args.team_source_id)],
            ).fetchall()
        ]
        if len(fixture_ids) != 38:
            raise RuntimeError(f"Expected 38 validated demo fixtures, found {len(fixture_ids)}")

        escaped = str(source_path).replace("'", "''")
        schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{escaped}')").fetchall()
        columns = [row[0] for row in schema]
        types = {row[0]: row[1] for row in schema}

        mapping = {
            logical: resolve_column(columns, candidates)
            for logical, candidates in FIELD_CANDIDATES.items()
        }

        match_col = mapping["match_id"]
        team_col = mapping["team_id"]
        if not match_col:
            raise RuntimeError("Could not resolve a match identifier in opta_lineups.")

        quoted_match = '"' + match_col.replace('"', '""') + '"'
        placeholders = ",".join("?" for _ in fixture_ids)
        sql = f"SELECT * FROM read_parquet('{escaped}') WHERE CAST({quoted_match} AS VARCHAR) IN ({placeholders})"
        params: list[object] = fixture_ids
        if team_col:
            quoted_team = '"' + team_col.replace('"', '""') + '"'
            sql += f" AND CAST({quoted_team} AS VARCHAR) = ?"
            params.append(str(args.team_source_id))

        frame = con.execute(sql, params).fetchdf()

    print("=" * 88)
    print("DATA-02 — REAL opta_lineups INSPECTION")
    print("=" * 88)
    print(f"Source: {source_path}")
    print(f"Demo rows: {len(frame)}")
    print("\nSCHEMA (all columns):")
    for column in columns:
        print(f"  {column:32} {types[column]}")

    print("\nCANDIDATE MAPPING:")
    for logical, source in mapping.items():
        print(f"  {logical:16} -> {source}")

    print("\nDEMO-ROW DIAGNOSTICS:")
    if frame.empty:
        print("  No demo-team rows found. Check team_id mapping/source semantics.")
    else:
        for column in columns:
            series = frame[column]
            nulls = int(series.isna().sum())
            unique = int(series.nunique(dropna=True))
            print(f"\n[{column}] null={nulls}/{len(frame)} unique={unique}")
            print("  " + compact_values(series))

    print("\nEND DATA-02 INSPECTION")


if __name__ == "__main__":
    main()
