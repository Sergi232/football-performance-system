"""PERF-03: validate structural mapping of FEATURE-01 into performance dimensions.

This phase resolves coverage/mapping only. It does NOT create metric directions,
weights, thresholds, dimension scores, rankings or a global performance score.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURE_CATALOG = ROOT / "features" / "catalog.json"
DOMAIN_CATALOG = ROOT / "decision_tree" / "domain_catalog.json"
MAPPING_FILE = Path(__file__).with_name("performance_dimension_map.json")
OUTPUT_DIR = Path(__file__).with_name("output")
VERSION = "performance_dimension_mapping_audit_0.1.0"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def approved_features() -> list[str]:
    catalog = load_json(FEATURE_CATALOG)
    specs = catalog.get("ratio_features", []) + catalog.get("per90_features", [])
    return [str(item["name"]) for item in specs]


def build_audit() -> dict:
    approved = approved_features()
    approved_set = set(approved)
    mapping = load_json(MAPPING_FILE)
    entries = mapping.get("feature_mapping", [])
    dimensions = mapping.get("dimensions", {})

    mapped_names = [str(item.get("feature_name", "")) for item in entries]
    counts = Counter(mapped_names)
    mapped_set = set(mapped_names)

    missing = sorted(approved_set - mapped_set)
    unknown = sorted(mapped_set - approved_set)
    duplicate_primary = sorted(name for name, n in counts.items() if n != 1)

    invalid_dimensions = sorted(
        {
            str(item.get("primary_dimension"))
            for item in entries
            if str(item.get("primary_dimension")) not in dimensions
        }
    )

    by_dimension = Counter(str(item.get("primary_dimension")) for item in entries)

    goalkeeping_entries = [
        item for item in entries if str(item.get("primary_dimension")) == "goalkeeping"
    ]
    goalkeeping_scope_ok = (
        dimensions.get("goalkeeping", {}).get("scope") == "goalkeeper_only"
        and {str(x.get("feature_name")) for x in goalkeeping_entries}
        == {"saves_per90", "goals_conceded_per90"}
    )

    shots_entries = [item for item in entries if item.get("feature_name") == "shots_total_per90"]
    shots_primary_once = len(shots_entries) == 1
    shots_secondary_finishing = (
        shots_primary_once and "finishing" in shots_entries[0].get("secondary_context", [])
    )

    expert_nodes = load_json(DOMAIN_CATALOG).get("domain_nodes", [])
    expert_shots_nodes = [
        str(node.get("node_id"))
        for node in expert_nodes
        if str(node.get("feature")) == "shots_total_per90"
    ]

    if missing or unknown or duplicate_primary or invalid_dimensions:
        conclusion = "DIMENSION_MAPPING_INCOMPLETE_OR_INVALID"
    elif not goalkeeping_scope_ok or not shots_primary_once:
        conclusion = "DIMENSION_MAPPING_POLICY_REQUIRES_FIX"
    else:
        conclusion = "DIMENSION_MAPPING_COMPLETE_DIRECTION_VALIDATION_REQUIRED"

    return {
        "version": VERSION,
        "status": "STRUCTURAL_MAPPING_AUDIT_ONLY",
        "summary": {
            "approved_features": len(approved),
            "mapping_entries": len(entries),
            "mapped_unique_features": len(mapped_set & approved_set),
            "dimensions": len(dimensions),
            "missing_features": len(missing),
            "unknown_features": len(unknown),
            "duplicate_primary_mappings": len(duplicate_primary),
            "goalkeeping_scope_ok": goalkeeping_scope_ok,
            "shots_primary_once": shots_primary_once,
            "shots_secondary_finishing_context": shots_secondary_finishing,
            "expert_shots_nodes": len(expert_shots_nodes),
            "conclusion": conclusion,
        },
        "dimension_feature_counts": dict(sorted(by_dimension.items())),
        "missing_features": missing,
        "unknown_features": unknown,
        "duplicate_primary_mappings": duplicate_primary,
        "invalid_dimensions": invalid_dimensions,
        "expert_shots_nodes": expert_shots_nodes,
        "mapping_version": mapping.get("version"),
        "guardrails": [
            "No metric direction is assigned in PERF-03.",
            "No dimension/global weight is assigned.",
            "No score, threshold, percentile, ranking or recommendation is created.",
            "A primary dimension is a structural ownership rule, not evidence of positive/negative value.",
            "Secondary context never authorizes double counting in a future global score.",
        ],
    }


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# PERF-03 — Performance dimension mapping audit",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
    ]
    for key, value in s.items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Features per primary dimension"])
    for dimension, count in result["dimension_feature_counts"].items():
        lines.append(f"- `{dimension}`: {count}")

    lines.extend(["", "## Guardrails"])
    for rule in result["guardrails"]:
        lines.append(f"- {rule}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    result = build_audit()
    s = result["summary"]

    print("PERF-03 PERFORMANCE DIMENSION MAPPING AUDIT: COMPLETE")
    print(f"version={VERSION}")
    print(
        f"approved_features={s['approved_features']} mapping_entries={s['mapping_entries']} "
        f"mapped_unique_features={s['mapped_unique_features']} dimensions={s['dimensions']}"
    )
    print(
        f"missing={s['missing_features']} unknown={s['unknown_features']} "
        f"duplicate_primary={s['duplicate_primary_mappings']}"
    )
    print(
        f"goalkeeping_scope_ok={s['goalkeeping_scope_ok']} "
        f"shots_primary_once={s['shots_primary_once']} "
        f"shots_secondary_finishing_context={s['shots_secondary_finishing_context']}"
    )
    print("dimension_counts=" + ",".join(
        f"{k}:{v}" for k, v in result["dimension_feature_counts"].items()
    ))
    print(f"conclusion={s['conclusion']}")
    print("No signs, weights, score, thresholds, ranking or recommendation were created.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "performance_dimension_mapping_audit.json"
    md_path = OUTPUT_DIR / "performance_dimension_mapping_audit.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")
    print(f"json: {json_path}")
    print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
