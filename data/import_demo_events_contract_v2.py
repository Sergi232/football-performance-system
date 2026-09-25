"""DATA-03 Stage 3A importer following the approved source contract.

Shot rules are delegated to ``validate_shot_contract``: event-level data is kept
only where identifiable and Opta aggregate metrics remain canonical where event
identity is not recoverable.

Card attribution rule:
- if opta_events identifies a normalized player, link the card to that player;
- if player attribution is absent or cannot be resolved, keep the CARD as a
  team-level event (player_id=NULL) and preserve the source attribution state in
  qualifiers. Never invent a player.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

import import_demo_events_semantic as semantic
from import_demo_events import (
    EXPECTED_MATCHES,
    DEFAULT_DB,
    DEFAULT_INPUT,
    DEFAULT_TEAM_SOURCE_ID,
    match_second,
    nullable_bool,
    nullable_float,
    safe_text,
    sql_literal,
    sql_path,
    stable_id,
    synthetic_event_source_id,
)
from import_demo_events_contract import validate_shot_contract


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import DATA-03 source-contract shots/cards")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--team-source-id", default=DEFAULT_TEAM_SOURCE_ID)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.expanduser().resolve()
    db_path = args.db.expanduser().resolve()
    shot_events_path = input_dir / "opta_shot_events.parquet"
    shots_path = input_dir / "opta_shots.parquet"
    events_path = input_dir / "opta_events.parquet"

    for path in (shot_events_path, shots_path, events_path):
        if not path.exists():
            raise FileNotFoundError(f"Missing source: {path}")
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}. Run DATA-01/DATA-02 first.")

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
        if len(fixture_rows) != EXPECTED_MATCHES:
            raise RuntimeError(f"Expected {EXPECTED_MATCHES} validated demo fixtures, found {len(fixture_rows)}")

        match_map = {str(source_id): match_id for source_id, match_id in fixture_rows}
        in_list = ", ".join(sql_literal(value) for value in match_map)
        team_literal = sql_literal(args.team_source_id)

        shot_events = con.execute(
            f"SELECT * FROM read_parquet('{sql_path(shot_events_path)}') "
            f"WHERE team_id = {team_literal} AND match_id IN ({in_list})"
        ).fetchdf()
        shot_totals = con.execute(
            f"SELECT * FROM read_parquet('{sql_path(shots_path)}') "
            f"WHERE team_id = {team_literal} AND match_id IN ({in_list})"
        ).fetchdf()
        summary_events = con.execute(
            f"SELECT * FROM read_parquet('{sql_path(events_path)}') "
            f"WHERE team_id = {team_literal} AND match_id IN ({in_list})"
        ).fetchdf()

        if shot_events["match_id"].nunique() != EXPECTED_MATCHES:
            raise RuntimeError(f"Shot-event coverage is {shot_events['match_id'].nunique()}/{EXPECTED_MATCHES}")
        if shot_events["event_id"].duplicated().any():
            raise RuntimeError("Duplicate source event_id detected in demo shot events")

        normalized, checks = validate_shot_contract(shot_events, shot_totals)

        player_source_ids = {
            str(source_id): player_id
            for source_id, player_id in con.execute(
                "SELECT source_player_id, player_id FROM players WHERE source_player_id IS NOT NULL"
            ).fetchall()
        }

        shot_records: list[tuple] = []
        for row in normalized.itertuples(index=False):
            if semantic.bool_value(row.is_own_goal):
                continue
            outcome = row.normalized_outcome
            if outcome not in {"GOAL", "ON_TARGET", "OFF_TARGET", "BLOCKED"}:
                raise RuntimeError(f"Invalid normalized shot outcome for event {row.event_id}: {outcome}")

            source_match_id = str(row.match_id)
            source_player_id = str(row.player_id)
            player_id = player_source_ids.get(source_player_id)
            if not player_id:
                raise RuntimeError(f"Shot event player not found in normalized players: {source_player_id}")

            source_event_id = str(int(row.event_id))
            raw_situation = safe_text(row.situation)
            source_on_target = (
                None if row.source_on_target is None or pd.isna(row.source_on_target)
                else bool(row.source_on_target)
            )
            qualifiers = {
                "source_type_id": semantic.type_id_int(row.type_id),
                "body_part": safe_text(row.body_part),
                "raw_situation": raw_situation,
                "big_chance": nullable_bool(row.big_chance),
                "xg": nullable_float(row.xg),
                "xgot": nullable_float(row.xgot),
                "goalmouth_y": nullable_float(row.goalmouth_y),
                "goalmouth_z": nullable_float(row.goalmouth_z),
                "source_on_target": source_on_target,
                "source_on_target_event_identity": (
                    "UNRESOLVED_BLOCKED_ATTEMPT" if source_on_target is None else "DIRECT"
                ),
                "source_is_blocked": bool(row.source_is_blocked),
                "penalty_shot": bool(raw_situation == "Penalty"),
            }
            qualifiers = {k: v for k, v in qualifiers.items() if v is not None}
            shot_records.append((
                stable_id("event", f"opta_shot_events:{source_match_id}:{source_event_id}"),
                match_map[source_match_id], demo_team_id, player_id,
                "SHOT", None, outcome, None,
                match_second(row.minute, row.second), None,
                nullable_float(row.x), nullable_float(row.y),
                json.dumps(qualifiers, ensure_ascii=False),
                None, "opta_shot_events", source_event_id, None,
            ))

        card_source = summary_events[
            summary_events["event_type"].isin(["yellow_card", "second_yellow", "red_card"])
        ].copy()

        card_records: list[tuple] = []
        unattributed_cards = 0
        unresolved_player_cards = 0
        seen_source_ids: dict[str, int] = {}

        for _, row in card_source.iterrows():
            source_player_id = safe_text(row.get("player_id"))
            source_player_name = safe_text(row.get("player_name"))
            player_id = player_source_ids.get(source_player_id) if source_player_id else None

            if not source_player_id:
                attribution = "UNAVAILABLE_IN_SOURCE"
                unattributed_cards += 1
            elif not player_id:
                attribution = "SOURCE_PLAYER_NOT_IN_NORMALIZED_PLAYERS"
                unresolved_player_cards += 1
            else:
                attribution = "DIRECT"

            event_type = str(row["event_type"])
            if event_type == "yellow_card":
                subtype = "YELLOW"
                card_qualifiers = {"source_event_type": event_type}
            elif event_type == "second_yellow":
                subtype = "RED"
                card_qualifiers = {
                    "source_event_type": event_type,
                    "dismissal_reason": "SECOND_YELLOW",
                    "also_yellow": True,
                }
            else:
                subtype = "RED"
                card_qualifiers = {
                    "source_event_type": event_type,
                    "dismissal_reason": "DIRECT_RED",
                }

            card_qualifiers.update({
                "player_attribution": attribution,
                "source_player_id": source_player_id,
                "source_player_name": source_player_name,
                "source_event_id_kind": "synthetic_composite",
            })
            card_qualifiers = {k: v for k, v in card_qualifiers.items() if v is not None}

            base_source_event_id = synthetic_event_source_id(row)
            occurrence = seen_source_ids.get(base_source_event_id, 0)
            seen_source_ids[base_source_event_id] = occurrence + 1
            source_event_id = (
                base_source_event_id if occurrence == 0
                else f"{base_source_event_id}:dup{occurrence}"
            )
            source_match_id = str(row["match_id"])
            card_records.append((
                stable_id("event", f"opta_events:{source_match_id}:{source_event_id}"),
                match_map[source_match_id], demo_team_id, player_id,
                "CARD", subtype, None, None,
                match_second(row.get("minute"), row.get("second")), None,
                None, None,
                json.dumps(card_qualifiers, ensure_ascii=False),
                None, "opta_events", source_event_id, None,
            ))

        if len({record[15] for record in shot_records}) != len(shot_records):
            raise RuntimeError("Duplicate shot source_event_id generated")
        if len({record[15] for record in card_records}) != len(card_records):
            raise RuntimeError("Duplicate card source_event_id generated")

        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(
                """
                DELETE FROM match_events
                WHERE team_id = ?
                  AND (
                    source_type = 'opta_shot_events'
                    OR (source_type = 'opta_events' AND action_type = 'CARD')
                  )
                """,
                [demo_team_id],
            )
            insert_sql = """
                INSERT INTO match_events (
                    event_id, match_id, team_id, player_id,
                    action_type, subtype, outcome,
                    period, match_second, video_second,
                    x, y, qualifiers, linked_event_id,
                    source_type, source_event_id, collector_session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            if shot_records:
                con.executemany(insert_sql, shot_records)
            if card_records:
                con.executemany(insert_sql, card_records)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

        imported_shots = con.execute(
            "SELECT COUNT(*) FROM match_events WHERE team_id = ? AND source_type = 'opta_shot_events'",
            [demo_team_id],
        ).fetchone()[0]
        shot_coverage = con.execute(
            "SELECT COUNT(DISTINCT match_id) FROM match_events WHERE team_id = ? AND source_type = 'opta_shot_events'",
            [demo_team_id],
        ).fetchone()[0]
        imported_cards = con.execute(
            "SELECT COUNT(*) FROM match_events WHERE team_id = ? AND source_type = 'opta_events' AND action_type = 'CARD'",
            [demo_team_id],
        ).fetchone()[0]
        team_level_cards = con.execute(
            "SELECT COUNT(*) FROM match_events WHERE team_id = ? AND action_type = 'CARD' AND player_id IS NULL",
            [demo_team_id],
        ).fetchone()[0]
        outcome_rows = con.execute(
            "SELECT outcome, COUNT(*) FROM match_events WHERE team_id = ? AND action_type = 'SHOT' GROUP BY outcome ORDER BY outcome",
            [demo_team_id],
        ).fetchall()

    print("DATA-03 Stage 3A source-contract import complete")
    print(f"Raw demo shot-event rows: {len(shot_events)}")
    print(f"Own-goal rows excluded from attacking shots: {checks['own_goals_excluded']}")
    print(f"Normalized/imported SHOT rows: {imported_shots}")
    print(f"Shot coverage: {shot_coverage}/{EXPECTED_MATCHES}")
    print("Source-contract shot validation:")
    print(f"  total_shots mismatches: {checks['total_shots']}")
    print(f"  shots_off_target mismatches: {checks['shots_off_target']}")
    print(f"  goals mismatches: {checks['goals']}")
    print(f"  shots_penalty mismatches: {checks['shots_penalty']}")
    print(f"  shots_on_target bound mismatches: {checks['shots_on_target']}")
    print(f"  on_target + blocked partition mismatches: {checks['on_target_plus_blocked_partition']}")
    print(f"  shots_blocked: {checks['shots_blocked']}")
    print("Normalized collector-facing shot outcomes:")
    for outcome, count in outcome_rows:
        print(f"  {outcome}: {count}")
    print(f"Imported CARD rows: {imported_cards}")
    print(f"Team-level CARD rows (no normalized player attribution): {team_level_cards}")
    print(f"  source player missing: {unattributed_cards}")
    print(f"  source player id unresolved: {unresolved_player_cards}")
    print("Goals from opta_events skipped to avoid double counting with shot_events.")
    print("Atomic pass/dribble/defensive/foul events were not invented from this summary export.")


if __name__ == "__main__":
    main()
