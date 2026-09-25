"""Import selected raw player-match aggregates from opta_player_stats.

DATA-04 rules:
- preserve source NULLs; do not silently convert missing values to zero;
- only persist fields that map to the approved/candidate amateur Collector or
  are required as source controls for already-normalized shots;
- keep provider aggregates separate from derived features;
- do not import semantically unclear/source-only fields merely because they exist.

Explicitly excluded for now:
- key passes: no verified source column in the inspected export;
- wonTackle: Collector MVP does not distinguish tackle outcome yet;
- divingSave: unnecessary granularity for the approved GK MVP;
- goalsConceded: inspected source is populated across many non-GK player-match
  rows, so it is not accepted as a goalkeeper metric without further evidence.
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
}

PAIR_CONSTRAINTS = [
    ("passes_completed", "passes_total"),
    ("long_balls_completed", "long_balls_total"),
    ("crosses_completed", "crosses_total"),
    ("dribbles_won", "dribbles_total"),
    ("shots_blocked", "shots_total"),
    ("goals", "shots_total"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import DATA-04 raw player-match stats")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--team-source-id", default=DEFAULT_TEAM_SOURCE_ID)
    return parser.parse_args()


def nullable_count(value: object, label: str = "value") -> int | None:
    """Return an integer count while preserving source NULL as None."""
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
    """Validate non-negative integral source counts and logical subset pairs."""
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
            sample = frame.loc[invalid, ["source_match_id", "source_player_id", child, parent]].head(20)
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
        table_exists = con.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'main' AND table_name = 'player_match_raw_stats'
            """
        ).fetchone()[0]
        if not table_exists:
            raise RuntimeError(
                "player_match_raw_stats table missing. Run data/init_database.py with the updated schema first."
            )

        normalized_rows = con.execute(
            """
            SELECT
                m.source_match_id,
                p.source_player_id,
                pm.match_id,
                pm.team_id,
                pm.player_id,
                pm.minutes_played
            FROM player_match pm
            JOIN matches m ON m.match_id = pm.match_id
            JOIN players p ON p.player_id = pm.player_id
            WHERE pm.team_id = ?
            ORDER BY m.source_match_id, p.source_player_id
            """,
            [demo_team_id],
        ).fetchall()

        if len(normalized_rows) != 835:
            raise RuntimeError(f"Expected 835 normalized demo player_match rows, found {len(normalized_rows)}")

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

        in_list = ", ".join(sql_literal(value) for value in fixture_ids)
        team_literal = sql_literal(args.team_source_id)

        required_source_columns = [
            "match_id",
            "team_id",
            "player_id",
            "minsPlayed",
            *STAT_COLUMNS.values(),
        ]
        schema = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{sql_path(source_path)}')"
        ).fetchdf()
        available = set(schema["column_name"].astype(str))
        missing = [column for column in required_source_columns if column not in available]
        if missing:
            raise RuntimeError(f"Missing required DATA-04 source columns: {missing}")

        source_select = ", ".join(f'"{column}"' for column in required_source_columns)
        source = con.execute(
            f"""
            SELECT {source_select}
            FROM read_parquet('{sql_path(source_path)}')
            WHERE team_id = {team_literal}
              AND match_id IN ({in_list})
            """
        ).fetchdf()

        if len(source) != 835:
            raise RuntimeError(f"Expected 835 source player-stat rows, found {len(source)}")
        if source["match_id"].nunique() != EXPECTED_MATCHES:
            raise RuntimeError(
                f"DATA-04 source match coverage is {source['match_id'].nunique()}/{EXPECTED_MATCHES}"
            )
        duplicate_mask = source.duplicated(["match_id", "player_id"], keep=False)
        if duplicate_mask.any():
            sample = source.loc[duplicate_mask, ["match_id", "player_id"]].head(20)
            raise RuntimeError("Duplicate source player-match rows detected:\n" + sample.to_string(index=False))

        source_keys = set(zip(source["match_id"].astype(str), source["player_id"].astype(str)))
        normalized_keys = set(normalized_map)
        if source_keys != normalized_keys:
            missing_normalized = sorted(source_keys - normalized_keys)[:20]
            missing_source = sorted(normalized_keys - source_keys)[:20]
            raise RuntimeError(
                "DATA-04 source/player_match key mismatch. "
                f"not_in_normalized={missing_normalized} not_in_source={missing_source}"
            )

        # Build logical normalized-source columns while preserving source NULLs.
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

        # Minutes are already canonical from lineups. Here they are only a source audit.
        minute_mismatches: list[tuple[str, str, object, float]] = []
        zero_minute_positive_stats: list[tuple[str, str]] = []
        for row in logical.itertuples(index=False):
            key = (row.source_match_id, row.source_player_id)
            _, _, _, normalized_minutes = normalized_map[key]
            if pd.isna(row.source_minutes):
                if abs(normalized_minutes) > 1e-9:
                    minute_mismatches.append((key[0], key[1], None, normalized_minutes))
            elif abs(float(row.source_minutes) - normalized_minutes) > 0.01:
                minute_mismatches.append((key[0], key[1], row.source_minutes, normalized_minutes))

            if normalized_minutes == 0:
                positive = False
                for stat_name in STAT_COLUMNS:
                    value = getattr(row, stat_name)
                    if not pd.isna(value) and float(value) > 0:
                        positive = True
                        break
                if positive:
                    zero_minute_positive_stats.append(key)

        if minute_mismatches:
            raise RuntimeError(f"Source/player_match minute mismatches: {minute_mismatches[:20]}")
        if zero_minute_positive_stats:
            raise RuntimeError(
                "Zero-minute rows contain positive selected stats: "
                f"{zero_minute_positive_stats[:20]}"
            )

        # DATA-03 provides atomic shot truth where identifiable. Validate totals/goals
        # at player-match level without trying to reclassify blocked/on-target identity.
        event_shots = con.execute(
            """
            SELECT
                m.source_match_id,
                p.source_player_id,
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
            (str(row.source_match_id), str(row.source_player_id)): (int(row.shots_total), int(row.goals))
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

        records: list[tuple] = []
        insert_columns = [
            "match_id",
            "team_id",
            "player_id",
            "source_type",
            "source_match_id",
            "source_player_id",
            "source_minutes",
            *STAT_COLUMNS.keys(),
        ]

        for row in logical.itertuples(index=False):
            key = (row.source_match_id, row.source_player_id)
            match_id, team_id, player_id, _ = normalized_map[key]
            values = [
                match_id,
                team_id,
                player_id,
                SOURCE_TYPE,
                row.source_match_id,
                row.source_player_id,
                None if pd.isna(row.source_minutes) else float(row.source_minutes),
            ]
            for stat_name in STAT_COLUMNS:
                values.append(nullable_count(getattr(row, stat_name), stat_name))
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
        zero_minute_rows = con.execute(
            """
            SELECT COUNT(*)
            FROM player_match_raw_stats s
            JOIN player_match pm ON pm.match_id = s.match_id AND pm.player_id = s.player_id
            WHERE s.team_id = ? AND s.source_type = ? AND pm.minutes_played = 0
            """,
            [demo_team_id, SOURCE_TYPE],
        ).fetchone()[0]

    print("DATA-04 raw player-match stats import complete")
    print(f"Source rows: {len(source)}")
    print(f"Imported raw rows: {imported_rows}")
    print(f"Coverage: {imported_matches}/{EXPECTED_MATCHES}")
    print(f"Distinct players: {imported_players}")
    print(f"Zero-minute bench rows preserved: {zero_minute_rows}")
    print("Source/player_match minute alignment: PASS")
    print("Non-negative integral count constraints: PASS")
    print("Completed/won <= total constraints: PASS")
    print("Zero-minute rows with positive selected stats: 0")
    print("DATA-03 player-match shots_total/goals cross-check: PASS")
    print("Source NULL values preserved as NULL in player_match_raw_stats")
    print("Not imported: key_passes (missing source column)")
    print("Not imported: wonTackle, divingSave (outside current Collector MVP)")
    print("Not imported: goalsConceded (semantics not accepted as GK metric yet)")


if __name__ == "__main__":
    main()
