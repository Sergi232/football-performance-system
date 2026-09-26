"""PERF-14: position-specific experimental performance score.

Builds on PERF-13's selected AVAILABLE_3PLUS + role-aware approach, but moves the
comparison population to broad tactical position groups and applies transparent
position-specific relevance priors. This is experimental only.

No DB mutation, production threshold, product ranking or recommendation is made.
Goalkeeper scoring remains on its separate validated path from PERF-06/07/09.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

import performance_score_policy_experiment_v2 as compat

perf = compat.perf
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
PRIORS_FILE = Path(__file__).with_name("performance_position_weight_priors.json")
OUTPUT_DIR = Path(__file__).with_name("output")
VERSION = "performance_position_score_experiment_0.1.0"
MIN_DIMENSIONS = 3
DIMENSIONS = [
    "attacking_threat",
    "creation_progression",
    "defensive_contribution",
    "finishing",
    "discipline",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-14 position-specific score experiment")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--no-write", action="store_true")
    return p.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def norm_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def classify_position(primary_role: object, source_position: object) -> tuple[str, str]:
    """Map detailed role text first, then fall back to coarse source position."""
    role = norm_text(primary_role)
    source = norm_text(source_position)
    text = f"{role} | {source}".strip()

    if any(k in text for k in ["goalkeeper", "goal keeper", "keeper", "porter", "portero"]):
        return "GK", "detailed_or_source"

    # Wide defenders before generic/central defender matching.
    if any(k in text for k in [
        "full back", "fullback", "wing back", "wingback", "left back", "right back",
        "lateral", "carrilero", "defender | left", "defender | right",
    ]):
        return "FB_WB", "detailed_role"

    if any(k in text for k in [
        "centre back", "center back", "central defender", "central back", "centre defender",
        "defender | centre", "defender | center", "defender | central",
    ]):
        return "CB", "detailed_role"

    # Advanced/wide midfield before generic midfield matching.
    if any(k in text for k in [
        "attacking midfield", "attacking midfielder", "winger", "left wing", "right wing",
        "wide midfield", "left midfield", "right midfield", "midfielder | left",
        "midfielder | right", "midfielder | attacking",
    ]):
        return "AM_W", "detailed_role"

    if any(k in text for k in [
        "defensive midfield", "defensive midfielder", "central midfield", "central midfielder",
        "centre midfield", "holding midfield", "midfielder | defensive", "midfielder | central",
        "midfielder | centre",
    ]):
        return "DM_CM", "detailed_role"

    if any(k in text for k in ["striker", "centre forward", "center forward", "forward", "attacker"]):
        return "ST", "detailed_role"

    # Coarse source-position fallback.
    if source == "defender" or "defender" in source:
        return "CB", "coarse_source_fallback"
    if source == "midfielder" or "midfield" in source:
        return "DM_CM", "coarse_source_fallback"
    if source in {"attacker", "forward"} or "attacker" in source or "forward" in source:
        return "ST", "coarse_source_fallback"

    if "defender" in role:
        return "CB", "coarse_role_fallback"
    if "midfield" in role:
        return "DM_CM", "coarse_role_fallback"
    if "attacker" in role or "forward" in role:
        return "ST", "coarse_role_fallback"

    return "OTHER_OUTFIELD", "unmapped_fallback"


def weighted_row_score(row: pd.Series, levels: dict[str, float], dim_cols: dict[str, str]) -> tuple[float, float, int, list[str]]:
    available = [d for d, c in dim_cols.items() if pd.notna(row[c])]
    if not available:
        return np.nan, 0.0, 0, []
    intended = float(sum(levels[d] for d in dim_cols))
    observed_weight = float(sum(levels[d] for d in available))
    score = sum(float(row[dim_cols[d]]) * float(levels[d]) for d in available) / observed_weight
    confidence = 100.0 * observed_weight / intended if intended > 0 else 0.0
    return float(score), float(confidence), len(available), available


def score_with_levels(frame: pd.DataFrame, levels: dict[str, float], dim_cols: dict[str, str]) -> pd.Series:
    out = pd.Series(np.nan, index=frame.index, dtype=float)
    for idx, row in frame.iterrows():
        score, _conf, _n, _available = weighted_row_score(row, levels, dim_cols)
        out.loc[idx] = score
    return out


def describe(values: pd.Series) -> dict:
    x = pd.to_numeric(values, errors="coerce").dropna()
    if x.empty:
        return {"rows": 0, "min": None, "median": None, "mean": None, "max": None, "std": None}
    return {
        "rows": int(len(x)),
        "min": float(x.min()),
        "median": float(x.median()),
        "mean": float(x.mean()),
        "max": float(x.max()),
        "std": float(x.std(ddof=0)),
    }


def build_experiment(db_path: Path) -> tuple[dict, pd.DataFrame]:
    priors = load_json(PRIORS_FILE)
    base, direction_by_feature, primary_dimension, used_features, dimensions = perf.build_base_frame(db_path)

    # Preserve provider label, then create the tactical comparison population.
    base["raw_source_position"] = base["source_position"]
    mapped = base.apply(lambda r: classify_position(r.get("primary_role"), r.get("raw_source_position")), axis=1)
    base["position_group"] = [x[0] for x in mapped]
    base["position_mapping_status"] = [x[1] for x in mapped]

    # True position-aware normalization: feature percentiles are estimated within
    # the tactical position group, with PERF-13 global fallback when not estimable.
    norm_base = base.copy()
    norm_base["source_position"] = norm_base["position_group"]
    scored, norm_meta = perf.add_variant_scores(
        norm_base,
        "ROLE_AWARE",
        direction_by_feature,
        primary_dimension,
        used_features,
        dimensions,
    )
    scored["source_position"] = scored["raw_source_position"]

    dim_cols = {d: f"role_aware__dimension__{d}" for d in DIMENSIONS}
    coverage_col = "role_aware__dimension_coverage_count"
    baseline_col = "role_aware__score__AVAILABLE_3PLUS"

    position_score = pd.Series(np.nan, index=scored.index, dtype=float)
    evidence_confidence = pd.Series(np.nan, index=scored.index, dtype=float)
    score_status = pd.Series("", index=scored.index, dtype="object")
    available_weight_pct = pd.Series(np.nan, index=scored.index, dtype=float)

    for idx, row in scored.iterrows():
        group = str(row["position_group"])
        cfg = priors["position_groups"].get(group, priors["position_groups"]["OTHER_OUTFIELD"])
        levels = {d: float(cfg["relevance_levels"][d]) for d in DIMENSIONS}
        required = list(cfg.get("required_dimensions", []))
        score, conf, n_dims, available = weighted_row_score(row, levels, dim_cols)
        available_weight_pct.loc[idx] = conf

        if n_dims < MIN_DIMENSIONS:
            score_status.loc[idx] = "INELIGIBLE_LT3_DIMENSIONS"
            continue
        missing_required = [d for d in required if d not in available]
        if missing_required:
            score_status.loc[idx] = "INELIGIBLE_MISSING_CORE_DIMENSION"
            continue

        position_score.loc[idx] = score
        evidence_confidence.loc[idx] = conf
        score_status.loc[idx] = (
            "FALLBACK_OTHER_OUTFIELD_EXPERIMENTAL"
            if group == "OTHER_OUTFIELD"
            else "ELIGIBLE_POSITION_SCORE"
        )

    scored["performance_score_position_experimental"] = position_score
    scored["score_evidence_confidence"] = evidence_confidence
    scored["available_intended_weight_pct"] = available_weight_pct
    scored["score_status"] = score_status
    scored["score_version"] = VERSION
    scored["unweighted_role_aware_3plus"] = scored[baseline_col]
    scored["delta_vs_unweighted_3plus"] = (
        scored["performance_score_position_experimental"] - scored["unweighted_role_aware_3plus"]
    )

    # Mapping audit avoids pandas null-category behavior by explicit sentinels.
    mapping_frame = scored[["primary_role", "raw_source_position", "position_group", "position_mapping_status"]].copy()
    mapping_frame = mapping_frame.fillna("__NULL__")
    mapping_audit = (
        mapping_frame.groupby(
            ["primary_role", "raw_source_position", "position_group", "position_mapping_status"],
            sort=False,
        )
        .size()
        .reset_index(name="rows")
        .sort_values("rows", ascending=False)
        .to_dict(orient="records")
    )

    by_group = []
    sensitivity = []
    perturbation = []

    for group, cfg in priors["position_groups"].items():
        g = scored[scored["position_group"] == group].copy()
        if g.empty:
            by_group.append({
                "position_group": group,
                "rows": 0,
                "eligible_rows": 0,
                "coverage_rate": None,
                "score": describe(pd.Series(dtype=float)),
                "confidence": describe(pd.Series(dtype=float)),
                "spearman_vs_unweighted": None,
                "mean_abs_delta_vs_unweighted": None,
            })
            continue

        eligible = g["performance_score_position_experimental"].notna()
        pair = g.loc[eligible, ["performance_score_position_experimental", "unweighted_role_aware_3plus"]].dropna()
        spearman = perf.safe_spearman(pair.iloc[:, 0], pair.iloc[:, 1]) if len(pair) else None
        mad = (
            float((pair.iloc[:, 0] - pair.iloc[:, 1]).abs().mean())
            if len(pair)
            else None
        )
        by_group.append({
            "position_group": group,
            "rows": int(len(g)),
            "eligible_rows": int(eligible.sum()),
            "coverage_rate": float(eligible.mean()),
            "score": describe(g["performance_score_position_experimental"]),
            "confidence": describe(g["score_evidence_confidence"]),
            "spearman_vs_unweighted": spearman,
            "mean_abs_delta_vs_unweighted": mad,
        })

        levels = {d: float(cfg["relevance_levels"][d]) for d in DIMENSIONS}
        original = g["performance_score_position_experimental"]

        # Leave-one-dimension-out sensitivity for eligible positional scores.
        for removed in DIMENSIONS:
            remaining = {d: c for d, c in dim_cols.items() if d != removed}
            reduced = score_with_levels(g, {d: levels[d] for d in remaining}, remaining)
            common = original.notna() & reduced.notna()
            delta = (original[common] - reduced[common]).abs()
            sensitivity.append({
                "position_group": group,
                "removed_dimension": removed,
                "rows": int(common.sum()),
                "mean_abs_delta": float(delta.mean()) if len(delta) else None,
                "p95_abs_delta": float(delta.quantile(0.95)) if len(delta) else None,
                "spearman": perf.safe_spearman(original[common], reduced[common]),
            })

        # Perturb each ordinal relevance level by +/-1 (bounded 1..5).
        for dim in DIMENSIONS:
            for shift in (-1, 1):
                alt = dict(levels)
                alt[dim] = float(max(1, min(5, int(levels[dim]) + shift)))
                if alt[dim] == levels[dim]:
                    continue
                alt_score = score_with_levels(g, alt, dim_cols)
                common = original.notna() & alt_score.notna()
                delta = (original[common] - alt_score[common]).abs()
                perturbation.append({
                    "position_group": group,
                    "dimension": dim,
                    "shift": shift,
                    "base_level": levels[dim],
                    "alt_level": alt[dim],
                    "rows": int(common.sum()),
                    "mean_abs_delta": float(delta.mean()) if len(delta) else None,
                    "p95_abs_delta": float(delta.quantile(0.95)) if len(delta) else None,
                    "spearman": perf.safe_spearman(original[common], alt_score[common]),
                })

    eligible_all = scored["performance_score_position_experimental"].notna()
    product_candidate = eligible_all & (scored["position_group"] != "OTHER_OUTFIELD")
    pair_all = scored.loc[
        product_candidate,
        ["performance_score_position_experimental", "unweighted_role_aware_3plus"],
    ].dropna()

    unmapped = scored["position_group"] == "OTHER_OUTFIELD"
    result = {
        "version": VERSION,
        "status": "EXPERIMENTAL_NO_DEPLOY",
        "method": {
            "normalization": "feature percentiles within broad tactical position group with global fallback if group-feature is not estimable",
            "aggregation": "weighted mean of available dimensions using normalized ordinal relevance priors",
            "eligibility": f">={MIN_DIMENSIONS} dimensions plus required core dimension(s) for mapped position group",
            "confidence": "percentage of intended positional relevance weight actually observed; not calibrated probability",
        },
        "summary": {
            "outfield_rows": int(len(scored)),
            "eligible_rows_all_including_fallback": int(eligible_all.sum()),
            "eligible_rows_mapped_positions": int(product_candidate.sum()),
            "coverage_rate_mapped_positions": float(product_candidate.mean()) if len(scored) else None,
            "unmapped_rows": int(unmapped.sum()),
            "unmapped_rate": float(unmapped.mean()) if len(scored) else None,
            "score_distribution": describe(scored.loc[product_candidate, "performance_score_position_experimental"]),
            "confidence_distribution": describe(scored.loc[product_candidate, "score_evidence_confidence"]),
            "spearman_vs_unweighted_3plus": (
                perf.safe_spearman(pair_all.iloc[:, 0], pair_all.iloc[:, 1]) if len(pair_all) else None
            ),
            "mean_abs_delta_vs_unweighted_3plus": (
                float((pair_all.iloc[:, 0] - pair_all.iloc[:, 1]).abs().mean()) if len(pair_all) else None
            ),
            "conclusion": "POSITION_SPECIFIC_SCORE_READY_FOR_SENSITIVITY_GATE",
        },
        "position_group_summary": by_group,
        "role_mapping_audit": mapping_audit,
        "leave_one_dimension_out": sensitivity,
        "weight_level_perturbation": perturbation,
        "normalization_diagnostics": norm_meta.get("normalization", {}),
        "guardrails": priors.get("guardrails", []) + [
            "Position group is derived from primary_role first and source_position only as fallback.",
            "OTHER_OUTFIELD scores are diagnostic fallback and are excluded from mapped-position product coverage.",
            "Goalkeepers remain on their separate validated score path.",
            "No database or FEATURE-01 mutation occurs.",
            "No score threshold, ranking label or recommendation is approved.",
        ],
    }

    export_cols = [
        "match_id", "player_id", "minutes_played", "primary_role", "raw_source_position",
        "position_group", "position_mapping_status", coverage_col,
        *dim_cols.values(),
        "unweighted_role_aware_3plus", "performance_score_position_experimental",
        "score_evidence_confidence", "available_intended_weight_pct", "score_status",
        "delta_vs_unweighted_3plus", "score_version",
    ]
    return result, scored[export_cols].copy()


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# PERF-14 — Position-specific performance score experiment",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
        f"- outfield_rows: {s['outfield_rows']}",
        f"- eligible_rows_mapped_positions: {s['eligible_rows_mapped_positions']}",
        f"- coverage_rate_mapped_positions: {s['coverage_rate_mapped_positions']:.3f}",
        f"- unmapped_rows: {s['unmapped_rows']}",
        f"- spearman_vs_unweighted_3plus: {s['spearman_vs_unweighted_3plus']}",
        f"- mean_abs_delta_vs_unweighted_3plus: {s['mean_abs_delta_vs_unweighted_3plus']}",
        f"- conclusion: `{s['conclusion']}`",
        "",
        "## Position groups",
    ]
    for row in result["position_group_summary"]:
        lines.append(
            f"- `{row['position_group']}`: rows={row['rows']} eligible={row['eligible_rows']} "
            f"coverage={row['coverage_rate']} median={row['score']['median']} "
            f"confidence_median={row['confidence']['median']}"
        )
    lines += ["", "## Guardrails"]
    lines.extend(f"- {x}" for x in result["guardrails"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    result, export = build_experiment(db_path)
    s = result["summary"]
    print("PERF-14 POSITION SCORE EXPERIMENT: COMPLETE")
    print(f"version={VERSION}")
    print(f"db={db_path}")
    print(
        f"outfield_rows={s['outfield_rows']} eligible_mapped={s['eligible_rows_mapped_positions']} "
        f"coverage={s['coverage_rate_mapped_positions']:.4f} unmapped={s['unmapped_rows']}"
    )
    for row in result["position_group_summary"]:
        print(
            f"{row['position_group']}: rows={row['rows']} eligible={row['eligible_rows']} "
            f"coverage={row['coverage_rate']} median={row['score']['median']} "
            f"confidence_median={row['confidence']['median']}"
        )
    print(
        f"vs_unweighted: spearman={s['spearman_vs_unweighted_3plus']} "
        f"mean_abs_delta={s['mean_abs_delta_vs_unweighted_3plus']}"
    )
    print(f"conclusion={s['conclusion']}")

    if args.no_write:
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "performance_position_score_experiment.json"
    csv_path = OUTPUT_DIR / "performance_position_score_experiment.csv"
    md_path = OUTPUT_DIR / "performance_position_score_experiment.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    export.to_csv(csv_path, index=False)
    md_path.write_text(render_markdown(result), encoding="utf-8")
    print(f"json={json_path}")
    print(f"csv={csv_path}")
    print(f"md={md_path}")


if __name__ == "__main__":
    main()
