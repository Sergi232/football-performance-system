"""Import real demo-team lineup context into the normalized FPS database.

DATA-02 / Stage 2B.

The source schema was inspected against the real PannaData export on 2026-09-25.
This importer therefore uses only confirmed columns from ``opta_lineups.parquet``.

Confirmed source columns used:
    match_id, player_id, player_name, team_id, position, position_side,
    formation_place, shirt_number, is_starter, minutes_played,
    sub_on_minute, sub_off_minute

Important methodological rule:
- ``opta_lineups`` has no explicit team formation column in the inspected export.
  ``team_match.starting_formation`` is therefore NOT inferred from formation_place.
- Bench rows expose ``position='Substitute'`` and no side, so the importer does not
  invent a match role for them. Existing player-stats role is retained when present.
- Zero-minute bench players are now safe to add to player_match because lineups
  explicitly reports ``minutes_played = 0``.
"""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path

import duckdb
import pandas as pd


HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = Path(r"C:\Users\sergi\Desktop\analisi_futbol\input\pannadata")
DEFAULT_DB = HERE / "football_performance.duckdb"
DEFAULT_TEAM_SOURCE_ID = "4dtdjgnpdq9uw4sdutti0vaar"

REQUIRED_COLUMNS = {
    "match_id",
    "player_id",
    "player_name",
    "team_id",
    "position",
    "position_side",
    "formation_place",
    "shirt_number",
    "is_starter",
    "minutes_played",
    "sub_on_minute",
    "sub_off_minute",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import FPS demo lineups / roles")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--team-source-id", default=DEFAULT_TEAM_SOURCE_ID)
    return parser.parse_args()


def stable_id(entity: str, source_id: object) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:{entity}:{source_id}"))


def sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def sql_literal(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def safe_text(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def nullable_int(value: object) -> int | None:
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def build_source_role(position: object, side: object, started: bool) -> str | None:
    """Return only a role directly supported by the lineup source."""
    if not started:
        return None
    pos = safe_text(position)
    if not pos or pos.lower() == "substitute":
        return None
    side_text = safe_text(side)
    return f"{pos} | {side_text}" if side_text else pos


def main() -> None:
    args = parse_args()
    source_path = args.input_dir.expanduser().resolve() / "opta_lineups.parquet"
    db_path = args.db.expanduser().resolve()

    if not source_path.exists():
        raise FileNotFoundError(f"Missing source: {source_path}")
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}. Run python data/run_stage2.py --reset first."
        )

    demo_team_id = stable_id("team", args.team_source_id)

    with duckdb.connect(str(db_path)) as con:
        fixture_rows = con.execute(
            """
            SELECT m.source_match_id, m.match_id
            FROM matches m
            JOIN team_match tm ON tm.match_id = m.match_id
            WHERE tm.team_id = ?
            ORDER BY m.source_match_id
            """,
            [demo_team_id],
        ).fetchall()
        if len(fixture_rows) != 38:
            raise RuntimeError(
                f"DATA-01 is not valid: expected 38 demo fixtures, found {len(fixture_rows)}"
            )

        match_map = {str(source_id): match_id for source_id, match_id in fixture_rows}
        source_match_ids = list(match_map)

        escaped = sql_path(source_path)
        schema = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{escaped}')"
        ).fetchall()
        available = {row[0] for row in schema}
        missing = sorted(REQUIRED_COLUMNS - available)
        if missing:
            raise RuntimeError(
                "Real opta_lineups schema changed; missing required columns: "
                + ", ".join(missing)
            )

        in_list = ", ".join(sql_literal(match_id) for match_id in source_match_ids)
        team_literal = sql_literal(args.team_source_id)
        frame = con.execute(
            f"""
            SELECT
                match_id,
                player_id,
                player_name,
                team_id,
                position,
                position_side,
                formation_place,
                shirt_number,
                is_starter,
                minutes_played,
                sub_on_minute,
                sub_off_minute
            FROM read_parquet('{escaped}')
            WHERE team_id = {team_literal}
              AND match_id IN ({in_list})
            """
        ).fetchdf()

        if frame.empty:
            raise RuntimeError("No demo-team lineup rows found for the 38 validated matches")

        frame["match_id"] = frame["match_id"].astype("string")
        frame["player_id"] = frame["player_id"].astype("string")
        frame["minutes_played"] = pd.to_numeric(frame["minutes_played"], errors="coerce")

        if frame["match_id"].nunique() != 38:
            raise RuntimeError(
                f"Lineup coverage is {frame['match_id'].nunique()}/38 matches"
            )
        if frame["player_id"].isna().any() or frame["player_id"].eq("").any():
            raise RuntimeError("Lineup rows without player_id detected")
        if frame["minutes_played"].isna().any():
            raise RuntimeError("Lineup rows with missing minutes_played detected")
        if (~frame["minutes_played"].between(0, 130)).any():
            raise RuntimeError("Lineup rows with minutes outside 0..130 detected")

        duplicate_mask = frame.duplicated(subset=["match_id", "player_id"], keep=False)
        if duplicate_mask.any():
            sample = frame.loc[duplicate_mask, ["match_id", "player_id"]].head(20)
            raise RuntimeError(
                "Duplicate lineup player-match rows detected. Sample:\n"
                + sample.to_string(index=False)
            )

        starter_counts = frame.groupby("match_id")["is_starter"].sum()
        bad_starters = starter_counts[starter_counts != 11]
        if not bad_starters.empty:
            raise RuntimeError(
                "Expected 11 starters in every demo match. Bad matches:\n"
                + bad_starters.to_string()
            )

        starter_zero = frame[frame["is_starter"] & frame["minutes_played"].eq(0)]
        if not starter_zero.empty:
            raise RuntimeError(
                f"Found {len(starter_zero)} starters with 0 minutes; source consistency failed"
            )

        # DATA-01 participant rows must agree with the lineup source before enrichment.
        existing_rows = con.execute(
            """
            SELECT m.source_match_id, p.source_player_id, pm.minutes_played
            FROM player_match pm
            JOIN matches m ON m.match_id = pm.match_id
            JOIN players p ON p.player_id = pm.player_id
            WHERE pm.team_id = ? AND pm.minutes_played > 0
            """,
            [demo_team_id],
        ).fetchall()
        existing_participants = {
            (str(match_id), str(player_id)): float(minutes)
            for match_id, player_id, minutes in existing_rows
        }
        lineup_participants = {
            (str(row.match_id), str(row.player_id)): float(row.minutes_played)
            for row in frame.itertuples(index=False)
            if float(row.minutes_played) > 0
        }

        missing_from_lineup = sorted(set(existing_participants) - set(lineup_participants))
        extra_in_lineup = sorted(set(lineup_participants) - set(existing_participants))
        if missing_from_lineup or extra_in_lineup:
            raise RuntimeError(
                "DATA-01 participants do not match lineups. "
                f"missing_from_lineup={len(missing_from_lineup)} "
                f"extra_in_lineup={len(extra_in_lineup)}"
            )

        minute_mismatches = [
            (key, existing_participants[key], lineup_participants[key])
            for key in existing_participants
            if abs(existing_participants[key] - lineup_participants[key]) > 0.01
        ]
        if minute_mismatches:
            raise RuntimeError(
                "Player minutes differ between player_stats and lineups. Sample: "
                + repr(minute_mismatches[:10])
            )

        inserted_zero_minute = 0
        updated_existing = 0
        starter_roles_written = 0

        con.execute("BEGIN TRANSACTION")
        try:
            for row in frame.itertuples(index=False):
                source_match_id = str(row.match_id)
                source_player_id = str(row.player_id)
                match_id = match_map[source_match_id]
                player_id = stable_id("player", source_player_id)
                started = bool(row.is_starter)
                minutes = float(row.minutes_played)
                shirt_number = nullable_int(row.shirt_number)
                role = build_source_role(row.position, row.position_side, started)
                player_name = safe_text(row.player_name) or source_player_id

                # Do not update an already referenced parent row in DuckDB; insert only
                # when the player was absent from DATA-01 (e.g. unused bench-only player).
                player_exists = con.execute(
                    "SELECT 1 FROM players WHERE player_id = ? LIMIT 1", [player_id]
                ).fetchone()
                if not player_exists:
                    default_position = safe_text(row.position)
                    if default_position and default_position.lower() == "substitute":
                        default_position = None
                    con.execute(
                        """
                        INSERT INTO players (
                            player_id, display_name, source_name, source_player_id,
                            default_position, is_anonymized
                        ) VALUES (?, ?, ?, ?, ?, FALSE)
                        """,
                        [
                            player_id,
                            player_name,
                            player_name,
                            source_player_id,
                            default_position,
                        ],
                    )

                current = con.execute(
                    """
                    SELECT primary_role
                    FROM player_match
                    WHERE match_id = ? AND player_id = ?
                    """,
                    [match_id, player_id],
                ).fetchone()

                if current:
                    existing_role = current[0]
                    final_role = role if role is not None else existing_role
                    con.execute(
                        """
                        UPDATE player_match
                        SET started = ?,
                            minutes_played = ?,
                            primary_role = ?,
                            shirt_number = ?
                        WHERE match_id = ? AND player_id = ?
                        """,
                        [
                            started,
                            minutes,
                            final_role,
                            shirt_number,
                            match_id,
                            player_id,
                        ],
                    )
                    updated_existing += 1
                else:
                    con.execute(
                        """
                        INSERT INTO player_match (
                            match_id, team_id, player_id, started,
                            minutes_played, primary_role, shirt_number
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            match_id,
                            demo_team_id,
                            player_id,
                            started,
                            minutes,
                            role,
                            shirt_number,
                        ],
                    )
                    if minutes == 0:
                        inserted_zero_minute += 1

                if role is not None:
                    starter_roles_written += 1

            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

        db_rows = con.execute(
            "SELECT COUNT(*) FROM player_match WHERE team_id = ?",
            [demo_team_id],
        ).fetchone()[0]
        covered_matches = con.execute(
            "SELECT COUNT(DISTINCT match_id) FROM player_match WHERE team_id = ?",
            [demo_team_id],
        ).fetchone()[0]
        starters = con.execute(
            "SELECT COUNT(*) FROM player_match WHERE team_id = ? AND started = TRUE",
            [demo_team_id],
        ).fetchone()[0]
        zero_minute = con.execute(
            "SELECT COUNT(*) FROM player_match WHERE team_id = ? AND minutes_played = 0",
            [demo_team_id],
        ).fetchone()[0]
        distinct_players = con.execute(
            "SELECT COUNT(DISTINCT player_id) FROM player_match WHERE team_id = ?",
            [demo_team_id],
        ).fetchone()[0]
        formation_rows = con.execute(
            """
            SELECT COUNT(*)
            FROM team_match
            WHERE team_id = ? AND starting_formation IS NOT NULL
            """,
            [demo_team_id],
        ).fetchone()[0]

    print("DATA-02 lineup import complete")
    print(f"Source lineup rows: {len(frame)}")
    print(f"Updated existing participant rows: {updated_existing}")
    print(f"Inserted verified zero-minute bench rows: {inserted_zero_minute}")
    print(f"player_match rows after enrichment: {db_rows}")
    print(f"Covered matches: {covered_matches}/38")
    print(f"Starters: {starters} (expected 418 = 38 x 11)")
    print(f"Zero-minute bench rows: {zero_minute}")
    print(f"Distinct demo players: {distinct_players}")
    print(f"Starter source roles written: {starter_roles_written}")
    print(f"team_match starting_formation populated: {formation_rows}/38")
    print("Formation note: not inferred; inspected source has no explicit formation field.")
    print("player_role_stints note: not created; lineup source does not reliably encode role changes.")


if __name__ == "__main__":
    main()
