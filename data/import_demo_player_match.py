"""Import demo-team player participation from opta_player_stats.parquet.

Stage 2A of the normalized PannaData/Opta pipeline.

Requires Stage 1 to have loaded the 38 demo fixtures into the database. The script
uses those source match ids as an allow-list, filters the source team explicitly,
and refuses to continue if required identity/minutes fields cannot be resolved.

Rows with missing minutes are not treated as played matches. They are excluded from
`player_match` and reported so that unused substitutes / lineup-only records can be
handled later from `opta_lineups.parquet` instead of inventing minutes.

Usage:
    python data/import_demo_player_match.py
    python data/import_demo_player_match.py --input-dir C:/path/to/pannadata
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
DEFAULT_TEAM_SOURCE_ID = "4dtdjgnpdq9uw4sdutti0vaar"

FIELD_CANDIDATES = {
    "match_id": [
        "match_id", "matchId", "game_id", "gameId", "fixture_id", "fixtureId",
        "opta_match_id",
    ],
    "team_id": [
        "team_id", "teamId", "contestant_id", "contestantId", "club_id", "clubId",
    ],
    "player_id": [
        "player_id", "playerId", "person_id", "personId", "athlete_id", "athleteId",
    ],
    "player_name": [
        "player_name", "playerName", "full_name", "fullName", "name",
    ],
    "minutes": [
        "minutes_played", "minutesPlayed", "mins_played", "minsPlayed", "minutes",
        "mins", "time_played", "timePlayed",
    ],
    "position": [
        "position", "position_name", "positionName", "pos", "player_position",
        "playerPosition",
    ],
    "started": [
        "started", "starter", "is_starter", "isStarter", "starting", "is_starting",
        "isStarting",
    ],
    "shirt_number": [
        "shirt_number", "shirtNumber", "jersey_number", "jerseyNumber", "number",
    ],
}

REQUIRED_FIELDS = ("match_id", "team_id", "player_id", "minutes")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import FPS demo player-match rows")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--team-source-id", default=DEFAULT_TEAM_SOURCE_ID)
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
            "Could not resolve required player-stats fields: "
            f"{missing}.\nAvailable columns:\n  - " + "\n  - ".join(columns)
        )
    return mapping


def stable_id(entity: str, source_id: object) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:{entity}:{source_id}"))


def sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def nullable_int(value: object) -> int | None:
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def nullable_float(value: object) -> float | None:
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def nullable_bool(value: object) -> bool | None:
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "si", "sí", "starter", "start"}:
        return True
    if text in {"0", "false", "no", "n", "bench", "sub", "substitute"}:
        return False
    return None


def safe_text(value: object, fallback: str | None = None) -> str | None:
    if pd.isna(value):
        return fallback
    text = str(value).strip()
    return text if text else fallback


def load_source(
    con: duckdb.DuckDBPyConnection,
    path: Path,
) -> tuple[pd.DataFrame, dict[str, str | None]]:
    escaped = sql_path(path)
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


def main() -> None:
    args = parse_args()
    source_path = args.input_dir.expanduser().resolve() / "opta_player_stats.parquet"
    db_path = args.db.expanduser().resolve()

    if not source_path.exists():
        raise FileNotFoundError(f"Missing source: {source_path}")
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}. Run python data/run_stage1.py first."
        )

    demo_team_id = stable_id("team", args.team_source_id)

    with duckdb.connect(str(db_path)) as con:
        fixture_rows = con.execute(
            """
            SELECT m.source_match_id, m.match_id
            FROM matches m
            JOIN team_match tm ON tm.match_id = m.match_id
            WHERE tm.team_id = ?
            """,
            [demo_team_id],
        ).fetchall()
        if len(fixture_rows) != 38:
            raise RuntimeError(
                f"Stage 1 is not valid: expected 38 demo fixtures, found {len(fixture_rows)}"
            )

        match_map = {str(source_id): match_id for source_id, match_id in fixture_rows}
        source_match_ids = set(match_map)

        frame, mapping = load_source(con, source_path)
        match_col = mapping["match_id"]
        team_col = mapping["team_id"]
        player_col = mapping["player_id"]
        minutes_col = mapping["minutes"]
        assert match_col and team_col and player_col and minutes_col

        filtered = frame[
            frame[match_col].astype("string").fillna("").isin(source_match_ids)
            & frame[team_col].astype("string").fillna("").eq(str(args.team_source_id))
        ].copy()

        if filtered.empty:
            raise RuntimeError(
                "No demo-team player-stat rows found after filtering by the 38 source "
                "match ids and source team id."
            )

        # Player stats can include lineup/squad rows with missing minutes. Do not
        # invent 0 minutes here: only actual participation belongs in player_match.
        numeric_minutes = pd.to_numeric(filtered[minutes_col], errors="coerce")
        missing_minutes_mask = numeric_minutes.isna()
        skipped_missing_minutes = int(missing_minutes_mask.sum())
        filtered = filtered.loc[~missing_minutes_mask].copy()
        filtered["__minutes"] = numeric_minutes.loc[filtered.index].astype(float)

        if filtered.empty:
            raise RuntimeError(
                "All demo-team player-stat rows have missing minutes. "
                "Player participation cannot be built from opta_player_stats."
            )

        invalid_minutes = ~filtered["__minutes"].between(0, 130)
        if invalid_minutes.any():
            sample = filtered.loc[
                invalid_minutes, [match_col, player_col, minutes_col]
            ].head(20)
            raise RuntimeError(
                "Player-stat rows with invalid non-null minutes detected. Sample:\n"
                + sample.to_string(index=False)
            )

        filtered["__source_match_id"] = filtered[match_col].astype("string")
        filtered["__source_player_id"] = filtered[player_col].astype("string")

        invalid_identity = (
            filtered["__source_player_id"].isna()
            | filtered["__source_player_id"].eq("")
            | filtered["__source_player_id"].eq("<NA>")
        )
        if invalid_identity.any():
            raise RuntimeError(
                f"Found {int(invalid_identity.sum())} participating rows without player id."
            )

        duplicate_mask = filtered.duplicated(
            subset=["__source_match_id", "__source_player_id"], keep=False
        )
        if duplicate_mask.any():
            sample = filtered.loc[
                duplicate_mask, ["__source_match_id", "__source_player_id"]
            ].head(20)
            raise RuntimeError(
                "Duplicate player-match source rows detected. Import aborted. Sample:\n"
                + sample.to_string(index=False)
            )

        name_col = mapping.get("player_name")
        position_col = mapping.get("position")
        started_col = mapping.get("started")
        shirt_col = mapping.get("shirt_number")

        con.execute("BEGIN TRANSACTION")
        try:
            for _, row in filtered.iterrows():
                source_match_id = str(row["__source_match_id"])
                source_player_id = str(row["__source_player_id"])
                match_id = match_map[source_match_id]
                player_id = stable_id("player", source_player_id)

                player_name = safe_text(
                    row[name_col] if name_col else None,
                    fallback=source_player_id,
                )
                position = safe_text(row[position_col] if position_col else None)
                minutes = float(row["__minutes"])

                started = nullable_bool(row[started_col]) if started_col else None
                shirt_number = nullable_int(row[shirt_col]) if shirt_col else None

                con.execute(
                    """
                    INSERT INTO players (
                        player_id, display_name, source_name, source_player_id,
                        default_position, is_anonymized
                    ) VALUES (?, ?, ?, ?, ?, FALSE)
                    ON CONFLICT (player_id) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        source_name = EXCLUDED.source_name,
                        source_player_id = EXCLUDED.source_player_id,
                        default_position = COALESCE(EXCLUDED.default_position, players.default_position)
                    """,
                    [
                        player_id, player_name, player_name, source_player_id,
                        position,
                    ],
                )

                con.execute(
                    """
                    INSERT INTO player_match (
                        match_id, team_id, player_id, started,
                        minutes_played, primary_role, shirt_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (match_id, player_id) DO UPDATE SET
                        team_id = EXCLUDED.team_id,
                        started = EXCLUDED.started,
                        minutes_played = EXCLUDED.minutes_played,
                        primary_role = COALESCE(EXCLUDED.primary_role, player_match.primary_role),
                        shirt_number = COALESCE(EXCLUDED.shirt_number, player_match.shirt_number)
                    """,
                    [
                        match_id, demo_team_id, player_id, started,
                        minutes, position, shirt_number,
                    ],
                )

            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

        row_count = con.execute(
            "SELECT COUNT(*) FROM player_match WHERE team_id = ?",
            [demo_team_id],
        ).fetchone()[0]
        covered_matches = con.execute(
            "SELECT COUNT(DISTINCT match_id) FROM player_match WHERE team_id = ?",
            [demo_team_id],
        ).fetchone()[0]
        player_count = con.execute(
            """
            SELECT COUNT(DISTINCT player_id)
            FROM player_match
            WHERE team_id = ?
            """,
            [demo_team_id],
        ).fetchone()[0]

    print("Player-stats mapping used:")
    for logical, source in mapping.items():
        print(f"  {logical:16} -> {source}")
    print(f"Skipped source rows with missing minutes: {skipped_missing_minutes}")
    print(f"Imported player_match rows: {row_count}")
    print(f"Covered matches: {covered_matches}/38")
    print(f"Distinct demo players: {player_count}")


if __name__ == "__main__":
    main()
