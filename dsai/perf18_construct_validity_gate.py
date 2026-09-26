"""PERF-18 — construct-validity diagnostics for the position-aware outfield rating.

Checks before any production promotion:
- structural monotonicity under coherent event perturbations;
- association with minutes played versus the external Opta Points benchmark;
- whether goals_conceded behaves as player-specific/on-pitch context or as a flat
  team-match value in the provider aggregates.

The script is diagnostic only. It does not change the production Match Rating.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from perf18_opta_points_benchmark_audit import ROOT, discover_input_dir
from perf18_position_aware_rating_candidate_v2 import (
    ROLE_ORDER,
    apply_dimension,
    build_frame,
    split_dates,
)
from perf18_position_prior_sensitivity import (
    DIMENSION_ORDER,
    ROLE_PRIORS,
    apply_calibration,
    calibrate,
    composite,
    fit_dimension_reference,
    norm_weights,
)

DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_construct_validity"

EVENT_TESTS: dict[str, dict[str, Any]] = {
    "goal": {"expected": +1, "increments": {"goals": 1.0, "shots_total": 1.0, "shots_on_target": 1.0}},
    "assist": {"expected": +1, "increments": {"assists": 1.0}},
    "dribble_won": {"expected": +1, "increments": {"dribbles_won": 1.0, "dribbles_total": 1.0}},
    "tackle_won": {"expected": +1, "increments": {"tackles_won": 1.0, "tackles_total": 1.0}},
    "interception": {"expected": +1, "increments": {"interceptions": 1.0}},
    "penalty_won": {"expected": +1, "increments": {"penalties_won": 1.0}},
    "foul_received": {"expected": +1, "increments": {"fouls_received": 1.0}},
    "turnover": {"expected": -1, "increments": {"turnovers": 1.0}},
    "dispossessed": {"expected": -1, "increments": {"dispossessed": 1.0}},
    "foul_committed": {"expected": -1, "increments": {"fouls_committed": 1.0}},
    "yellow_card": {"expected": -1, "increments": {"yellow_cards": 1.0}},
    "red_card": {"expected": -1, "increments": {"red_cards": 1.0}},
    "penalty_conceded": {"expected": -1, "increments": {"penalties_conceded": 1.0}},
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-18 construct validity gate")
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--min-minutes", type=float, default=30.0)
    p.add_argument("--sample-per-role", type=int, default=10000)
    return p.parse_args()


def safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    n = pd.to_numeric(num, errors="coerce")
    d = pd.to_numeric(den, errors="coerce")
    return (n / d.where(d > 0)).clip(0.0, 1.0)


def refresh_ratios(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["pass_accuracy"] = safe_ratio(out["passes_completed"], out["passes_total"])
    out["dribble_success"] = safe_ratio(out["dribbles_won"], out["dribbles_total"])
    out["tackle_success"] = safe_ratio(out["tackles_won"], out["tackles_total"])
    return out


def fit_refs(train: pd.DataFrame) -> dict[str, Any]:
    return {dim: fit_dimension_reference(train, dim) for dim in DIMENSION_ORDER}


def apply_dims(frame: pd.DataFrame, refs: dict[str, Any]) -> pd.DataFrame:
    out = pd.DataFrame(index=frame.index)
    for dim in DIMENSION_ORDER:
        out[dim] = apply_dimension(frame, refs[dim])
    return out


def spearman(a: pd.Series, b: pd.Series) -> float | None:
    aa = pd.to_numeric(a, errors="coerce")
    bb = pd.to_numeric(b, errors="coerce")
    valid = aa.notna() & bb.notna()
    if int(valid.sum()) < 3:
        return None
    return float(aa[valid].rank(method="average").corr(bb[valid].rank(method="average")))


def minute_summary(frame: pd.DataFrame, rating: pd.Series) -> dict[str, Any]:
    work = pd.DataFrame(
        {
            "minutes": pd.to_numeric(frame["minutes_played"], errors="coerce"),
            "rating": pd.to_numeric(rating, errors="coerce"),
            "benchmark": pd.to_numeric(frame["opta_points_target"], errors="coerce"),
        },
        index=frame.index,
    )
    work["bucket"] = pd.cut(
        work["minutes"],
        bins=[29.999, 44.0, 59.0, 74.0, 89.0, np.inf],
        labels=["30-44", "45-59", "60-74", "75-89", "90+"],
        include_lowest=True,
    )
    buckets: dict[str, Any] = {}
    for label, g in work.groupby("bucket", observed=True):
        buckets[str(label)] = {
            "n": int(len(g)),
            "rating_mean": float(g["rating"].mean()),
            "rating_median": float(g["rating"].median()),
            "opta_points_mean": float(g["benchmark"].mean()),
            "opta_points_median": float(g["benchmark"].median()),
        }
    return {
        "spearman_minutes_vs_rating": spearman(work["minutes"], work["rating"]),
        "spearman_minutes_vs_opta_points": spearman(work["minutes"], work["benchmark"]),
        "buckets": buckets,
    }


def event_monotonicity(
    sample: pd.DataFrame,
    refs: dict[str, Any],
    weights: dict[str, float],
    intercept: float,
    slope: float,
) -> dict[str, Any]:
    base_dims = apply_dims(sample, refs)
    base_core = composite(base_dims, weights)
    base_rating = apply_calibration(base_core, intercept, slope)
    result: dict[str, Any] = {}

    for name, spec in EVENT_TESTS.items():
        alt = sample.copy()
        for feature, inc in spec["increments"].items():
            alt[feature] = pd.to_numeric(alt[feature], errors="coerce").fillna(0.0) + float(inc)
        alt = refresh_ratios(alt)
        alt_dims = apply_dims(alt, refs)
        alt_rating = apply_calibration(composite(alt_dims, weights), intercept, slope)
        delta = pd.to_numeric(alt_rating - base_rating, errors="coerce")
        expected = int(spec["expected"])
        if expected > 0:
            nonwrong = delta >= -1e-12
            strict = delta > 1e-12
        else:
            nonwrong = delta <= 1e-12
            strict = delta < -1e-12
        result[name] = {
            "expected_direction": "UP" if expected > 0 else "DOWN",
            "median_delta": float(delta.median()),
            "mean_delta": float(delta.mean()),
            "nonwrong_share": float(nonwrong.mean()),
            "strict_direction_share": float(strict.mean()),
        }
    return result


def context_variation(frame: pd.DataFrame) -> dict[str, Any]:
    work = frame[["match_id", "team_id", "player_id", "goals_conceded", "minutes_played"]].copy()
    work["goals_conceded"] = pd.to_numeric(work["goals_conceded"], errors="coerce")
    grouped = work.groupby(["match_id", "team_id"], dropna=False)
    nunique = grouped["goals_conceded"].nunique(dropna=True)
    return {
        "team_matches": int(len(nunique)),
        "share_team_matches_with_multiple_player_values": float((nunique > 1).mean()),
        "share_team_matches_single_value": float((nunique <= 1).mean()),
        "interpretation": (
            "Multiple values within a team-match indicate player-specific exposure is present in the provider aggregate; "
            "a single value everywhere would indicate flat team-match context."
        ),
    }


def main() -> None:
    args = parse_args()
    input_dir = discover_input_dir(args.input_dir)
    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    frame = build_frame(input_dir, args.min_minutes)
    train, _, test, split_info = split_dates(frame)

    print("PERF-18 CONSTRUCT VALIDITY GATE")
    print(f"rows={len(frame)} train={len(train)} test={len(test)} split={split_info}")

    result: dict[str, Any] = {
        "method": "construct_validity_diagnostics",
        "split": split_info,
        "min_minutes": float(args.min_minutes),
        "roles": {},
        "context_variation": context_variation(frame),
        "production_status": "EXPERIMENT_ONLY",
    }

    all_monotonic = True
    for role in ROLE_ORDER:
        tr = train.loc[train["position_group"] == role].copy()
        te = test.loc[test["position_group"] == role].copy()
        if min(len(tr), len(te)) < 200:
            continue

        refs = fit_refs(tr)
        weights = norm_weights(ROLE_PRIORS[role])
        tr_rating_core = composite(apply_dims(tr, refs), weights)
        intercept, slope = calibrate(tr_rating_core, tr["opta_points_target"])
        te_rating = apply_calibration(composite(apply_dims(te, refs), weights), intercept, slope)

        if len(te) > int(args.sample_per_role):
            sample = te.sample(int(args.sample_per_role), random_state=18)
        else:
            sample = te.copy()

        events = event_monotonicity(sample, refs, weights, intercept, slope)
        role_mono = all(float(v["nonwrong_share"]) >= 0.999 for v in events.values())
        all_monotonic = all_monotonic and role_mono
        minutes = minute_summary(te, te_rating)

        result["roles"][role] = {
            "rows": {"train": int(len(tr)), "test": int(len(te))},
            "minutes": minutes,
            "event_monotonicity": events,
            "monotonicity_gate": role_mono,
        }

        print(f"\nPOSITION={role}")
        print(
            " minutes_spearman="
            f"candidate:{minutes['spearman_minutes_vs_rating']:.4f} "
            f"opta_points:{minutes['spearman_minutes_vs_opta_points']:.4f}"
        )
        print(f" monotonicity_gate={'PASS' if role_mono else 'FAIL'}")
        for event in ["goal", "assist", "turnover", "red_card", "penalty_conceded"]:
            e = events[event]
            print(
                f"  {event}: median_delta={e['median_delta']:+.4f} "
                f"nonwrong={e['nonwrong_share']:.4f} strict={e['strict_direction_share']:.4f}"
            )

    result["overall_monotonicity_gate"] = bool(all_monotonic and result["roles"])

    artifact = out_dir / "construct_validity_gate.json"
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nCONTEXT GOALS_CONCEDED")
    print(str(result["context_variation"]))
    print(f"overall_monotonicity_gate={'PASS' if result['overall_monotonicity_gate'] else 'FAIL'}")
    print(f"artifact={artifact}")
    print("No production rating was changed.")


if __name__ == "__main__":
    main()
