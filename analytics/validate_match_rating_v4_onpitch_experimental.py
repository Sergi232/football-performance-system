"""Validate PERF-18 Match Rating V4.1 experimental on-pitch context candidate.

Checks:
- full coverage of V4-eligible outfield rows;
- exact implementation of the public -0.10 goals-conceded anchor;
- no duplicates/null/out-of-range values;
- effect by match result and heavy losses;
- agreement between derived on-pitch GA and provider goalsConceded where available.

No production promotion occurs here.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
V4 = "match_rating_v0.4-experimental-outfield"
V41 = "match_rating_v0.4.1-experimental-onpitch"
CTX = "on_pitch_goal_context_v0.2"
WEIGHT = -0.10


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate PERF-18 V4.1 on-pitch experiment")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--player", default="Aleñá")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)

    with duckdb.connect(str(db), read_only=True) as con:
        df = con.execute(
            """
            SELECT
                n.*, b.match_rating_10 AS v4_rating,
                c.goals_against_on_pitch, c.goals_for_on_pitch,
                c.timing_precision, c.boundary_ambiguity_goals,
                rs.goals_conceded AS provider_goals_conceded,
                p.display_name, tm.score_for, tm.score_against,
                CASE
                  WHEN tm.score_for > tm.score_against THEN 'WIN'
                  WHEN tm.score_for < tm.score_against THEN 'LOSS'
                  ELSE 'DRAW'
                END AS result
            FROM player_match_rating n
            JOIN player_match_rating b
              ON b.match_id=n.match_id AND b.team_id=n.team_id AND b.player_id=n.player_id
             AND b.match_rating_version=?
            JOIN player_match_on_pitch_context c
              ON c.match_id=n.match_id AND c.team_id=n.team_id AND c.player_id=n.player_id
             AND c.context_version=?
            LEFT JOIN player_match_raw_stats rs
              ON rs.match_id=n.match_id AND rs.team_id=n.team_id AND rs.player_id=n.player_id
            JOIN players p ON p.player_id=n.player_id
            JOIN team_match tm ON tm.match_id=n.match_id AND tm.team_id=n.team_id
            WHERE n.match_rating_version=?
            ORDER BY n.match_date, p.display_name
            """,
            [V4, CTX, V41],
        ).df()
        expected = int(con.execute(
            "SELECT COUNT(*) FROM player_match_rating WHERE match_rating_version=?",
            [V4],
        ).fetchone()[0])

    rows = len(df)
    nulls = int(df["match_rating_10"].isna().sum())
    duplicates = int(df.duplicated(["match_id", "player_id"]).sum())
    out_of_range = int((~df["match_rating_10"].between(3.0, 10.0)).sum())

    expected_rating = (
        pd.to_numeric(df["v4_rating"], errors="coerce")
        + WEIGHT * pd.to_numeric(df["goals_against_on_pitch"], errors="coerce")
    ).clip(3.0, 10.0)
    implementation_error = (pd.to_numeric(df["match_rating_10"], errors="coerce") - expected_rating).abs()
    max_anchor_error = float(implementation_error.max()) if len(df) else float("nan")

    delta = pd.to_numeric(df["match_rating_10"], errors="coerce") - pd.to_numeric(df["v4_rating"], errors="coerce")
    wrong_direction = int((delta > 1e-12).sum())

    provider = df.loc[df["provider_goals_conceded"].notna()].copy()
    if len(provider):
        provider["provider_goals_conceded"] = pd.to_numeric(provider["provider_goals_conceded"], errors="coerce")
        provider["goals_against_on_pitch"] = pd.to_numeric(provider["goals_against_on_pitch"], errors="coerce")
        provider_mae = float((provider["provider_goals_conceded"] - provider["goals_against_on_pitch"]).abs().mean())
        provider_exact = float((provider["provider_goals_conceded"] == provider["goals_against_on_pitch"]).mean())
    else:
        provider_mae = None
        provider_exact = None

    contract = bool(
        rows == expected
        and nulls == 0
        and duplicates == 0
        and out_of_range == 0
        and max_anchor_error <= 1e-9
        and wrong_direction == 0
    )

    print("PERF-18 MATCH RATING V4.1 ON-PITCH VALIDATION")
    print(f"coverage={rows}/{expected}")
    print(f"null_ratings={nulls} duplicates={duplicates} out_of_range={out_of_range}")
    print(f"anchor_weight={WEIGHT:+.2f} max_implementation_error={max_anchor_error:.12f}")
    print(f"wrong_direction_rows={wrong_direction}")
    print("timing_precision=" + str(df["timing_precision"].value_counts().to_dict()))
    print(f"boundary_ambiguity_rows={int((df['boundary_ambiguity_goals'] > 0).sum())}")
    print(f"provider_vs_derived_ga_mae={provider_mae} exact_share={provider_exact}")
    print(
        "distribution_v41="
        + str({
            "mean": float(df["match_rating_10"].mean()),
            "median": float(df["match_rating_10"].median()),
            "q10": float(df["match_rating_10"].quantile(0.10)),
            "q90": float(df["match_rating_10"].quantile(0.90)),
            "min": float(df["match_rating_10"].min()),
            "max": float(df["match_rating_10"].max()),
            "mean_delta_vs_v4": float(delta.mean()),
        })
    )

    print("\nBY RESULT")
    print(
        df.groupby("result")["match_rating_10"]
        .agg(["count", "mean", "median"])
        .reset_index()
        .to_string(index=False)
    )

    heavy = df.loc[(df["score_against"] - df["score_for"]) >= 2].copy()
    if not heavy.empty:
        print("\nHEAVY LOSSES")
        print(
            heavy.groupby(["match_date", "match_id", "score_for", "score_against"])["match_rating_10"]
            .agg(players="count", mean="mean", median="median")
            .reset_index()
            .sort_values("match_date")
            .to_string(index=False)
        )

    needle = str(args.player).strip().lower()
    sample = df.loc[df["display_name"].astype(str).str.lower().str.contains(needle, regex=False)].copy()
    if not sample.empty:
        print(f"\nPLAYER SAMPLE: {args.player}")
        print(
            sample[[
                "match_date", "display_name", "position_group", "minutes_played",
                "score_for", "score_against", "goals_against_on_pitch",
                "v4_rating", "match_rating_10",
            ]].to_string(index=False)
        )

    print(f"\nV4_1_ON_PITCH_CONTRACT={'PASS' if contract else 'FAIL'}")
    print("Promotion status: still experimental; goalkeeper remains separate and must be validated before production switch.")
    if not contract:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
