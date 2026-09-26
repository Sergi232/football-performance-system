"""PERF-06: audit whether a defensible goalkeeper efficiency feature is derivable.

Candidate only:
    shots_on_target_faced = saves + goals_conceded
    save_rate = saves / (saves + goals_conceded)

This phase does NOT add the feature to FEATURE-01 and does NOT create a goalkeeper
score, weights, thresholds, rankings or recommendations.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
OUTPUT_DIR = Path(__file__).with_name("output")
VERSION = "goalkeeper_efficiency_feasibility_0.1.0"
REQUIRED_RAW = {"saves", "goals_conceded"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit goalkeeper efficiency feature feasibility")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def scalar(value):
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def build_audit(db_path: Path) -> dict:
    with duckdb.connect(str(db_path), read_only=True) as con:
        table_info = con.execute("PRAGMA table_info('player_match_raw_stats')").fetchdf()
        raw_columns = set(table_info["name"].astype(str).tolist())
        missing_raw = sorted(REQUIRED_RAW - raw_columns)

        if missing_raw:
            return {
                "version": VERSION,
                "status": "AUDIT_ONLY_NO_FEATURE_CREATED",
                "summary": {
                    "missing_required_raw_columns": missing_raw,
                    "conclusion": "GOALKEEPER_EFFICIENCY_BLOCKED_MISSING_RAW_COLUMNS",
                },
                "rules": [
                    "No goalkeeper feature or score is created in PERF-06.",
                    "Missing raw inputs are never imputed.",
                ],
            }

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
              AND (rs.saves IS NOT NULL OR rs.goals_conceded IS NOT NULL)
            """
        ).fetchdf()

    if frame.empty:
        conclusion = "GOALKEEPER_EFFICIENCY_INSUFFICIENT_RAW_EVIDENCE"
        summary = {
            "candidate_rows": 0,
            "players": 0,
            "matches": 0,
            "rows_with_both_inputs": 0,
            "rows_with_positive_denominator": 0,
            "save_rate_rows": 0,
            "conclusion": conclusion,
        }
        role_counts = []
        distribution = {}
        anomalies = []
    else:
        both = frame["saves"].notna() & frame["goals_conceded"].notna()
        derivable = frame.loc[both].copy()
        derivable["shots_on_target_faced"] = (
            pd.to_numeric(derivable["saves"], errors="coerce")
            + pd.to_numeric(derivable["goals_conceded"], errors="coerce")
        )
        positive_denominator = derivable["shots_on_target_faced"] > 0
        rates = derivable.loc[positive_denominator].copy()
        rates["save_rate"] = (
            pd.to_numeric(rates["saves"], errors="coerce")
            / rates["shots_on_target_faced"]
        )

        anomalies_df = rates[(rates["save_rate"] < 0) | (rates["save_rate"] > 1)]
        anomalies = [
            {
                "match_id": str(row.match_id),
                "player_id": str(row.player_id),
                "saves": scalar(row.saves),
                "goals_conceded": scalar(row.goals_conceded),
                "save_rate": scalar(row.save_rate),
            }
            for row in anomalies_df.itertuples(index=False)
        ]

        if len(rates) == 0:
            conclusion = "GOALKEEPER_EFFICIENCY_INSUFFICIENT_DENOMINATOR_EVIDENCE"
        elif anomalies:
            conclusion = "GOALKEEPER_EFFICIENCY_DATA_INCONSISTENCY_REQUIRES_FIX"
        else:
            conclusion = "GOALKEEPER_SAVE_RATE_DERIVABLE_CONTEXT_VALIDATION_REQUIRED"

        roles = (
            frame["primary_role"]
            .fillna("<NULL>")
            .astype(str)
            .value_counts(dropna=False)
            .reset_index()
        )
        roles.columns = ["primary_role", "rows"]
        role_counts = roles.to_dict(orient="records")

        if len(rates):
            distribution = {
                "save_rate_min": float(rates["save_rate"].min()),
                "save_rate_p25": float(rates["save_rate"].quantile(0.25)),
                "save_rate_median": float(rates["save_rate"].median()),
                "save_rate_p75": float(rates["save_rate"].quantile(0.75)),
                "save_rate_max": float(rates["save_rate"].max()),
                "shots_on_target_faced_min": float(rates["shots_on_target_faced"].min()),
                "shots_on_target_faced_median": float(rates["shots_on_target_faced"].median()),
                "shots_on_target_faced_max": float(rates["shots_on_target_faced"].max()),
            }
        else:
            distribution = {}

        summary = {
            "candidate_rows": int(len(frame)),
            "players": int(frame["player_id"].nunique()),
            "matches": int(frame["match_id"].nunique()),
            "rows_with_both_inputs": int(both.sum()),
            "rows_with_positive_denominator": int(positive_denominator.sum()),
            "save_rate_rows": int(len(rates)),
            "anomalies": int(len(anomalies)),
            "conclusion": conclusion,
        }

    return {
        "version": VERSION,
        "status": "AUDIT_ONLY_NO_FEATURE_CREATED",
        "candidate_definition": {
            "shots_on_target_faced": "saves + goals_conceded",
            "save_rate": "saves / (saves + goals_conceded)",
            "calculation_rule": "both raw inputs non-null and denominator > 0",
        },
        "summary": summary,
        "role_counts": role_counts,
        "distribution": distribution,
        "anomalies": anomalies,
        "interpretation": {
            "direction_candidate": "POSITIVE_SUPPORTED_WITH_CONTEXT",
            "reason": (
                "For observed shots on target faced, a higher saved share is a direct goalkeeper "
                "efficiency signal. It remains context-sensitive because shot quality and defensive "
                "environment are not available."
            ),
            "not_available": "No xGOT/PSxG or shot-quality adjustment is invented.",
        },
        "rules": [
            "No goalkeeper feature is added to FEATURE-01 in PERF-06.",
            "No goalkeeper or global score is created.",
            "No weight, threshold, percentile, ranking or recommendation is created.",
            "Missing saves/goals_conceded remain missing.",
            "Zero-denominator rows do not receive a fabricated save rate.",
            "save_rate cannot be interpreted as shot-quality-adjusted goal prevention.",
        ],
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# PERF-06 — Goalkeeper efficiency feasibility audit",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Candidate", ""])
    for key, value in result.get("candidate_definition", {}).items():
        lines.append(f"- {key}: `{value}`")

    if result.get("distribution"):
        lines.extend(["", "## Distribution", ""])
        for key, value in result["distribution"].items():
            lines.append(f"- {key}: {value}")

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

    print("PERF-06 GOALKEEPER EFFICIENCY FEASIBILITY: COMPLETE")
    print(f"version={VERSION}")
    print(f"db: {db_path}")
    if "missing_required_raw_columns" in s:
        print("missing_required_raw_columns=" + ",".join(s["missing_required_raw_columns"]))
    else:
        print(
            f"candidate_rows={s['candidate_rows']} players={s['players']} matches={s['matches']} "
            f"rows_with_both_inputs={s['rows_with_both_inputs']}"
        )
        print(
            f"positive_denominator={s['rows_with_positive_denominator']} "
            f"save_rate_rows={s['save_rate_rows']} anomalies={s['anomalies']}"
        )
        if result["distribution"]:
            d = result["distribution"]
            print(
                f"save_rate=min:{d['save_rate_min']:.4f} median:{d['save_rate_median']:.4f} "
                f"max:{d['save_rate_max']:.4f}"
            )
    print(f"conclusion={s['conclusion']}")
    print("No feature catalog mutation, score, weights, thresholds, ranking or recommendation was created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "goalkeeper_efficiency_feasibility.json"
        md_path = OUTPUT_DIR / "goalkeeper_efficiency_feasibility.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
