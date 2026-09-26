"""PERF-18 — role-prior multidimensional rating sensitivity.

This experiment separates two purposes that must not be conflated:
1) Opta Points is used only as an external transparent scale/calibration benchmark.
2) The Football Performance System rating remains position-aware and multidimensional.

The proprietary Opta Player Rating weights are not public. Therefore the role weights
below are explicit football hypotheses, not claimed Opta weights. Their acceptability is
stress-tested by perturbing every weight around the prior and measuring ranking stability.
No production rating is changed by this script.
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
    DIMENSIONS,
    ROLE_ORDER,
    apply_dimension,
    build_frame,
    fit_dimension_reference,
    metric,
    split_dates,
)

DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_position_prior_sensitivity"
DIMENSION_ORDER = list(DIMENSIONS.keys())

# Explicit role hypotheses. They are intentionally auditable and are NOT represented
# as proprietary Opta Player Rating weights. Exact values remain experimental until
# sensitivity and case validation pass.
ROLE_PRIORS: dict[str, dict[str, float]] = {
    "CB": {"shooting": 0.08, "passing_creation": 0.20, "possession_1v1": 0.10, "defending": 0.47, "discipline_context": 0.15},
    "FB": {"shooting": 0.10, "passing_creation": 0.25, "possession_1v1": 0.20, "defending": 0.30, "discipline_context": 0.15},
    "DM": {"shooting": 0.08, "passing_creation": 0.30, "possession_1v1": 0.18, "defending": 0.29, "discipline_context": 0.15},
    "CM": {"shooting": 0.12, "passing_creation": 0.35, "possession_1v1": 0.23, "defending": 0.15, "discipline_context": 0.15},
    "AM": {"shooting": 0.25, "passing_creation": 0.30, "possession_1v1": 0.25, "defending": 0.05, "discipline_context": 0.15},
    "W":  {"shooting": 0.25, "passing_creation": 0.22, "possession_1v1": 0.33, "defending": 0.05, "discipline_context": 0.15},
    "ST": {"shooting": 0.45, "passing_creation": 0.15, "possession_1v1": 0.20, "defending": 0.05, "discipline_context": 0.15},
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-18 position-prior sensitivity")
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--min-minutes", type=float, default=30.0)
    p.add_argument("--draws", type=int, default=200)
    p.add_argument("--perturbation", type=float, default=0.20)
    p.add_argument("--rank-sample-per-role", type=int, default=50000)
    return p.parse_args()


def norm_weights(w: dict[str, float]) -> dict[str, float]:
    total = float(sum(max(0.0, float(v)) for v in w.values()))
    if total <= 0:
        raise RuntimeError("Weight vector has zero total")
    return {k: max(0.0, float(v)) / total for k, v in w.items()}


def build_dimensions(train: pd.DataFrame, other: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    out = pd.DataFrame(index=other.index)
    refs: dict[str, Any] = {}
    for dim in DIMENSION_ORDER:
        ref = fit_dimension_reference(train, dim)
        refs[dim] = ref
        out[dim] = apply_dimension(other, ref)
    return out, refs


def composite(dim: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    w = norm_weights(weights)
    score = pd.Series(0.0, index=dim.index, dtype=float)
    for d in DIMENSION_ORDER:
        score = score + pd.to_numeric(dim[d], errors="coerce").fillna(0.0) * float(w[d])
    return score


def calibrate(train_score: pd.Series, train_target: pd.Series) -> tuple[float, float]:
    x = pd.to_numeric(train_score, errors="coerce")
    y = pd.to_numeric(train_target, errors="coerce")
    valid = x.notna() & y.notna()
    x = x[valid].to_numpy(dtype=float)
    y = y[valid].to_numpy(dtype=float)
    if len(x) < 100 or float(np.std(x)) < 1e-12:
        raise RuntimeError("Insufficient variation for scale calibration")
    slope, intercept = np.polyfit(x, y, 1)
    return float(intercept), float(slope)


def apply_calibration(score: pd.Series, intercept: float, slope: float) -> pd.Series:
    return (float(intercept) + float(slope) * score).clip(3.0, 10.0)


def rank_corr(a: pd.Series, b: pd.Series) -> float:
    valid = a.notna() & b.notna()
    if int(valid.sum()) < 3:
        return float("nan")
    return float(a[valid].rank(method="average").corr(b[valid].rank(method="average")))


def top_overlap(a: pd.Series, b: pd.Series, share: float = 0.10) -> float:
    valid = a.notna() & b.notna()
    aa, bb = a[valid], b[valid]
    if aa.empty:
        return float("nan")
    k = max(1, int(round(len(aa) * share)))
    ia = set(aa.nlargest(k).index)
    ib = set(bb.nlargest(k).index)
    return float(len(ia & ib) / k)


def perturb(prior: dict[str, float], rng: np.random.Generator, pct: float) -> dict[str, float]:
    raw = {}
    for d, base in prior.items():
        multiplier = rng.uniform(1.0 - pct, 1.0 + pct)
        raw[d] = max(0.0, float(base) * float(multiplier))
    return norm_weights(raw)


def quantile_dict(values: list[float]) -> dict[str, float | None]:
    a = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    if a.size == 0:
        return {"q05": None, "median": None, "q95": None, "min": None}
    return {
        "q05": float(np.quantile(a, 0.05)),
        "median": float(np.quantile(a, 0.50)),
        "q95": float(np.quantile(a, 0.95)),
        "min": float(np.min(a)),
    }


def main() -> None:
    args = parse_args()
    input_dir = discover_input_dir(args.input_dir)
    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    frame = build_frame(input_dir, args.min_minutes)
    train, valid, test, split_info = split_dates(frame)
    rng = np.random.default_rng(1806)

    print("PERF-18 POSITION-PRIOR SENSITIVITY")
    print(f"rows={len(frame)} train={len(train)} valid={len(valid)} test={len(test)}")
    print(f"split={split_info}")
    print("Opta Points is calibration/benchmark only; role weights are explicit FPS hypotheses.")

    result: dict[str, Any] = {
        "method": "role_specific_signed_dimensions_plus_prior_sensitivity_plus_opta_points_scale_calibration",
        "target_role": "external_scale_and_sanity_benchmark_only",
        "split": split_info,
        "min_minutes": float(args.min_minutes),
        "perturbation": float(args.perturbation),
        "draws": int(args.draws),
        "roles": {},
        "production_status": "EXPERIMENT_ONLY",
    }

    pooled_y: list[pd.Series] = []
    pooled_p: list[pd.Series] = []

    for role in ROLE_ORDER:
        tr = train.loc[train["position_group"] == role].copy()
        va = valid.loc[valid["position_group"] == role].copy()
        te = test.loc[test["position_group"] == role].copy()
        if min(len(tr), len(va), len(te)) < 200:
            print(f"POSITION={role} SKIP insufficient rows")
            continue

        tr_dim, refs = build_dimensions(tr, tr)
        va_dim, _ = build_dimensions(tr, va)
        te_dim, _ = build_dimensions(tr, te)

        prior = norm_weights(ROLE_PRIORS[role])
        tr_core = composite(tr_dim, prior)
        va_core = composite(va_dim, prior)
        te_core = composite(te_dim, prior)
        intercept, slope = calibrate(tr_core, tr["opta_points_target"])
        if slope <= 0:
            raise RuntimeError(f"Negative/zero calibration slope for {role}: {slope}")

        va_rating = apply_calibration(va_core, intercept, slope)
        te_rating = apply_calibration(te_core, intercept, slope)
        valid_metric = metric(va["opta_points_target"], va_rating.to_numpy())
        test_metric = metric(te["opta_points_target"], te_rating.to_numpy())

        # Sample at most N rows for sensitivity to keep runtime bounded.
        if len(te) > args.rank_sample_per_role:
            sample_idx = te.sample(args.rank_sample_per_role, random_state=18).index
            base_rank = te_rating.loc[sample_idx]
            sample_dim = te_dim.loc[sample_idx]
        else:
            sample_idx = te.index
            base_rank = te_rating
            sample_dim = te_dim

        rhos: list[float] = []
        overlaps: list[float] = []
        benchmark_corrs: list[float] = []
        for _ in range(int(args.draws)):
            w = perturb(prior, rng, float(args.perturbation))
            alt_core = composite(sample_dim, w)
            alt_rating = apply_calibration(alt_core, intercept, slope)
            rhos.append(rank_corr(base_rank, alt_rating))
            overlaps.append(top_overlap(base_rank, alt_rating, 0.10))
            benchmark_corrs.append(rank_corr(te.loc[sample_idx, "opta_points_target"], alt_rating))

        rho_q = quantile_dict(rhos)
        overlap_q = quantile_dict(overlaps)
        bench_q = quantile_dict(benchmark_corrs)
        stable = bool(
            rho_q["q05"] is not None
            and overlap_q["q05"] is not None
            and float(rho_q["q05"]) >= 0.90
            and float(overlap_q["q05"]) >= 0.75
        )

        dist = te_rating.quantile([0.01, 0.10, 0.50, 0.90, 0.99]).to_dict()
        role_result = {
            "rows": {"train": int(len(tr)), "valid": int(len(va)), "test": int(len(te))},
            "prior_weights": prior,
            "calibration": {"intercept": intercept, "slope": slope},
            "valid_vs_opta_points": valid_metric,
            "test_vs_opta_points": test_metric,
            "rating_quantiles_test": {str(k): float(v) for k, v in dist.items()},
            "sensitivity": {
                "rank_spearman_vs_baseline": rho_q,
                "top10_overlap_vs_baseline": overlap_q,
                "spearman_vs_opta_points": bench_q,
                "stability_gate": stable,
                "gate_definition": "q05 Spearman>=0.90 and q05 top10 overlap>=0.75 under independent +/- perturbations",
            },
            "dimension_reference": refs,
        }
        result["roles"][role] = role_result
        pooled_y.append(te["opta_points_target"])
        pooled_p.append(te_rating)

        print(f"\nPOSITION={role}")
        print(" priors=" + str({k: round(v, 3) for k, v in prior.items()}))
        print(f" calibration=intercept:{intercept:.4f} slope:{slope:.4f}")
        print(" test_vs_opta=" + str(test_metric))
        print(f" sensitivity_spearman_q05={rho_q['q05']:.4f} median={rho_q['median']:.4f}")
        print(f" sensitivity_top10_q05={overlap_q['q05']:.4f} median={overlap_q['median']:.4f}")
        print(f" stability_gate={'PASS' if stable else 'FAIL'}")

    if pooled_y:
        y = pd.concat(pooled_y).sort_index()
        p = pd.concat(pooled_p).reindex(y.index)
        result["overall_test_vs_opta_points"] = metric(y, p.to_numpy())
    else:
        result["overall_test_vs_opta_points"] = None

    overall_pass = bool(result["roles"] and all(r["sensitivity"]["stability_gate"] for r in result["roles"].values()))
    result["overall_sensitivity_gate"] = overall_pass

    artifact = out_dir / "position_prior_sensitivity.json"
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nPERF-18 POSITION-PRIOR SENSITIVITY: COMPLETE")
    print("overall_test_vs_opta_points=" + str(result["overall_test_vs_opta_points"]))
    print(f"overall_sensitivity_gate={'PASS' if overall_pass else 'FAIL'}")
    print(f"artifact={artifact}")
    print("No production rating was changed.")


if __name__ == "__main__":
    main()
