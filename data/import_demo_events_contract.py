"""DATA-03 Stage 3A adapter that enforces the approved source contract.

Important source finding from the real demo data:
- atomic ``opta_shot_events.is_blocked`` is useful event context;
- aggregate ``opta_shots.shots_blocked`` and ``shots_on_target`` form an Opta
  classification that cannot always be assigned back to one concrete blocked
  event without guessing.

Therefore:
- exact event-level checks: total shots, off-target, goals, penalties;
- shots_on_target is validated only as a feasible aggregate bound;
- shots_on_target + shots_blocked is validated as an exact aggregate partition;
- shots_blocked itself remains aggregate-canonical and is NOT reconstructed from
  ``is_blocked``.

The existing semantic importer is reused for persistence. Only its validation
contract is replaced here, so no event identity is fabricated.
"""

from __future__ import annotations

import pandas as pd

import import_demo_events_semantic as semantic


def validate_shot_contract(
    shot_events: pd.DataFrame, shot_totals: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, object]]:
    work = shot_events.copy()
    work["normalized_outcome"] = work.apply(semantic.normalized_outcome, axis=1)
    work["source_on_target"] = work.apply(semantic.source_on_target_state, axis=1)
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
    final["goals"] = final["normalized_outcome"].eq("GOAL").astype(int)
    final["shots_penalty"] = final["situation"].fillna("").eq("Penalty").astype(int)
    final["clear_on_target"] = final["source_on_target"].map(
        lambda value: value is True
    ).astype(int)
    final["ambiguous_on_target"] = final["source_on_target"].map(
        lambda value: value is None
    ).astype(int)

    # At Opta aggregate level, every non-off-target attacking shot belongs to the
    # on-target/blocked partition. We can validate that partition exactly without
    # deciding which ambiguous blocked event belongs to which side.
    final["on_target_or_blocked_partition"] = (
        ~final["normalized_outcome"].eq("OFF_TARGET")
    ).astype(int)

    totals = semantic.source_totals_by_player_match(shot_totals)
    checks: dict[str, object] = {}

    exact_metrics = ["total_shots", "shots_off_target", "goals", "shots_penalty"]
    derived = final.groupby(["match_id", "player_id"], as_index=True)[
        exact_metrics
    ].sum()
    compare = derived.join(
        totals[exact_metrics],
        lsuffix="_derived",
        rsuffix="_source",
        how="outer",
    ).fillna(0)

    for metric in exact_metrics:
        mismatch = (
            compare[f"{metric}_derived"].astype(int)
            != compare[f"{metric}_source"].astype(int)
        )
        checks[metric] = int(mismatch.sum())
        if checks[metric]:
            bad = compare.loc[
                mismatch, [f"{metric}_derived", f"{metric}_source"]
            ].head(20)
            raise RuntimeError(
                f"Shot contract validation failed for {metric}: "
                f"{checks[metric]} player-match mismatches.\n"
                + bad.to_string()
            )

    # Event identity for blocked type_id=15 is not always enough to know whether
    # Opta also counted it in shots_on_target. Validate only the feasible interval.
    on_target_bounds = final.groupby(["match_id", "player_id"], as_index=True)[
        ["clear_on_target", "ambiguous_on_target"]
    ].sum()
    on_target_bounds["lower"] = on_target_bounds["clear_on_target"]
    on_target_bounds["upper"] = (
        on_target_bounds["clear_on_target"]
        + on_target_bounds["ambiguous_on_target"]
    )
    on_target_compare = on_target_bounds.join(
        totals[["shots_on_target"]].rename(columns={"shots_on_target": "source"}),
        how="outer",
    ).fillna(0)
    invalid_on_target = (
        on_target_compare["source"].astype(int)
        < on_target_compare["lower"].astype(int)
    ) | (
        on_target_compare["source"].astype(int)
        > on_target_compare["upper"].astype(int)
    )
    checks["shots_on_target"] = int(invalid_on_target.sum())
    if checks["shots_on_target"]:
        bad = on_target_compare.loc[
            invalid_on_target,
            ["lower", "upper", "source", "ambiguous_on_target"],
        ].head(20)
        raise RuntimeError(
            "Shot contract validation failed for shots_on_target bounds: "
            f"{checks['shots_on_target']} player-match mismatches.\n"
            + bad.to_string()
        )

    # The exact recoverable invariant is the aggregate partition, not each side.
    partition_derived = final.groupby(["match_id", "player_id"])[
        "on_target_or_blocked_partition"
    ].sum()
    partition_source = (
        totals["shots_on_target"].astype(int) + totals["shots_blocked"].astype(int)
    ).rename("source")
    partition_compare = partition_derived.rename("derived").to_frame().join(
        partition_source, how="outer"
    ).fillna(0)
    invalid_partition = (
        partition_compare["derived"].astype(int)
        != partition_compare["source"].astype(int)
    )
    checks["on_target_plus_blocked_partition"] = int(invalid_partition.sum())
    if checks["on_target_plus_blocked_partition"]:
        bad = partition_compare.loc[invalid_partition].head(20)
        raise RuntimeError(
            "Shot contract validation failed for shots_on_target + shots_blocked "
            f"partition: {checks['on_target_plus_blocked_partition']} "
            "player-match mismatches.\n"
            + bad.to_string()
        )

    # Explicitly report that this metric is aggregate-canonical rather than
    # pretending event-level reconstruction was validated.
    checks["shots_blocked"] = "AGGREGATE_CANONICAL"
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
    semantic.validate_shot_semantics = validate_shot_contract
    semantic.main()


if __name__ == "__main__":
    main()
