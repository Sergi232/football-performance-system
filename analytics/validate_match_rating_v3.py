"""Validation gate for PERF-17 Match Rating V3 on-pitch context."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.build_match_rating_v3 import (  # noqa: E402
    CONTEXT_VERSION,
    V3_VERSION,
    build_rating_frame,
)

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
V2_VERSION = "match_rating_v0.2-candidate"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate Match Rating V3 on-pitch")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--player", default="Ale")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)

    with duckdb.connect(str(db), read_only=True) as con:
        v3 = con.execute(
            """
            SELECT r.*, p.display_name AS player,
                   tm.score_for, tm.score_against,
                   c.goals_for_on_pitch, c.goals_against_on_pitch, c.goal_diff_on_pitch,
                   c.start_second, c.end_second, c.timing_precision,
                   CASE
                     WHEN tm.score_for > tm.score_against THEN 'WIN'
                     WHEN tm.score_for = tm.score_against THEN 'DRAW'
                     ELSE 'LOSS'
                   END AS result
            FROM player_match_rating r
            JOIN players p ON p.player_id=r.player_id
            JOIN team_match tm ON tm.match_id=r.match_id AND tm.team_id=r.team_id
            JOIN player_match_on_pitch_context c
              ON c.match_id=r.match_id AND c.team_id=r.team_id AND c.player_id=r.player_id
             AND c.context_version=?
            WHERE r.match_rating_version=?
            ORDER BY r.match_date, r.match_id, p.display_name
            """,
            [CONTEXT_VERSION, V3_VERSION],
        ).df()
        v2 = con.execute(
            """
            SELECT match_id, player_id, match_rating_10
            FROM player_match_rating
            WHERE match_rating_version=?
            """,
            [V2_VERSION],
        ).df()

    if v3.empty:
        raise AssertionError("V3 candidate not materialized")
    if v3["match_rating_10"].isna().any():
        raise AssertionError("V3 contains null ratings")
    if len(v3) != 590:
        raise AssertionError(f"Unexpected V3 coverage: {len(v3)}")

    if ((v3["goals_for_on_pitch"] < 0) | (v3["goals_against_on_pitch"] < 0)).any():
        raise AssertionError("Negative on-pitch goal counts")
    if (v3["goals_for_on_pitch"] > v3["score_for"]).any():
        raise AssertionError("On-pitch goals-for exceeds final team goals")
    if (v3["goals_against_on_pitch"] > v3["score_against"]).any():
        raise AssertionError("On-pitch goals-against exceeds final team goals")

    overall_median = float(v3["match_rating_10"].median())
    if not (5.5 <= overall_median <= 6.8):
        raise AssertionError(f"Overall median implausible: {overall_median:.3f}")

    by_result = (
        v3.groupby("result", as_index=False)
        .agg(rows=("match_rating_10", "size"), mean_rating=("match_rating_10", "mean"), median_rating=("match_rating_10", "median"))
        .sort_values("result")
    )
    med = {r.result: float(r.median_rating) for r in by_result.itertuples(index=False)}
    if "WIN" in med and "LOSS" in med and med["WIN"] <= med["LOSS"]:
        raise AssertionError(f"WIN median must exceed LOSS median: {med}")

    match_summary = (
        v3.groupby(["match_id", "match_date", "score_for", "score_against"], as_index=False)
        .agg(players=("player_id", "size"), median_rating=("match_rating_10", "median"), mean_rating=("match_rating_10", "mean"))
    )
    match_summary["goal_diff"] = match_summary["score_for"] - match_summary["score_against"]
    heavy_losses = match_summary[match_summary["goal_diff"] <= -2].sort_values(["goal_diff", "match_date"])
    if not heavy_losses.empty and float(heavy_losses["median_rating"].max()) > 6.8:
        raise AssertionError("Heavy-loss median still too high")

    # The on-pitch refinement should matter for at least some substitutes/partial appearances.
    compare = v3.merge(v2, on=["match_id", "player_id"], how="left", suffixes=("_v3", "_v2"))
    compare["final_goal_diff"] = compare["score_for"] - compare["score_against"]
    context_diff = compare[compare["goal_diff_on_pitch"] != compare["final_goal_diff"]].copy()
    if context_diff.empty:
        raise AssertionError("No row differs between final-score and on-pitch context")
    changed = context_diff[
        (context_diff["match_rating_10_v3"] - context_diff["match_rating_10_v2"]).abs() > 1e-9
    ]
    if changed.empty:
        raise AssertionError("On-pitch context does not change any affected rating")

    # Chronology gate: first-match ratings do not change when future dates are hidden.
    first_date = pd.to_datetime(v3["match_date"]).min().date()
    full_first = build_rating_frame(db)
    full_first = full_first[pd.to_datetime(full_first["match_date"]).dt.date == first_date].copy()
    cutoff_first = build_rating_frame(db, max_match_date=first_date)
    cols = ["match_id", "player_id", "match_rating_10", "match_rating_confidence"]
    a = full_first[cols].sort_values(["match_id", "player_id"]).reset_index(drop=True)
    b = cutoff_first[cols].sort_values(["match_id", "player_id"]).reset_index(drop=True)
    if len(a) != len(b) or not a.equals(b):
        raise AssertionError("Chronology gate failed")

    player_case = v3[v3["player"].str.contains(args.player, case=False, na=False)].copy()

    print("PERF-17 MATCH RATING V3 VALIDATION")
    print(f"version={V3_VERSION}")
    print(f"coverage={len(v3)}/590")
    print(f"overall_mean={v3['match_rating_10'].mean():.3f} overall_median={overall_median:.3f}")
    print(f"rows_with_on_pitch_context_different_from_final_result={len(context_diff)}")
    print(f"ratings_changed_by_on_pitch_context={len(changed)}")
    print("\nBY RESULT")
    print(by_result.to_string(index=False))
    print("\nHEAVY LOSSES")
    print(heavy_losses[["match_date", "score_for", "score_against", "players", "median_rating", "mean_rating", "goal_diff"]].to_string(index=False))
    print("\nAFFECTED SAMPLE")
    sample = changed[[
        "match_date", "player", "score_for", "score_against",
        "goals_for_on_pitch", "goals_against_on_pitch",
        "match_rating_10_v2", "match_rating_10_v3"
    ]].head(15)
    print(sample.to_string(index=False))
    print("\nPLAYER CASE")
    if player_case.empty:
        print(f"No player contains {args.player!r}")
    else:
        print(player_case[[
            "match_date", "player", "primary_role", "position_group",
            "score_for", "score_against", "goals_for_on_pitch", "goals_against_on_pitch",
            "match_rating_10", "match_rating_confidence"
        ]].to_string(index=False))
    print("\nchronology_no_future_dependency=PASS")
    print("on_pitch_goal_context=PASS")
    print("PERF-17 MATCH RATING V3: PASS")


if __name__ == "__main__":
    main()
