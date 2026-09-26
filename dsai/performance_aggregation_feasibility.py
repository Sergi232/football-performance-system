"""PERF-08: audit normalization/aggregation feasibility for the performance score.

No score or approved weight is created here. The audit checks whether the signed
outfield core and validated goalkeeper save_rate have enough empirical support
for a transparent experimental baseline.
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
FEATURE_CATALOG = ROOT / "features" / "catalog.json"
DIMENSION_MAP = Path(__file__).with_name("performance_dimension_map.json")
DIRECTION_FILE = Path(__file__).with_name("performance_direction_evidence.json")
ROLE_SPECIFIC_FILE = Path(__file__).with_name("performance_role_specific_features.json")
OUTPUT_DIR = Path(__file__).with_name("output")
VERSION = "performance_aggregation_feasibility_0.1.0"
SIGNED = {"POSITIVE_SUPPORTED", "NEGATIVE_SUPPORTED"}
GK_POSITION = "Goalkeeper"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit performance-score aggregation feasibility")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--no-write", action="store_true")
    return p.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_position(role: object) -> str | None:
    if role is None or pd.isna(role):
        return None
    text = str(role).strip()
    if not text or text == "Substitute":
        return None
    return text.split(" | ", 1)[0].strip() or None


def clean_number(value):
    if value is None or pd.isna(value):
        return None
    value = float(value)
    if not np.isfinite(value):
        return None
    return value


def distribution(values: pd.Series, denominator_rows: int) -> dict:
    x = pd.to_numeric(values, errors="coerce").dropna()
    if x.empty:
        return {
            "non_null_rows": 0,
            "coverage_rate": 0.0,
            "unique_values": 0,
            "zero_rate_non_null": None,
            "p25": None,
            "median": None,
            "p75": None,
            "iqr": None,
            "rank_normalization_feasible": False,
            "robust_z_feasible": False,
        }
    p25 = float(x.quantile(0.25))
    p75 = float(x.quantile(0.75))
    unique = int(x.nunique(dropna=True))
    iqr = p75 - p25
    return {
        "non_null_rows": int(len(x)),
        "coverage_rate": float(len(x) / denominator_rows) if denominator_rows else None,
        "unique_values": unique,
        "zero_rate_non_null": float((x == 0).mean()),
        "p25": p25,
        "median": float(x.median()),
        "p75": p75,
        "iqr": float(iqr),
        "rank_normalization_feasible": unique >= 2,
        "robust_z_feasible": bool(unique >= 2 and iqr > 0),
    }


def build_audit(db_path: Path) -> dict:
    catalog = load_json(FEATURE_CATALOG)
    feature_version = str(catalog["feature_version"])
    directions = load_json(DIRECTION_FILE)
    mapping = load_json(DIMENSION_MAP)
    role_specific = load_json(ROLE_SPECIFIC_FILE)

    direction_by_feature = {
        str(x["feature_name"]): str(x["direction_status"])
        for x in directions.get("features", [])
    }
    signed_features = [
        name for name, status in direction_by_feature.items() if status in SIGNED
    ]
    primary_dimension = {
        str(x["feature_name"]): str(x["primary_dimension"])
        for x in mapping.get("feature_mapping", [])
    }
    dimension_scope = {
        str(name): str(meta.get("scope", "unknown"))
        for name, meta in mapping.get("dimensions", {}).items()
    }
    outfield_dimensions = [
        name for name, scope in dimension_scope.items() if scope != "goalkeeper_only"
    ]

    with duckdb.connect(str(db_path), read_only=True) as con:
        played = con.execute(
            """
            SELECT match_id, player_id, minutes_played, primary_role
            FROM player_match
            WHERE minutes_played > 0
            """
        ).fetchdf()
        long = con.execute(
            """
            SELECT f.match_id, f.player_id, f.feature_name, f.feature_value
            FROM player_match_features f
            JOIN player_match pm
              ON pm.match_id = f.match_id AND pm.player_id = f.player_id
            WHERE f.feature_version = ?
              AND pm.minutes_played > 0
            """,
            [feature_version],
        ).fetchdf()
        raw = con.execute(
            """
            SELECT pm.match_id, pm.player_id, pm.primary_role,
                   rs.saves, rs.goals_conceded
            FROM player_match pm
            JOIN player_match_raw_stats rs
              ON rs.match_id = pm.match_id AND rs.player_id = pm.player_id
            WHERE pm.minutes_played > 0
            """
        ).fetchdf()

    played["source_position"] = played["primary_role"].map(source_position)
    known_role_rows = int(played["source_position"].notna().sum())
    direct_gk_rows = int((played["source_position"] == GK_POSITION).sum())

    signed_long = long[long["feature_name"].isin(signed_features)].copy()
    wide = signed_long.pivot_table(
        index=["match_id", "player_id"],
        columns="feature_name",
        values="feature_value",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    frame = played.merge(wide, on=["match_id", "player_id"], how="left")

    # Outfield path excludes only rows directly observed as Goalkeeper. Unknown-role
    # substitute appearances remain eligible for the generic baseline; role is context,
    # not a requirement for having a performance score.
    outfield = frame[frame["source_position"] != GK_POSITION].copy()
    outfield_rows = int(len(outfield))

    feature_diagnostics: list[dict] = []
    for feature in signed_features:
        values = outfield[feature] if feature in outfield.columns else pd.Series(dtype=float)
        diag = distribution(values, outfield_rows)
        diag.update(
            {
                "feature_name": feature,
                "direction_status": direction_by_feature[feature],
                "primary_dimension": primary_dimension.get(feature),
            }
        )
        feature_diagnostics.append(diag)

    degenerate = sorted(
        x["feature_name"] for x in feature_diagnostics if not x["rank_normalization_feasible"]
    )
    robust_limited = sorted(
        x["feature_name"]
        for x in feature_diagnostics
        if x["rank_normalization_feasible"] and not x["robust_z_feasible"]
    )

    dimension_diagnostics: list[dict] = []
    dimensions_without_any_evidence: list[str] = []
    for dimension in outfield_dimensions:
        names = [f for f in signed_features if primary_dimension.get(f) == dimension]
        existing = [f for f in names if f in outfield.columns]
        if existing:
            any_mask = outfield[existing].notna().any(axis=1)
            all_mask = outfield[existing].notna().all(axis=1)
            available_count = outfield[existing].notna().sum(axis=1)
            rows_any = int(any_mask.sum())
            rows_all = int(all_mask.sum())
            median_available = float(available_count.median())
        else:
            rows_any = 0
            rows_all = 0
            median_available = 0.0
        if rows_any == 0:
            dimensions_without_any_evidence.append(dimension)
        dimension_diagnostics.append(
            {
                "dimension": dimension,
                "signed_features": names,
                "signed_feature_count": len(names),
                "rows_with_any_signed_evidence": rows_any,
                "rows_with_all_signed_evidence": rows_all,
                "coverage_any": rows_any / outfield_rows if outfield_rows else None,
                "coverage_all": rows_all / outfield_rows if outfield_rows else None,
                "median_available_signed_features_per_row": median_available,
            }
        )

    # Role support is descriptive only. No minimum sample cutoff is invented here.
    role_support: list[dict] = []
    for position, group in frame[frame["source_position"].notna()].groupby("source_position"):
        row = {
            "source_position": str(position),
            "rows": int(len(group)),
            "players": int(group["player_id"].nunique()),
        }
        support_counts = []
        for feature in signed_features:
            if feature in group.columns:
                support_counts.append(int(group[feature].notna().sum()))
        row["signed_feature_non_null_counts_min"] = min(support_counts) if support_counts else 0
        row["signed_feature_non_null_counts_median"] = (
            float(np.median(support_counts)) if support_counts else 0.0
        )
        row["signed_feature_non_null_counts_max"] = max(support_counts) if support_counts else 0
        role_support.append(row)

    # Validated role-specific goalkeeper candidate.
    raw["source_position"] = raw["primary_role"].map(source_position)
    gk = raw[raw["source_position"] == GK_POSITION].copy()
    gk_saves = pd.to_numeric(gk["saves"], errors="coerce")
    gk_conceded = pd.to_numeric(gk["goals_conceded"], errors="coerce")
    denom = gk_saves + gk_conceded
    valid_gk = gk_saves.notna() & gk_conceded.notna() & (denom > 0)
    save_rate = gk_saves.loc[valid_gk] / denom.loc[valid_gk]
    gk_diag = distribution(save_rate, int(len(gk)))
    gk_diag.update(
        {
            "feature_name": "save_rate",
            "primary_dimension": "goalkeeping",
            "scope": "goalkeeper_only",
            "direction_status": "POSITIVE_SUPPORTED_WITH_CONTEXT",
            "goalkeeper_rows": int(len(gk)),
            "validated_formula_rows": int(valid_gk.sum()),
        }
    )

    if degenerate:
        conclusion = "AGGREGATION_BASELINE_BLOCKED_DEGENERATE_SIGNED_FEATURES"
    elif dimensions_without_any_evidence:
        conclusion = "AGGREGATION_BASELINE_BLOCKED_DIMENSION_WITHOUT_EVIDENCE"
    elif not gk_diag["rank_normalization_feasible"]:
        conclusion = "OUTFIELD_BASELINE_FEASIBLE_GOALKEEPER_NORMALIZATION_LIMITED"
    elif robust_limited:
        conclusion = "RANK_BASED_BASELINE_FEASIBLE_ROBUST_Z_LIMITED_BY_DISTRIBUTIONS"
    else:
        conclusion = "ROBUST_AND_RANK_BASELINE_FEASIBLE"

    return {
        "version": VERSION,
        "status": "AUDIT_ONLY_NO_SCORE_CREATED",
        "summary": {
            "played_rows": int(len(played)),
            "outfield_baseline_rows": outfield_rows,
            "known_role_rows": known_role_rows,
            "direct_goalkeeper_rows": direct_gk_rows,
            "signed_outfield_features": len(signed_features),
            "outfield_dimensions": len(outfield_dimensions),
            "rank_feasible_signed_features": int(
                sum(x["rank_normalization_feasible"] for x in feature_diagnostics)
            ),
            "robust_z_feasible_signed_features": int(
                sum(x["robust_z_feasible"] for x in feature_diagnostics)
            ),
            "degenerate_signed_features": len(degenerate),
            "robust_z_limited_features": len(robust_limited),
            "dimensions_without_any_signed_evidence": len(dimensions_without_any_evidence),
            "goalkeeper_save_rate_rows": int(valid_gk.sum()),
            "goalkeeper_save_rate_rank_feasible": bool(gk_diag["rank_normalization_feasible"]),
            "conclusion": conclusion,
        },
        "degenerate_signed_features": degenerate,
        "robust_z_limited_features": robust_limited,
        "dimensions_without_any_signed_evidence": sorted(dimensions_without_any_evidence),
        "feature_diagnostics": feature_diagnostics,
        "dimension_diagnostics": dimension_diagnostics,
        "role_support": sorted(role_support, key=lambda x: x["source_position"]),
        "goalkeeper_diagnostic": gk_diag,
        "candidate_next_baseline": {
            "normalization": "rank/percentile candidate when distributions are sparse or IQR=0",
            "sign_handling": "invert NEGATIVE_SUPPORTED after normalization so higher always means better",
            "aggregation_stage_1": "available signed features within each dimension",
            "aggregation_stage_2": "dimensions into global outfield score",
            "weight_policy": "equal weights only as experimental null baseline, followed by sensitivity/ablation",
            "goalkeeper": "separate goalkeeper path using validated save_rate; do not mix with outfield baseline yet",
        },
        "guardrails": [
            "No performance score is created in PERF-08.",
            "No equal or unequal weight is approved for product use.",
            "Missing values remain missing and are never silently converted to zero.",
            "Role/position is descriptive context, not the prediction target.",
            "Rank feasibility is a distributional property, not proof that the feature deserves a larger weight.",
            "PCA/correlation/variance are not used to define performance quality.",
        ],
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# PERF-08 — Performance aggregation feasibility",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
    ]
    for k, v in result["summary"].items():
        lines.append(f"- {k}: {v}")

    lines.extend([
        "",
        "## Signed feature diagnostics",
        "",
        "| Feature | Dimension | Direction | Coverage | Unique | Zero rate | IQR | Rank feasible | Robust-z feasible |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ])
    for row in result["feature_diagnostics"]:
        lines.append(
            f"| {row['feature_name']} | {row['primary_dimension']} | {row['direction_status']} | "
            f"{row['coverage_rate']:.3f} | {row['unique_values']} | "
            f"{'' if row['zero_rate_non_null'] is None else f'{row['zero_rate_non_null']:.3f}'} | "
            f"{'' if row['iqr'] is None else f'{row['iqr']:.4f}'} | "
            f"{row['rank_normalization_feasible']} | {row['robust_z_feasible']} |"
        )

    lines.extend(["", "## Dimension coverage"])
    for row in result["dimension_diagnostics"]:
        lines.append(
            f"- `{row['dimension']}`: signed={row['signed_feature_count']}, "
            f"any={row['rows_with_any_signed_evidence']}, all={row['rows_with_all_signed_evidence']}"
        )

    lines.extend(["", "## Goalkeeper"])
    g = result["goalkeeper_diagnostic"]
    lines.append(
        f"- save_rate rows: {g['validated_formula_rows']} / goalkeeper rows {g['goalkeeper_rows']}"
    )
    lines.append(f"- rank feasible: {g['rank_normalization_feasible']}")
    lines.append(f"- robust-z feasible: {g['robust_z_feasible']}")

    lines.extend(["", "## Guardrails"])
    for rule in result["guardrails"]:
        lines.append(f"- {rule}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    result = build_audit(db_path)
    s = result["summary"]
    print("PERF-08 PERFORMANCE AGGREGATION FEASIBILITY: COMPLETE")
    print(f"version={VERSION}")
    print(f"db: {db_path}")
    print(
        f"played_rows={s['played_rows']} outfield_rows={s['outfield_baseline_rows']} "
        f"known_role_rows={s['known_role_rows']} direct_gk_rows={s['direct_goalkeeper_rows']}"
    )
    print(
        f"signed_features={s['signed_outfield_features']} outfield_dimensions={s['outfield_dimensions']} "
        f"rank_feasible={s['rank_feasible_signed_features']} robust_z_feasible={s['robust_z_feasible_signed_features']}"
    )
    print(
        f"degenerate={s['degenerate_signed_features']} robust_z_limited={s['robust_z_limited_features']} "
        f"dimensions_without_evidence={s['dimensions_without_any_signed_evidence']}"
    )
    if result["robust_z_limited_features"]:
        print("robust_z_limited_features=" + ",".join(result["robust_z_limited_features"]))
    if result["degenerate_signed_features"]:
        print("degenerate_features=" + ",".join(result["degenerate_signed_features"]))
    print(
        f"goalkeeper_save_rate_rows={s['goalkeeper_save_rate_rows']} "
        f"goalkeeper_rank_feasible={s['goalkeeper_save_rate_rank_feasible']}"
    )
    print(f"conclusion={s['conclusion']}")
    print("No score, approved weights, thresholds, ranking or recommendation were created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "performance_aggregation_feasibility.json"
        md_path = OUTPUT_DIR / "performance_aggregation_feasibility.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
