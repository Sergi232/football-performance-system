"""PERF-12: quantify coverage impact of event-validated NULL-as-zero semantics.

This script applies the semantics validated in PERF-11 only in memory:
- shots_total NULL -> observed zero
- goals NULL -> observed zero
- red_cards NULL -> observed zero

It does not mutate DuckDB, FEATURE-01, the feature catalog, score weights,
thresholds, rankings, or recommendations. yellow_cards remains unchanged.
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
OUTPUT_DIR = Path(__file__).with_name("output")
VERSION = "performance_validated_zero_impact_0.1.0"
SIGNED = {"POSITIVE_SUPPORTED", "NEGATIVE_SUPPORTED"}
VALIDATED_ZERO_RAW = {"shots_total", "goals", "red_cards"}
GK_POSITION = "Goalkeeper"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-12 validated-zero coverage impact audit")
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


def counts(series: pd.Series, max_dim: int) -> dict[str, int]:
    return {str(i): int((series == i).sum()) for i in range(max_dim + 1)}


def dimension_summary(frame: pd.DataFrame, feature_names: list[str], dimension_map: dict[str, str], dimensions: list[str]) -> tuple[pd.DataFrame, pd.Series, dict[str, dict[str, object]]]:
    availability = {}
    diagnostics: dict[str, dict[str, object]] = {}
    for dim in dimensions:
        names = [f for f in feature_names if dimension_map.get(f) == dim and f in frame.columns]
        if names:
            mask = frame[names].notna().any(axis=1)
        else:
            mask = pd.Series(False, index=frame.index)
        availability[dim] = mask
        diagnostics[dim] = {
            "features": names,
            "rows_with_evidence": int(mask.sum()),
            "coverage_rate": float(mask.mean()) if len(mask) else None,
        }
    avail = pd.DataFrame(availability, index=frame.index)
    count = avail.sum(axis=1).astype(int)
    return avail, count, diagnostics


def build_audit(db_path: Path) -> dict:
    catalog = load_json(FEATURE_CATALOG)
    directions = load_json(DIRECTION_FILE)
    mapping = load_json(DIMENSION_MAP)
    feature_version = str(catalog["feature_version"])

    ratio_specs = {str(x["name"]): x for x in catalog.get("ratio_features", [])}
    per90_specs = {str(x["name"]): x for x in catalog.get("per90_features", [])}
    direction_by_feature = {str(x["feature_name"]): str(x["direction_status"]) for x in directions.get("features", [])}
    signed_features = [f for f, status in direction_by_feature.items() if status in SIGNED]
    primary_dimension = {str(x["feature_name"]): str(x["primary_dimension"]) for x in mapping.get("feature_mapping", [])}
    outfield_dimensions = [
        str(name)
        for name, meta in mapping.get("dimensions", {}).items()
        if str(meta.get("scope")) != "goalkeeper_only"
    ]

    with duckdb.connect(str(db_path), read_only=True) as con:
        played = con.execute(
            """
            SELECT match_id, player_id, minutes_played, primary_role
            FROM player_match
            WHERE minutes_played > 0
            """
        ).fetchdf()
        raw = con.execute(
            """
            SELECT rs.*
            FROM player_match_raw_stats rs
            JOIN player_match pm
              ON pm.match_id=rs.match_id AND pm.player_id=rs.player_id
            WHERE pm.minutes_played > 0
            """
        ).fetchdf()
        feature_long = con.execute(
            """
            SELECT f.match_id, f.player_id, f.feature_name, f.feature_value
            FROM player_match_features f
            JOIN player_match pm
              ON pm.match_id=f.match_id AND pm.player_id=f.player_id
            WHERE f.feature_version=? AND pm.minutes_played > 0
            """,
            [feature_version],
        ).fetchdf()

    played["source_position"] = played["primary_role"].map(source_position)
    raw = raw.merge(
        played[["match_id", "player_id", "minutes_played", "source_position"]],
        on=["match_id", "player_id"],
        how="left",
    )

    saves = pd.to_numeric(raw.get("saves"), errors="coerce")
    raw["__saves_num"] = saves
    direct_gk_keys = set(map(tuple, raw.loc[raw["source_position"] == GK_POSITION, ["match_id", "player_id"]].to_numpy()))
    unknown_gk_keys = set(map(tuple, raw.loc[raw["source_position"].isna() & (raw["__saves_num"].fillna(0) > 0), ["match_id", "player_id"]].to_numpy()))

    played["__key"] = list(zip(played["match_id"], played["player_id"]))
    outfield = played[~played["__key"].isin(direct_gk_keys | unknown_gk_keys)].copy()
    outfield_keys = set(outfield["__key"])

    raw["__key"] = list(zip(raw["match_id"], raw["player_id"]))
    raw_out = raw[raw["__key"].isin(outfield_keys)].copy()

    signed_long = feature_long[feature_long["feature_name"].isin(signed_features)].copy()
    signed_long["__key"] = list(zip(signed_long["match_id"], signed_long["player_id"]))
    signed_long = signed_long[signed_long["__key"].isin(outfield_keys)]
    baseline = signed_long.pivot_table(
        index=["match_id", "player_id"],
        columns="feature_name",
        values="feature_value",
        aggfunc="first",
    ).reset_index()
    baseline.columns.name = None
    baseline = outfield[["match_id", "player_id", "source_position"]].merge(baseline, on=["match_id", "player_id"], how="left")

    adjusted = baseline.copy()
    raw_indexed = raw_out.set_index(["match_id", "player_id"], drop=False)

    # Apply only PERF-11 validated raw semantics in memory.
    goals = pd.to_numeric(raw_indexed["goals"], errors="coerce").fillna(0.0)
    shots = pd.to_numeric(raw_indexed["shots_total"], errors="coerce").fillna(0.0)
    reds = pd.to_numeric(raw_indexed["red_cards"], errors="coerce").fillna(0.0)
    minutes = pd.to_numeric(raw_indexed["minutes_played"], errors="coerce")

    derived = pd.DataFrame(index=raw_indexed.index)
    derived["goals_per90"] = np.where(minutes > 0, goals * 90.0 / minutes, np.nan)
    derived["red_cards_per90"] = np.where(minutes > 0, reds * 90.0 / minutes, np.nan)
    derived["shots_total_per90"] = np.where(minutes > 0, shots * 90.0 / minutes, np.nan)
    derived["goal_per_shot_rate"] = np.where(shots > 0, goals / shots, np.nan)
    derived = derived.reset_index(drop=True)
    derived.insert(0, "player_id", raw_out["player_id"].to_numpy())
    derived.insert(0, "match_id", raw_out["match_id"].to_numpy())

    # Only signed features affect signed-core dimensional coverage; shots_total_per90
    # is reported because its raw semantic was validated but remains contextual.
    adjusted = adjusted.drop(columns=[c for c in ["goals_per90", "red_cards_per90", "goal_per_shot_rate"] if c in adjusted.columns])
    adjusted = adjusted.merge(
        derived[["match_id", "player_id", "goals_per90", "red_cards_per90", "goal_per_shot_rate"]],
        on=["match_id", "player_id"],
        how="left",
    )

    # Keep the same degeneracy rule as PERF-09/10.
    baseline_used: list[str] = []
    adjusted_used: list[str] = []
    baseline_degenerate: list[str] = []
    adjusted_degenerate: list[str] = []
    for feature in signed_features:
        bx = pd.to_numeric(baseline.get(feature), errors="coerce") if feature in baseline.columns else pd.Series(dtype=float)
        ax = pd.to_numeric(adjusted.get(feature), errors="coerce") if feature in adjusted.columns else pd.Series(dtype=float)
        (baseline_degenerate if int(bx.nunique(dropna=True)) < 2 else baseline_used).append(feature)
        (adjusted_degenerate if int(ax.nunique(dropna=True)) < 2 else adjusted_used).append(feature)

    b_avail, b_count, b_diag = dimension_summary(baseline, baseline_used, primary_dimension, outfield_dimensions)
    a_avail, a_count, a_diag = dimension_summary(adjusted, adjusted_used, primary_dimension, outfield_dimensions)

    before_full = int((b_count == len(outfield_dimensions)).sum())
    after_full = int((a_count == len(outfield_dimensions)).sum())

    feature_impact = []
    for feature in ["goals_per90", "goal_per_shot_rate", "red_cards_per90"]:
        before = pd.to_numeric(baseline.get(feature), errors="coerce") if feature in baseline.columns else pd.Series(np.nan, index=baseline.index)
        after = pd.to_numeric(adjusted.get(feature), errors="coerce") if feature in adjusted.columns else pd.Series(np.nan, index=adjusted.index)
        feature_impact.append({
            "feature_name": feature,
            "before_non_null": int(before.notna().sum()),
            "after_non_null": int(after.notna().sum()),
            "gain": int(after.notna().sum() - before.notna().sum()),
        })

    shots_context_before = feature_long[
        (feature_long["feature_name"] == "shots_total_per90")
        & feature_long.apply(lambda r: (r["match_id"], r["player_id"]) in outfield_keys, axis=1)
    ]["feature_value"]
    shots_context_after = derived["shots_total_per90"]

    dimension_impact = []
    for dim in outfield_dimensions:
        dimension_impact.append({
            "dimension": dim,
            "before_rows": int(b_diag[dim]["rows_with_evidence"]),
            "after_rows": int(a_diag[dim]["rows_with_evidence"]),
            "gain": int(a_diag[dim]["rows_with_evidence"] - b_diag[dim]["rows_with_evidence"]),
            "before_rate": b_diag[dim]["coverage_rate"],
            "after_rate": a_diag[dim]["coverage_rate"],
        })

    min_after = min((x["after_rows"] for x in dimension_impact), default=0)
    residual_bottlenecks = sorted(x["dimension"] for x in dimension_impact if x["after_rows"] == min_after)

    conclusion = (
        "VALIDATED_ZERO_SEMANTICS_FULL_COVERAGE_READY"
        if after_full == len(outfield) and len(outfield) > 0
        else "VALIDATED_ZERO_SEMANTICS_IMPROVE_COVERAGE_POLICY_STILL_REQUIRED"
    )

    return {
        "version": VERSION,
        "status": "AUDIT_ONLY_NO_DB_OR_FEATURE_MUTATION",
        "summary": {
            "outfield_rows": int(len(outfield)),
            "validated_zero_raw_metrics": sorted(VALIDATED_ZERO_RAW),
            "baseline_used_signed_features": len(baseline_used),
            "adjusted_used_signed_features": len(adjusted_used),
            "baseline_degenerate_features": sorted(baseline_degenerate),
            "adjusted_degenerate_features": sorted(adjusted_degenerate),
            "full_five_before": before_full,
            "full_five_after": after_full,
            "full_five_gain": int(after_full - before_full),
            "full_five_rate_before": float(before_full / len(outfield)) if len(outfield) else None,
            "full_five_rate_after": float(after_full / len(outfield)) if len(outfield) else None,
            "residual_bottleneck_dimensions": residual_bottlenecks,
            "conclusion": conclusion,
        },
        "feature_impact": feature_impact,
        "shots_total_per90_contextual_impact": {
            "before_non_null": int(pd.to_numeric(shots_context_before, errors="coerce").notna().sum()),
            "after_non_null": int(pd.to_numeric(shots_context_after, errors="coerce").notna().sum()),
        },
        "dimension_impact": dimension_impact,
        "dimension_count_distribution_before": counts(b_count, len(outfield_dimensions)),
        "dimension_count_distribution_after": counts(a_count, len(outfield_dimensions)),
        "guardrails": [
            "Only PERF-11 event-validated NULL-as-zero semantics are applied in memory.",
            "yellow_cards is not reinterpreted.",
            "goal_per_shot_rate remains undefined when shots_total is zero.",
            "DuckDB and FEATURE-01 are not modified.",
            "No score weight, threshold, ranking or recommendation is approved.",
        ],
    }


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# PERF-12 — Validated zero semantics coverage impact",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
        f"- outfield_rows: {s['outfield_rows']}",
        f"- full_five_before: {s['full_five_before']}",
        f"- full_five_after: {s['full_five_after']}",
        f"- full_five_gain: {s['full_five_gain']}",
        f"- residual_bottleneck_dimensions: {', '.join(s['residual_bottleneck_dimensions'])}",
        f"- conclusion: `{s['conclusion']}`",
        "",
        "## Feature impact",
    ]
    for row in result["feature_impact"]:
        lines.append(f"- `{row['feature_name']}`: {row['before_non_null']} -> {row['after_non_null']} (+{row['gain']})")
    lines += ["", "## Dimension impact"]
    for row in result["dimension_impact"]:
        lines.append(f"- `{row['dimension']}`: {row['before_rows']} -> {row['after_rows']} (+{row['gain']})")
    lines += ["", "## Guardrails"]
    lines.extend(f"- {x}" for x in result["guardrails"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    result = build_audit(db_path)
    s = result["summary"]
    print("PERF-12 VALIDATED ZERO IMPACT: COMPLETE")
    print(f"version={VERSION}")
    print(f"db: {db_path}")
    print(
        f"outfield_rows={s['outfield_rows']} full_five_before={s['full_five_before']} "
        f"full_five_after={s['full_five_after']} gain={s['full_five_gain']}"
    )
    print("feature_impact=" + ",".join(
        f"{x['feature_name']}:{x['before_non_null']}->{x['after_non_null']}"
        for x in result["feature_impact"]
    ))
    print("dimension_impact=" + ",".join(
        f"{x['dimension']}:{x['before_rows']}->{x['after_rows']}"
        for x in result["dimension_impact"]
    ))
    print("dimension_count_before=" + ",".join(f"{k}:{v}" for k, v in result["dimension_count_distribution_before"].items()))
    print("dimension_count_after=" + ",".join(f"{k}:{v}" for k, v in result["dimension_count_distribution_after"].items()))
    print("residual_bottleneck_dimensions=" + ",".join(s["residual_bottleneck_dimensions"]))
    print(f"conclusion={s['conclusion']}")
    print("No DB/FEATURE-01 mutation, score weights, thresholds, ranking or recommendation were created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "performance_validated_zero_impact.json"
        md_path = OUTPUT_DIR / "performance_validated_zero_impact.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
