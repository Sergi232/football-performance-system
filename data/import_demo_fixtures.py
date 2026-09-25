"""Import the demo team's 2025/26 fixtures into the normalized FPS database.

Stage 1 of the PannaData/Opta import pipeline.

The script is deliberately fail-fast: it auto-detects common fixture column names,
but if a required field cannot be resolved it stops and prints the real available
columns instead of guessing silently.

Usage:
    python data/import_demo_fixtures.py
    python data/import_demo_fixtures.py --input-dir C:/path/to/pannadata
    python data/import_demo_fixtures.py --db C:/path/to/football_performance.duckdb

Default demo source team:
    Deportivo Alavés, Opta id 4dtdjgnpdq9uw4sdutti0vaar
"""

from __future__ import annotations

import argparse
import re
import uuid
from pathlib import Path

import duckdb
import pandas as pd


HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = Path(r"C:\Users\sergi\Desktop\analisi_futbol\input\pannadata")
DEFAULT_DB = HERE / "football_performance.duckdb"
SCHEMA_FILE = HERE / "schema.sql"
DEFAULT_TEAM_SOURCE_ID = "4dtdjgnpdq9uw4sdutti0vaar"
DEFAULT_TEAM_NAME = "Deportivo Alavés"
DEFAULT_SEASON = "2025/26"
DEFAULT_COMPETITION = "LaLiga"
SEASON_START = pd.Timestamp("2025-07-01")
SEASON_END = pd.Timestamp("2026-06-30 23:59:59")


FIELD_CANDIDATES = {
    "match_id": [
        "match_id", "matchId", "game_id", "gameId", "fixture_id", "fixtureId",
        "opta_match_id", "id",
    ],
    "match_date": [
        "match_date", "matchDate", "date", "game_date", "gameDate", "kickoff",
        "kick_off", "kickoff_time", "kickoffTime", "start_time", "startTime",
        "start_date", "startDate",
    ],
    "home_team_id": [
        "home_team_id", "homeTeamId", "home_id", "homeId", "team_home_id",
        "home_team_uid", "homeTeamUid",
    ],
    "away_team_id": [
        "away_team_id", "awayTeamId", "away_id", "awayId", "team_away_id",
        "away_team_uid", "awayTeamUid",
    ],
    "home_team_name": [
        "home_team_name", "homeTeamName", "home_name", "homeName", "home_team",
        "homeTeam",
    ],
    "away_team_name": [
        "away_team_name", "awayTeamName", "away_name", "awayName", "away_team",
        "awayTeam",
    ],
    "home_score": [
        "home_score", "homeScore", "score_home", "home_goals", "homeGoals",
    ],
    "away_score": [
        "away_score", "awayScore", "score_away", "away_goals", "awayGoals",
    ],
    "competition": [
        "competition", "competition_name", "competitionName", "tournament",
        "tournament_name", "tournamentName",
    ],
    "season": ["season", "season_name", "seasonName"],
}


REQUIRED_FIELDS = ("match_id", "home_team_id", "away_team_id")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import demo fixtures into FPS DuckDB")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--team-source-id", default=DEFAULT_TEAM_SOURCE_ID)
    parser.add_argument("--team-name", default=DEFAULT_TEAM_NAME)
    parser.add_argument("--season", default=DEFAULT_SEASON)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION)
    parser.add_argument(
        "--allow-non-38",
        action="store_true",
        help="Allow a demo import with a fixture count other than 38.",
    )
    return parser.parse_args()


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def resolve_column(columns: list[str], candidates: list[str]) -> str | None:
    by_normalized: dict[str, list[str]] = {}
    for column in columns:
        by_normalized.setdefault(normalize_name(column), []).append(column)

    for candidate in candidates:
        if candidate in columns:
            return candidate
        matches = by_normalized.get(normalize_name(candidate), [])
        if len(matches) == 1:
            return matches[0]
    return None


def resolve_mapping(columns: list[str]) -> dict[str, str | None]:
    mapping = {
        logical: resolve_column(columns, candidates)
        for logical, candidates in FIELD_CANDIDATES.items()
    }
    missing = [field for field in REQUIRED_FIELDS if mapping[field] is None]
    if missing:
        raise RuntimeError(
            "Could not resolve required fixture fields: "
            f"{missing}.\nAvailable columns:\n  - " + "\n  - ".join(columns)
        )
    return mapping


def stable_id(entity: str, source_id: object) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:{entity}:{source_id}"))


def sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def safe_text(value: object, fallback: str) -> str:
    if pd.isna(value):
        return fallback
    text = str(value).strip()
    return text if text else fallback


def nullable_int(value: object) -> int | None:
    if pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def initialize_schema(con: duckdb.DuckDBPyConnection) -> None:
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_FILE}")
    con.execute(SCHEMA_FILE.read_text(encoding="utf-8"))


def load_fixtures(con: duckdb.DuckDBPyConnection, fixture_path: Path) -> tuple[pd.DataFrame, dict[str, str | None]]:
    escaped = sql_path(fixture_path)
    schema = con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{escaped}')"
    ).fetchall()
    columns = [row[0] for row in schema]
    mapping = resolve_mapping(columns)

    selected = sorted({column for column in mapping.values() if column is not None})
    quoted = ", ".join(f'"{column.replace(chr(34), chr(34)*2)}"' for column in selected)
    frame = con.execute(
        f"SELECT {quoted} FROM read_parquet('{escaped}')"
    ).fetchdf()
    return frame, mapping


def filter_demo_matches(
    fixtures: pd.DataFrame,
    mapping: dict[str, str | None],
    team_source_id: str,
    allow_non_38: bool,
) -> pd.DataFrame:
    home_col = mapping["home_team_id"]
    away_col = mapping["away_team_id"]
    assert home_col and away_col

    team_source_id = str(team_source_id)
    mask = (
        fixtures[home_col].astype("string").fillna("").eq(team_source_id)
        | fixtures[away_col].astype("string").fillna("").eq(team_source_id)
    )
    demo = fixtures.loc[mask].copy()

    date_col = mapping.get("match_date")
    if date_col and not demo.empty:
        parsed = pd.to_datetime(demo[date_col], errors="coerce", utc=True)
        parsed_naive = parsed.dt.tz_convert(None)
        usable = parsed_naive.notna()
        if usable.any():
            in_season = (~usable) | parsed_naive.between(SEASON_START, SEASON_END)
            demo = demo.loc[in_season].copy()
            demo["__match_date"] = parsed_naive.loc[demo.index]

    demo = demo.drop_duplicates(subset=[mapping["match_id"]])

    if demo.empty:
        raise RuntimeError(
            f"No fixtures found for source team id {team_source_id}. "
            "Run data/audit_pannadata_sources.py and inspect the real fixture schema."
        )

    if len(demo) != 38 and not allow_non_38:
        raise RuntimeError(
            f"Expected 38 LaLiga fixtures for the demo season, found {len(demo)}. "
            "Import aborted to avoid silently mixing competitions/seasons. "
            "Use --allow-non-38 only for diagnostics."
        )

    return demo


def upsert_team(
    con: duckdb.DuckDBPyConnection,
    source_team_id: object,
    display_name: str,
) -> str:
    source_team_id = str(source_team_id)
    team_id = stable_id("team", source_team_id)
    con.execute(
        """
        INSERT INTO teams (team_id, display_name, source_name, source_team_id, is_anonymized)
        VALUES (?, ?, ?, ?, FALSE)
        ON CONFLICT (team_id) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            source_name = EXCLUDED.source_name,
            source_team_id = EXCLUDED.source_team_id
        """,
        [team_id, display_name, display_name, source_team_id],
    )
    return team_id


def import_matches(
    con: duckdb.DuckDBPyConnection,
    demo: pd.DataFrame,
    mapping: dict[str, str | None],
    args: argparse.Namespace,
) -> None:
    match_col = mapping["match_id"]
    home_id_col = mapping["home_team_id"]
    away_id_col = mapping["away_team_id"]
    assert match_col and home_id_col and away_id_col

    for _, row in demo.iterrows():
        source_match_id = safe_text(row[match_col], "")
        if not source_match_id:
            raise RuntimeError("Fixture with empty source match id encountered")

        source_home_id = safe_text(row[home_id_col], "")
        source_away_id = safe_text(row[away_id_col], "")
        if not source_home_id or not source_away_id:
            raise RuntimeError(f"Fixture {source_match_id} has empty team identifiers")

        home_name_col = mapping.get("home_team_name")
        away_name_col = mapping.get("away_team_name")
        home_name = safe_text(
            row[home_name_col] if home_name_col else None,
            args.team_name if source_home_id == args.team_source_id else source_home_id,
        )
        away_name = safe_text(
            row[away_name_col] if away_name_col else None,
            args.team_name if source_away_id == args.team_source_id else source_away_id,
        )

        home_team_id = upsert_team(con, source_home_id, home_name)
        away_team_id = upsert_team(con, source_away_id, away_name)
        match_id = stable_id("match", source_match_id)

        home_score_col = mapping.get("home_score")
        away_score_col = mapping.get("away_score")
        home_score = nullable_int(row[home_score_col]) if home_score_col else None
        away_score = nullable_int(row[away_score_col]) if away_score_col else None

        match_date = row.get("__match_date")
        if pd.isna(match_date):
            date_col = mapping.get("match_date")
            raw_date = row[date_col] if date_col else None
            parsed_date = pd.to_datetime(raw_date, errors="coerce")
            match_date = None if pd.isna(parsed_date) else parsed_date.to_pydatetime()
        elif hasattr(match_date, "to_pydatetime"):
            match_date = match_date.to_pydatetime()

        competition_col = mapping.get("competition")
        season_col = mapping.get("season")
        competition = safe_text(row[competition_col] if competition_col else None, args.competition)
        season = safe_text(row[season_col] if season_col else None, args.season)

        con.execute(
            """
            INSERT INTO matches (
                match_id, competition, season, match_date,
                home_team_id, away_team_id, home_score, away_score,
                source_match_id, source_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PANNADATA_OPTA')
            ON CONFLICT (match_id) DO UPDATE SET
                competition = EXCLUDED.competition,
                season = EXCLUDED.season,
                match_date = EXCLUDED.match_date,
                home_team_id = EXCLUDED.home_team_id,
                away_team_id = EXCLUDED.away_team_id,
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score,
                source_match_id = EXCLUDED.source_match_id,
                source_type = EXCLUDED.source_type
            """,
            [
                match_id, competition, season, match_date,
                home_team_id, away_team_id, home_score, away_score, source_match_id,
            ],
        )

        for team_id, opponent_id, is_home, score_for, score_against in (
            (home_team_id, away_team_id, True, home_score, away_score),
            (away_team_id, home_team_id, False, away_score, home_score),
        ):
            con.execute(
                """
                INSERT INTO team_match (
                    match_id, team_id, opponent_team_id, is_home,
                    score_for, score_against
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (match_id, team_id) DO UPDATE SET
                    opponent_team_id = EXCLUDED.opponent_team_id,
                    is_home = EXCLUDED.is_home,
                    score_for = EXCLUDED.score_for,
                    score_against = EXCLUDED.score_against
                """,
                [match_id, team_id, opponent_id, is_home, score_for, score_against],
            )


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.expanduser().resolve()
    db_path = args.db.expanduser().resolve()
    fixture_path = input_dir / "opta_fixtures.parquet"

    if not fixture_path.exists():
        raise FileNotFoundError(f"Missing fixture source: {fixture_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as con:
        initialize_schema(con)
        fixtures, mapping = load_fixtures(con, fixture_path)
        demo = filter_demo_matches(
            fixtures,
            mapping,
            args.team_source_id,
            args.allow_non_38,
        )

        con.execute("BEGIN TRANSACTION")
        try:
            import_matches(con, demo, mapping, args)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

        demo_team_id = stable_id("team", args.team_source_id)
        match_count = con.execute(
            "SELECT COUNT(*) FROM team_match WHERE team_id = ?",
            [demo_team_id],
        ).fetchone()[0]

    print("Fixture mapping used:")
    for logical, source in mapping.items():
        print(f"  {logical:16} -> {source}")
    print(f"Imported demo fixtures: {match_count}")
    print(f"Database: {db_path}")


if __name__ == "__main__":
    main()
