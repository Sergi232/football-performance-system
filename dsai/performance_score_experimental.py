"""PERF-09: first experimental player-match performance score.

This is an auditable null baseline only. It does not approve production weights,
thresholds, rankings or recommendations.
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
VERSION = "performance_score_experimental_0.1.0"
SIGNED = {"POSITIVE_SUPPORTED", "NEGATIVE_SUPPORTED"}
GK_POSITION = "Goalkeeper"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build first experimental performance score")
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


def empirical_score(values: pd.Series, direction: str) -> pd.Series:
    x = pd.to_numeric(values, errors="coerce")
    if direction == "POSITIVE_SUPPORTED":
        return x.rank(method="average", pct=True) * 100.0
    if direction == "NEGATIVE_SUPPORTED":
        return (-x).rank(method="average", pct=True) * 100.0
    raise ValueError(f"Unsupported signed direction: {direction}")


def describe_score(values: pd.Series) -> dict:
    x = pd.to_numeric(values, errors="coerce").dropna()
    if x.empty:
        return {"rows": 0, "min": None, "p25": None, "median": None, "p75": None, "max": None}
    return {
        "rows": int(len(x)),
        "min": float(x.min()),
        "p25": float(x.quantile(0.25)),
        "median": float(x.median()),
        "p75": float(x.quantile(0.75)),
        "max": float(x.max()),
    }


def build_score(db_path: Path) -> tuple[dict, pd.DataFrame]:
    catalog = load_json(FEATURE_CATALOG)
    feature_version = str(catalog["feature_version"])
    directions = load_json(DIRECTION_FILE)
    mapping = load_json(DIMENSION_MAP)
    role_specific = load_json(ROLE_SPECIFIC_FILE)

    direction_by_feature = {
        str(x["feature_name"]): str(x["direction_status"])
        for x in directions.get("features", [])
    }
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
    signed_features = [
        name for name, status in direction_by_feature.items() if status in SIGNED
    ]

    role_specific_names = {str(x.get("feature_name")) for x in role_specific.get("features", [])}
    if "save_rate" not in role_specific_names:
        raise RuntimeError("Validated role-specific save_rate registry entry is missing")

    with duckdb.connect(str(db_path), read_only=True) as con:
        played = con.execute(
            """
            SELECT match_id, player_id, minutes_played, primary_role
            FROM player_match
            WHERE minutes_played > 0
            """
        ).fetchdf()
        feature_long = con.execute(
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
    raw["source_position"] = raw["primary_role"].map(source_position)
    raw["saves_num"] = pd.to_numeric(raw["saves"], errors="coerce")
    raw["goals_conceded_num"] = pd.to_numeric(raw["goals_conceded"], errors="coerce")

    wide = (
        feature_long[feature_long["feature_name"].isin(signed_features)]
        .pivot_table(
            index=["match_id", "player_id"],
            columns="feature_name",
            values="feature_value",
            aggfunc="first",
        )
        .reset_index()
    )
    wide.columns.name = None

    frame = played.merge(wide, on=["match_id", "player_id"], how="left")
    raw_small = raw[["match_id", "player_id", "saves_num", "goals_conceded_num"]].copy()
    frame = frame.merge(raw_small, on=["match_id", "player_id"], how="left")

    unknown_positive_save = frame["source_position"].isna() & (frame["saves_num"].fillna(0) > 0)
    direct_gk = frame["source_position"] == GK_POSITION
    outfield_eligible = ~(direct_gk | unknown_positive_save)
    outfield = frame.loc[outfield_eligible].copy()

    used_features: list[str] = []
    excluded_degenerate: list[str] = []
    normalized_columns: dict[str, str] = {}

    for feature in signed_features:
        if feature not in outfield.columns:
            excluded_degenerate.append(feature)
            continue
        x = pd.to_numeric(outfield[feature], errors="coerce")
        if int(x.nunique(dropna=True)) < 2:
            excluded_degenerate.append(feature)
            continue
        used_features.append(feature)
        col = f"feature_score__{feature}"
        outfield[col] = empirical_score(x, direction_by_feature[feature])
        normalized_columns[feature] = col

    dimension_feature_map: dict[str, list[str]] = {}
    for dimension in outfield_dimensions:
        names = [
            feature for feature in used_features
            if primary_dimension.get(feature) == dimension
        ]
        dimension_feature_map[dimension] = names
        score_cols = [normalized_columns[f] for f in names]
        dim_col = f"dimension_score__{dimension}"
        count_col = f"dimension_evidence_count__{dimension}"
        if score_cols:
            outfield[count_col] = outfield[score_cols].notna().sum(axis=1)
            outfield[dim_col] = outfield[score_cols].mean(axis=1, skipna=True)
            outfield.loc[outfield[count_col] == 0, dim_col] = np.nan
        else:
            outfield[count_col] = 0
            outfield[dim_col] = np.nan

    dimension_cols = [f"dimension_score__{d}" for d in outfield_dimensions]
    outfield["dimension_coverage_count"] = outfield[dimension_cols].notna().sum(axis=1)
    outfield["dimension_coverage_total"] = len(outfield_dimensions)
    complete_mask = outfield["dimension_coverage_count"] == len(outfield_dimensions)
    outfield["performance_score_experimental"] = np.nan
    outfield.loc[complete_mask, "performance_score_experimental"] = outfield.loc[
        complete_mask, dimension_cols
    ].mean(axis=1)
    outfield["score_path"] = "outfield"
    outfield["score_version"] = VERSION

    # Goalkeeper path remains structurally separate and uses only validated save_rate.
    gk = raw[raw["source_position"] == GK_POSITION].copy()
    denom = gk["saves_num"] + gk["goals_conceded_num"]
    valid_gk = gk["saves_num"].notna() & gk["goals_conceded_num"].notna() & (denom > 0)
    gk["save_rate"] = np.nan
    gk.loc[valid_gk, "save_rate"] = gk.loc[valid_gk, "saves_num"] / denom.loc[valid_gk]
    gk["goalkeeper_score_experimental"] = (
        pd.to_numeric(gk["save_rate"], errors="coerce").rank(method="average", pct=True) * 100.0
    )
    gk["score_path"] = "goalkeeper"
    gk["score_version"] = VERSION

    # Combined export keeps paths explicit; scores are never mixed into one comparison population.
    out_export_cols = [
        "match_id", "player_id", "minutes_played", "primary_role", "source_position",
        "score_path", "score_version", "dimension_coverage_count", "dimension_coverage_total",
        *dimension_cols, "performance_score_experimental",
    ]
    out_export = outfield[out_export_cols].copy()

    gk_export = gk[[
        "match_id", "player_id", "primary_role", "source_position",
        "score_path", "score_version", "save_rate", "goalkeeper_score_experimental",
    ]].copy()
    gk_export["minutes_played"] = np.nan
    gk_export["dimension_coverage_count"] = np.nan
    gk_export["dimension_coverage_total"] = np.nan
    for col in dimension_cols:
        gk_export[col] = np.nan
    gk_export["performance_score_experimental"] = np.nan
    gk_export = gk_export[out_export_cols + ["save_rate", "goalkeeper_score_experimental"]]

    out_export["save_rate"] = np.nan
    out_export["goalkeeper_score_experimental"] = np.nan
    out_export = out_export[out_export_cols + ["save_rate", "goalkeeper_score_experimental"]]
    combined = pd.concat([out_export, gk_export], ignore_index=True)

    dimension_coverage = {}
    for dimension in outfield_dimensions:
        col = f"dimension_score__{dimension}"
        dimension_coverage[dimension] = {
            "used_features": dimension_feature_map[dimension],
            "rows_with_score": int(outfield[col].notna().sum()),
            "coverage_rate": float(outfield[col].notna().mean()) if len(outfield) else None,
        }

    conclusion = (
        "EXPERIMENTAL_SCORE_BASELINE_CREATED_SENSITIVITY_REQUIRED"
        if int(complete_mask.sum()) > 0
        else "EXPERIMENTAL_SCORE_BLOCKED_NO_COMPLETE_DIMENSION_ROWS"
    )

    result = {
        "version": VERSION,
        "status": "EXPERIMENTAL_NO_DEPLOY",
        "summary": {
            "played_rows": int(len(played)),
            "direct_goalkeeper_rows": int(direct_gk.sum()),
            "unknown_role_positive_save_rows_excluded_from_outfield": int(unknown_positive_save.sum()),
            "outfield_eligible_rows": int(len(outfield)),
            "signed_candidate_features": int(len(signed_features)),
            "used_non_degenerate_features": int(len(used_features)),
            "excluded_degenerate_features": int(len(excluded_degenerate)),
            "outfield_dimensions": int(len(outfield_dimensions)),
            "complete_outfield_score_rows": int(complete_mask.sum()),
            "goalkeeper_rows": int(len(gk)),
            "goalkeeper_score_rows": int(gk["goalkeeper_score_experimental"].notna().sum()),
            "conclusion": conclusion,
        },
        "used_features": used_features,
        "excluded_degenerate_features": sorted(excluded_degenerate),
        "dimension_feature_map": dimension_feature_map,
        "dimension_coverage": dimension_coverage,
        "outfield_score_distribution": describe_score(outfield["performance_score_experimental"]),
        "goalkeeper_score_distribution": describe_score(gk["goalkeeper_score_experimental"]),
        "method": {
            "feature_normalization": "empirical rank percentile 0-100 with average ties",
            "positive_direction": "higher raw value -> higher percentile score",
            "negative_direction": "lower raw value -> higher percentile score by ranking -value",
            "dimension_aggregation": "equal mean of available normalized signed features within each dimension",
            "global_aggregation": "equal mean of five dimension scores only when all five are present",
            "goalkeeper": "separate percentile of validated save_rate; never pooled with outfield",
            "weight_status": "equal weights are null-baseline experimental weights only, not approved product weights",
        },
        "guardrails": [
            "No production weight or threshold is approved.",
            "No missing value is silently converted to zero.",
            "Degenerate signed features are excluded from this sample baseline, not deleted from the system.",
            "Role/position is context and exclusion protection only; it is not a direct score component.",
            "Outfield and goalkeeper score distributions are separate and not directly comparable.",
            "Sensitivity and ablation analysis is required before any deployment decision.",
        ],
    }
    return result, combined


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# PERF-09 — Experimental performance score",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
    ]
    for k, v in s.items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Features used"])
    for name in result["used_features"]:
        lines.append(f"- `{name}`")
    lines.extend(["", "## Excluded because degenerate in this sample"])
    for name in result["excluded_degenerate_features"]:
        lines.append(f"- `{name}`")
    lines.extend(["", "## Dimension coverage"])
    for dim, data in result["dimension_coverage"].items():
        lines.append(
            f"- `{dim}`: rows={data['rows_with_score']}, coverage={data['coverage_rate']:.3f}, "
            f"features={','.join(data['used_features'])}"
        )
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

    result, combined = build_score(db_path)
    s = result["summary"]

    print("PERF-09 EXPERIMENTAL PERFORMANCE SCORE: COMPLETE")
    print(f"version={VERSION}")
    print(f"db: {db_path}")
    print(
        f"played_rows={s['played_rows']} outfield_eligible_rows={s['outfield_eligible_rows']} "
        f"direct_gk_rows={s['direct_goalkeeper_rows']} unknown_gk_evidence_excluded={s['unknown_role_positive_save_rows_excluded_from_outfield']}"
    )
    print(
        f"signed_candidates={s['signed_candidate_features']} used_features={s['used_non_degenerate_features']} "
        f"excluded_degenerate={s['excluded_degenerate_features']} dimensions={s['outfield_dimensions']}"
    )
    print(
        f"complete_outfield_score_rows={s['complete_outfield_score_rows']} "
        f"goalkeeper_score_rows={s['goalkeeper_score_rows']}"
    )
    print("excluded_features=" + ",".join(result["excluded_degenerate_features"]))
    d = result["outfield_score_distribution"]
    print(
        f"outfield_score=min:{d['min']} p25:{d['p25']} median:{d['median']} p75:{d['p75']} max:{d['max']}"
    )
    gd = result["goalkeeper_score_distribution"]
    print(
        f"goalkeeper_score=min:{gd['min']} p25:{gd['p25']} median:{gd['median']} p75:{gd['p75']} max:{gd['max']}"
    )
    print(f"conclusion={s['conclusion']}")
    print("Experimental null baseline only; no production weights, thresholds, ranking or recommendation were approved.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "performance_score_experimental.json"
        md_path = OUTPUT_DIR / "performance_score_experimental.md"
        csv_path = OUTPUT_DIR / "performance_score_experimental.csv"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        combined.to_csv(csv_path, index=False)
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")
        print(f"scores: {csv_path}")


if __name__ == "__main__":
    main()
