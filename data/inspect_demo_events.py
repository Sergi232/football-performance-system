"""Inspect the real event/shot sources for DATA-03 without guessing mappings.

Run from repository root after DATA-02:
    python data/inspect_demo_events.py

The script reads only the 38 already validated demo matches and prints the real
schema, candidate field mappings and value distributions needed to implement
match_events safely.
"""

from __future__ import annotations

import argparse
import re
import uuid
from pathlib import Path

import duckdb


HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = Path(r"C:\Users\sergi\Desktop\analisi_futbol\input\pannadata")
DEFAULT_DB = HERE / "football_performance.duckdb"
DEFAULT_TEAM_SOURCE_ID = "4dtdjgnpdq9uw4sdutti0vaar"

SOURCES = (
    "opta_events.parquet",
    "opta_shot_events.parquet",
    "opta_shots.parquet",
)

FIELD_CANDIDATES = {
    "match_id": ["match_id", "matchId", "game_id", "gameId", "fixture_id", "fixtureId"],
    "team_id": ["team_id", "teamId", "contestant_id", "contestantId", "club_id", "clubId"],
    "player_id": ["player_id", "playerId", "person_id", "personId", "athlete_id", "athleteId"],
    "event_id": ["event_id", "eventId", "id", "source_event_id", "sourceEventId"],
    "type_id": ["type_id", "typeId", "event_type_id", "eventTypeId", "event_type", "eventType", "type"],
    "outcome": ["outcome", "outcome_id", "outcomeId", "result", "successful", "success"],
    "period": ["period", "period_id", "periodId", "half"],
    "minute": ["minute", "min", "match_minute", "matchMinute", "time_min"],
    "second": ["second", "sec", "match_second", "matchSecond", "time_sec", "timestamp"],
    "x": ["x", "x_coord", "xCoord", "start_x", "startX"],
    "y": ["y", "y_coord", "yCoord", "start_y", "startY"],
    "qualifiers": ["qualifiers", "qualifier", "qualifier_ids", "qualifierIds", "attributes"],
}

INTERESTING_KEYWORDS = (
    "match", "team", "contestant", "player", "person", "event", "type", "outcome",
    "result", "period", "minute", "second", "time", "qual", "shot", "goal", "target",
    "block", "penalt", "body", "situation", "assist", "xg", "coord", "position", "x", "y",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect DATA-03 event/shot sources")
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


def stable_id(entity: str, source_id: object) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:{entity}:{source_id}"))


def sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def sql_literal(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def qident(column: str) -> str:
    return '"' + column.replace('"', '""') + '"'


def relevant_columns(columns: list[str], mapping: dict[str, str | None]) -> list[str]:
    mapped = {value for value in mapping.values() if value}
    output = []
    for column in columns:
        norm = normalize_name(column)
        keyword_match = any(normalize_name(keyword) in norm for keyword in INTERESTING_KEYWORDS)
        if column in mapped or keyword_match:
            output.append(column)
    return output


def summarize_column(
    con: duckdb.DuckDBPyConnection,
    source_sql: str,
    column: str,
    where_sql: str,
    limit: int = 12,
) -> None:
    col = qident(column)
    stats = con.execute(
        f"""
        SELECT
            COUNT(*) AS n,
            SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) AS null_n,
            COUNT(DISTINCT CAST({col} AS VARCHAR)) AS unique_n
        FROM {source_sql}
        {where_sql}
        """
    ).fetchone()
    n, null_n, unique_n = stats
    values = con.execute(
        f"""
        SELECT CAST({col} AS VARCHAR) AS value, COUNT(*) AS n
        FROM {source_sql}
        {where_sql}
          {"AND" if where_sql else "WHERE"} {col} IS NOT NULL
        GROUP BY 1
        ORDER BY n DESC, value
        LIMIT {int(limit)}
        """
    ).fetchall()
    rendered = "; ".join(f"{value!r} ({count})" for value, count in values)
    print(f"  [{column}] null={int(null_n or 0)}/{n} unique={unique_n}")
    if rendered:
        print(f"    {rendered}")


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.expanduser().resolve()
    db_path = args.db.expanduser().resolve()

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    demo_team_id = stable_id("team", args.team_source_id)

    with duckdb.connect(str(db_path), read_only=True) as con:
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
        source_match_ids = [str(row[0]) for row in fixture_rows]
        if len(source_match_ids) != 38:
            raise RuntimeError(f"Expected 38 validated demo matches, found {len(source_match_ids)}")

        in_list = ", ".join(sql_literal(value) for value in source_match_ids)

        print("=" * 96)
        print("DATA-03 — REAL EVENT / SHOT SOURCE INSPECTION")
        print("=" * 96)
        print(f"Validated demo matches: {len(source_match_ids)}")
        print(f"Demo source team id: {args.team_source_id}")

        for filename in SOURCES:
            path = input_dir / filename
            print("\n" + "=" * 96)
            print(filename)
            print("=" * 96)
            if not path.exists():
                print(f"MISSING: {path}")
                continue

            escaped = sql_path(path)
            source_sql = f"read_parquet('{escaped}')"
            schema = con.execute(f"DESCRIBE SELECT * FROM {source_sql}").fetchall()
            columns = [row[0] for row in schema]
            mapping = {
                logical: resolve_column(columns, candidates)
                for logical, candidates in FIELD_CANDIDATES.items()
            }

            print("SCHEMA:")
            for name, dtype, *_ in schema:
                print(f"  {name:34} {dtype}")

            print("\nCANDIDATE MAPPING:")
            for logical, source in mapping.items():
                print(f"  {logical:14} -> {source}")

            match_col = mapping.get("match_id")
            team_col = mapping.get("team_id")
            if not match_col:
                print("\nSTOP FOR THIS SOURCE: match_id could not be resolved.")
                continue

            match_filter = f"WHERE {qident(match_col)} IN ({in_list})"
            demo_match_rows = con.execute(
                f"SELECT COUNT(*) FROM {source_sql} {match_filter}"
            ).fetchone()[0]
            print(f"\nRows in the 38 demo matches: {demo_match_rows:,}")

            where_sql = match_filter
            if team_col:
                team_condition = f"{qident(team_col)} = {sql_literal(args.team_source_id)}"
                demo_team_rows = con.execute(
                    f"SELECT COUNT(*) FROM {source_sql} {match_filter} AND {team_condition}"
                ).fetchone()[0]
                print(f"Rows attributed to demo team: {demo_team_rows:,}")
                where_sql = f"{match_filter} AND {team_condition}"
            else:
                print("Rows attributed to demo team: unavailable (no team field resolved)")

            inspect_cols = columns if len(columns) <= 15 else relevant_columns(columns, mapping)
            print("\nVALUE DIAGNOSTICS (demo team when team field exists):")
            for column in inspect_cols:
                try:
                    summarize_column(con, source_sql, column, where_sql)
                except Exception as exc:
                    print(f"  [{column}] summary failed: {type(exc).__name__}: {exc}")

            type_col = mapping.get("type_id")
            if type_col:
                print("\nTYPE DISTRIBUTION:")
                rows = con.execute(
                    f"""
                    SELECT CAST({qident(type_col)} AS VARCHAR) AS type_value, COUNT(*) AS n
                    FROM {source_sql}
                    {where_sql}
                    GROUP BY 1
                    ORDER BY n DESC, type_value
                    LIMIT 60
                    """
                ).fetchall()
                for value, count in rows:
                    print(f"  {value!r:28} {count}")

        print("\n" + "=" * 96)
        print("END DATA-03 INSPECTION")
        print("=" * 96)


if __name__ == "__main__":
    main()
