"""PERF-18 — anchored outfield rating candidate.

Purpose
-------
Fix construct-validity failures found in the previous position-prior experiment.
The final candidate separates:
1) structural performance (per-90 + shrunk efficiency, standardized by role);
2) decisive event anchors with explicit monotonic effects;
3) external Opta Points used only to calibrate the display scale.

Important guardrails
--------------------
- Goalkeepers remain on their separate modelling path.
- Public Opta Points weights are used only for anchors that are explicitly published
  (goal, assist, penalty won, yellow, red).
- Penalty conceded is an FPS hypothesis (-0.40) and is labelled as such.
- goals_conceded is deliberately EXCLUDED from the outfield candidate until reliable
  on-pitch goal context is available.
- Missing aggregate event COUNTS are treated as zero. This is supported by the prior
  Opta Points reconstruction, where COALESCE(count, 0) reproduced the benchmark.
- Ratio features use empirical shrinkage toward the role-specific training prior.
- No production Match Rating is changed.
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
from perf18_position_prior_sensitivity import ROLE_PRIORS, norm_weights

DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_outfield_anchored"

STRUCTURAL_DIMENSIONS: dict[str, dict[str, float]] = {
    "shooting": {
        "shots_on_target_p90": +1.0,
        "shots_total_p90": +1.0,
        "shots_blocked_p90": +1.0,
    },
    "passing_creation": {
        "passes_completed_p90": +1.0,
        "pass_accuracy_shrunk": +1.0,
        "long_balls_completed_p90": +1.0,
        "crosses_completed_p90": +1.0,
    },
    "possession_1v1": {
        "dribbles_won_p90": +1.0,
        "dribble_success_shrunk": +1.0,
        "turnovers_p90": -1.0,
        "dispossessed_p90": -1.0,
    },
    "defending": {
        "tackles_won_p90": +1.0,
        "tackle_success_shrunk": +1.0,
        "interceptions_p90": +1.0,
        "blocked_passes_p90": +1.0,
        "clearances_p90": +1.0,
    },
    "discipline_context": {
        "fouls_received_p90": +1.0,
        "fouls_committed_p90": -1.0,
    },
}
DIMENSION_ORDER = list(STRUCTURAL_DIMENSIONS)

# Published public Opta Points anchors. These are transparent benchmark references,
# not proprietary Opta Player Rating weights.
PUBLIC_ANCHORS = {
    "goals": +1.00,
    "assists": +0.60,
    "penalties_won": +0.40,
    "yellow_cards": -0.20,
    "red_cards": -0.50,
}
# Not part of the public Opta Points formula. Kept explicit and separately labelled.
FPS_HYPOTHESIS_ANCHORS = {
    "penalties_conceded": -0.40,
}

COUNT_FEATURES = {
    "passes_total", "passes_completed", "long_balls_total", "long_balls_completed",
    "crosses_total", "crosses_completed", "dribbles_total", "dribbles_won",
    "turnovers", "dispossessed", "shots_total", "shots_on_target", "shots_blocked",
    "goals", "tackles_total", "tackles_won", "interceptions", "blocked_passes",
    "clearances", "fouls_committed", "fouls_received", "yellow_cards", "red_cards",
    "penalties_conceded", "penalties_won", "assists",
}
PER90_BASE = {
    "shots_on_target", "shots_total", "shots_blocked", "passes_completed",
    "long_balls_completed", "crosses_completed", "dribbles_won", "turnovers",
    "dispossessed", "tackles_won", "interceptions", "blocked_passes", "clearances",
    "fouls_received", "fouls_committed",
}
RATIO_SPECS = {
    "pass_accuracy_shrunk": ("passes_completed", "passes_total"),
    "dribble_success_shrunk": ("dribbles_won", "dribbles_total"),
    "tackle_success_shrunk": ("tackles_won", "tackles_total"),
}

EVENT_TESTS: dict[str, dict[str, Any]] = {
    "goal": {"expected": +1, "increments": {"goals": 1.0}, "decisive": True},
    "assist": {"expected": +1, "increments": {"assists": 1.0}, "decisive": True},
    "penalty_won": {"expected": +1, "increments": {"penalties_won": 1.0}, "decisive": True},
    "yellow_card": {"expected": -1, "increments": {"yellow_cards": 1.0}, "decisive": True},
    "red_card": {"expected": -1, "increments": {"red_cards": 1.0}, "decisive": True},
    "penalty_conceded": {"expected": -1, "increments": {"penalties_conceded": 1.0}, "decisive": True},
    "turnover": {"expected": -1, "increments": {"turnovers": 1.0}, "decisive": False},
    "dispossessed": {"expected": -1, "increments": {"dispossessed": 1.0}, "decisive": False},
    "interception": {"expected": +1, "increments": {"interceptions": 1.0}, "decisive": False},
    "tackle_won": {"expected": +1, "increments": {"tackles_won": 1.0, "tackles_total": 1.0}, "decisive": False},
    "dribble_won": {"expected": +1, "increments": {"dribbles_won": 1.0, "dribbles_total": 1.0}, "decisive": False},
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-18 anchored outfield candidate")
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--min-minutes", type=float, default=30.0)
    p.add_argument("--sample-per-role", type=int, default=10000)
    return p.parse_args()


def zero_counts(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for c in COUNT_FEATURES:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)
    out["minutes_played"] = pd.to_numeric(out["minutes_played"], errors="coerce")
    return out


def ratio_prior(train: pd.DataFrame, success: str, attempts: str) -> dict[str, float]:
    s = pd.to_numeric(train[success], errors="coerce").fillna(0.0)
    a = pd.to_numeric(train[attempts], errors="coerce").fillna(0.0)
    total_a = float(a.sum())
    rate = float(s.sum() / total_a) if total_a > 0 else 0.5
    positive = a[a > 0]
    strength = float(max(1.0, positive.median())) if len(positive) else 1.0
    return {"rate": rate, "strength": strength}


def add_derived(frame: pd.DataFrame, ratio_priors: dict[str, dict[str, float]]) -> pd.DataFrame:
    out = zero_counts(frame)
    factor = 90.0 / out["minutes_played"].where(out["minutes_played"] > 0)
    for c in PER90_BASE:
        out[f"{c}_p90"] = out[c] * factor
    for name, (success, attempts) in RATIO_SPECS.items():
        prior = ratio_priors[name]
        s = out[success]
        a = out[attempts]
        out[name] = (s + prior["rate"] * prior["strength"]) / (a + prior["strength"])
    return out


def fit_role_model(train: pd.DataFrame, role: str) -> dict[str, Any]:
    tr = zero_counts(train)
    ratio_priors = {
        name: ratio_prior(tr, success, attempts)
        for name, (success, attempts) in RATIO_SPECS.items()
    }
    derived = add_derived(tr, ratio_priors)
    refs: dict[str, Any] = {}
    for dim, mapping in STRUCTURAL_DIMENSIONS.items():
        refs[dim] = {"features": {}}
        for feature, sign in mapping.items():
            s = pd.to_numeric(derived[feature], errors="coerce")
            mean = float(s.mean())
            sd = float(s.std(ddof=0))
            if not np.isfinite(sd) or sd < 1e-9:
                sd = 1.0
            refs[dim]["features"][feature] = {
                "sign": float(sign), "mean": mean, "sd": sd,
            }
    return {
        "role": role,
        "ratio_priors": ratio_priors,
        "dimension_refs": refs,
        "weights": norm_weights(ROLE_PRIORS[role]),
    }


def structural_dimensions(frame: pd.DataFrame, model: dict[str, Any]) -> pd.DataFrame:
    d = add_derived(frame, model["ratio_priors"])
    out = pd.DataFrame(index=d.index)
    for dim in DIMENSION_ORDER:
        parts: list[pd.Series] = []
        for feature, meta in model["dimension_refs"][dim]["features"].items():
            raw = pd.to_numeric(d[feature], errors="coerce")
            z = ((raw - float(meta["mean"])) / float(meta["sd"])) * float(meta["sign"])
            parts.append(z.clip(-3.0, 3.0))
        out[dim] = pd.concat(parts, axis=1).mean(axis=1) if parts else 0.0
    return out


def structural_core(frame: pd.DataFrame, model: dict[str, Any]) -> pd.Series:
    dims = structural_dimensions(frame, model)
    score = pd.Series(0.0, index=frame.index, dtype=float)
    for dim, weight in model["weights"].items():
        score = score + pd.to_numeric(dims[dim], errors="coerce").fillna(0.0) * float(weight)
    return score


def public_anchor(frame: pd.DataFrame) -> pd.Series:
    f = zero_counts(frame)
    out = pd.Series(0.0, index=f.index, dtype=float)
    for feature, weight in PUBLIC_ANCHORS.items():
        out = out + f[feature] * float(weight)
    return out


def fps_hypothesis_anchor(frame: pd.DataFrame) -> pd.Series:
    f = zero_counts(frame)
    out = pd.Series(0.0, index=f.index, dtype=float)
    for feature, weight in FPS_HYPOTHESIS_ANCHORS.items():
        out = out + f[feature] * float(weight)
    return out


def fit_calibration(train: pd.DataFrame, model: dict[str, Any]) -> tuple[float, float]:
    x = structural_core(train, model)
    # Remove public decisive-event contribution before calibrating the structural baseline.
    y = pd.to_numeric(train["opta_points_target"], errors="coerce") - public_anchor(train)
    valid = x.notna() & y.notna()
    xx = x[valid].to_numpy(dtype=float)
    yy = y[valid].to_numpy(dtype=float)
    slope, intercept = np.polyfit(xx, yy, 1)
    if not np.isfinite(slope) or slope <= 0:
        raise RuntimeError(f"Invalid structural calibration slope: {slope}")
    return float(intercept), float(slope)


def rating(frame: pd.DataFrame, model: dict[str, Any]) -> pd.Series:
    base = float(model["calibration"]["intercept"]) + float(model["calibration"]["slope"]) * structural_core(frame, model)
    score = base + public_anchor(frame) + fps_hypothesis_anchor(frame)
    return score.clip(3.0, 10.0)


def spearman(a: pd.Series, b: pd.Series) -> float | None:
    aa = pd.to_numeric(a, errors="coerce")
    bb = pd.to_numeric(b, errors="coerce")
    valid = aa.notna() & bb.notna()
    if int(valid.sum()) < 3:
        return None
    return float(aa[valid].rank(method="average").corr(bb[valid].rank(method="average")))


def metric(y: pd.Series, p: pd.Series) -> dict[str, Any]:
    a = pd.to_numeric(y, errors="coerce")
    b = pd.to_numeric(p, errors="coerce")
    valid = a.notna() & b.notna()
    a, b = a[valid], b[valid]
    if a.empty:
        return {"n": 0}
    e = b - a
    return {
        "n": int(len(a)),
        "mae": float(e.abs().mean()),
        "rmse": float(np.sqrt(np.mean(np.square(e)))),
        "pearson": float(a.corr(b)) if len(a) >= 3 else None,
        "spearman": spearman(a, b),
        "bias": float(e.mean()),
    }


def minute_summary(frame: pd.DataFrame, score: pd.Series) -> dict[str, Any]:
    return {
        "candidate_spearman": spearman(frame["minutes_played"], score),
        "opta_points_spearman": spearman(frame["minutes_played"], frame["opta_points_target"]),
    }


def monotonicity(sample: pd.DataFrame, model: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    base = rating(sample, model)
    result: dict[str, Any] = {}
    overall = True
    for name, spec in EVENT_TESTS.items():
        alt = sample.copy()
        for feature, inc in spec["increments"].items():
            # Preserve zero semantics: source count null means no observed event.
            alt[feature] = pd.to_numeric(alt[feature], errors="coerce").fillna(0.0) + float(inc)
        changed = rating(alt, model)
        delta = changed - base
        expected = int(spec["expected"])
        if expected > 0:
            nonwrong = delta >= -1e-12
            nonsat = base < 9.999999
            strict = delta[nonsat] > 1e-12
        else:
            nonwrong = delta <= 1e-12
            nonsat = base > 3.000001
            strict = delta[nonsat] < -1e-12
        nonwrong_share = float(nonwrong.mean())
        strict_share = float(strict.mean()) if len(strict) else 1.0
        decisive = bool(spec["decisive"])
        passed = nonwrong_share >= 0.999 and (strict_share >= (0.999 if decisive else 0.95))
        overall = overall and passed
        result[name] = {
            "expected": "UP" if expected > 0 else "DOWN",
            "decisive_anchor": decisive,
            "median_delta": float(delta.median()),
            "mean_delta": float(delta.mean()),
            "nonwrong_share": nonwrong_share,
            "strict_nonsaturated_share": strict_share,
            "pass": passed,
        }
    return result, overall


def main() -> None:
    args = parse_args()
    input_dir = discover_input_dir(args.input_dir)
    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    frame = build_frame(input_dir, args.min_minutes)
    train, valid, test, split_info = split_dates(frame)

    print("PERF-18 ANCHORED OUTFIELD CANDIDATE")
    print(f"rows={len(frame)} train={len(train)} valid={len(valid)} test={len(test)} split={split_info}")
    print("goals_conceded=EXCLUDED until reliable on-pitch context is available")
    print("public_anchors=" + str(PUBLIC_ANCHORS))
    print("fps_hypothesis_anchors=" + str(FPS_HYPOTHESIS_ANCHORS))

    result: dict[str, Any] = {
        "method": "role_structural_per90_shrunk_efficiency_plus_decisive_anchors",
        "split": split_info,
        "public_anchors": PUBLIC_ANCHORS,
        "fps_hypothesis_anchors": FPS_HYPOTHESIS_ANCHORS,
        "goals_conceded_policy": "excluded_from_outfield_until_on_pitch_context_is_validated",
        "roles": {},
        "production_status": "EXPERIMENT_ONLY",
    }

    pooled_y: list[pd.Series] = []
    pooled_p: list[pd.Series] = []
    overall_gate = True

    for role in ROLE_ORDER:
        tr = train.loc[train["position_group"] == role].copy()
        va = valid.loc[valid["position_group"] == role].copy()
        te = test.loc[test["position_group"] == role].copy()
        if min(len(tr), len(va), len(te)) < 200:
            continue

        model = fit_role_model(tr, role)
        intercept, slope = fit_calibration(tr, model)
        model["calibration"] = {"intercept": intercept, "slope": slope}

        va_rating = rating(va, model)
        te_rating = rating(te, model)
        if len(te) > int(args.sample_per_role):
            sample = te.sample(int(args.sample_per_role), random_state=18)
        else:
            sample = te.copy()
        events, mono_pass = monotonicity(sample, model)
        minutes = minute_summary(te, te_rating)

        result["roles"][role] = {
            "rows": {"train": int(len(tr)), "valid": int(len(va)), "test": int(len(te))},
            "weights": model["weights"],
            "ratio_priors": model["ratio_priors"],
            "calibration": model["calibration"],
            "valid_vs_opta_points": metric(va["opta_points_target"], va_rating),
            "test_vs_opta_points": metric(te["opta_points_target"], te_rating),
            "minutes": minutes,
            "monotonicity": events,
            "monotonicity_gate": mono_pass,
            "rating_quantiles_test": {str(k): float(v) for k, v in te_rating.quantile([0.01,0.10,0.50,0.90,0.99]).items()},
        }
        overall_gate = overall_gate and mono_pass
        pooled_y.append(te["opta_points_target"])
        pooled_p.append(te_rating)

        print(f"\nPOSITION={role}")
        print(f" calibration=intercept:{intercept:.4f} slope:{slope:.4f}")
        print(" minutes=" + str(minutes))
        print(f" monotonicity_gate={'PASS' if mono_pass else 'FAIL'}")
        for e in ["goal", "assist", "penalty_won", "red_card", "penalty_conceded", "turnover", "interception"]:
            x = events[e]
            print(
                f"  {e}: median_delta={x['median_delta']:+.4f} "
                f"nonwrong={x['nonwrong_share']:.4f} strict_nonsat={x['strict_nonsaturated_share']:.4f} "
                f"pass={x['pass']}"
            )

    if pooled_y:
        y = pd.concat(pooled_y).sort_index()
        p = pd.concat(pooled_p).reindex(y.index)
        result["overall_test_vs_opta_points"] = metric(y, p)
    else:
        result["overall_test_vs_opta_points"] = None
    result["overall_construct_gate"] = bool(overall_gate and result["roles"])

    artifact = out_dir / "outfield_anchored_candidate.json"
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nPERF-18 ANCHORED OUTFIELD CANDIDATE: COMPLETE")
    print("overall_test_vs_opta_points=" + str(result["overall_test_vs_opta_points"]))
    print(f"overall_construct_gate={'PASS' if result['overall_construct_gate'] else 'FAIL'}")
    print(f"artifact={artifact}")
    print("No production rating was changed.")


if __name__ == "__main__":
    main()
