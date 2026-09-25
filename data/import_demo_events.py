"""Import validated demo-team shots and cards into match_events.

DATA-03 / Stage 3A.

The real PannaData sources were inspected on 2026-09-25.

Source limitations confirmed:
- opta_events.parquet contains only substitution/card/goal summary events for the
  demo matches. It does NOT contain atomic passes, dribbles, tackles, fouls, etc.
- opta_shot_events.parquet contains atomic shot events with real event_id, x/y,
  type_id, is_goal, is_blocked and other shot context.
- opta_shots.parquet contains player-match aggregate shot totals and is used as
  an independent control before any shot events are written.

Approved shot mapping (must exactly reconcile to opta_shots):
- own goal rows are excluded from attacking SHOT events;
- type_id 16 -> SHOT / GOAL;
- type_id 15 + is_blocked=True -> SHOT / BLOCKED;
- type_id 15 + is_blocked=False -> SHOT / ON_TARGET;
- type_id 13 or 14 -> SHOT / OFF_TARGET.

Cards:
- yellow_card -> CARD / YELLOW;
- second_yellow -> CARD / RED with qualifiers retaining the second-yellow
  dismissal semantics (also_yellow=True);
- red_card -> CARD / RED when present.

Goals in opta_events are deliberately NOT imported because shot_events is the
canonical source for goals and importing both would double count them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from pathlib import Path

import duckdb
import pandas as pd


HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = Path(r"C:\Users\sergi\Desktop\analisi_futbol\input\pannadata")
DEFAULT_DB = HERE / "football_performance.duckdb"
DEFAULT_TEAM_SOURCE_ID = "4dtdjgnpdq9uw4sdutti0vaar"
EXPECTED_MATCHES = 38


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import validated demo shot/card events")
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
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def nullable_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def nullable_bool(value: object) -> bool | None:
    if value is None or pd.isna(value):
        return None
    return bool(value)


def shot_outcome(type_id: object, is_blocked: object, is_goal: object, is_own_goal: object) -> str | None:
    """Map only the source combinations validated against aggregate shot totals."""
    own_goal = bool(is_own_goal) if not pd.isna(is_own_goal) else False
    if own_goal:
        return None

    try:
        tid = int(float(type_id))
    except (TypeError, ValueError):
        return None

    goal = bool(is_goal) if not pd.isna(is_goal) else False
    blocked = bool(is_blocked) if not pd.isna(is_blocked) else False

    if tid == 16 or goal:
        return "GOAL"
    if tid == 15:
        return "BLOCKED" if blocked else "ON_TARGET"
    if tid in (13, 14):
        return "OFF_TARGET"
    return None


def match_second(minute: object, second: object) -> int | None:
    if minute is None or pd.isna(minute):
        return None
    minute_value = int(float(minute))
    second_value = 0 if second is None or pd.isna(second) else int(float(second))
    return minute_value * 60 + second_value


def synthetic_event_source_id(row: pd.Series) -> str:
    fields = [
        safe_text(row.get("match_id")) or "",
        safe_text(row.get("event_type")) or "",
        str(nullable_float(row.get("minute")) or ""),
        str(nullable_float(row.get("second")) or ""),
        safe_text(row.get("team_id")) or "",
        safe_text(row.get("player_id")) or "",
        safe_text(row.get("player_on_id")) or "",
        safe_text(row.get("player_off_id")) or "",
        safe_text(row.get("assist_player_id")) or "",
    ]
    digest = hashlib.sha256("|".join(fields).encode("utf-8")).hexdigest()[:24]
    return f"synthetic:{digest}"


def validate_shot_aggregates(shot_events: pd.DataFrame, shot_totals: pd.DataFrame) -> dict[str, int]:
    work = shot_events.copy()
    work["normalized_outcome"] = work.apply(
        lambda row: shot_outcome(
            row["type_id"], row["is_blocked"], row["is_goal"], row["is_own_goal"]
        ),
        axis=1,
    )

    unknown = work[
        (~work["is_own_goal"].fillna(False).astype(bool))
        & work["normalized_outcome"].isna()
    ]
    if not unknown.empty:
        sample = unknown[["match_id", "event_id", "type_id", "is_goal", "is_blocked"]].head(20)
        raise RuntimeError(
            "Unmapped non-own-goal shot rows detected. Sample:\n"
            + sample.to_string(index=False)
        )

    normal = work[work["normalized_outcome"].notna()].copy()
    normal["total_shots"] = 1
    normal["shots_on_target"] = normal["normalized_outcome"].isin(["GOAL", "ON_TARGET"]).astype(int)
    normal["shots_off_target"] = normal["normalized_outcome"].eq("OFF_TARGET").astype(int)
    normal["shots_blocked"] = normal["normalized_outcome"].eq("BLOCKED").astype(int)
    normal["goals"] = normal["normalized_outcome"].eq("GOAL").astype(int)
    normal["shots_penalty_candidate"] = normal["situation"].fillna("").eq("Penalty").astype(int)

    derived = (
        normal.groupby(["match_id", "player_id"], as_index=False)[
            [
                "total_shots",
                "shots_on_target",
                "shots_off_target",
                "shots_blocked",
                "goals",
                "shots_penalty_candidate",
            ]
        ]
        .sum()
    )

    totals = shot_totals[
        [
            "match_id",
            "player_id",
            "total_shots",
            "shots_on_target",
            "shots_off_target",
            "shots_blocked",
            "goals",
            "shots_penalty",
        ]
    ].copy()

    numeric_cols = [
        "total_shots",
        "shots_on_target",
        "shots_off_target",
        "shots_blocked",
        "goals",
        "shots_penalty",
    ]
    for col in numeric_cols:
        totals[col] = pd.to_numeric(totals[col], errors="coerce").fillna(0).astype(int)

    merged = derived.merge(
        totals,
        on=["match_id", "player_id"],
        how="outer",
        suffixes=("_derived", "_source"),
    ).fillna(0)

    checks: dict[str, int] = {}
    core_metrics = ["total_shots", "shots_on_target", "shots_off_target", "shots_blocked", "goals"]
    for metric in core_metrics:
        left = merged[f"{metric}_derived"].astype(int)
        right = merged[f"{metric}_source"].astype(int)
        mismatches = int((left != right).sum())
        checks[metric] = mismatches
        if mismatches:
            bad = merged.loc[
                left != right,
                [
                    "match_id",
                    "player_id",
                    f"{metric}_derived",
                    f"{metric}_source",
                ],
            ].head(20)
            raise RuntimeError(
                f"Shot mapping failed aggregate validation for {metric}: "
                f"{mismatches} player-match mismatches. Sample:\n"
                + bad.to_string(index=False)
            )

    penalty_mismatches = int(
        (
            merged["shots_penalty_candidate"].astype(int)
            != merged["shots_penalty"].astype(int)
        ).sum()
    )
    checks["shots_penalty"] = penalty_mismatches

    checks["normalized_shots"] = len(normal)
    checks["own_goals_excluded"] = int(work["is_own_goal"].fillna(False).astype(bool).sum())
    return checks


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.expanduser().resolve()
    db_path = args.db.expanduser().resolve()
    shot_events_path = input_dir / "opta_shot_events.parquet"
    shots_path = input_dir / "opta_shots.parquet"
    events_path = input_dir / "opta_events.parquet"

    for path in [shot_events_path, shots_path, events_path]:
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
        source_match_ids = list(match_map)
        in_list = ", ".join(sql_literal(value) for value in source_match_ids)
        team_literal = sql_literal(args.team_source_id)

        shot_events = con.execute(
            f"""
            SELECT *
            FROM read_parquet('{sql_path(shot_events_path)}')
            WHERE team_id = {team_literal}
              AND match_id IN ({in_list})
            """
        ).fetchdf()

        shot_totals = con.execute(
            f"""
            SELECT *
            FROM read_parquet('{sql_path(shots_path)}')
            WHERE team_id = {team_literal}
              AND match_id IN ({in_list})
            """
        ).fetchdf()

        summary_events = con.execute(
            f"""
            SELECT *
            FROM read_parquet('{sql_path(events_path)}')
            WHERE team_id = {team_literal}
              AND match_id IN ({in_list})
            """
        ).fetchdf()

        if shot_events["match_id"].nunique() != EXPECTED_MATCHES:
            raise RuntimeError(
                f"Shot-event coverage is {shot_events['match_id'].nunique()}/{EXPECTED_MATCHES}"
            )

        if shot_events["event_id"].duplicated().any():
            raise RuntimeError("Duplicate source event_id detected in demo shot events")

        checks = validate_shot_aggregates(shot_events, shot_totals)

        penalty_verified = checks["shots_penalty"] == 0

        player_source_ids = {
            str(row[0]): row[1]
            for row in con.execute(
                """
                SELECT source_player_id, player_id
                FROM players
                WHERE source_player_id IS NOT NULL
                """
            ).fetchall()
        }

        shot_records: list[tuple] = []
        for row in shot_events.itertuples(index=False):
            outcome = shot_outcome(row.type_id, row.is_blocked, row.is_goal, row.is_own_goal)
            if outcome is None:
                continue

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
                "penalty_shot": bool(raw_situation == "Penalty") if penalty_verified else None,
                "penalty_qualifier_verified": penalty_verified,
            }
            qualifiers = {k: v for k, v in qualifiers.items() if v is not None}

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
            """
            SELECT COUNT(*)
            FROM match_events
            WHERE team_id = ? AND source_type = 'opta_shot_events'
            """,
            [demo_team_id],
        ).fetchone()[0]
        shot_match_coverage = con.execute(
            """
            SELECT COUNT(DISTINCT match_id)
            FROM match_events
            WHERE team_id = ? AND source_type = 'opta_shot_events'
            """,
            [demo_team_id],
        ).fetchone()[0]
        imported_cards = con.execute(
            """
            SELECT COUNT(*)
            FROM match_events
            WHERE team_id = ? AND source_type = 'opta_events' AND action_type = 'CARD'
            """,
            [demo_team_id],
        ).fetchone()[0]
        outcome_rows = con.execute(
            """
            SELECT outcome, COUNT(*)
            FROM match_events
            WHERE team_id = ? AND action_type = 'SHOT'
            GROUP BY outcome
            ORDER BY outcome
            """,
            [demo_team_id],
        ).fetchall()

    print("DATA-03 Stage 3A import complete")
    print(f"Raw demo shot-event rows: {len(shot_events)}")
    print(f"Own-goal rows excluded from attacking shots: {checks['own_goals_excluded']}")
    print(f"Normalized/imported SHOT rows: {imported_shots}")
    print(f"Shot coverage: {shot_match_coverage}/{EXPECTED_MATCHES}")
    print("Shot aggregate validation mismatches:")
    for metric in [
        "total_shots",
        "shots_on_target",
        "shots_off_target",
        "shots_blocked",
        "goals",
    ]:
        print(f"  {metric}: {checks[metric]}")
    print(
        "  shots_penalty qualifier: "
        + ("VERIFIED" if penalty_verified else f"NOT VERIFIED ({checks['shots_penalty']} mismatches)")
    )
    print("Normalized shot outcomes:")
    for outcome, count in outcome_rows:
        print(f"  {outcome}: {count}")
    print(f"Imported CARD rows: {imported_cards}")
    print("Skipped opta_events goal rows to avoid double counting with shot_events.")
    print("Skipped substitutions from match_events; lineup context already exists in DATA-02.")
    print(
        "Atomic PASS/DRIBBLE/TACKLE/INTERCEPTION/BLOCK/CLEARANCE/FOUL/LOSS "
        "cannot be sourced from this opta_events export and were not invented."
    )


if __name__ == "__main__":
    main()
