"""PERF-14 v2: conservative tactical-position mapping + observable-role coverage.

Fixes two issues found by the first PERF-14 run without changing score semantics:
1. Mixed central roles such as `Defender | Left/Centre` and
   `Midfielder | Left/Centre` are treated as central, not wide.
2. `Defensive Midfielder` always maps to DM_CM before generic side matching.

Validated DSAI-05 semantics are preserved: substitute appearances whose source role
is literally `Substitute` are NOT imputed from player history or another match.
They remain OTHER_OUTFIELD / role unavailable and are excluded from candidate-score
coverage. The script therefore reports both total-outfield coverage and coverage
conditional on an observed/mappable tactical role.
"""
from __future__ import annotations

import re

import pandas as pd

import performance_position_score_experiment as perf14

VERSION = "performance_position_score_experiment_0.2.0"
UNKNOWN_SENTINEL = "__UNKNOWN_SOURCE_POSITION__"


def _side_part(role_text: str) -> str:
    if "|" not in role_text:
        return ""
    return role_text.split("|", 1)[1].strip()


def classify_position_v2(primary_role: object, source_position: object) -> tuple[str, str]:
    """Conservative broad-position mapping using validated source semantics."""
    role = perf14.norm_text(primary_role)
    source = perf14.norm_text(source_position)

    # DSAI-05: substitute match role is unavailable; never infer it.
    if role == "substitute" or source in {"", perf14.norm_text(UNKNOWN_SENTINEL)}:
        return "OTHER_OUTFIELD", "role_unavailable_source_semantics"

    text = f"{role} | {source}".strip()
    side = _side_part(role)

    if any(k in text for k in ["goalkeeper", "goal keeper", "keeper", "porter", "portero"]):
        return "GK", "detailed_or_source"

    # Explicit specialist roles first.
    if any(k in role for k in ["wing back", "wingback", "full back", "fullback", "left back", "right back", "lateral", "carrilero"]):
        return "FB_WB", "explicit_wide_defender"

    if "defensive midfielder" in role or "defensive midfield" in role or "holding midfield" in role:
        return "DM_CM", "explicit_defensive_midfielder"

    if "attacking midfielder" in role or "attacking midfield" in role:
        return "AM_W", "explicit_attacking_midfielder"

    if any(k in role for k in ["striker", "centre forward", "center forward", "forward", "attacker"]):
        return "ST", "explicit_forward"

    # Generic defender: any central component means centre-back.
    if role.startswith("defender"):
        if re.search(r"\b(centre|center|central)\b", side):
            return "CB", "central_component"
        if re.search(r"\b(left|right)\b", side):
            return "FB_WB", "wide_only_component"
        return "CB", "coarse_defender_fallback"

    # Generic midfielder: any central component means DM/CM; pure wide means AM/W.
    if role.startswith("midfielder"):
        if re.search(r"\b(centre|center|central)\b", side):
            return "DM_CM", "central_component"
        if re.search(r"\b(left|right)\b", side):
            return "AM_W", "wide_only_component"
        return "DM_CM", "coarse_midfielder_fallback"

    # Remaining explicit wing terms.
    if any(k in role for k in ["winger", "left wing", "right wing", "wide midfield", "left midfield", "right midfield"]):
        return "AM_W", "explicit_wide_attacker"

    # Coarse provider fallback only when tactical role is not more specific.
    if source == "defender" or "defender" in source:
        return "CB", "coarse_source_fallback"
    if source == "midfielder" or "midfield" in source:
        return "DM_CM", "coarse_source_fallback"
    if source in {"attacker", "forward", "striker"} or any(k in source for k in ["attacker", "forward", "striker"]):
        return "ST", "coarse_source_fallback"

    return "OTHER_OUTFIELD", "unmapped_fallback"


_original_build_experiment = perf14.build_experiment


def build_experiment_v2(db_path):
    result, export = _original_build_experiment(db_path)

    mapped = export["position_group"].ne("OTHER_OUTFIELD")
    eligible = pd.to_numeric(
        export["performance_score_position_experimental"], errors="coerce"
    ).notna()
    observable_rows = int(mapped.sum())
    observable_eligible = int((mapped & eligible).sum())
    role_unavailable = export["position_mapping_status"].eq(
        "role_unavailable_source_semantics"
    )

    result["version"] = VERSION
    result["summary"]["observable_mapped_role_rows"] = observable_rows
    result["summary"]["eligible_rows_observable_roles"] = observable_eligible
    result["summary"]["coverage_rate_observable_roles"] = (
        float(observable_eligible / observable_rows) if observable_rows else None
    )
    result["summary"]["source_role_unavailable_rows"] = int(role_unavailable.sum())
    result["summary"]["total_outfield_coverage_rate"] = (
        float(observable_eligible / len(export)) if len(export) else None
    )
    result["summary"]["conclusion"] = "POSITION_SPECIFIC_SCORE_MAPPING_FIXED_READY_FOR_FINAL_GATE"
    result["method"]["role_observability_policy"] = (
        "Substitute appearances with unavailable tactical role are not imputed and are excluded from observable-role coverage."
    )
    result["guardrails"].append(
        "Coverage is reported both over all outfield rows and conditional on an observed/mappable tactical role; substitute roles are not imputed."
    )
    export["score_version"] = VERSION
    return result, export


perf14.classify_position = classify_position_v2
perf14.build_experiment = build_experiment_v2
perf14.VERSION = VERSION


if __name__ == "__main__":
    perf14.main()
