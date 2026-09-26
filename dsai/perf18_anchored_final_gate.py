"""PERF-18 — saturation-aware final construct gate for anchored outfield rating.

This validator does not change the candidate. It distinguishes three different cases:
- decisive anchors must move the internal score strictly in the declared direction;
- structural events must never move the score in the wrong direction, but a small
  fraction may show zero marginal effect when a role-standardized feature is already
  winsorized at the +/-3 z boundary;
- display clipping to 3–10 may hide otherwise valid raw-score movement.

Checks:
1) raw-score monotonicity for every event;
2) displayed-score non-wrong direction plus explicit saturation masking rate;
3) rating distribution/variance by minute bucket;
4) sensitivity of the only FPS-specific decisive anchor, penalty_conceded=-0.40.

No production Match Rating is changed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from perf18_opta_points_benchmark_audit import ROOT, discover_input_dir
from perf18_position_aware_rating_candidate_v2 import ROLE_ORDER, build_frame, split_dates
from perf18_outfield_anchored_candidate import (
    EVENT_TESTS,
    PUBLIC_ANCHORS,
    FPS_HYPOTHESIS_ANCHORS,
    fit_role_model,
    fit_calibration,
    structural_core,
    public_anchor,
    fps_hypothesis_anchor,
    rating,
    spearman,
    zero_counts,
)

DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_anchored_final_gate"
TOL = 1e-12
DECISIVE_NONWRONG_REQUIRED = 0.999999
DECISIVE_STRICT_REQUIRED = 0.999
STRUCTURAL_NONWRONG_REQUIRED = 0.999
STRUCTURAL_STRICT_REQUIRED = 0.97


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-18 anchored outfield final gate")
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--min-minutes", type=float, default=30.0)
    p.add_argument("--sample-per-role", type=int, default=15000)
    p.add_argument("--anchor-draws", type=int, default=100)
    return p.parse_args()


def raw_rating(frame: pd.DataFrame, model: dict[str, Any], penalty_weight: float | None = None) -> pd.Series:
    base = (
        float(model["calibration"]["intercept"])
        + float(model["calibration"]["slope"]) * structural_core(frame, model)
    )
    score = base + public_anchor(frame)
    if penalty_weight is None:
        score = score + fps_hypothesis_anchor(frame)
    else:
        f = zero_counts(frame)
        score = score + f["penalties_conceded"] * float(penalty_weight)
    return pd.to_numeric(score, errors="coerce")


def display(raw: pd.Series) -> pd.Series:
    return pd.to_numeric(raw, errors="coerce").clip(3.0, 10.0)


def perturb_event(frame: pd.DataFrame, increments: dict[str, float]) -> pd.DataFrame:
    alt = frame.copy()
    for feature, inc in increments.items():
        alt[feature] = pd.to_numeric(alt[feature], errors="coerce").fillna(0.0) + float(inc)
    return alt


def monotonicity(sample: pd.DataFrame, model: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    base_raw = raw_rating(sample, model)
    base_display = display(base_raw)
    out: dict[str, Any] = {}
    overall = True

    for name, spec in EVENT_TESTS.items():
        alt = perturb_event(sample, spec["increments"])
        alt_raw = raw_rating(alt, model)
        alt_display = display(alt_raw)
        raw_delta = alt_raw - base_raw
        display_delta = alt_display - base_display
        expected = int(spec["expected"])

        if expected > 0:
            raw_nonwrong = raw_delta >= -TOL
            raw_strict = raw_delta > TOL
            display_nonwrong = display_delta >= -TOL
            median_correct = float(raw_delta.median()) > TOL
        else:
            raw_nonwrong = raw_delta <= TOL
            raw_strict = raw_delta < -TOL
            display_nonwrong = display_delta <= TOL
            median_correct = float(raw_delta.median()) < -TOL

        # Correct raw movement can be invisible after display clipping. This is
        # reported as display saturation and is not a construct-validity failure.
        saturation_masked = raw_strict & (display_delta.abs() <= TOL)
        eligible = ~saturation_masked
        if expected > 0:
            display_strict_eligible = display_delta[eligible] > TOL
        else:
            display_strict_eligible = display_delta[eligible] < -TOL

        raw_nonwrong_share = float(raw_nonwrong.mean())
        raw_strict_share = float(raw_strict.mean())
        display_nonwrong_share = float(display_nonwrong.mean())
        masked_share = float(saturation_masked.mean())
        display_strict_share = (
            float(display_strict_eligible.mean()) if int(eligible.sum()) else 1.0
        )

        decisive = bool(spec["decisive"])
        if decisive:
            nonwrong_required = DECISIVE_NONWRONG_REQUIRED
            strict_required = DECISIVE_STRICT_REQUIRED
        else:
            # Structural features are winsorized at +/-3 z. Therefore a small tail
            # can legitimately have zero marginal effect once the relevant feature
            # is saturated. Wrong-sign movement is still effectively forbidden.
            nonwrong_required = STRUCTURAL_NONWRONG_REQUIRED
            strict_required = STRUCTURAL_STRICT_REQUIRED

        passed = bool(
            raw_nonwrong_share >= nonwrong_required
            and raw_strict_share >= strict_required
            and median_correct
            and display_nonwrong_share >= nonwrong_required
        )
        overall = overall and passed
        out[name] = {
            "expected": "UP" if expected > 0 else "DOWN",
            "decisive_anchor": decisive,
            "raw_median_delta": float(raw_delta.median()),
            "raw_nonwrong_share": raw_nonwrong_share,
            "raw_strict_share": raw_strict_share,
            "display_nonwrong_share": display_nonwrong_share,
            "display_strict_when_not_saturation_masked": display_strict_share,
            "display_saturation_masked_share": masked_share,
            "median_direction_correct": bool(median_correct),
            "required_nonwrong_share": float(nonwrong_required),
            "required_strict_share": float(strict_required),
            "pass": passed,
        }
    return out, overall


def minute_buckets(frame: pd.DataFrame, scores: pd.Series) -> dict[str, Any]:
    work = pd.DataFrame(
        {
            "minutes": pd.to_numeric(frame["minutes_played"], errors="coerce"),
            "rating": pd.to_numeric(scores, errors="coerce"),
        },
        index=frame.index,
    )
    work["bucket"] = pd.cut(
        work["minutes"],
        bins=[29.999, 44.0, 59.0, 74.0, 89.0, np.inf],
        labels=["30-44", "45-59", "60-74", "75-89", "90+"],
        include_lowest=True,
    )
    result: dict[str, Any] = {}
    sds: list[float] = []
    for label, group in work.groupby("bucket", observed=True):
        sd = float(group["rating"].std(ddof=0))
        sds.append(sd)
        result[str(label)] = {
            "n": int(len(group)),
            "mean": float(group["rating"].mean()),
            "median": float(group["rating"].median()),
            "sd": sd,
            "q10": float(group["rating"].quantile(0.10)),
            "q90": float(group["rating"].quantile(0.90)),
        }
    finite = [x for x in sds if np.isfinite(x) and x > 0]
    variance_ratio = float(max(finite) / min(finite)) if finite else None
    return {
        "spearman_minutes_rating": spearman(work["minutes"], work["rating"]),
        "sd_max_to_min_ratio": variance_ratio,
        "buckets": result,
    }


def top_overlap(a: pd.Series, b: pd.Series, share: float = 0.10) -> float:
    valid = a.notna() & b.notna()
    aa, bb = a[valid], b[valid]
    if aa.empty:
        return float("nan")
    k = max(1, int(round(len(aa) * share)))
    ia = set(aa.nlargest(k).index)
    ib = set(bb.nlargest(k).index)
    return float(len(ia & ib) / k)


def penalty_anchor_sensitivity(sample: pd.DataFrame, model: dict[str, Any], draws: int) -> dict[str, Any]:
    base_weight = float(FPS_HYPOTHESIS_ANCHORS["penalties_conceded"])
    base = display(raw_rating(sample, model, penalty_weight=base_weight))
    rng = np.random.default_rng(1806)
    rhos: list[float] = []
    overlaps: list[float] = []
    for _ in range(int(draws)):
        # Wide +/-50% range because this is an FPS hypothesis, not a public weight.
        weight = base_weight * float(rng.uniform(0.50, 1.50))
        alt = display(raw_rating(sample, model, penalty_weight=weight))
        rho = spearman(base, alt)
        if rho is not None:
            rhos.append(float(rho))
        overlaps.append(top_overlap(base, alt))
    return {
        "base_weight": base_weight,
        "tested_multiplier_range": [0.50, 1.50],
        "spearman_q05": float(np.quantile(rhos, 0.05)) if rhos else None,
        "spearman_min": float(np.min(rhos)) if rhos else None,
        "top10_overlap_q05": float(np.quantile(overlaps, 0.05)) if overlaps else None,
        "top10_overlap_min": float(np.min(overlaps)) if overlaps else None,
        "pass": bool(
            rhos and overlaps
            and float(np.quantile(rhos, 0.05)) >= 0.995
            and float(np.quantile(overlaps, 0.05)) >= 0.98
        ),
    }


def main() -> None:
    args = parse_args()
    input_dir = discover_input_dir(args.input_dir)
    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    frame = build_frame(input_dir, args.min_minutes)
    train, _, test, split_info = split_dates(frame)

    print("PERF-18 ANCHORED FINAL GATE")
    print(f"rows={len(frame)} train={len(train)} test={len(test)} split={split_info}")
    print("display_clip=3.0..10.0; saturation is reported separately from raw monotonicity")
    print(
        "gate_thresholds="
        f"decisive(nonwrong>={DECISIVE_NONWRONG_REQUIRED},strict>={DECISIVE_STRICT_REQUIRED}); "
        f"structural(nonwrong>={STRUCTURAL_NONWRONG_REQUIRED},strict>={STRUCTURAL_STRICT_REQUIRED},median-sign-correct)"
    )

    result: dict[str, Any] = {
        "method": "raw_construct_monotonicity_plus_display_saturation_plus_minute_variance_plus_anchor_sensitivity",
        "split": split_info,
        "gate_thresholds": {
            "decisive_nonwrong_required": DECISIVE_NONWRONG_REQUIRED,
            "decisive_strict_required": DECISIVE_STRICT_REQUIRED,
            "structural_nonwrong_required": STRUCTURAL_NONWRONG_REQUIRED,
            "structural_strict_required": STRUCTURAL_STRICT_REQUIRED,
            "structural_median_direction_required": True,
            "rationale": "structural z-features are winsorized at +/-3, so zero marginal effect in a small saturated tail is allowed; wrong-sign movement is not",
        },
        "roles": {},
        "production_status": "EXPERIMENT_ONLY",
    }
    overall = True

    for role in ROLE_ORDER:
        tr = train.loc[train["position_group"] == role].copy()
        te = test.loc[test["position_group"] == role].copy()
        if min(len(tr), len(te)) < 200:
            continue

        model = fit_role_model(tr, role)
        intercept, slope = fit_calibration(tr, model)
        model["calibration"] = {"intercept": intercept, "slope": slope}
        scores = rating(te, model)
        sample = te.sample(min(int(args.sample_per_role), len(te)), random_state=18)

        events, mono_pass = monotonicity(sample, model)
        minutes = minute_buckets(te, scores)
        penalty_sens = penalty_anchor_sensitivity(sample, model, int(args.anchor_draws))

        # Minute variance is diagnostic rather than a hard gate in this version: a
        # decisive event can legitimately make short appearances more dispersed.
        role_pass = bool(mono_pass and penalty_sens["pass"])
        overall = overall and role_pass
        result["roles"][role] = {
            "monotonicity": events,
            "monotonicity_gate": mono_pass,
            "minutes": minutes,
            "penalty_anchor_sensitivity": penalty_sens,
            "role_gate": role_pass,
        }

        print(f"\nPOSITION={role}")
        print(
            f" minutes_spearman={minutes['spearman_minutes_rating']:.4f} "
            f"sd_ratio={minutes['sd_max_to_min_ratio']:.3f}"
        )
        print(f" monotonicity_gate={'PASS' if mono_pass else 'FAIL'}")
        for e in ["goal", "assist", "red_card", "penalty_conceded", "turnover", "interception"]:
            x = events[e]
            print(
                f"  {e}: raw_delta={x['raw_median_delta']:+.4f} "
                f"raw_strict={x['raw_strict_share']:.4f} "
                f"required={x['required_strict_share']:.3f} "
                f"masked_by_clip={x['display_saturation_masked_share']:.4f} "
                f"pass={x['pass']}"
            )
        print(
            " penalty_anchor_sensitivity="
            f"spearman_q05:{penalty_sens['spearman_q05']:.4f} "
            f"top10_q05:{penalty_sens['top10_overlap_q05']:.4f} "
            f"gate:{'PASS' if penalty_sens['pass'] else 'FAIL'}"
        )

    result["overall_gate"] = bool(overall and result["roles"])
    artifact = out_dir / "anchored_final_gate.json"
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nPERF-18 ANCHORED FINAL GATE: COMPLETE")
    print(f"overall_gate={'PASS' if result['overall_gate'] else 'FAIL'}")
    print(f"artifact={artifact}")
    print("No production rating was changed.")


if __name__ == "__main__":
    main()
