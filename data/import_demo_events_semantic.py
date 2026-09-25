"""DATA-03 Stage 3A importer with conservative Opta shot semantics.

The inspected Opta/PannaData export gives us enough information to normalize every
shot for the Football Performance System, but not enough information to decide
whether every blocked type_id=15 attempt also belongs to Opta's aggregate
``shots_on_target`` count.

The two layers are therefore kept separate:

1. Collector-facing normalized outcome (exclusive):
   GOAL / ON_TARGET / OFF_TARGET / BLOCKED
2. Source properties:
   - source_is_blocked: observed directly at event level
   - source_on_target: True/False only when event identity is directly supported;
     None for blocked type_id=15 attempts whose on-target membership is ambiguous

Aggregate ``opta_shots`` totals are used as validation, not to invent which one of
multiple ambiguous blocked events was on target. For shots_on_target we validate
that the source total lies inside the exact lower/upper bounds implied by the
unambiguous and ambiguous events of each player-match.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import demo shot/card events with conservative Opta semantics"
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--team-source-id", default=DEFAULT_TEAM_SOURCE_ID)
    return parser.parse_args()


def bool_value(value: object) -> bool:
    return False if value is None or pd.isna(value) else bool(value)


def type_id_int(value: object) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return -1


def normalized_outcome(row: pd.Series) -> str | None:
    """Return one exclusive collector-facing outcome."""
    if bool_value(row["is_own_goal"]):
        return None

    tid = type_id_int(row["type_id"])
    is_goal = bool_value(row["is_goal"])
    is_blocked = bool_value(row["is_blocked"])

    if tid == 16 or is_goal:
        return "GOAL"
    if tid in (13, 14):
        return "OFF_TARGET"
    if tid == 15 and is_blocked:
        return "BLOCKED"
    if tid == 15:
        return "ON_TARGET"
    return "UNKNOWN"


def source_on_target_state(row: pd.Series) -> bool | None:
    """Return event-level Opta on-target state only when directly identifiable.

    Blocked type_id=15 attempts are deliberately left as None: the inspected
    source proves that some can contribute to aggregate shots_on_target, but it
    does not identify which event when multiple candidates exist.
    """
    if bool_value(row["is_own_goal"]):
        return False

    tid = type_id_int(row["type_id"])
    is_goal = bool_value(row["is_goal"])
    is_blocked = bool_value(row["is_blocked"])

    if tid == 16 or is_goal:
        return True
    if tid in (13, 14):
        return False
    if tid == 15 and is_blocked:
        return None
    if tid == 15:
        return True
    return None


def source_totals_by_player_match(shot_totals: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "total_shots",
        "shots_on_target",
        "shots_off_target",
        "shots_blocked",
        "goals",
        "shots_penalty",
    ]
    totals = shot_totals[["match_id", "player_id", *metrics]].copy()
    for metric in metrics:
        totals[metric] = pd.to_numeric(totals[metric], errors="coerce").fillna(0).astype(int)

    duplicates = totals.duplicated(["match_id", "player_id"], keep=False)
    if duplicates.any():
        sample = totals.loc[duplicates, ["match_id", "player_id"]].head(20)
        raise RuntimeError(
            "Duplicate player-match rows in opta_shots. Sample:\n"
            + sample.to_string(index=False)
        )

    return totals.set_index(["match_id", "player_id"])


def validate_shot_semantics(
    shot_events: pd.DataFrame, shot_totals: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int]]:
    work = shot_events.copy()
    work["normalized_outcome"] = work.apply(normalized_outcome, axis=1)
    work["source_on_target"] = work.apply(source_on_target_state, axis=1)
    work["source_is_blocked"] = work["is_blocked"].fillna(False).astype(bool)

    unknown = work[
        (~work["is_own_goal"].fillna(False).astype(bool))
        & work["normalized_outcome"].eq("UNKNOWN")
    ]
    if not unknown.empty:
        sample = unknown[
            ["match_id", "event_id", "type_id", "is_goal", "is_blocked"]
        ].head(20)
        raise RuntimeError(
            "Unmapped non-own-goal shot rows detected. Sample:\n"
            + sample.to_string(index=False)
        )

    final = work[~work["is_own_goal"].fillna(False).astype(bool)].copy()
    final["total_shots"] = 1
    final["shots_off_target"] = final["normalized_outcome"].eq("OFF_TARGET").astype(int)
    final["shots_blocked"] = final["source_is_blocked"].astype(int)
    final["goals"] = final["normalized_outcome"].eq("GOAL").astype(int)
    final["shots_penalty"] = final["situation"].fillna("").eq("Penalty").astype(int)
    final["clear_on_target"] = final["source_on_target"].map(lambda value: value is True).astype(int)
    final["ambiguous_on_target"] = final["source_on_target"].map(lambda value: value is None).astype(int)

    totals = source_totals_by_player_match(shot_totals)

    # Exact metrics: these are directly observable from the atomic shot source.
    exact_metrics = [
        "total_shots",
        "shots_off_target",
        "shots_blocked",
        "goals",
        "shots_penalty",
    ]
    derived = final.groupby(["match_id", "player_id"], as_index=True)[exact_metrics].sum()
    compare = derived.join(
        totals[exact_metrics],
        lsuffix="_derived",
        rsuffix="_source",
        how="outer",
    ).fillna(0)

    checks: dict[str, int] = {}
    for metric in exact_metrics:
        mismatch = (
            compare[f"{metric}_derived"].astype(int)
            != compare[f"{metric}_source"].astype(int)
        )
        checks[metric] = int(mismatch.sum())
        if checks[metric]:
            bad = compare.loc[
                mismatch,
                [f"{metric}_derived", f"{metric}_source"],
            ].head(20)
            raise RuntimeError(
                f"Shot semantic validation failed for {metric}: "
                f"{checks[metric]} player-match mismatches.\n"
                + bad.to_string()
            )

    # shots_on_target is not fully identifiable event-by-event for blocked type 15.
    # Validate the aggregate total against the exact feasible interval instead.
    on_target_bounds = final.groupby(["match_id", "player_id"], as_index=True)[
        ["clear_on_target", "ambiguous_on_target"]
    ].sum()
    on_target_bounds["lower"] = on_target_bounds["clear_on_target"]
    on_target_bounds["upper"] = (
        on_target_bounds["clear_on_target"] + on_target_bounds["ambiguous_on_target"]
    )
    on_target_compare = on_target_bounds.join(
        totals[["shots_on_target"]].rename(columns={"shots_on_target": "source"}),
        how="outer",
    ).fillna(0)
    invalid_on_target = (
        (on_target_compare["source"].astype(int) < on_target_compare["lower"].astype(int))
        | (on_target_compare["source"].astype(int) > on_target_compare["upper"].astype(int))
    )
    checks["shots_on_target"] = int(invalid_on_target.sum())
    if checks["shots_on_target"]:
        bad = on_target_compare.loc[
            invalid_on_target,
            ["lower", "upper", "source", "ambiguous_on_target"],
        ].head(20)
        raise RuntimeError(
            "Shot semantic validation failed for shots_on_target bounds: "
            f"{checks['shots_on_target']} player-match mismatches.\n"
            + bad.to_string()
        )

    checks["normalized_shots"] = len(final)
    checks["own_goals_excluded"] = int(
        work["is_own_goal"].fillna(False).astype(bool).sum()
    )
    checks["ambiguous_on_target_events"] = int(final["ambiguous_on_target"].sum())
    checks["ambiguous_on_target_player_matches"] = int(
        (on_target_bounds["ambiguous_on_target"] > 0).sum()
    )
    checks["source_on_target_requires_ambiguous_block"] = int(
        (
            on_target_compare["source"].astype(int)
            > on_target_compare["lower"].astype(int)
        ).sum()
    )
    return work, checks


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
        raise FileNotFoundError(
            f"Database not found: {db_path}. Run DATA-01/DATA-02 first."
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
        if len(fixture_rows) != EXPECTED_MATCHES:
            raise RuntimeError(
                f"Expected {EXPECTED_MATCHES} validated demo fixtures, found {len(fixture_rows)}"
            )

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
            raise RuntimeError(
                f"Shot-event coverage is {shot_events['match_id'].nunique()}/{EXPECTED_MATCHES}"
            )
        if shot_events["event_id"].duplicated().any():
            raise RuntimeError("Duplicate source event_id detected in demo shot events")

        normalized, checks = validate_shot_semantics(shot_events, shot_totals)

        player_source_ids = {
            str(source_id): player_id
            for source_id, player_id in con.execute(
                "SELECT source_player_id, player_id FROM players "
                "WHERE source_player_id IS NOT NULL"
            ).fetchall()
        }

        shot_records: list[tuple] = []
        for row in normalized.itertuples(index=False):
            if bool_value(row.is_own_goal):
                continue
            outcome = row.normalized_outcome
            if outcome not in {"GOAL", "ON_TARGET", "OFF_TARGET", "BLOCKED"}:
                raise RuntimeError(
                    f"Invalid normalized outcome for event {row.event_id}: {outcome}"
                )

            source_match_id = str(row.match_id)
            source_player_id = str(row.player_id)
            player_id = player_source_ids.get(source_player_id)
            if not player_id:
                raise RuntimeError(
                    f"Shot event player not found in normalized players: {source_player_id}"
                )

            source_event_id = str(int(row.event_id))
            internal_event_id = stable_id(
                "event", f"opta_shot_events:{source_match_id}:{source_event_id}"
            )
            raw_situation = safe_text(row.situation)
            source_on_target = (
                None if row.source_on_target is None or pd.isna(row.source_on_target)
                else bool(row.source_on_target)
            )
            qualifiers = {
                "source_type_id": type_id_int(row.type_id),
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
            qualifiers = {
                key: value for key, value in qualifiers.items() if value is not None
            }

            shot_records.append(
                (
                    internal_event_id,
                    match_map[source_match_id],
                    demo_team_id,
                    player_id,
                    "SHOT",
                    None,
                    outcome,
                    None,
                    match_second(row.minute, row.second),
                    None,
                    nullable_float(row.x),
                    nullable_float(row.y),
                    json.dumps(qualifiers, ensure_ascii=False),
                    None,
                    "opta_shot_events",
                    source_event_id,
                    None,
                )
            )

        card_source = summary_events[
            summary_events["event_type"].isin(
                ["yellow_card", "second_yellow", "red_card"]
            )
        ].copy()
        card_records: list[tuple] = []
        for _, row in card_source.iterrows():
            source_player_id = safe_text(row.get("player_id"))
            if not source_player_id:
                raise RuntimeError(
                    "Card row without player_id detected:\n" + row.to_string()
                )
            player_id = player_source_ids.get(source_player_id)
            if not player_id:
                raise RuntimeError(
                    f"Card event player not found in normalized players: {source_player_id}"
                )

            event_type = str(row["event_type"])
            if event_type == "yellow_card":
                subtype = "YELLOW"
                qualifiers = {"source_event_type": event_type}
            elif event_type == "second_yellow":
                subtype = "RED"
                qualifiers = {
                    "source_event_type": event_type,
                    "dismissal_reason": "SECOND_YELLOW",
                    "also_yellow": True,
                }
            else:
                subtype = "RED"
                qualifiers = {
                    "source_event_type": event_type,
                    "dismissal_reason": "DIRECT_RED",
                }

            source_event_id = synthetic_event_source_id(row)
            source_match_id = str(row["match_id"])
            internal_event_id = stable_id(
                "event", f"opta_events:{source_match_id}:{source_event_id}"
            )
            card_records.append(
                (
                    internal_event_id,
                    match_map[source_match_id],
                    demo_team_id,
                    player_id,
                    "CARD",
                    subtype,
                    None,
                    None,
                    match_second(row.get("minute"), row.get("second")),
                    None,
                    None,
                    None,
                    json.dumps(
                        {
                            **qualifiers,
                            "source_event_id_kind": "synthetic_composite",
                        },
                        ensure_ascii=False,
                    ),
                    None,
                    "opta_events",
                    source_event_id,
                    None,
                )
            )

        if len({record[15] for record in shot_records}) != len(shot_records):
            raise RuntimeError("Duplicate shot source_event_id generated")
        if len({record[15] for record in card_records}) != len(card_records):
            raise RuntimeError("Duplicate synthetic card source_event_id generated")

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
            "SELECT COUNT(*) FROM match_events "
            "WHERE team_id = ? AND source_type = 'opta_shot_events'",
            [demo_team_id],
        ).fetchone()[0]
        shot_match_coverage = con.execute(
            "SELECT COUNT(DISTINCT match_id) FROM match_events "
            "WHERE team_id = ? AND source_type = 'opta_shot_events'",
            [demo_team_id],
        ).fetchone()[0]
        imported_cards = con.execute(
            "SELECT COUNT(*) FROM match_events "
            "WHERE team_id = ? AND source_type = 'opta_events' "
            "AND action_type = 'CARD'",
            [demo_team_id],
        ).fetchone()[0]
        outcome_rows = con.execute(
            "SELECT outcome, COUNT(*) FROM match_events "
            "WHERE team_id = ? AND action_type = 'SHOT' "
            "GROUP BY outcome ORDER BY outcome",
            [demo_team_id],
        ).fetchall()

    print("DATA-03 Stage 3A conservative semantic import complete")
    print(f"Raw demo shot-event rows: {len(shot_events)}")
    print(
        f"Own-goal rows excluded from attacking shots: {checks['own_goals_excluded']}"
    )
    print(f"Normalized/imported SHOT rows: {imported_shots}")
    print(f"Shot coverage: {shot_match_coverage}/{EXPECTED_MATCHES}")
    print("Source-metric validation mismatches:")
    for metric in [
        "total_shots",
        "shots_on_target",
        "shots_off_target",
        "shots_blocked",
        "goals",
        "shots_penalty",
    ]:
        print(f"  {metric}: {checks[metric]}")
    print(
        "Blocked attempts with unresolved event-level on-target identity: "
        f"{checks['ambiguous_on_target_events']} events across "
        f"{checks['ambiguous_on_target_player_matches']} player-matches"
    )
    print(
        "Player-matches where Opta aggregate on-target requires at least one "
        "ambiguous blocked attempt: "
        f"{checks['source_on_target_requires_ambiguous_block']}"
    )
    print("Normalized collector-facing shot outcomes:")
    for outcome, count in outcome_rows:
        print(f"  {outcome}: {count}")
    print(f"Imported CARD rows: {imported_cards}")
    print("Goals from opta_events skipped to avoid double counting with shot_events.")
    print(
        "Atomic pass/dribble/defensive/foul events were not invented from this summary export."
    )


if __name__ == "__main__":
    main()
