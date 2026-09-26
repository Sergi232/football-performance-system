"""PERF-17 validation gate for leakage-safe Match Rating V2 candidate."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.build_match_rating_v2 import V2_VERSION, build_rating_frame  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate Match Rating V2 candidate")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--player", default="Ale")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(db_path)

    with duckdb.connect(str(db_path), read_only=True) as con:
        v2 = con.execute(
            """
            SELECT r.*, p.display_name AS player,
                   tm.score_for, tm.score_against,
                   CASE
                     WHEN tm.score_for > tm.score_against THEN 'WIN'
                     WHEN tm.score_for = tm.score_against THEN 'DRAW'
                     ELSE 'LOSS'
                   END AS result
            FROM player_match_rating r
            JOIN players p ON p.player_id=r.player_id
            JOIN team_match tm ON tm.match_id=r.match_id AND tm.team_id=r.team_id
            WHERE r.match_rating_version=?
            ORDER BY r.match_date, r.match_id, p.display_name
            """,
            [V2_VERSION],
        ).df()

    if v2.empty:
        raise AssertionError("V2 candidate not materialized")

    played_rows = len(v2)
    rated_rows = int(v2["match_rating_10"].notna().sum())
    if rated_rows != played_rows:
        raise AssertionError(f"Coverage failure: {rated_rows}/{played_rows}")

    overall_mean = float(v2["match_rating_10"].mean())
    overall_median = float(v2["match_rating_10"].median())
    if not (5.5 <= overall_median <= 6.8):
        raise AssertionError(f"Overall median implausible: {overall_median:.3f}")

    by_result = (
        v2.groupby("result", as_index=False)
        .agg(rows=("match_rating_10", "size"), mean_rating=("match_rating_10", "mean"), median_rating=("match_rating_10", "median"))
        .sort_values("result")
    )
    med = {r.result: float(r.median_rating) for r in by_result.itertuples(index=False)}
    if "WIN" in med and "LOSS" in med and med["WIN"] <= med["LOSS"]:
        raise AssertionError(f"WIN median must exceed LOSS median: {med}")

    match_summary = (
        v2.groupby(["match_id", "match_date", "score_for", "score_against"], as_index=False)
        .agg(players=("player_id", "size"), median_rating=("match_rating_10", "median"), mean_rating=("match_rating_10", "mean"))
    )
    match_summary["goal_diff"] = match_summary["score_for"] - match_summary["score_against"]
    heavy_losses = match_summary[match_summary["goal_diff"] <= -2].sort_values(["goal_diff", "match_date"])
    if not heavy_losses.empty and float(heavy_losses["median_rating"].max()) > 6.8:
        raise AssertionError(
            "Heavy-loss median still too high: "
            + heavy_losses[["match_date", "score_for", "score_against", "median_rating"]].to_string(index=False)
        )

    # Leakage gate: ratings for the first match must be exactly identical when the
    # builder is allowed to see only data up to that first match.
    first_date = pd.to_datetime(v2["match_date"]).min().date()
    full_first = build_rating_frame(db_path)
    full_first = full_first[pd.to_datetime(full_first["match_date"]).dt.date == first_date].copy()
    cutoff_first = build_rating_frame(db_path, max_match_date=first_date)
    cols = ["match_id", "player_id", "match_rating_10", "match_rating_confidence"]
    a = full_first[cols].sort_values(["match_id", "player_id"]).reset_index(drop=True)
    b = cutoff_first[cols].sort_values(["match_id", "player_id"]).reset_index(drop=True)
    if len(a) != len(b) or not a.equals(b):
        raise AssertionError("Chronology gate failed: first-match V2 changes when future matches are hidden")

    player_case = v2[v2["player"].str.contains(args.player, case=False, na=False)].copy()

    print("PERF-17 MATCH RATING V2 VALIDATION")
    print(f"version={V2_VERSION}")
    print(f"coverage={rated_rows}/{played_rows}")
    print(f"overall_mean={overall_mean:.3f} overall_median={overall_median:.3f}")
    print("\nBY RESULT")
    print(by_result.to_string(index=False))
    print("\nHEAVY LOSSES")
    if heavy_losses.empty:
        print("none")
    else:
        print(heavy_losses[["match_date", "score_for", "score_against", "players", "median_rating", "mean_rating", "goal_diff"]].to_string(index=False))
    print("\nPLAYER CASE")
    if player_case.empty:
        print(f"No player contains {args.player!r}")
    else:
        show = [
            "match_date", "player", "primary_role", "position_group", "score_for", "score_against",
            "match_rating_10", "match_rating_confidence", "attacking_threat", "creation_progression",
            "defensive_contribution", "finishing", "discipline", "match_rating_status",
        ]
        print(player_case[show].to_string(index=False))
    print("\nchronology_no_future_dependency=PASS")
    print("PERF-17 MATCH RATING V2: PASS")


if __name__ == "__main__":
    main()
