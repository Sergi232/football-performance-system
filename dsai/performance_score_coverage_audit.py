"""PERF-10: audit coverage and observability bottlenecks of the performance score.

This phase explains why PERF-09 produced only a few complete five-dimension
outfield scores. It does not create a new score, approve weights, choose a
minimum-dimension threshold, or convert missing values to zero.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
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
VERSION = "performance_score_coverage_audit_0.1.0"
SIGNED = {"POSITIVE_SUPPORTED", "NEGATIVE_SUPPORTED"}
GK_POSITION = "Goalkeeper"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit performance-score coverage bottlenecks")
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


def build_audit(db_path: Path) -> dict:
    catalog = load_json(FEATURE_CATALOG)
    directions = load_json(DIRECTION_FILE)
    mapping = load_json(DIMENSION_MAP)
    feature_version = str(catalog["feature_version"])

    ratio_specs = {str(x["name"]): x for x in catalog.get("ratio_features", [])}
    per90_specs = {str(x["name"]): x for x in catalog.get("per90_features", [])}
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
        feature_long = con.execute(
            """
            SELECT f.match_id, f.player_id, f.feature_name, f.feature_value
            FROM player_match_features f
            JOIN player_match pm
              ON pm.match_id=f.match_id AND pm.player_id=f.player_id
            WHERE f.feature_version=? AND pm.minutes_played>0
            """,
            [feature_version],
        ).fetchdf()
        raw = con.execute(
            """
            SELECT rs.*
            FROM player_match_raw_stats rs
            JOIN player_match pm
              ON pm.match_id=rs.match_id AND pm.player_id=rs.player_id
            WHERE pm.minutes_played>0
            """
        ).fetchdf()

    played["source_position"] = played["primary_role"].map(source_position)
    raw = raw.merge(
        played[["match_id", "player_id", "source_position"]],
        on=["match_id", "player_id"],
        how="left",
    )

    saves_num = pd.to_numeric(raw.get("saves"), errors="coerce")
    raw["__saves_num"] = saves_num
    gk_keys = set(
        map(tuple, raw.loc[raw["source_position"] == GK_POSITION, ["match_id", "player_id"]].to_numpy())
    )
    unknown_save_keys = set(
        map(
            tuple,
            raw.loc[
                raw["source_position"].isna() & (raw["__saves_num"].fillna(0) > 0),
                ["match_id", "player_id"],
            ].to_numpy(),
        )
    )

    played["__key"] = list(zip(played["match_id"], played["player_id"]))
    outfield = played[
        ~played["__key"].isin(gk_keys | unknown_save_keys)
    ].copy()
    outfield_keys = set(outfield["__key"])

    signed_long = feature_long[feature_long["feature_name"].isin(signed_features)].copy()
    signed_long["__key"] = list(zip(signed_long["match_id"], signed_long["player_id"]))
    signed_long = signed_long[signed_long["__key"].isin(outfield_keys)].copy()

    wide = signed_long.pivot_table(
        index=["match_id", "player_id"],
        columns="feature_name",
        values="feature_value",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    frame = outfield.merge(wide, on=["match_id", "player_id"], how="left")

    degenerate: list[str] = []
    used_features: list[str] = []
    for feature in signed_features:
        x = pd.to_numeric(frame.get(feature), errors="coerce") if feature in frame.columns else pd.Series(dtype=float)
        if int(x.nunique(dropna=True)) < 2:
            degenerate.append(feature)
        else:
            used_features.append(feature)

    feature_diagnostics: list[dict] = []
    raw_outfield = raw[
        raw.apply(lambda r: (r["match_id"], r["player_id"]) in outfield_keys, axis=1)
    ].copy()

    for feature in signed_features:
        row = {
            "feature_name": feature,
            "direction_status": direction_by_feature[feature],
            "primary_dimension": primary_dimension.get(feature),
            "used_in_perf09": feature in used_features,
            "degenerate_in_sample": feature in degenerate,
            "feature_non_null_rows": int(pd.to_numeric(frame.get(feature), errors="coerce").notna().sum()) if feature in frame.columns else 0,
        }
        if feature in per90_specs:
            source = str(per90_specs[feature]["source"])
            raw_values = pd.to_numeric(raw_outfield.get(source), errors="coerce")
            row.update(
                {
                    "feature_type": "per90",
                    "raw_source": source,
                    "raw_source_null_rows": int(raw_values.isna().sum()),
                    "raw_source_zero_rows": int((raw_values == 0).sum()),
                    "raw_source_positive_rows": int((raw_values > 0).sum()),
                }
            )
        elif feature in ratio_specs:
            numerator = str(ratio_specs[feature]["numerator"])
            denominator = str(ratio_specs[feature]["denominator"])
            num = pd.to_numeric(raw_outfield.get(numerator), errors="coerce")
            den = pd.to_numeric(raw_outfield.get(denominator), errors="coerce")
            both = num.notna() & den.notna()
            row.update(
                {
                    "feature_type": "ratio",
                    "raw_numerator": numerator,
                    "raw_denominator": denominator,
                    "raw_input_missing_rows": int((~both).sum()),
                    "raw_denominator_zero_rows": int((both & (den == 0)).sum()),
                    "raw_denominator_positive_rows": int((both & (den > 0)).sum()),
                    "raw_numerator_zero_with_positive_denominator_rows": int((both & (den > 0) & (num == 0)).sum()),
                }
            )
        else:
            row["feature_type"] = "unknown"
        feature_diagnostics.append(row)

    dimension_features = {
        dimension: [f for f in used_features if primary_dimension.get(f) == dimension]
        for dimension in outfield_dimensions
    }
    dimension_available: dict[str, pd.Series] = {}
    dimension_diagnostics: list[dict] = []
    for dimension in outfield_dimensions:
        names = dimension_features[dimension]
        cols = [f for f in names if f in frame.columns]
        available = frame[cols].notna().any(axis=1) if cols else pd.Series(False, index=frame.index)
        dimension_available[dimension] = available
        dimension_diagnostics.append(
            {
                "dimension": dimension,
                "used_features": names,
                "rows_with_evidence": int(available.sum()),
                "coverage_rate": float(available.mean()) if len(frame) else None,
            }
        )

    availability_df = pd.DataFrame(dimension_available)
    dimension_count = availability_df.sum(axis=1).astype(int)
    count_distribution = {
        str(k): int((dimension_count == k).sum())
        for k in range(0, len(outfield_dimensions) + 1)
    }

    pattern_counter: Counter[str] = Counter()
    for idx in availability_df.index:
        missing = [d for d in outfield_dimensions if not bool(availability_df.loc[idx, d])]
        key = "<NONE>" if not missing else "|".join(missing)
        pattern_counter[key] += 1
    missing_patterns = [
        {"missing_dimensions": key, "rows": int(count)}
        for key, count in pattern_counter.most_common()
    ]

    full_mask = dimension_count == len(outfield_dimensions)
    full_rows = int(full_mask.sum())
    leave_one_out: list[dict] = []
    for dimension in outfield_dimensions:
        other = [d for d in outfield_dimensions if d != dimension]
        complete_without = int(availability_df[other].all(axis=1).sum()) if other else len(frame)
        leave_one_out.append(
            {
                "dimension": dimension,
                "complete_rows_if_dimension_not_required": complete_without,
                "additional_rows_vs_full_five": int(complete_without - full_rows),
            }
        )

    role_context: list[dict] = []
    temp = frame[["source_position"]].copy()
    temp["dimension_count"] = dimension_count.values
    for position, group in temp.groupby("source_position", dropna=False):
        label = "<UNKNOWN>" if pd.isna(position) else str(position)
        role_context.append(
            {
                "source_position": label,
                "rows": int(len(group)),
                "median_dimensions_available": float(group["dimension_count"].median()),
                "full_five_rows": int((group["dimension_count"] == len(outfield_dimensions)).sum()),
            }
        )

    min_coverage = min((x["coverage_rate"] for x in dimension_diagnostics), default=None)
    bottleneck_dimensions = sorted(
        x["dimension"] for x in dimension_diagnostics if x["coverage_rate"] == min_coverage
    ) if min_coverage is not None else []

    conclusion = (
        "FULL_DIMENSION_COVERAGE_COMPLETE_SENSITIVITY_READY"
        if full_rows == len(frame) and len(frame) > 0
        else "FULL_DIMENSION_COVERAGE_INCOMPLETE_POLICY_REDESIGN_REQUIRED"
    )

    return {
        "version": VERSION,
        "status": "AUDIT_ONLY_NO_SCORE_POLICY_CHANGE",
        "summary": {
            "outfield_eligible_rows": int(len(frame)),
            "signed_candidate_features": len(signed_features),
            "used_features": len(used_features),
            "degenerate_features": len(degenerate),
            "outfield_dimensions": len(outfield_dimensions),
            "full_five_dimension_rows": full_rows,
            "full_five_dimension_coverage_rate": float(full_rows / len(frame)) if len(frame) else None,
            "bottleneck_dimensions": bottleneck_dimensions,
            "conclusion": conclusion,
        },
        "used_features": used_features,
        "degenerate_features": sorted(degenerate),
        "feature_diagnostics": feature_diagnostics,
        "dimension_diagnostics": dimension_diagnostics,
        "dimension_count_distribution": count_distribution,
        "missing_dimension_patterns": missing_patterns,
        "leave_one_dimension_out": leave_one_out,
        "role_context": sorted(role_context, key=lambda x: x["source_position"]),
        "guardrails": [
            "No new performance score is created in PERF-10.",
            "No minimum number of dimensions is approved.",
            "Missing values are never silently converted to zero.",
            "Raw zero and raw NULL are reported separately when the raw schema permits it.",
            "A ratio with denominator zero is structurally undefined, not equivalent to poor performance.",
            "Role/position is diagnostic context only.",
            "No weight, threshold, ranking or recommendation is approved.",
        ],
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# PERF-10 — Performance score coverage audit",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Dimension coverage"])
    for row in result["dimension_diagnostics"]:
        lines.append(
            f"- `{row['dimension']}`: rows={row['rows_with_evidence']}, coverage={row['coverage_rate']:.3f}, features={','.join(row['used_features'])}"
        )
    lines.extend(["", "## Dimension count distribution"])
    for key, value in result["dimension_count_distribution"].items():
        lines.append(f"- {key} dimensions: {value} rows")
    lines.extend(["", "## Most common missing-dimension patterns"])
    for row in result["missing_dimension_patterns"][:15]:
        lines.append(f"- `{row['missing_dimensions']}`: {row['rows']}")
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
    print("PERF-10 PERFORMANCE SCORE COVERAGE AUDIT: COMPLETE")
    print(f"version={VERSION}")
    print(f"db: {db_path}")
    print(
        f"outfield_rows={s['outfield_eligible_rows']} signed_candidates={s['signed_candidate_features']} "
        f"used_features={s['used_features']} degenerate={s['degenerate_features']} dimensions={s['outfield_dimensions']}"
    )
    print(
        f"full_five_rows={s['full_five_dimension_rows']} "
        f"full_five_coverage={s['full_five_dimension_coverage_rate']}"
    )
    print("dimension_count_distribution=" + ",".join(
        f"{k}:{v}" for k, v in result["dimension_count_distribution"].items()
    ))
    print("bottleneck_dimensions=" + ",".join(s["bottleneck_dimensions"]))
    print("leave_one_out=" + ",".join(
        f"{x['dimension']}:{x['complete_rows_if_dimension_not_required']}"
        for x in result["leave_one_dimension_out"]
    ))
    print(f"conclusion={s['conclusion']}")
    print("No score policy, minimum-dimension threshold, weights, ranking or recommendation were approved.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "performance_score_coverage_audit.json"
        md_path = OUTPUT_DIR / "performance_score_coverage_audit.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
