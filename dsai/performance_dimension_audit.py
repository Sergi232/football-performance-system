"""PERF-02: audit performance-dimension evidence before signs, weights or a global score.

This stage is deliberately descriptive. It does NOT create:
- a performance score;
- positive/negative metric directions;
- domain/global weights;
- thresholds, percentiles, rankings or recommendations.

It audits the current FEATURE-01 and N4000-N7000 evidence structure so the next
phase can validate metric directions and construct coverage without hiding approved
variables that are currently outside the expert domain catalog.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
FEATURE_CATALOG = ROOT / "features" / "catalog.json"
DOMAIN_CATALOG = ROOT / "decision_tree" / "domain_catalog.json"
OUTPUT_DIR = Path(__file__).with_name("output")
VERSION = "performance_dimension_audit_0.1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit performance-dimension evidence")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def clean(value):
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def records(df: pd.DataFrame) -> list[dict]:
    return [{k: clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def feature_catalog() -> tuple[str, list[dict]]:
    catalog = load_json(FEATURE_CATALOG)
    features = catalog.get("ratio_features", []) + catalog.get("per90_features", [])
    return str(catalog["feature_version"]), features


def domain_catalog() -> list[dict]:
    return load_json(DOMAIN_CATALOG).get("domain_nodes", [])


def describe_series(series: pd.Series) -> dict:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return {
            "non_null_rows": 0,
            "distinct_values": 0,
            "zero_rows": 0,
            "zero_rate_observed": None,
            "min": None,
            "p25": None,
            "median": None,
            "p75": None,
            "max": None,
        }
    return {
        "non_null_rows": int(len(numeric)),
        "distinct_values": int(numeric.nunique(dropna=True)),
        "zero_rows": int((numeric == 0).sum()),
        "zero_rate_observed": float((numeric == 0).mean()),
        "min": float(numeric.min()),
        "p25": float(numeric.quantile(0.25)),
        "median": float(numeric.median()),
        "p75": float(numeric.quantile(0.75)),
        "max": float(numeric.max()),
    }


def direction_policy(metric_role: str) -> dict:
    role = str(metric_role or "unknown")
    if role in {"volume", "context"}:
        note = (
            "Context-dependent metric role. Higher/lower cannot be interpreted as better/worse "
            "without external football justification and role context."
        )
        route = "CONTEXT_DEPENDENT_DIRECTION_VALIDATION_REQUIRED"
    elif role in {"output", "efficiency", "cost"}:
        note = (
            "Semantic role is informative but does not authorize a positive/negative sign. "
            "Direction requires literature/expert/empirical validation."
        )
        route = "SEMANTIC_PRIOR_ONLY_DIRECTION_VALIDATION_REQUIRED"
    else:
        note = "No approved performance direction exists."
        route = "DIRECTION_VALIDATION_REQUIRED"
    return {"direction_status": route, "direction": None, "note": note}


def build_audit(db_path: Path) -> dict:
    feature_version, feature_specs = feature_catalog()
    domain_nodes = domain_catalog()
    feature_names = [str(item["name"]) for item in feature_specs]
    feature_groups = {str(item["name"]): str(item.get("group", "unknown")) for item in feature_specs}

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

    total_played = int(len(played))
    played_roles = played.copy()
    played_roles["tactical_role_valid"] = (
        played_roles["primary_role"].notna()
        & played_roles["primary_role"].astype(str).str.strip().ne("")
        & played_roles["primary_role"].astype(str).str.strip().str.lower().ne("substitute")
    )
    role_keys = set(
        zip(
            played_roles.loc[played_roles["tactical_role_valid"], "match_id"],
            played_roles.loc[played_roles["tactical_role_valid"], "player_id"],
        )
    )

    wide = feature_long.pivot_table(
        index=["match_id", "player_id"],
        columns="feature_name",
        values="feature_value",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    for name in feature_names:
        if name not in wide.columns:
            wide[name] = pd.NA

    feature_to_nodes: dict[str, list[dict]] = defaultdict(list)
    for node in domain_nodes:
        feature_to_nodes[str(node["feature"])].append(node)

    metric_rows: list[dict] = []
    for spec in feature_specs:
        name = str(spec["name"])
        desc = describe_series(wide[name])
        nodes = feature_to_nodes.get(name, [])
        observed_keys = set(
            zip(
                wide.loc[wide[name].notna(), "match_id"],
                wide.loc[wide[name].notna(), "player_id"],
            )
        )
        role_observed = len(observed_keys & role_keys)

        metric_roles = sorted({str(node.get("metric_role", "unknown")) for node in nodes})
        families = sorted({str(node.get("family")) for node in nodes})
        labels = sorted({str(node.get("label")) for node in nodes})

        if len(metric_roles) == 1:
            policy = direction_policy(metric_roles[0])
        elif len(metric_roles) > 1:
            policy = {
                "direction_status": "MULTIPLE_DOMAIN_SEMANTICS_REQUIRES_EXPLICIT_POLICY",
                "direction": None,
                "note": "The same feature appears with more than one metric role; no sign can be inferred.",
            }
        else:
            policy = {
                "direction_status": "UNMAPPED_FEATURE_DIRECTION_VALIDATION_REQUIRED",
                "direction": None,
                "note": "Approved FEATURE-01 metric is not currently represented in N4000-N7000.",
            }

        metric_rows.append(
            {
                "feature_name": name,
                "feature_group": feature_groups.get(name),
                "mapped_node_count": len(nodes),
                "families": families,
                "node_labels": labels,
                "metric_roles": metric_roles,
                "coverage_rows": desc["non_null_rows"],
                "coverage_rate": desc["non_null_rows"] / total_played if total_played else None,
                "role_context_rows": role_observed,
                "role_context_rate_within_observed": (
                    role_observed / desc["non_null_rows"] if desc["non_null_rows"] else None
                ),
                **desc,
                **policy,
            }
        )

    metrics = pd.DataFrame(metric_rows)

    family_rows: list[dict] = []
    for family in sorted({str(node["family"]) for node in domain_nodes}):
        nodes = [node for node in domain_nodes if str(node["family"]) == family]
        names = sorted({str(node["feature"]) for node in nodes})
        existing = [name for name in names if name in wide.columns]
        any_evidence = int(wide[existing].notna().any(axis=1).sum()) if existing else 0
        all_evidence = int(wide[existing].notna().all(axis=1).sum()) if existing else 0
        family_rows.append(
            {
                "family": family,
                "nodes": len(nodes),
                "unique_features": len(names),
                "played_rows_with_any_evidence": any_evidence,
                "played_rows_with_all_mapped_features": all_evidence,
                "played_rows": total_played,
                "coverage_any_rate": any_evidence / total_played if total_played else None,
                "coverage_all_rate": all_evidence / total_played if total_played else None,
                "feature_names": names,
            }
        )

    duplicate_features = [
        {
            "feature_name": feature,
            "node_count": len(nodes),
            "nodes": [str(node["node_id"]) for node in nodes],
            "families": sorted({str(node["family"]) for node in nodes}),
            "metric_roles": sorted({str(node.get("metric_role", "unknown")) for node in nodes}),
        }
        for feature, nodes in sorted(feature_to_nodes.items())
        if len(nodes) > 1
    ]

    mapped_features = set(feature_to_nodes)
    approved_features = set(feature_names)
    unmapped_features = sorted(approved_features - mapped_features)
    unknown_domain_features = sorted(mapped_features - approved_features)

    unmapped_by_group = dict(Counter(feature_groups.get(name, "unknown") for name in unmapped_features))

    # Explicitly surface groups that are especially relevant to a universal player score.
    goalkeeping_features = sorted(
        name for name in feature_names if feature_groups.get(name) in {"goalkeeping", "goalkeeping_context"}
    )
    discipline_features = sorted(
        name for name in feature_names if feature_groups.get(name) == "discipline"
    )
    one_v_one_features = sorted(
        name for name in feature_names if feature_groups.get(name) == "one_v_one"
    )

    if feature_long.empty or int(metrics["coverage_rows"].sum()) == 0:
        conclusion = "INSUFFICIENT_DIMENSION_EVIDENCE"
    elif unknown_domain_features:
        conclusion = "CATALOG_INCONSISTENCY_REQUIRES_FIX"
    elif unmapped_features:
        conclusion = "DIMENSION_MAPPING_AND_DIRECTION_VALIDATION_REQUIRED"
    else:
        conclusion = "DIRECTION_VALIDATION_REQUIRED"

    return {
        "version": VERSION,
        "status": "AUDIT_ONLY_NO_SCORE_CREATED",
        "summary": {
            "played_rows": total_played,
            "players": int(played["player_id"].nunique()),
            "matches": int(played["match_id"].nunique()),
            "feature_version": feature_version,
            "approved_features": len(feature_names),
            "domain_nodes": len(domain_nodes),
            "mapped_unique_features": len(mapped_features & approved_features),
            "unmapped_approved_features": len(unmapped_features),
            "duplicate_mapped_features": len(duplicate_features),
            "role_context_rows": int(played_roles["tactical_role_valid"].sum()),
            "conclusion": conclusion,
        },
        "family_evidence": family_rows,
        "metric_evidence": records(metrics.sort_values(["feature_group", "feature_name"])),
        "duplicate_feature_mappings": duplicate_features,
        "unmapped_approved_features": [
            {"feature_name": name, "group": feature_groups.get(name)} for name in unmapped_features
        ],
        "unmapped_by_group": unmapped_by_group,
        "unknown_domain_features": unknown_domain_features,
        "coverage_focus": {
            "goalkeeping_features": goalkeeping_features,
            "discipline_features": discipline_features,
            "one_v_one_features": one_v_one_features,
        },
        "direction_policy": {
            "status": "UNVALIDATED",
            "rules": [
                "metric_role=output/efficiency/cost is a semantic prior only, not an approved sign",
                "metric_role=volume/context is explicitly context-dependent",
                "no sign is inferred from correlation, prevalence or variance",
                "role/position may contextualize a metric but does not define its value automatically",
            ],
        },
        "rules": [
            "No performance score or dimension score is created in PERF-02.",
            "No positive/negative direction is assigned automatically.",
            "No weights or thresholds are created.",
            "Approved features outside N4000-N7000 remain visible and must be dispositioned explicitly.",
            "Duplicate feature mappings are surfaced so one metric is not silently counted twice later.",
            "Goalkeeping and discipline coverage are surfaced because a universal player score cannot silently ignore them.",
        ],
    }


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# PERF-02 — Performance dimension evidence audit",
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
        "## Family evidence",
        "",
        "| Family | Nodes | Unique features | Any evidence | All mapped features | Played rows |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for row in result["family_evidence"]:
        lines.append(
            f"| {row['family']} | {row['nodes']} | {row['unique_features']} | "
            f"{row['played_rows_with_any_evidence']} | {row['played_rows_with_all_mapped_features']} | "
            f"{row['played_rows']} |"
        )

    lines.extend(["", "## Approved features not mapped into N4000-N7000"])
    if result["unmapped_approved_features"]:
        for item in result["unmapped_approved_features"]:
            lines.append(f"- `{item['feature_name']}` — group `{item['group']}`")
    else:
        lines.append("- None.")

    lines.extend(["", "## Duplicate mappings"])
    if result["duplicate_feature_mappings"]:
        for item in result["duplicate_feature_mappings"]:
            lines.append(
                f"- `{item['feature_name']}` → {', '.join(item['nodes'])} "
                f"({', '.join(item['families'])})"
            )
    else:
        lines.append("- None.")

    lines.extend(["", "## Direction policy", ""])
    for rule in result["direction_policy"]["rules"]:
        lines.append(f"- {rule}")

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

    print("PERF-02 PERFORMANCE DIMENSION AUDIT: COMPLETE")
    print(f"version={VERSION}")
    print(f"db: {db_path}")
    print(
        f"played_rows={s['played_rows']} players={s['players']} matches={s['matches']} "
        f"approved_features={s['approved_features']} domain_nodes={s['domain_nodes']}"
    )
    print(
        f"mapped_unique_features={s['mapped_unique_features']} "
        f"unmapped_approved_features={s['unmapped_approved_features']} "
        f"duplicate_mapped_features={s['duplicate_mapped_features']}"
    )
    if result["unmapped_approved_features"]:
        print(
            "unmapped_features="
            + ",".join(item["feature_name"] for item in result["unmapped_approved_features"])
        )
    if result["duplicate_feature_mappings"]:
        print(
            "duplicate_features="
            + ",".join(item["feature_name"] for item in result["duplicate_feature_mappings"])
        )
    print(f"role_context={s['role_context_rows']}/{s['played_rows']}")
    print(f"conclusion={s['conclusion']}")
    print("No score, signs, weights, thresholds, ranking or recommendation was created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "performance_dimension_audit.json"
        md_path = OUTPUT_DIR / "performance_dimension_audit.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
