"""DATA-03 Stage 3A importer with explicit Opta shot reconciliation.

Why this exists:
Opta defines some last-line defensive blocks as shots on target. In the inspected
PannaData export those rows can still expose ``is_blocked=True`` in
``opta_shot_events``. Therefore ``is_blocked`` alone cannot always distinguish
BLOCKED from ON_TARGET.

Method:
1. Map unambiguous shot events directly.
2. Treat type_id=15 + is_blocked=True as an ambiguous Opta block candidate.
3. Reconcile only those candidates against the independent player-match totals in
   ``opta_shots``.
4. Assign an event outcome only when the aggregate constraints make the assignment
   unique. If a player-match would require mixing ON_TARGET and BLOCKED across
   multiple indistinguishable candidates, abort rather than invent event identity.
5. Revalidate every player-match total before writing to DuckDB.

This follows Opta's published definition that last-line blocks can count as shots
on target while ordinary blocked shots remain a separate category.
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
    parser = argparse.ArgumentParser(description="Import reconciled demo shot/card events")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--team-source-id", default=DEFAULT_TEAM_SOURCE_ID)
    return parser.parse_args()


def initial_outcome(row: pd.Series) -> str | None:
    """Map only cases that are unambiguous before aggregate reconciliation."""
    own_goal = bool(row["is_own_goal"]) if not pd.isna(row["is_own_goal"]) else False
    if own_goal:
        return None

    try:
        tid = int(float(row["type_id"]))
    except (TypeError, ValueError):
        return "UNKNOWN"

    goal = bool(row["is_goal"]) if not pd.isna(row["is_goal"]) else False
    blocked = bool(row["is_blocked"]) if not pd.isna(row["is_blocked"]) else False

    if tid == 16 or goal:
        return "GOAL"
    if tid in (13, 14):
        return "OFF_TARGET"
    if tid == 15 and not blocked:
        return "ON_TARGET"
    if tid == 15 and blocked:
        return "AMBIGUOUS_BLOCK"
    return "UNKNOWN"


def source_totals_by_player_match(shot_totals: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "total_shots",
        "shots_on_target",
        "shots_off_target",
        "shots_blocked",
        "goals",
        "shots_penalty",
    ]
    totals = shot_totals[["match_id", "player_id", *columns]].copy()
    for column in columns:
        totals[column] = pd.to_numeric(totals[column], errors="coerce").fillna(0).astype(int)

    # The expected grain is player-match. Fail instead of silently summing duplicates.
    duplicates = totals.duplicated(["match_id", "player_id"], keep=False)
    if duplicates.any():
        sample = totals.loc[duplicates, ["match_id", "player_id"]].head(20)
        raise RuntimeError(
            "Duplicate player-match rows in opta_shots. Sample:\n" + sample.to_string(index=False)
        )
    return totals.set_index(["match_id", "player_id"])


def reconcile_shots(
    shot_events: pd.DataFrame, shot_totals: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int]]:
    work = shot_events.copy()
    work["normalized_outcome"] = work.apply(initial_outcome, axis=1)
    work["aggregate_reconciled"] = False
    work["last_line_on_target_reconciled"] = False

    unknown = work[
        (~work["is_own_goal"].fillna(False).astype(bool))
        & work["normalized_outcome"].eq("UNKNOWN")
    ]
    if not unknown.empty:
        sample = unknown[["match_id", "event_id", "type_id", "is_goal", "is_blocked"]].head(20)
        raise RuntimeError(
            "Unmapped non-own-goal shot rows detected. Sample:\n" + sample.to_string(index=False)
        )

    totals = source_totals_by_player_match(shot_totals)
    normal_mask = ~work["is_own_goal"].fillna(False).astype(bool)
    normal = work.loc[normal_mask].copy()

    reconciled_on_target = 0
    reconciled_blocked = 0
    reconciled_groups = 0

    for (match_id, player_id), group in normal.groupby(["match_id", "player_id"], sort=False):
        key = (match_id, player_id)
        if key not in totals.index:
            raise RuntimeError(
                f"Shot-event player-match missing from opta_shots: match={match_id} player={player_id}"
            )
        source = totals.loc[key]
        if isinstance(source, pd.DataFrame):
            raise RuntimeError(f"Non-unique opta_shots player-match: {key}")

        source_total = int(source["total_shots"])
        source_on = int(source["shots_on_target"])
        source_off = int(source["shots_off_target"])
        source_blocked = int(source["shots_blocked"])
        source_goals = int(source["goals"])

        if len(group) != source_total:
            raise RuntimeError(
                f"total_shots mismatch before reconciliation for {key}: events={len(group)} source={source_total}"
            )

        clear_goals = int(group["normalized_outcome"].eq("GOAL").sum())
        clear_off = int(group["normalized_outcome"].eq("OFF_TARGET").sum())
        clear_on = int(group["normalized_outcome"].isin(["GOAL", "ON_TARGET"]).sum())
        ambiguous_idx = group.index[group["normalized_outcome"].eq("AMBIGUOUS_BLOCK")].tolist()
        ambiguous_count = len(ambiguous_idx)

        if clear_goals != source_goals:
            raise RuntimeError(
                f"goals mismatch for {key}: clear={clear_goals} source={source_goals}"
            )
        if clear_off != source_off:
            raise RuntimeError(
                f"shots_off_target mismatch for {key}: clear={clear_off} source={source_off}"
            )

        need_on = source_on - clear_on
        need_blocked = source_blocked
        if need_on < 0 or need_blocked < 0 or need_on + need_blocked != ambiguous_count:
            raise RuntimeError(
                "Ambiguous block counts cannot reconcile for "
                f"{key}: ambiguous={ambiguous_count}, need_on={need_on}, "
                f"need_blocked={need_blocked}, source_on={source_on}, source_blocked={source_blocked}"
            )

        if ambiguous_count == 0:
            continue

        # Aggregate data can identify event outcomes only if all indistinguishable
        # ambiguous candidates in this player-match belong to the same class.
        if need_on and need_blocked:
            details = work.loc[
                ambiguous_idx,
                ["event_id", "minute", "second", "x", "y", "type_id", "is_blocked"],
            ]
            raise RuntimeError(
                "Event-level identity is underdetermined: a player-match contains multiple "
                "ambiguous blocked attempts and the aggregate requires both ON_TARGET and "
                f"BLOCKED. Refusing to guess for {key}. Candidates:\n{details.to_string(index=False)}"
            )

        reconciled_groups += 1
        work.loc[ambiguous_idx, "aggregate_reconciled"] = True
        if need_on == ambiguous_count:
            work.loc[ambiguous_idx, "normalized_outcome"] = "ON_TARGET"
            work.loc[ambiguous_idx, "last_line_on_target_reconciled"] = True
            reconciled_on_target += ambiguous_count
        elif need_blocked == ambiguous_count:
            work.loc[ambiguous_idx, "normalized_outcome"] = "BLOCKED"
            reconciled_blocked += ambiguous_count
        else:
            raise RuntimeError(f"Unexpected reconciliation state for {key}")

    # Ensure opta_shots has no positive-shot player-match absent from event source.
    event_keys = set(
        tuple(row)
        for row in normal[["match_id", "player_id"]].drop_duplicates().itertuples(index=False, name=None)
    )
    source_keys = set(totals.index.tolist())
    missing_events = [key for key in source_keys - event_keys if int(totals.loc[key, "total_shots"]) > 0]
    if missing_events:
        raise RuntimeError(f"opta_shots player-matches missing from shot_events: {missing_events[:20]}")

    final = work.loc[normal_mask].copy()
    final["total_shots"] = 1
    final["shots_on_target"] = final["normalized_outcome"].isin(["GOAL", "ON_TARGET"]).astype(int)
    final["shots_off_target"] = final["normalized_outcome"].eq("OFF_TARGET").astype(int)
    final["shots_blocked"] = final["normalized_outcome"].eq("BLOCKED").astype(int)
    final["goals"] = final["normalized_outcome"].eq("GOAL").astype(int)
    final["shots_penalty_candidate"] = final["situation"].fillna("").eq("Penalty").astype(int)

    metrics = ["total_shots", "shots_on_target", "shots_off_target", "shots_blocked", "goals"]
    derived = final.groupby(["match_id", "player_id"], as_index=True)[metrics].sum()
    compare = derived.join(totals[metrics], lsuffix="_derived", rsuffix="_source", how="outer").fillna(0)

    checks: dict[str, int] = {}
    for metric in metrics:
        mismatch = compare[f"{metric}_derived"].astype(int) != compare[f"{metric}_source"].astype(int)
        checks[metric] = int(mismatch.sum())
        if checks[metric]:
            bad = compare.loc[mismatch, [f"{metric}_derived", f"{metric}_source"]].head(20)
            raise RuntimeError(
                f"Post-reconciliation validation failed for {metric}: {checks[metric]} mismatches.\n"
                + bad.to_string()
            )

    penalty_derived = final.groupby(["match_id", "player_id"])["shots_penalty_candidate"].sum()
    penalty_compare = penalty_derived.to_frame("derived").join(
        totals[["shots_penalty"]].rename(columns={"shots_penalty": "source"}), how="outer"
    ).fillna(0)
    checks["shots_penalty"] = int(
        (penalty_compare["derived"].astype(int) != penalty_compare["source"].astype(int)).sum()
    )
    checks["normalized_shots"] = len(final)
    checks["own_goals_excluded"] = int(work["is_own_goal"].fillna(False).astype(bool).sum())
    checks["reconciled_groups"] = reconciled_groups
    checks["reconciled_on_target"] = reconciled_on_target
    checks["reconciled_blocked"] = reconciled_blocked
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

        reconciled, checks = reconcile_shots(shot_events, shot_totals)
        penalty_verified = checks["shots_penalty"] == 0

        player_source_ids = {
            str(source_id): player_id
            for source_id, player_id in con.execute(
                "SELECT source_player_id, player_id FROM players WHERE source_player_id IS NOT NULL"
            ).fetchall()
        }

        shot_records: list[tuple] = []
        for row in reconciled.itertuples(index=False):
            if bool(row.is_own_goal):
                continue
            outcome = row.normalized_outcome
            if outcome not in {"GOAL", "ON_TARGET", "OFF_TARGET", "BLOCKED"}:
                raise RuntimeError(f"Invalid reconciled outcome for event {row.event_id}: {outcome}")

            source_match_id = str(row.match_id)
            source_player_id = str(row.player_id)
            player_id = player_source_ids.get(source_player_id)
            if not player_id:
                raise RuntimeError(f"Shot event player not found in normalized players: {source_player_id}")

            source_event_id = str(int(row.event_id))
            internal_event_id = stable_id("event", f"opta_shot_events:{source_match_id}:{source_event_id}")
            raw_situation = safe_text(row.situation)
            qualifiers = {
                "source_type_id": int(float(row.type_id)),
                "body_part": safe_text(row.body_part),
                "raw_situation": raw_situation,
                "big_chance": nullable_bool(row.big_chance),
                "xg": nullable_float(row.xg),
                "xgot": nullable_float(row.xgot),
                "goalmouth_y": nullable_float(row.goalmouth_y),
                "goalmouth_z": nullable_float(row.goalmouth_z),
                "source_is_blocked": nullable_bool(row.is_blocked),
                "aggregate_reconciled": bool(row.aggregate_reconciled),
                "last_line_on_target_reconciled": bool(row.last_line_on_target_reconciled),
                "penalty_shot": bool(raw_situation == "Penalty") if penalty_verified else None,
                "penalty_qualifier_verified": penalty_verified,
            }
            qualifiers = {key: value for key, value in qualifiers.items() if value is not None}

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
            summary_events["event_type"].isin(["yellow_card", "second_yellow", "red_card"])
        ].copy()
        card_records: list[tuple] = []
        for _, row in card_source.iterrows():
            source_player_id = safe_text(row.get("player_id"))
            if not source_player_id:
                raise RuntimeError("Card row without player_id detected:\n" + row.to_string())
            player_id = player_source_ids.get(source_player_id)
            if not player_id:
                raise RuntimeError(f"Card event player not found in normalized players: {source_player_id}")

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
                qualifiers = {"source_event_type": event_type, "dismissal_reason": "DIRECT_RED"}

            source_event_id = synthetic_event_source_id(row)
            source_match_id = str(row["match_id"])
            internal_event_id = stable_id("event", f"opta_events:{source_match_id}:{source_event_id}")
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
                    json.dumps({**qualifiers, "source_event_id_kind": "synthetic_composite"}, ensure_ascii=False),
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
                  AND (source_type = 'opta_shot_events'
                       OR (source_type = 'opta_events' AND action_type = 'CARD'))
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
        shot_match_coverage = con.execute(
            "SELECT COUNT(DISTINCT match_id) FROM match_events "
            "WHERE team_id = ? AND source_type = 'opta_shot_events'",
            [demo_team_id],
        ).fetchone()[0]
        imported_cards = con.execute(
            "SELECT COUNT(*) FROM match_events "
            "WHERE team_id = ? AND source_type = 'opta_events' AND action_type = 'CARD'",
            [demo_team_id],
        ).fetchone()[0]
        outcome_rows = con.execute(
            "SELECT outcome, COUNT(*) FROM match_events "
            "WHERE team_id = ? AND action_type = 'SHOT' GROUP BY outcome ORDER BY outcome",
            [demo_team_id],
        ).fetchall()

    print("DATA-03 Stage 3A reconciled import complete")
    print(f"Raw demo shot-event rows: {len(shot_events)}")
    print(f"Own-goal rows excluded from attacking shots: {checks['own_goals_excluded']}")
    print(f"Normalized/imported SHOT rows: {imported_shots}")
    print(f"Shot coverage: {shot_match_coverage}/{EXPECTED_MATCHES}")
    print("Shot aggregate validation mismatches after reconciliation:")
    for metric in ["total_shots", "shots_on_target", "shots_off_target", "shots_blocked", "goals"]:
        print(f"  {metric}: {checks[metric]}")
    print(f"Ambiguous block groups reconciled: {checks['reconciled_groups']}")
    print(f"  reconciled as ON_TARGET: {checks['reconciled_on_target']}")
    print(f"  reconciled as BLOCKED: {checks['reconciled_blocked']}")
    print(
        "  shots_penalty qualifier: "
        + ("VERIFIED" if penalty_verified else f"NOT VERIFIED ({checks['shots_penalty']} mismatches)")
    )
    print("Normalized shot outcomes:")
    for outcome, count in outcome_rows:
        print(f"  {outcome}: {count}")
    print(f"Imported CARD rows: {imported_cards}")
    print("Goals from opta_events skipped to avoid double counting with shot_events.")
    print("Atomic pass/dribble/defensive/foul events were not invented from this summary export.")


if __name__ == "__main__":
    main()
