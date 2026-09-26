"""PERF-05: audit whether direction-supported features form a usable scoring core.

This phase is descriptive only. It does NOT create dimension scores, weights,
standardization rules, thresholds, rankings or a global performance score.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
FEATURE_CATALOG = ROOT / "features" / "catalog.json"
MAPPING_FILE = Path(__file__).with_name("performance_dimension_map.json")
DIRECTION_FILE = Path(__file__).with_name("performance_direction_evidence.json")
OUTPUT_DIR = Path(__file__).with_name("output")
VERSION = "performance_signed_core_audit_0.1.0"

SIGNED_STATUSES = {"POSITIVE_SUPPORTED", "NEGATIVE_SUPPORTED"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit direction-supported performance core")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def feature_version_and_names() -> tuple[str, list[str]]:
    catalog = load_json(FEATURE_CATALOG)
    specs = catalog.get("ratio_features", []) + catalog.get("per90_features", [])
    return str(catalog["feature_version"]), [str(x["name"]) for x in specs]


def build_audit(db_path: Path) -> dict:
    feature_version, approved = feature_version_and_names()
    mapping = load_json(MAPPING_FILE)
    directions = load_json(DIRECTION_FILE)

    primary_dimension = {
        str(item["feature_name"]): str(item["primary_dimension"])
        for item in mapping.get("feature_mapping", [])
    }
    dimension_scope = {
        str(name): str(meta.get("scope", "unknown"))
        for name, meta in mapping.get("dimensions", {}).items()
    }
    direction_status = {
        str(item["feature_name"]): str(item["direction_status"])
        for item in directions.get("features", [])
    }

    signed_features = [
        name for name in approved if direction_status.get(name) in SIGNED_STATUSES
    ]
    contextual_features = [
        name for name in approved if direction_status.get(name) == "CONTEXT_DEPENDENT"
    ]

    with duckdb.connect(str(db_path), read_only=True) as con:
        played = con.execute(
            """
            SELECT match_id, player_id, minutes_played, primary_role
            FROM player_match
            WHERE minutes_played > 0
            """
        ).fetchdf()
        if played.empty:
            raise RuntimeError("No played player_match rows available")

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

    total_played = int(len(played))
    long = long[long["feature_name"].isin(approved)].copy()

    feature_rows: list[dict] = []
    for name in approved:
        values = long.loc[long["feature_name"] == name, "feature_value"]
        non_null = int(values.notna().sum())
        status = direction_status.get(name, "MISSING")
        feature_rows.append(
            {
                "feature_name": name,
                "primary_dimension": primary_dimension.get(name),
                "direction_status": status,
                "signed": status in SIGNED_STATUSES,
                "non_null_rows": non_null,
                "played_rows": total_played,
                "coverage_rate": non_null / total_played if total_played else None,
            }
        )

    feature_df = pd.DataFrame(feature_rows)

    wide = long.pivot_table(
        index=["match_id", "player_id"],
        columns="feature_name",
        values="feature_value",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None

    dimensions = list(mapping.get("dimensions", {}).keys())
    dimension_rows: list[dict] = []
    for dimension in dimensions:
        all_names = [
            name for name in approved if primary_dimension.get(name) == dimension
        ]
        signed_names = [name for name in all_names if name in signed_features]
        contextual_names = [name for name in all_names if name in contextual_features]

        existing_signed = [name for name in signed_names if name in wide.columns]
        if existing_signed:
            any_signed_rows = int(wide[existing_signed].notna().any(axis=1).sum())
            all_signed_rows = int(wide[existing_signed].notna().all(axis=1).sum())
        else:
            any_signed_rows = 0
            all_signed_rows = 0

        dimension_rows.append(
            {
                "dimension": dimension,
                "scope": dimension_scope.get(dimension),
                "total_features": len(all_names),
                "signed_features": len(signed_names),
                "contextual_features": len(contextual_names),
                "signed_feature_names": signed_names,
                "contextual_feature_names": contextual_names,
                "rows_with_any_signed_evidence": any_signed_rows,
                "rows_with_all_signed_evidence": all_signed_rows,
                "played_rows": total_played,
                "coverage_any_signed": any_signed_rows / total_played if total_played else None,
                "coverage_all_signed": all_signed_rows / total_played if total_played else None,
                "signed_core_present": len(signed_names) > 0,
            }
        )

    dim_df = pd.DataFrame(dimension_rows)
    dimensions_without_signed = sorted(
        dim_df.loc[~dim_df["signed_core_present"], "dimension"].astype(str).tolist()
    )
    outfield_dimensions = dim_df[dim_df["scope"] != "goalkeeper_only"]
    outfield_without_signed = sorted(
        outfield_dimensions.loc[
            ~outfield_dimensions["signed_core_present"], "dimension"
        ].astype(str).tolist()
    )
    goalkeeping = dim_df[dim_df["dimension"] == "goalkeeping"]
    goalkeeping_signed_present = bool(
        not goalkeeping.empty and bool(goalkeeping.iloc[0]["signed_core_present"])
    )

    if outfield_without_signed:
        conclusion = "OUTFIELD_SIGNED_CORE_INCOMPLETE"
    elif not goalkeeping_signed_present:
        conclusion = "OUTFIELD_SIGNED_CORE_AVAILABLE_GOALKEEPER_SEPARATE_VALIDATION_REQUIRED"
    else:
        conclusion = "SIGNED_CORE_AVAILABLE_ALL_DIMENSIONS_WEIGHT_VALIDATION_REQUIRED"

    return {
        "version": VERSION,
        "status": "AUDIT_ONLY_NO_SCORE_CREATED",
        "summary": {
            "played_rows": total_played,
            "players": int(played["player_id"].nunique()),
            "matches": int(played["match_id"].nunique()),
            "approved_features": len(approved),
            "signed_features": len(signed_features),
            "contextual_features": len(contextual_features),
            "dimensions": len(dimensions),
            "dimensions_without_signed_core": len(dimensions_without_signed),
            "outfield_dimensions_without_signed_core": len(outfield_without_signed),
            "goalkeeping_signed_core_present": goalkeeping_signed_present,
            "conclusion": conclusion,
        },
        "dimensions_without_signed_core": dimensions_without_signed,
        "outfield_dimensions_without_signed_core": outfield_without_signed,
        "feature_coverage": feature_rows,
        "dimension_coverage": dimension_rows,
        "rules": [
            "No dimension or global score is created in PERF-05.",
            "No standardization, normalization or equal-weight assumption is introduced.",
            "CONTEXT_DEPENDENT metrics remain visible but are not silently assigned a sign.",
            "A dimension with no direction-supported feature is not forced into a score.",
            "Goalkeeping may require a separate score path if its available metrics remain context-only.",
        ],
    }


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# PERF-05 — Signed core feasibility audit",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
    ]
    for key, value in s.items():
        lines.append(f"- {key}: {value}")

    lines.extend([
        "",
        "## Dimension coverage",
        "",
        "| Dimension | Scope | Signed | Contextual | Any signed rows | All signed rows |",
        "|---|---|---:|---:|---:|---:|",
    ])
    for row in result["dimension_coverage"]:
        lines.append(
            f"| {row['dimension']} | {row['scope']} | {row['signed_features']} | "
            f"{row['contextual_features']} | {row['rows_with_any_signed_evidence']} | "
            f"{row['rows_with_all_signed_evidence']} |"
        )

    lines.extend(["", "## Guardrails"])
    for rule in result["rules"]:
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

    print("PERF-05 SIGNED CORE FEASIBILITY AUDIT: COMPLETE")
    print(f"version={VERSION}")
    print(f"db: {db_path}")
    print(
        f"played_rows={s['played_rows']} players={s['players']} matches={s['matches']} "
        f"approved_features={s['approved_features']}"
    )
    print(
        f"signed_features={s['signed_features']} contextual_features={s['contextual_features']} "
        f"dimensions={s['dimensions']}"
    )
    print(
        f"dimensions_without_signed_core={s['dimensions_without_signed_core']} "
        f"outfield_without_signed_core={s['outfield_dimensions_without_signed_core']} "
        f"goalkeeping_signed_core_present={s['goalkeeping_signed_core_present']}"
    )
    if result["dimensions_without_signed_core"]:
        print("dimensions_without_signed=" + ",".join(result["dimensions_without_signed_core"]))
    print(f"conclusion={s['conclusion']}")
    print("No dimension score, weights, normalization, thresholds, ranking or recommendation were created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "performance_signed_core_audit.json"
        md_path = OUTPUT_DIR / "performance_signed_core_audit.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
