"""PERF-04: validate direction-evidence coverage for all approved FEATURE-01 metrics.

This phase validates only direction classification. It does NOT create weights,
dimension scores, global scores, thresholds, percentiles, rankings or recommendations.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURE_CATALOG = ROOT / "features" / "catalog.json"
DIMENSION_MAP = Path(__file__).with_name("performance_dimension_map.json")
DIRECTION_REGISTRY = Path(__file__).with_name("performance_direction_evidence.json")
OUTPUT_DIR = Path(__file__).with_name("output")
VERSION = "performance_direction_audit_0.1.0"

ALLOWED = {
    "POSITIVE_SUPPORTED",
    "NEGATIVE_SUPPORTED",
    "CONTEXT_DEPENDENT",
    "PENDING_EVIDENCE",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def approved_features() -> list[str]:
    catalog = load_json(FEATURE_CATALOG)
    specs = catalog.get("ratio_features", []) + catalog.get("per90_features", [])
    return [str(item["name"]) for item in specs]


def build_audit() -> dict:
    approved = approved_features()
    approved_set = set(approved)

    mapping = load_json(DIMENSION_MAP)
    mapping_entries = mapping.get("feature_mapping", [])
    primary_dimension = {
        str(item.get("feature_name")): str(item.get("primary_dimension"))
        for item in mapping_entries
    }

    registry = load_json(DIRECTION_REGISTRY)
    entries = registry.get("features", [])
    names = [str(item.get("feature_name", "")) for item in entries]
    counts = Counter(names)
    name_set = set(names)

    missing = sorted(approved_set - name_set)
    unknown = sorted(name_set - approved_set)
    duplicate = sorted(name for name, n in counts.items() if n != 1)

    invalid_status = sorted(
        {
            str(item.get("direction_status"))
            for item in entries
            if str(item.get("direction_status")) not in ALLOWED
        }
    )

    mapping_missing = sorted(
        name for name in approved if name not in primary_dimension
    )

    status_counts = Counter(str(item.get("direction_status")) for item in entries)
    by_dimension: dict[str, Counter] = {}
    for item in entries:
        name = str(item.get("feature_name"))
        dimension = primary_dimension.get(name, "UNMAPPED")
        by_dimension.setdefault(dimension, Counter())[
            str(item.get("direction_status"))
        ] += 1

    no_evidence_basis = sorted(
        str(item.get("feature_name"))
        for item in entries
        if not item.get("evidence_basis")
    )
    no_reason = sorted(
        str(item.get("feature_name"))
        for item in entries
        if not str(item.get("reason", "")).strip()
    )

    pending = sorted(
        str(item.get("feature_name"))
        for item in entries
        if str(item.get("direction_status")) == "PENDING_EVIDENCE"
    )

    if missing or unknown or duplicate or invalid_status or mapping_missing:
        conclusion = "DIRECTION_REGISTRY_INCOMPLETE_OR_INVALID"
    elif no_evidence_basis or no_reason:
        conclusion = "DIRECTION_EVIDENCE_DOCUMENTATION_INCOMPLETE"
    elif pending:
        conclusion = "DIRECTION_CLASSIFICATION_PARTIAL_PENDING_EVIDENCE"
    else:
        conclusion = "DIRECTION_CLASSIFICATION_COMPLETE_CONTEXTUAL_METRICS_RETAINED"

    return {
        "version": VERSION,
        "status": "DIRECTION_EVIDENCE_AUDIT_ONLY",
        "summary": {
            "approved_features": len(approved),
            "direction_entries": len(entries),
            "covered_unique_features": len(name_set & approved_set),
            "positive_supported": int(status_counts.get("POSITIVE_SUPPORTED", 0)),
            "negative_supported": int(status_counts.get("NEGATIVE_SUPPORTED", 0)),
            "context_dependent": int(status_counts.get("CONTEXT_DEPENDENT", 0)),
            "pending_evidence": int(status_counts.get("PENDING_EVIDENCE", 0)),
            "missing_features": len(missing),
            "unknown_features": len(unknown),
            "duplicate_entries": len(duplicate),
            "invalid_statuses": len(invalid_status),
            "mapping_missing": len(mapping_missing),
            "conclusion": conclusion,
        },
        "status_counts": dict(sorted(status_counts.items())),
        "status_by_dimension": {
            dimension: dict(sorted(counter.items()))
            for dimension, counter in sorted(by_dimension.items())
        },
        "missing_features": missing,
        "unknown_features": unknown,
        "duplicate_entries": duplicate,
        "invalid_statuses": invalid_status,
        "mapping_missing": mapping_missing,
        "features_without_evidence_basis": no_evidence_basis,
        "features_without_reason": no_reason,
        "pending_features": pending,
        "literature_ids": [str(item.get("id")) for item in registry.get("literature", [])],
        "guardrails": [
            "Team-level literature is not treated as individual ground truth.",
            "Context-dependent metrics are retained for explanation/context but are not automatically signed.",
            "No weight, threshold, score, percentile, ranking or recommendation is created in PERF-04.",
            "A supported direction only authorizes later prototype testing; it does not authorize production scoring.",
        ],
    }


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# PERF-04 — Performance direction evidence audit",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
    ]
    for key, value in s.items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Direction status by dimension", ""])
    for dimension, counts in result["status_by_dimension"].items():
        text = ", ".join(f"{k}={v}" for k, v in counts.items())
        lines.append(f"- `{dimension}`: {text}")

    lines.extend(["", "## Guardrails"])
    for rule in result["guardrails"]:
        lines.append(f"- {rule}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    result = build_audit()
    s = result["summary"]

    print("PERF-04 PERFORMANCE DIRECTION AUDIT: COMPLETE")
    print(f"version={VERSION}")
    print(
        f"approved_features={s['approved_features']} direction_entries={s['direction_entries']} "
        f"covered_unique_features={s['covered_unique_features']}"
    )
    print(
        f"positive_supported={s['positive_supported']} negative_supported={s['negative_supported']} "
        f"context_dependent={s['context_dependent']} pending_evidence={s['pending_evidence']}"
    )
    print(
        f"missing={s['missing_features']} unknown={s['unknown_features']} "
        f"duplicates={s['duplicate_entries']} invalid_statuses={s['invalid_statuses']} "
        f"mapping_missing={s['mapping_missing']}"
    )
    print(f"conclusion={s['conclusion']}")
    print("No weights, score, thresholds, ranking or recommendation were created.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "performance_direction_audit.json"
    md_path = OUTPUT_DIR / "performance_direction_audit.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")
    print(f"json: {json_path}")
    print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
