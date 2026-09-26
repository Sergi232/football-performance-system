"""PERF-18 — goalkeeper core-score weight sensitivity.

Goalkeepers remain independent from outfield players.

This experiment does not choose weights by fitting a pseudo-target. Instead it tests
whether a domain-prior statement — shot stopping should dominate goalkeeper rating —
produces stable rankings across a broad plausible weight range.

Core components:
- shot stopping: empirical-Bayes shrunk save rate from the professional GK population;
- distribution: goalkeeper-only PCA score from passing/long-ball execution;
- discipline is deliberately excluded from the core weighting experiment because the
  relevant negative events are sparse; it will be added later as a bounded modifier.

No production rating is changed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from perf18_goalkeeper_reference_v2 import (
    ROOT,
    discover_input_dir,
    fit_distribution_pca,
    load_goalkeepers,
)

DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_gk_sensitivity"
SHOT_WEIGHTS = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
CENTRAL_WEIGHT = 0.75


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-18 goalkeeper weight sensitivity")
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--min-minutes", type=float, default=30.0)
    p.add_argument("--max-fit-rows", type=int, default=200000)
    return p.parse_args()


def robust_z(series: pd.Series) -> tuple[pd.Series, dict[str, float]]:
    s = pd.to_numeric(series, errors="coerce")
    q25 = float(s.quantile(0.25))
    med = float(s.quantile(0.50))
    q75 = float(s.quantile(0.75))
    iqr = q75 - q25
    robust_sd = iqr / 1.349 if iqr > 1e-12 else float(s.std(ddof=0) or 1.0)
    if not np.isfinite(robust_sd) or robust_sd <= 1e-12:
        robust_sd = 1.0
    z = ((s - med) / robust_sd).clip(-3.0, 3.0)
    return z, {"q25": q25, "median": med, "q75": q75, "robust_sd": float(robust_sd)}


def apply_distribution_score(df: pd.DataFrame, model: dict) -> pd.Series:
    cols = list(model["features"])
    z_parts: list[np.ndarray] = []
    for col in cols:
        raw = pd.to_numeric(df[col], errors="coerce").fillna(float(model["medians"][col]))
        scale = float(model["scaler_scale"][col])
        if not np.isfinite(scale) or abs(scale) < 1e-12:
            scale = 1.0
        z_parts.append(((raw - float(model["scaler_mean"][col])) / scale).to_numpy(dtype=float))
    matrix = np.column_stack(z_parts)
    loadings = np.array([float(model["loadings"][c]) for c in cols], dtype=float)
    pc = matrix @ loadings
    s = pd.Series(pc, index=df.index, dtype=float)
    sd = float(s.std(ddof=0))
    if not np.isfinite(sd) or sd <= 1e-12:
        sd = 1.0
    return ((s - float(s.mean())) / sd).clip(-3.0, 3.0)


def rank_corr(a: pd.Series, b: pd.Series) -> float:
    valid = a.notna() & b.notna()
    if int(valid.sum()) < 3:
        return float("nan")
    return float(a[valid].rank(method="average").corr(b[valid].rank(method="average")))


def top_share_overlap(a: pd.Series, b: pd.Series, share: float = 0.10) -> float:
    valid = a.notna() & b.notna()
    aa = a[valid]
    bb = b[valid]
    n = len(aa)
    if n == 0:
        return float("nan")
    k = max(1, int(round(n * share)))
    ia = set(aa.nlargest(k).index.tolist())
    ib = set(bb.nlargest(k).index.tolist())
    return float(len(ia & ib) / k)


def main() -> None:
    args = parse_args()
    input_dir = discover_input_dir(args.input_dir)
    out = args.output_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    df = load_goalkeepers(input_dir, args.min_minutes)
    faced = pd.to_numeric(df["shots_on_target_faced_proxy"], errors="coerce").fillna(0.0)
    observed = faced > 0
    if not observed.any():
        raise RuntimeError("No goalkeeper rows with shot-stopping evidence")

    total_saves = float(pd.to_numeric(df.loc[observed, "saves"], errors="coerce").fillna(0).sum())
    total_faced = float(faced[observed].sum())
    prior_save_rate = total_saves / total_faced
    prior_strength = float(max(1.0, faced[observed].median()))

    df["shrunk_save_rate"] = (
        pd.to_numeric(df["saves"], errors="coerce").fillna(0.0)
        + prior_save_rate * prior_strength
    ) / (faced + prior_strength)

    shot_z, shot_reference = robust_z(df["shrunk_save_rate"])
    distribution_model = fit_distribution_pca(df, args.max_fit_rows)
    distribution_z = apply_distribution_score(df, distribution_model)

    schemes: dict[str, pd.Series] = {}
    summaries: dict[str, dict] = {}
    for w in SHOT_WEIGHTS:
        key = f"shot_{w:.2f}_distribution_{1-w:.2f}"
        score = (w * shot_z + (1.0 - w) * distribution_z).clip(-3.0, 3.0)
        schemes[key] = score
        q = score.quantile([0.01, 0.10, 0.25, 0.50, 0.75, 0.90, 0.99])
        summaries[key] = {
            "shot_weight": float(w),
            "distribution_weight": float(1.0 - w),
            "mean": float(score.mean()),
            "sd": float(score.std(ddof=0)),
            "quantiles": {str(k): float(v) for k, v in q.items()},
            "rank_corr_with_shots_faced": rank_corr(score, faced),
        }

    keys = list(schemes)
    pairwise: list[dict] = []
    min_rho = 1.0
    min_top10 = 1.0
    for i, ka in enumerate(keys):
        for kb in keys[i + 1 :]:
            rho = rank_corr(schemes[ka], schemes[kb])
            overlap = top_share_overlap(schemes[ka], schemes[kb], 0.10)
            if np.isfinite(rho):
                min_rho = min(min_rho, rho)
            if np.isfinite(overlap):
                min_top10 = min(min_top10, overlap)
            pairwise.append({"a": ka, "b": kb, "spearman": rho, "top10_overlap": overlap})

    central_key = f"shot_{CENTRAL_WEIGHT:.2f}_distribution_{1-CENTRAL_WEIGHT:.2f}"
    central = schemes[central_key]
    evidence_groups = pd.cut(
        faced,
        bins=[-0.1, 1.0, 3.0, 6.0, np.inf],
        labels=["0-1", "2-3", "4-6", "7+"],
    )
    evidence_summary = {}
    for group in evidence_groups.cat.categories:
        mask = evidence_groups == group
        if not mask.any():
            continue
        evidence_summary[str(group)] = {
            "rows": int(mask.sum()),
            "score_median": float(central[mask].median()),
            "score_iqr": float(central[mask].quantile(0.75) - central[mask].quantile(0.25)),
            "shrunk_save_rate_median": float(df.loc[mask, "shrunk_save_rate"].median()),
        }

    stable = bool(min_rho >= 0.95 and min_top10 >= 0.80)
    result = {
        "rows": int(len(df)),
        "rows_with_shot_stopping_evidence": int(observed.sum()),
        "prior_save_rate": float(prior_save_rate),
        "prior_strength_shots": float(prior_strength),
        "shot_reference": shot_reference,
        "distribution_model": distribution_model,
        "weight_grid": SHOT_WEIGHTS,
        "central_domain_prior": {
            "shot_weight": CENTRAL_WEIGHT,
            "distribution_weight": 1.0 - CENTRAL_WEIGHT,
            "reason": "shot stopping is the primary goalkeeper function; exact weight is not claimed as proprietary or learned from a hidden target",
        },
        "schemes": summaries,
        "pairwise": pairwise,
        "min_pairwise_spearman": float(min_rho),
        "min_top10_overlap": float(min_top10),
        "stability_gate": {
            "required_min_spearman": 0.95,
            "required_min_top10_overlap": 0.80,
            "pass": stable,
        },
        "central_evidence_summary": evidence_summary,
        "discipline_policy": "excluded from core weighting; later bounded explicit modifier",
        "production_status": "EXPERIMENT_ONLY",
    }

    artifact = out / "goalkeeper_weight_sensitivity.json"
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("PERF-18 GOALKEEPER WEIGHT SENSITIVITY: COMPLETE")
    print(f"rows={len(df)} evidence_rows={int(observed.sum())}")
    print(f"prior_save_rate={prior_save_rate:.4f} prior_strength={prior_strength:.2f}")
    print(f"weight_grid={SHOT_WEIGHTS}")
    print(f"min_pairwise_spearman={min_rho:.4f}")
    print(f"min_top10_overlap={min_top10:.4f}")
    print(f"stability_gate={'PASS' if stable else 'FAIL'}")
    print(f"central_scheme={central_key}")
    print(f"central_rank_corr_with_shots_faced={rank_corr(central, faced):.4f}")
    print("evidence_groups=" + str(evidence_summary))
    print(f"artifact={artifact}")
    print("No production rating was changed.")


if __name__ == "__main__":
    main()
