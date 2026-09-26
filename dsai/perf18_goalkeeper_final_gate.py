"""PERF-18 — final methodological gate for the separate goalkeeper rating.

Purpose
-------
Choose an interpretable shot-stopping/distribution balance without letting PCA
implicitly decide football merit weights.

Method
------
1. Use only professional goalkeeper rows strictly before the local demo season.
2. Split those rows chronologically into TRAIN / VALID / TEST.
3. Fit shot-stopping shrinkage and the goalkeeper distribution PCA on TRAIN only.
4. Evaluate a pre-declared, interpretable weight grid where shot-stopping receives
   50–90% of the structural core and distribution receives the complement.
5. Select the weight on VALID using reconstructed public Opta Points only as a
   transparent external benchmark, then report untouched TEST performance.
6. Require monotonic football directions (save up, goal conceded down, successful
   distribution actions up) and local ranking stability around the selected weight.

Opta Points is a benchmark, not ground truth or the proprietary Opta Player Rating.
No production rating is changed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ANALYTICS_DIR = ROOT / "analytics"
DSAI_DIR = ROOT / "dsai"
for p in [ANALYTICS_DIR, DSAI_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import build_match_rating_gk_experimental as gk  # noqa: E402
from perf18_opta_points_benchmark_audit import discover_input_dir  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_gk_final_gate"
WEIGHT_GRID = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
TOL = 1e-12


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-18 constrained goalkeeper final gate")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--min-reference-minutes", type=float, default=30.0)
    p.add_argument("--max-pca-fit-rows", type=int, default=200000)
    p.add_argument("--sample-rows", type=int, default=20000)
    return p.parse_args()


def spearman(a: pd.Series, b: pd.Series) -> float | None:
    aa = pd.to_numeric(a, errors="coerce")
    bb = pd.to_numeric(b, errors="coerce")
    valid = aa.notna() & bb.notna()
    if int(valid.sum()) < 3:
        return None
    return float(aa[valid].rank(method="average").corr(bb[valid].rank(method="average")))


def pearson(a: pd.Series, b: pd.Series) -> float | None:
    aa = pd.to_numeric(a, errors="coerce")
    bb = pd.to_numeric(b, errors="coerce")
    valid = aa.notna() & bb.notna()
    if int(valid.sum()) < 3:
        return None
    return float(aa[valid].corr(bb[valid]))


def split_dates(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, str]]:
    dates = np.array(sorted(pd.to_datetime(frame["match_date"]).dt.normalize().unique()))
    if len(dates) < 20:
        raise RuntimeError(f"Too few goalkeeper dates for temporal split: {len(dates)}")
    train_end = dates[max(1, int(len(dates) * 0.70)) - 1]
    valid_end = dates[max(2, int(len(dates) * 0.85)) - 1]
    normalized = pd.to_datetime(frame["match_date"]).dt.normalize()
    train = frame.loc[normalized <= train_end].copy()
    valid = frame.loc[(normalized > train_end) & (normalized <= valid_end)].copy()
    test = frame.loc[normalized > valid_end].copy()
    return train, valid, test, {
        "train_end": str(pd.Timestamp(train_end).date()),
        "valid_end": str(pd.Timestamp(valid_end).date()),
    }


def fit_reference(train_raw: pd.DataFrame, max_pca_rows: int) -> dict[str, Any]:
    base = gk._zero_counts(train_raw)
    faced = base["saves"] + base["goals_conceded"]
    observed = faced > 0
    if int(observed.sum()) < 1000:
        raise RuntimeError("Insufficient TRAIN shot-stopping evidence")

    prior_rate = float(base.loc[observed, "saves"].sum() / faced[observed].sum())
    prior_strength = float(max(1.0, faced[observed].median()))
    train = gk._add_features(base, prior_rate, prior_strength)
    dist_model = gk._fit_distribution(train, max_pca_rows)
    train["distribution_pc"] = gk._apply_distribution(train, dist_model)

    shot_mean = float(train["shrunk_save_rate"].mean())
    shot_sd = float(train["shrunk_save_rate"].std(ddof=0))
    dist_mean = float(train["distribution_pc"].mean())
    dist_sd = float(train["distribution_pc"].std(ddof=0))
    if not np.isfinite(shot_sd) or shot_sd <= 1e-9:
        shot_sd = 1.0
    if not np.isfinite(dist_sd) or dist_sd <= 1e-9:
        dist_sd = 1.0

    return {
        "prior_save_rate": prior_rate,
        "prior_strength_shots": prior_strength,
        "distribution": dist_model,
        "shot_mean": shot_mean,
        "shot_sd": shot_sd,
        "distribution_mean": dist_mean,
        "distribution_sd": dist_sd,
        "train_rows": int(len(train)),
        "train_shot_evidence_rows": int(observed.sum()),
    }


def components(frame_raw: pd.DataFrame, ref: dict[str, Any]) -> pd.DataFrame:
    f = gk._add_features(frame_raw, ref["prior_save_rate"], ref["prior_strength_shots"])
    f["distribution_pc"] = gk._apply_distribution(f, ref["distribution"])
    f["shot_z"] = (
        f["shrunk_save_rate"] - float(ref["shot_mean"])
    ) / float(ref["shot_sd"])
    f["dist_z"] = (
        f["distribution_pc"] - float(ref["distribution_mean"])
    ) / float(ref["distribution_sd"])
    return f


def fit_calibration(train_raw: pd.DataFrame, comp: pd.DataFrame, shot_weight: float) -> dict[str, float]:
    w = float(shot_weight)
    core = w * comp["shot_z"].fillna(0.0) + (1.0 - w) * comp["dist_z"].fillna(0.0)
    residual = pd.to_numeric(train_raw["opta_points_target"], errors="coerce") - gk._public_anchor(train_raw)
    valid = core.notna() & residual.notna()
    x = core[valid].to_numpy(dtype=float)
    y = residual[valid].to_numpy(dtype=float)
    if len(x) < 100:
        raise RuntimeError("Insufficient calibration rows")
    var = float(np.var(x))
    slope = float(np.cov(x, y, ddof=0)[0, 1] / var) if var > 1e-12 else 0.0
    intercept = float(np.mean(y) - slope * np.mean(x))
    if not np.isfinite(slope) or slope <= 0:
        raise RuntimeError(f"Non-positive calibration slope for weight {w}: {slope}")
    return {"intercept": intercept, "slope": slope}


def score(
    frame_raw: pd.DataFrame,
    comp: pd.DataFrame,
    shot_weight: float,
    calibration: dict[str, float],
) -> pd.Series:
    w = float(shot_weight)
    core = w * comp["shot_z"].fillna(0.0) + (1.0 - w) * comp["dist_z"].fillna(0.0)
    raw = (
        float(calibration["intercept"])
        + float(calibration["slope"]) * core
        + gk._public_anchor(frame_raw)
    )
    return pd.to_numeric(raw, errors="coerce").clip(3.0, 10.0)


def metrics(target: pd.Series, pred: pd.Series) -> dict[str, float | int | None]:
    y = pd.to_numeric(target, errors="coerce")
    p = pd.to_numeric(pred, errors="coerce")
    valid = y.notna() & p.notna()
    yy, pp = y[valid], p[valid]
    diff = pp - yy
    return {
        "n": int(valid.sum()),
        "mae": float(diff.abs().mean()),
        "rmse": float(np.sqrt(np.mean(np.square(diff)))),
        "pearson": pearson(yy, pp),
        "spearman": spearman(yy, pp),
        "bias": float(diff.mean()),
    }


def top_overlap(a: pd.Series, b: pd.Series, share: float = 0.10) -> float:
    aa = pd.to_numeric(a, errors="coerce")
    bb = pd.to_numeric(b, errors="coerce")
    valid = aa.notna() & bb.notna()
    aa, bb = aa[valid], bb[valid]
    if aa.empty:
        return float("nan")
    k = max(1, int(round(len(aa) * share)))
    return float(len(set(aa.nlargest(k).index) & set(bb.nlargest(k).index)) / k)


def perturb(frame: pd.DataFrame, increments: dict[str, float]) -> pd.DataFrame:
    out = frame.copy()
    for c, inc in increments.items():
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0) + float(inc)
    return out


def monotonicity(
    sample: pd.DataFrame,
    ref: dict[str, Any],
    shot_weight: float,
    calibration: dict[str, float],
) -> tuple[dict[str, Any], bool]:
    tests = {
        "save": ({"saves": 1.0}, +1),
        "goal_conceded": ({"goals_conceded": 1.0}, -1),
        "successful_pass": ({"passes_total": 1.0, "passes_completed": 1.0}, +1),
        "successful_long_ball": ({"long_balls_total": 1.0, "long_balls_completed": 1.0}, +1),
    }
    base_comp = components(sample, ref)
    base = score(sample, base_comp, shot_weight, calibration)
    out: dict[str, Any] = {}
    overall = True
    for name, (incs, expected) in tests.items():
        alt = perturb(sample, incs)
        alt_comp = components(alt, ref)
        alt_score = score(alt, alt_comp, shot_weight, calibration)
        delta = alt_score - base
        if expected > 0:
            nonwrong = float((delta >= -TOL).mean())
            strict = float((delta > TOL).mean())
            median_ok = float(delta.median()) > TOL
        else:
            nonwrong = float((delta <= TOL).mean())
            strict = float((delta < -TOL).mean())
            median_ok = float(delta.median()) < -TOL
        passed = bool(nonwrong >= 0.999 and strict >= 0.95 and median_ok)
        overall = overall and passed
        out[name] = {
            "median_delta": float(delta.median()),
            "nonwrong_share": nonwrong,
            "strict_share": strict,
            "pass": passed,
        }
    return out, overall


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)
    input_dir = discover_input_dir(args.input_dir)
    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    local = gk.load_local(db)
    if local.empty or local["match_date"].isna().any():
        raise RuntimeError("Local goalkeeper dates unavailable")
    cutoff = pd.Timestamp(local["match_date"].min())
    reference, _ = gk.load_reference(input_dir, cutoff, float(args.min_reference_minutes))
    train, valid, test, split_info = split_dates(reference)

    ref = fit_reference(train, int(args.max_pca_fit_rows))
    comp_train = components(train, ref)
    comp_valid = components(valid, ref)
    comp_test = components(test, ref)

    leaderboard: list[dict[str, Any]] = []
    calibrations: dict[float, dict[str, float]] = {}
    valid_scores: dict[float, pd.Series] = {}
    for w in WEIGHT_GRID:
        cal = fit_calibration(train, comp_train, w)
        calibrations[w] = cal
        pred = score(valid, comp_valid, w, cal)
        valid_scores[w] = pred
        m = metrics(valid["opta_points_target"], pred)
        leaderboard.append({"shot_weight": w, "distribution_weight": 1.0 - w, **m})

    leaderboard.sort(key=lambda x: (float(x["mae"]), -float(x["spearman"] or -999)))
    selected = float(leaderboard[0]["shot_weight"])
    selected_cal = calibrations[selected]
    test_pred = score(test, comp_test, selected, selected_cal)
    test_metrics = metrics(test["opta_points_target"], test_pred)

    # Local robustness around the selected interpretable weight.
    neighbor_weights = sorted({
        max(0.50, min(0.95, selected - 0.05)),
        selected,
        max(0.50, min(0.95, selected + 0.05)),
    })
    local_comp = components(local, ref)
    local_base = score(local, local_comp, selected, selected_cal)
    stability: dict[str, Any] = {}
    rho_values: list[float] = []
    top_values: list[float] = []
    for w in neighbor_weights:
        cal = fit_calibration(train, comp_train, w)
        alt = score(local, local_comp, w, cal)
        rho = spearman(local_base, alt)
        overlap = top_overlap(local_base, alt)
        if rho is not None:
            rho_values.append(float(rho))
        top_values.append(float(overlap))
        stability[str(w)] = {"spearman": rho, "top10_overlap": overlap}
    stability_gate = bool(
        rho_values and top_values
        and min(rho_values) >= 0.95
        and min(top_values) >= 0.80
    )

    sample = test.sample(min(int(args.sample_rows), len(test)), random_state=18)
    mono, mono_gate = monotonicity(sample, ref, selected, selected_cal)

    overall_gate = bool(mono_gate and stability_gate and test_metrics["spearman"] is not None)
    result = {
        "cutoff_before_local": str(cutoff.date()),
        "split": split_info,
        "rows": {"train": int(len(train)), "valid": int(len(valid)), "test": int(len(test))},
        "weight_grid": WEIGHT_GRID,
        "validation_leaderboard": leaderboard,
        "selected_shot_weight": selected,
        "selected_distribution_weight": 1.0 - selected,
        "selected_calibration": selected_cal,
        "test_metrics_vs_opta_points": test_metrics,
        "monotonicity": mono,
        "monotonicity_gate": mono_gate,
        "local_weight_sensitivity": stability,
        "local_weight_sensitivity_gate": stability_gate,
        "overall_gate": overall_gate,
        "interpretation": "Opta Points selects among pre-declared interpretable goalkeeper weight schemes; it is an external benchmark, not ground truth.",
        "production_status": "EXPERIMENT_ONLY",
    }
    artifact = out_dir / "goalkeeper_final_gate.json"
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("PERF-18 GOALKEEPER FINAL GATE")
    print(f"reference_cutoff_before={cutoff.date()}")
    print(f"rows=train:{len(train)} valid:{len(valid)} test:{len(test)} split={split_info}")
    print("validation_leaderboard=")
    for row in leaderboard:
        print(
            f" shot={row['shot_weight']:.2f} dist={row['distribution_weight']:.2f} "
            f"mae={row['mae']:.4f} spearman={row['spearman']:.4f}"
        )
    print(f"selected_weights=shot:{selected:.2f} distribution:{1.0-selected:.2f}")
    print("test_vs_opta_points=" + str(test_metrics))
    print("monotonicity=")
    for name, x in mono.items():
        print(
            f" {name}: median_delta={x['median_delta']:+.4f} "
            f"nonwrong={x['nonwrong_share']:.4f} strict={x['strict_share']:.4f} pass={x['pass']}"
        )
    print(f"monotonicity_gate={'PASS' if mono_gate else 'FAIL'}")
    print("local_weight_sensitivity=" + str(stability))
    print(f"local_weight_sensitivity_gate={'PASS' if stability_gate else 'FAIL'}")
    print(f"GK_FINAL_GATE={'PASS' if overall_gate else 'FAIL'}")
    print(f"artifact={artifact}")
    print("No production rating was changed.")


if __name__ == "__main__":
    main()
