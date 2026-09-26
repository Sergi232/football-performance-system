"""PERF-17: concise diagnostics for the current Match Rating V1.

Read-only. Used to expose scale problems and sparse positional dimensions before V2.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
RATING_VERSION = "match_rating_v0.1-experimental"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Diagnose Match Rating V1")
    p.add_argument("--db", type=Path, default=Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)))
    p.add_argument("--player", default="Ale", help="Player-name substring for case inspection")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)

    with duckdb.connect(str(db), read_only=True) as con:
        base = con.execute(
            """
            SELECT
                r.match_id, r.match_date, r.team_id, r.player_id,
                p.display_name AS player,
                r.primary_role, r.position_group,
                r.match_rating_10, r.match_rating_confidence,
                r.attacking_threat, r.creation_progression,
                r.defensive_contribution, r.finishing, r.discipline,
                r.match_rating_context, r.match_rating_status,
                tm.score_for, tm.score_against,
                CASE
                    WHEN tm.score_for > tm.score_against THEN 'WIN'
                    WHEN tm.score_for = tm.score_against THEN 'DRAW'
                    WHEN tm.score_for < tm.score_against THEN 'LOSS'
                    ELSE 'UNKNOWN'
                END AS result
            FROM player_match_rating r
            JOIN players p ON p.player_id=r.player_id
            LEFT JOIN team_match tm ON tm.match_id=r.match_id AND tm.team_id=r.team_id
            WHERE r.match_rating_version=?
            """,
            [RATING_VERSION],
        ).df()

    print("PERF-17 MATCH RATING V1 DIAGNOSTICS")
    print(f"rating_version={RATING_VERSION}")
    print(f"rows={len(base)} matches={base['match_id'].nunique()}")
    x = pd.to_numeric(base["match_rating_10"], errors="coerce")
    print(f"overall_mean={x.mean():.3f} overall_median={x.median():.3f} min={x.min():.3f} max={x.max():.3f}")

    print("\nBY RESULT")
    grouped = (
        base.groupby("result", dropna=False)
        .agg(
            rows=("match_rating_10", "size"),
            matches=("match_id", "nunique"),
            mean_rating=("match_rating_10", "mean"),
            median_rating=("match_rating_10", "median"),
        )
        .reset_index()
    )
    print(grouped.to_string(index=False))

    print("\nHEAVIEST LOSSES")
    losses = base.loc[base["result"] == "LOSS"].copy()
    if losses.empty:
        print("none")
    else:
        match_loss = (
            losses.groupby(["match_id", "match_date", "score_for", "score_against"], dropna=False)
            .agg(players=("player_id", "nunique"), median_rating=("match_rating_10", "median"), mean_rating=("match_rating_10", "mean"))
            .reset_index()
        )
        match_loss["goal_diff"] = match_loss["score_for"] - match_loss["score_against"]
        print(match_loss.sort_values(["goal_diff", "match_date"]).head(8).to_string(index=False))

    print("\nMISSING POSITIONAL DIMENSIONS")
    for group in ["CB", "FB_WB", "DM_CM", "AM_W", "ST", "OTHER_OUTFIELD", "GK"]:
        g = base.loc[base["position_group"] == group]
        if g.empty:
            continue
        vals = {
            d: int(pd.to_numeric(g[d], errors="coerce").isna().sum())
            for d in ["attacking_threat", "creation_progression", "defensive_contribution", "finishing", "discipline"]
        }
        print(f"{group}: rows={len(g)} missing={vals}")

    print(f"\nPLAYER CASE contains='{args.player}'")
    case = base.loc[base["player"].str.contains(args.player, case=False, na=False)].copy()
    if case.empty:
        print("no matching player")
    else:
        cols = [
            "match_date", "player", "primary_role", "position_group", "score_for", "score_against",
            "match_rating_10", "match_rating_confidence", "attacking_threat", "creation_progression",
            "defensive_contribution", "finishing", "discipline", "match_rating_context", "match_rating_status",
        ]
        print(case.sort_values("match_date")[cols].to_string(index=False))

    print("\nDIAGNOSTIC COMPLETE")


if __name__ == "__main__":
    main()
