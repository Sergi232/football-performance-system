"""PERF-07: validate goalkeeper context/provenance for candidate save_rate.

Candidate from PERF-06:
    save_rate = saves / (saves + goals_conceded)

Important provider semantic distinction:
- `saves` is the goalkeeper-specific event signal used for contamination checks;
- `goals_conceded` can be populated for outfield players as match/player context and
  therefore MUST NOT by itself be treated as a goalkeeper event.

This audit does not add the feature to FEATURE-01 and does not create scores,
weights, thresholds, rankings or recommendations.
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
OUTPUT_DIR = Path(__file__).with_name("output")
VERSION = "goalkeeper_save_rate_context_audit_0.1.1"
EXPECTED_GK_POSITION = "Goalkeeper"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit goalkeeper context for save_rate")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def source_position(role: object) -> str | None:
    if role is None or pd.isna(role):
        return None
    text = str(role).strip()
    if not text or text == "Substitute":
        return None
    return text.split(" | ", 1)[0].strip() or None


def build_audit(db_path: Path) -> dict:
    with duckdb.connect(str(db_path), read_only=True) as con:
        frame = con.execute(
            """
            SELECT
                pm.match_id,
                pm.player_id,
                pm.minutes_played,
                pm.primary_role,
                rs.saves,
                rs.goals_conceded
            FROM player_match pm
            JOIN player_match_raw_stats rs
              ON rs.match_id = pm.match_id
             AND rs.player_id = pm.player_id
            WHERE pm.minutes_played > 0
            """
        ).fetchdf()

    frame["source_position"] = frame["primary_role"].map(source_position)
    saves = pd.to_numeric(frame["saves"], errors="coerce")
    conceded = pd.to_numeric(frame["goals_conceded"], errors="coerce")

    both = saves.notna() & conceded.notna()
    denominator = saves + conceded
    candidate_mask = both & (denominator > 0)
    candidates = frame.loc[candidate_mask].copy()
    candidates["shots_on_target_faced"] = denominator.loc[candidate_mask]
    candidates["save_rate"] = saves.loc[candidate_mask] / denominator.loc[candidate_mask]

    # Source-backed player position history is used only to audit provenance, not
    # to infer a tactical role for product scoring or prediction.
    history: dict[str, set[str]] = defaultdict(set)
    for row in frame[["player_id", "source_position"]].dropna().itertuples(index=False):
        history[str(row.player_id)].add(str(row.source_position))

    current_counts = Counter(
        "<UNKNOWN>" if pd.isna(pos) or pos is None else str(pos)
        for pos in candidates["source_position"].tolist()
    )

    classifications: list[dict] = []
    for row in candidates.itertuples(index=False):
        pid = str(row.player_id)
        current = source_position(row.primary_role)
        observed = sorted(history.get(pid, set()))
        has_gk_history = EXPECTED_GK_POSITION in observed
        has_non_gk_history = any(pos != EXPECTED_GK_POSITION for pos in observed)

        if current == EXPECTED_GK_POSITION:
            status = "CURRENT_ROLE_GOALKEEPER"
        elif current is not None:
            status = "CURRENT_ROLE_NON_GOALKEEPER_CONFLICT"
        elif has_gk_history and not has_non_gk_history:
            status = "CURRENT_ROLE_UNKNOWN_SOURCE_HISTORY_GK_ONLY"
        elif has_gk_history and has_non_gk_history:
            status = "CURRENT_ROLE_UNKNOWN_MIXED_POSITION_HISTORY"
        else:
            status = "CURRENT_ROLE_UNKNOWN_NO_GK_SOURCE_EVIDENCE"

        classifications.append(
            {
                "match_id": str(row.match_id),
                "player_id": pid,
                "primary_role": None if pd.isna(row.primary_role) else str(row.primary_role),
                "source_position": current,
                "observed_source_positions_for_player": observed,
                "saves": float(row.saves),
                "goals_conceded": float(row.goals_conceded),
                "shots_on_target_faced": float(row.shots_on_target_faced),
                "save_rate": float(row.save_rate),
                "context_status": status,
            }
        )

    status_counts = Counter(x["context_status"] for x in classifications)
    direct_conflicts = status_counts.get("CURRENT_ROLE_NON_GOALKEEPER_CONFLICT", 0)
    mixed_history = status_counts.get("CURRENT_ROLE_UNKNOWN_MIXED_POSITION_HISTORY", 0)
    no_gk_evidence = status_counts.get("CURRENT_ROLE_UNKNOWN_NO_GK_SOURCE_EVIDENCE", 0)
    direct_gk_rows = status_counts.get("CURRENT_ROLE_GOALKEEPER", 0)
    validated_rows = direct_gk_rows + status_counts.get(
        "CURRENT_ROLE_UNKNOWN_SOURCE_HISTORY_GK_ONLY", 0
    )

    # Provider semantics: saves are goalkeeper-specific; goals_conceded can be
    # contextual and appear on outfield player rows. Only positive saves are a
    # valid contamination test for goalkeeper-event assignment.
    positive_save_mask = saves.fillna(0) > 0
    positive_save_rows = frame.loc[positive_save_mask].copy()
    positive_save_non_gk_current = int(
        (
            positive_save_rows["source_position"].notna()
            & (positive_save_rows["source_position"] != EXPECTED_GK_POSITION)
        ).sum()
    )

    positive_conceded_mask = conceded.fillna(0) > 0
    positive_conceded_rows = frame.loc[positive_conceded_mask].copy()
    positive_conceded_non_gk_current = int(
        (
            positive_conceded_rows["source_position"].notna()
            & (positive_conceded_rows["source_position"] != EXPECTED_GK_POSITION)
        ).sum()
    )

    if candidates.empty:
        conclusion = "SAVE_RATE_CONTEXT_BLOCKED_NO_DERIVABLE_ROWS"
    elif direct_conflicts > 0 or positive_save_non_gk_current > 0:
        conclusion = "SAVE_RATE_CONTEXT_CONTAMINATION_REQUIRES_FIX"
    elif mixed_history > 0 or no_gk_evidence > 0:
        conclusion = "SAVE_RATE_CONTEXT_LIMITED_UNRESOLVED_ROLE_EVIDENCE"
    elif direct_gk_rows == len(candidates):
        conclusion = "SAVE_RATE_GOALKEEPER_CONTEXT_VALIDATED_FEATURE_ADMISSION_READY"
    elif validated_rows == len(candidates):
        conclusion = "SAVE_RATE_GOALKEEPER_CONTEXT_VALIDATED_WITH_HISTORY_LIMITATION"
    else:
        conclusion = "SAVE_RATE_CONTEXT_REVIEW_REQUIRED"

    return {
        "version": VERSION,
        "status": "AUDIT_ONLY_NO_FEATURE_CATALOG_MUTATION",
        "summary": {
            "played_rows": int(len(frame)),
            "candidate_save_rate_rows": int(len(candidates)),
            "candidate_players": int(candidates["player_id"].nunique()) if len(candidates) else 0,
            "candidate_matches": int(candidates["match_id"].nunique()) if len(candidates) else 0,
            "direct_goalkeeper_candidate_rows": int(direct_gk_rows),
            "validated_context_rows": int(validated_rows),
            "direct_current_role_conflicts": int(direct_conflicts),
            "unknown_mixed_history_rows": int(mixed_history),
            "unknown_no_gk_evidence_rows": int(no_gk_evidence),
            "positive_save_rows": int(len(positive_save_rows)),
            "positive_save_current_non_gk_rows": positive_save_non_gk_current,
            "positive_goals_conceded_rows": int(len(positive_conceded_rows)),
            "positive_goals_conceded_current_non_gk_rows": positive_conceded_non_gk_current,
            "conclusion": conclusion,
        },
        "candidate_current_source_position_counts": dict(sorted(current_counts.items())),
        "context_status_counts": dict(sorted(status_counts.items())),
        "candidate_rows": classifications,
        "provider_semantics": {
            "saves": "goalkeeper-specific contamination signal",
            "goals_conceded": (
                "context field that may be populated for outfield players; non-GK positive values "
                "are informational and are not treated as goalkeeper-event contamination"
            ),
            "admission_rule": (
                "save_rate is only admissible as a role-specific feature on rows whose current "
                "source_position is Goalkeeper; history is audit evidence only"
            ),
        },
        "rules": [
            "The only expected source position label for direct goalkeeper validation is the source-backed value 'Goalkeeper'.",
            "Positive saves on a current non-goalkeeper row are contamination; positive goals_conceded alone are not.",
            "Player position history is used only for provenance audit when the current role is unavailable; it is not written back or used as a performance predictor.",
            "No xGOT/PSxG or shot-quality adjustment is invented.",
            "No missing value is imputed.",
            "No feature catalog mutation, score, weight, threshold, ranking or recommendation is created in PERF-07.",
        ],
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# PERF-07 — Goalkeeper save-rate context audit",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Current source-position counts"])
    for key, value in result["candidate_current_source_position_counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Context status counts"])
    for key, value in result["context_status_counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Provider semantics"])
    for key, value in result["provider_semantics"].items():
        lines.append(f"- `{key}`: {value}")
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
    print("PERF-07 GOALKEEPER SAVE RATE CONTEXT AUDIT: COMPLETE")
    print(f"version={VERSION}")
    print(f"db: {db_path}")
    print(
        f"played_rows={s['played_rows']} candidate_rows={s['candidate_save_rate_rows']} "
        f"players={s['candidate_players']} matches={s['candidate_matches']}"
    )
    print(
        f"direct_gk_candidates={s['direct_goalkeeper_candidate_rows']} "
        f"validated_context_rows={s['validated_context_rows']} "
        f"direct_conflicts={s['direct_current_role_conflicts']} "
        f"unknown_mixed={s['unknown_mixed_history_rows']} "
        f"unknown_no_gk_evidence={s['unknown_no_gk_evidence_rows']}"
    )
    print(
        f"positive_save_rows={s['positive_save_rows']} "
        f"positive_save_current_non_gk={s['positive_save_current_non_gk_rows']}"
    )
    print(
        f"positive_goals_conceded_rows={s['positive_goals_conceded_rows']} "
        f"positive_goals_conceded_current_non_gk={s['positive_goals_conceded_current_non_gk_rows']} "
        "(informational_context_only)"
    )
    print(
        "current_positions="
        + ",".join(f"{k}:{v}" for k, v in result["candidate_current_source_position_counts"].items())
    )
    print(f"conclusion={s['conclusion']}")
    print("No feature catalog mutation, score, weights, thresholds, ranking or recommendation were created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "goalkeeper_save_rate_context_audit.json"
        md_path = OUTPUT_DIR / "goalkeeper_save_rate_context_audit.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
