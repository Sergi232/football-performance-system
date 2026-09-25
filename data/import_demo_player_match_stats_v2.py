"""DATA-04 v2: import selected raw player-match aggregates from opta_player_stats.

Rules:
- preserve source NULLs;
- keep provider aggregates separate from derived features;
- lineup minutes remain canonical for participation;
- a raw stat on a zero-minute row is preserved and audited, never used to invent
  participation;
- include every currently approved/system variable with a verified source mapping.

Current source limitations:
- key passes remain unavailable in this export (no verified source column);
- divingSave is provider-only granularity and is not a current system variable.
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

SOURCE_TYPE = "opta_player_stats"

STAT_COLUMNS: dict[str, str] = {
    "passes_total": "totalPass",
    "passes_completed": "accuratePass",
    "assists": "goalAssist",
    "long_balls_total": "totalLongBalls",
    "long_balls_completed": "accurateLongBalls",
    "crosses_total": "totalCross",
    "crosses_completed": "accurateCross",
    "dribbles_total": "totalContest",
    "dribbles_won": "wonContest",
    "turnovers": "turnover",
    "dispossessed": "dispossessed",
    "shots_total": "totalScoringAtt",
    "shots_blocked": "blockedScoringAtt",
    "goals": "goals",
    "tackles_total": "totalTackle",
    "tackles_won": "wonTackle",
    "interceptions": "interception",
    "blocked_passes": "blockedPass",
    "clearances": "totalClearance",
    "fouls_committed": "fouls",
    "fouls_received": "wasFouled",
    "yellow_cards": "yellowCard",
    "red_cards": "redCard",
    "penalties_conceded": "penaltyConceded",
    "penalties_won": "penaltyWon",
    "saves": "saves",
    "goals_conceded": "goalsConceded",
}

PAIR_CONSTRAINTS = [
    ("passes_completed", "passes_total"),
    ("long_balls_completed", "long_balls_total"),
    ("crosses_completed", "crosses_total"),
    ("dribbles_won", "dribbles_total"),
    ("shots_blocked", "shots_total"),
    ("goals", "shots_total"),
    ("tackles_won", "tackles_total"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import DATA-04 v2 raw player-match stats")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--team-source-id", default=DEFAULT_TEAM_SOURCE_ID)
    return parser.parse_args()


def nullable_count(value: object, label: str = "value") -> int | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    if number < 0:
        raise RuntimeError(f"Negative count in {label}: {number}")
    rounded = round(number)
    if abs(number - rounded) > 1e-9:
        raise RuntimeError(f"Non-integer count in {label}: {number}")
    return int(rounded)


def validate_count_frame(frame: pd.DataFrame) -> None:
    for logical in STAT_COLUMNS:
        if logical not in frame.columns:
            raise RuntimeError(f"Missing normalized source column during validation: {logical}")
        for value in frame[logical].dropna().tolist():
            nullable_count(value, logical)

    for child, parent in PAIR_CONSTRAINTS:
        child_values = pd.to_numeric(frame[child], errors="coerce").fillna(0)
        parent_values = pd.to_numeric(frame[parent], errors="coerce").fillna(0)
        invalid = child_values > parent_values
        if invalid.any():
            sample = frame.loc[
                invalid,
                ["source_match_id", "source_player_id", child, parent],
            ].head(20)
            raise RuntimeError(
                f"Invalid count relation {child} > {parent}. Sample:\n"
                + sample.to_string(index=False)
            )


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.expanduser().resolve()
    db_path = args.db.expanduser().resolve()
    source_path = input_dir / "opta_player_stats.parquet"

    if not source_path.exists():
        raise FileNotFoundError(f"Missing source: {source_path}")
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}. Run previous DATA stages first.")

    demo_team_id = stable_id("team", args.team_source_id)

    with duckdb.connect(str(db_path)) as con:
        expected_columns = set(STAT_COLUMNS)
        actual_columns = {
            row[1]
            for row in con.execute("PRAGMA table_info('player_match_raw_stats')").fetchall()
        }
        missing_db_columns = sorted(expected_columns - actual_columns)
        if missing_db_columns:
            raise RuntimeError(
                "player_match_raw_stats is missing DATA-04 v2 columns "
                f"{missing_db_columns}. Run data/init_database.py first."
            )

        normalized_rows = con.execute(
            """
            SELECT m.source_match_id, p.source_player_id,
                   pm.match_id, pm.team_id, pm.player_id, pm.minutes_played
            FROM player_match pm
            JOIN matches m ON m.match_id = pm.match_id
            JOIN players p ON p.player_id = pm.player_id
            WHERE pm.team_id = ?
            ORDER BY m.source_match_id, p.source_player_id
            """,
            [demo_team_id],
        ).fetchall()
        if len(normalized_rows) != 835:
            raise RuntimeError(
                f"Expected 835 normalized demo player_match rows, found {len(normalized_rows)}"
            )

        normalized_map = {
            (str(source_match_id), str(source_player_id)): (
                match_id,
                team_id,
                player_id,
                float(minutes_played or 0),
            )
            for source_match_id, source_player_id, match_id, team_id, player_id, minutes_played
            in normalized_rows
        }
        fixture_ids = sorted({key[0] for key in normalized_map})
        if len(fixture_ids) != EXPECTED_MATCHES:
            raise RuntimeError(f"Expected {EXPECTED_MATCHES} source fixtures, found {len(fixture_ids)}")

        required = ["match_id", "team_id", "player_id", "minsPlayed", *STAT_COLUMNS.values()]
        schema = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{sql_path(source_path)}')"
        ).fetchdf()
        available = set(schema["column_name"].astype(str))
        missing_source = [column for column in required if column not in available]
        if missing_source:
            raise RuntimeError(f"Missing required DATA-04 source columns: {missing_source}")

        select_sql = ", ".join(f'"{column}"' for column in required)
        in_list = ", ".join(sql_literal(value) for value in fixture_ids)
        team_literal = sql_literal(args.team_source_id)
        source = con.execute(
            f"""
            SELECT {select_sql}
            FROM read_parquet('{sql_path(source_path)}')
            WHERE team_id = {team_literal}
              AND match_id IN ({in_list})
            """
        ).fetchdf()

        if len(source) != 835 or source["match_id"].nunique() != EXPECTED_MATCHES:
            raise RuntimeError(
                f"Unexpected DATA-04 source coverage: rows={len(source)} "
                f"matches={source['match_id'].nunique()}/{EXPECTED_MATCHES}"
            )
        duplicate_mask = source.duplicated(["match_id", "player_id"], keep=False)
        if duplicate_mask.any():
            raise RuntimeError(
                "Duplicate source player-match rows detected:\n"
                + source.loc[duplicate_mask, ["match_id", "player_id"]].head(20).to_string(index=False)
            )

        source_keys = set(zip(source["match_id"].astype(str), source["player_id"].astype(str)))
        if source_keys != set(normalized_map):
            raise RuntimeError("DATA-04 source/player_match key mismatch")

        logical = pd.DataFrame(
            {
                "source_match_id": source["match_id"].astype(str),
                "source_player_id": source["player_id"].astype(str),
                "source_minutes": pd.to_numeric(source["minsPlayed"], errors="coerce"),
            }
        )
        for logical_name, source_name in STAT_COLUMNS.items():
            logical[logical_name] = pd.to_numeric(source[source_name], errors="coerce")
        validate_count_frame(logical)

        minute_mismatches: list[tuple[str, str, object, float]] = []
        zero_minute_audit: list[tuple[str, str, list[str]]] = []
        for row in logical.itertuples(index=False):
            key = (row.source_match_id, row.source_player_id)
            normalized_minutes = normalized_map[key][3]
            if pd.isna(row.source_minutes):
                if abs(normalized_minutes) > 1e-9:
                    minute_mismatches.append((key[0], key[1], None, normalized_minutes))
            elif abs(float(row.source_minutes) - normalized_minutes) > 0.01:
                minute_mismatches.append((key[0], key[1], row.source_minutes, normalized_minutes))

            if normalized_minutes == 0:
                positive_fields = [
                    stat_name
                    for stat_name in STAT_COLUMNS
                    if not pd.isna(getattr(row, stat_name))
                    and float(getattr(row, stat_name)) > 0
                ]
                if positive_fields:
                    zero_minute_audit.append((key[0], key[1], positive_fields))

        if minute_mismatches:
            raise RuntimeError(f"Source/player_match minute mismatches: {minute_mismatches[:20]}")

        # DATA-03 is canonical for atomic shot totals/goals.
        event_shots = con.execute(
            """
            SELECT m.source_match_id, p.source_player_id,
                   COUNT(*) AS shots_total,
                   SUM(CASE WHEN e.outcome = 'GOAL' THEN 1 ELSE 0 END) AS goals
            FROM match_events e
            JOIN matches m ON m.match_id = e.match_id
            JOIN players p ON p.player_id = e.player_id
            WHERE e.team_id = ? AND e.action_type = 'SHOT'
            GROUP BY m.source_match_id, p.source_player_id
            """,
            [demo_team_id],
        ).fetchdf()
        event_map = {
            (str(row.source_match_id), str(row.source_player_id)): (
                int(row.shots_total), int(row.goals)
            )
            for row in event_shots.itertuples(index=False)
        }
        shot_mismatches: list[tuple] = []
        for row in logical.itertuples(index=False):
            key = (row.source_match_id, row.source_player_id)
            event_total, event_goals = event_map.get(key, (0, 0))
            source_total = nullable_count(row.shots_total, "shots_total") or 0
            source_goals = nullable_count(row.goals, "goals") or 0
            if source_total != event_total or source_goals != event_goals:
                shot_mismatches.append(
                    (key[0], key[1], source_total, event_total, source_goals, event_goals)
                )
        if shot_mismatches:
            raise RuntimeError(
                "DATA-04 source shot totals/goals disagree with validated DATA-03. "
                f"Sample: {shot_mismatches[:20]}"
            )

        insert_columns = [
            "match_id", "team_id", "player_id", "source_type",
            "source_match_id", "source_player_id", "source_minutes",
            *STAT_COLUMNS.keys(),
        ]
        records: list[tuple] = []
        for row in logical.itertuples(index=False):
            key = (row.source_match_id, row.source_player_id)
            match_id, team_id, player_id, _ = normalized_map[key]
            values: list[object] = [
                match_id, team_id, player_id, SOURCE_TYPE,
                row.source_match_id, row.source_player_id,
                None if pd.isna(row.source_minutes) else float(row.source_minutes),
            ]
            values.extend(
                nullable_count(getattr(row, stat_name), stat_name)
                for stat_name in STAT_COLUMNS
            )
            records.append(tuple(values))

        placeholders = ", ".join("?" for _ in insert_columns)
        columns_sql = ", ".join(insert_columns)
        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(
                "DELETE FROM player_match_raw_stats WHERE team_id = ? AND source_type = ?",
                [demo_team_id, SOURCE_TYPE],
            )
            con.executemany(
                f"INSERT INTO player_match_raw_stats ({columns_sql}) VALUES ({placeholders})",
                records,
            )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

        imported_rows = con.execute(
            "SELECT COUNT(*) FROM player_match_raw_stats WHERE team_id = ? AND source_type = ?",
            [demo_team_id, SOURCE_TYPE],
        ).fetchone()[0]
        imported_matches = con.execute(
            "SELECT COUNT(DISTINCT match_id) FROM player_match_raw_stats WHERE team_id = ? AND source_type = ?",
            [demo_team_id, SOURCE_TYPE],
        ).fetchone()[0]
        imported_players = con.execute(
            "SELECT COUNT(DISTINCT player_id) FROM player_match_raw_stats WHERE team_id = ? AND source_type = ?",
            [demo_team_id, SOURCE_TYPE],
        ).fetchone()[0]
        tackles_won_sum, goals_conceded_sum = con.execute(
            """
            SELECT COALESCE(SUM(tackles_won), 0), COALESCE(SUM(goals_conceded), 0)
            FROM player_match_raw_stats
            WHERE team_id = ? AND source_type = ?
            """,
            [demo_team_id, SOURCE_TYPE],
        ).fetchone()

    print("DATA-04 v2 raw player-match stats import complete")
    print(f"Source/imported rows: {len(source)}/{imported_rows}")
    print(f"Coverage: {imported_matches}/{EXPECTED_MATCHES}")
    print(f"Distinct players: {imported_players}")
    print("Source/player_match minute alignment: PASS")
    print("Non-negative/integer and subset constraints: PASS")
    print("DATA-03 shots_total/goals cross-check: PASS")
    print(f"tackles_won imported sum: {tackles_won_sum}")
    print(f"goals_conceded imported sum: {goals_conceded_sum}")
    print(f"Zero-minute rows with positive raw stats preserved/audited: {len(zero_minute_audit)}")
    for item in zero_minute_audit[:10]:
        print(f"  {item[0]} / {item[1]} -> {', '.join(item[2])}")
    print("Participation remains defined by lineup minutes; raw stats never override it.")
    print("Source NULL values preserved as NULL.")
    print("Unavailable in this source: key_passes (no verified column).")


if __name__ == "__main__":
    main()
