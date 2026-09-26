"""Validate the separate PERF-18 goalkeeper Match Rating candidate.

Checks coverage, chronology, component orientation, local distribution, relationship
with V2, and goalkeeper-specific sanity diagnostics. It does not promote the model.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
DEFAULT_METADATA = ROOT / "dsai" / "output" / "perf18_gk_local" / "goalkeeper_candidate_metadata.json"
V2_VERSION = "match_rating_v0.2-candidate"
GK_VERSION = "match_rating_v0.4.2-experimental-gk"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate PERF-18 goalkeeper Match Rating candidate")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    p.add_argument("--player", default="Sivera")
    return p.parse_args()


def spearman(a: pd.Series, b: pd.Series) -> float | None:
    aa = pd.to_numeric(a, errors="coerce")
    bb = pd.to_numeric(b, errors="coerce")
    valid = aa.notna() & bb.notna()
    if int(valid.sum()) < 3:
        return None
    return float(aa[valid].rank(method="average").corr(bb[valid].rank(method="average")))


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    metadata_path = args.metadata.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)
    if not metadata_path.exists():
        raise FileNotFoundError(metadata_path)
    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    model = meta["model"]

    with duckdb.connect(str(db), read_only=True) as con:
        gk = con.execute(
            """
            SELECT r.*, p.display_name, tm.score_for, tm.score_against,
                   rs.saves, rs.goals_conceded, rs.passes_total, rs.passes_completed,
                   rs.long_balls_total, rs.long_balls_completed,
                   c.goals_against_on_pitch,
                   CASE
                     WHEN tm.score_for > tm.score_against THEN 'WIN'
                     WHEN tm.score_for < tm.score_against THEN 'LOSS'
                     ELSE 'DRAW'
                   END AS result
            FROM player_match_rating r
            JOIN players p ON p.player_id=r.player_id
            JOIN team_match tm ON tm.match_id=r.match_id AND tm.team_id=r.team_id
            LEFT JOIN player_match_raw_stats rs
              ON rs.match_id=r.match_id AND rs.team_id=r.team_id AND rs.player_id=r.player_id
            LEFT JOIN player_match_on_pitch_context c
              ON c.match_id=r.match_id AND c.team_id=r.team_id AND c.player_id=r.player_id
             AND c.context_version='on_pitch_goal_context_v0.2'
            WHERE r.match_rating_version=?
            ORDER BY r.match_date, p.display_name
            """,
            [GK_VERSION],
        ).df()
        expected = int(con.execute(
            "SELECT COUNT(*) FROM player_match_rating WHERE match_rating_version=? AND position_group='GK'",
            [V2_VERSION],
        ).fetchone()[0])
        joined = con.execute(
            """
            SELECT g.match_id, g.player_id, g.match_rating_10 AS gk_rating,
                   v2.match_rating_10 AS v2_rating
            FROM player_match_rating g
            JOIN player_match_rating v2
              ON v2.match_id=g.match_id AND v2.team_id=g.team_id AND v2.player_id=g.player_id
             AND v2.match_rating_version=?
            WHERE g.match_rating_version=?
            """,
            [V2_VERSION, GK_VERSION],
        ).df()

    if gk.empty:
        raise RuntimeError("Goalkeeper candidate not materialized")

    rows = len(gk)
    nulls = int(gk["match_rating_10"].isna().sum())
    duplicates = int(gk.duplicated(["match_id", "player_id"]).sum())
    out_of_range = int((~gk["match_rating_10"].between(3.0, 10.0)).sum())
    bad_path = int((gk["rating_path"] != "GOALKEEPER_PERF18_LATENT").sum())
    bad_role = int((gk["position_group"] != "GK").sum())

    loads = model["latent_loadings"]
    load_shot = float(loads["shot_stopping"])
    load_dist = float(loads["distribution"])
    load_gate = bool(load_shot > 0 and load_dist > 0)
    slope_gate = bool(float(model["calibration"]["slope"]) > 0)
    chronology_gate = bool(str(meta["professional_reference_policy"]).startswith("goalkeeper rows with match_date strictly before"))

    print("PERF-18 GOALKEEPER MATCH RATING VALIDATION")
    print(f"version={GK_VERSION}")
    print(f"coverage={rows}/{expected}")
    print(f"null_ratings={nulls} duplicates={duplicates} out_of_range={out_of_range}")
    print(f"bad_role={bad_role} bad_path={bad_path}")
    print("latent_loadings=" + str(loads))
    print(f"component_direction_gate={'PASS' if load_gate else 'FAIL'}")
    print(f"calibration_slope={model['calibration']['slope']:.4f} gate={'PASS' if slope_gate else 'FAIL'}")
    print(f"chronology_gate={'PASS' if chronology_gate else 'FAIL'}")
    print(
        "distribution="
        + str({
            "mean": float(gk["match_rating_10"].mean()),
            "median": float(gk["match_rating_10"].median()),
            "q10": float(gk["match_rating_10"].quantile(0.10)),
            "q90": float(gk["match_rating_10"].quantile(0.90)),
            "min": float(gk["match_rating_10"].min()),
            "max": float(gk["match_rating_10"].max()),
        })
    )

    if not joined.empty:
        diff = joined["gk_rating"] - joined["v2_rating"]
        print(
            "GK_VS_V2="
            + str({
                "n": int(len(joined)),
                "pearson": float(joined["gk_rating"].corr(joined["v2_rating"])),
                "spearman": spearman(joined["gk_rating"], joined["v2_rating"]),
                "mean_delta": float(diff.mean()),
                "median_abs_delta": float(diff.abs().median()),
            })
        )

    by_result = gk.groupby("result")["match_rating_10"].agg(["count", "mean", "median"]).reset_index()
    print("\nBY RESULT")
    print(by_result.to_string(index=False))

    saves = pd.to_numeric(gk["saves"], errors="coerce")
    ga = pd.to_numeric(gk["goals_conceded"], errors="coerce")
    faced = saves.fillna(0) + ga.fillna(0)
    raw_save = saves / faced.where(faced > 0)
    print("\nGOALKEEPER SANITY")
    print(f"rating_vs_saves_spearman={spearman(gk['match_rating_10'], saves)}")
    print(f"rating_vs_goals_conceded_spearman={spearman(gk['match_rating_10'], ga)}")
    print(f"rating_vs_raw_save_rate_spearman={spearman(gk['match_rating_10'], raw_save)}")
    print(f"rating_vs_distribution_dimension_spearman={spearman(gk['match_rating_10'], gk['creation_progression'])}")

    compare = pd.DataFrame({
        "provider": pd.to_numeric(gk["goals_conceded"], errors="coerce"),
        "derived": pd.to_numeric(gk["goals_against_on_pitch"], errors="coerce"),
    }).dropna()
    if not compare.empty:
        err = (compare["provider"] - compare["derived"]).abs()
        print(
            "gk_provider_vs_onpitch_goals_against="
            + str({
                "n": int(len(compare)),
                "mae": float(err.mean()),
                "exact_share": float((err == 0).mean()),
            })
        )

    needle = str(args.player).strip().lower()
    sample = gk.loc[gk["display_name"].astype(str).str.lower().str.contains(needle, regex=False)].copy()
    if not sample.empty:
        cols = [
            "match_date", "display_name", "minutes_played", "score_for", "score_against",
            "saves", "goals_conceded", "match_rating_10", "match_rating_confidence",
            "defensive_contribution", "creation_progression", "discipline",
        ]
        print(f"\nPLAYER SAMPLE: {args.player}")
        print(sample[cols].to_string(index=False))

    contract = bool(
        rows == expected
        and nulls == 0
        and duplicates == 0
        and out_of_range == 0
        and bad_role == 0
        and bad_path == 0
        and load_gate
        and slope_gate
        and chronology_gate
    )
    print("\nGK_CONTRACT=" + ("PASS" if contract else "FAIL"))
    print("Promotion status: experimental until football sanity review and unified V4/GK access integration.")
    if not contract:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
