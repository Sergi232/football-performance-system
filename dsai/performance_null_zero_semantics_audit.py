"""PERF-11: audit whether provider NULL counts can be interpreted as observed zero.

Only metrics with an independent atomic event representation are audited. This
script does not mutate raw data, FEATURE-01 or score outputs.
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
VERSION = "performance_null_zero_semantics_audit_0.1.0"

METRICS = {
    "shots_total": "event_shots_total",
    "goals": "event_goals",
    "yellow_cards": "event_yellow_cards",
    "red_cards": "event_red_cards",
}

SIGNED_FEATURE_IMPACT = {
    "goals": ["goals_per90"],
    "yellow_cards": ["yellow_cards_per90"],
    "red_cards": ["red_cards_per90"],
    "shots_total": [],
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit raw NULL versus observed zero semantics")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--no-write", action="store_true")
    return p.parse_args()


def build_audit(db_path: Path) -> dict:
    with duckdb.connect(str(db_path), read_only=True) as con:
        frame = con.execute(
            """
            WITH event_counts AS (
                SELECT
                    pm.match_id,
                    pm.player_id,
                    SUM(CASE WHEN e.action_type = 'SHOT' THEN 1 ELSE 0 END) AS event_shots_total,
                    SUM(CASE WHEN e.action_type = 'SHOT' AND e.outcome = 'GOAL' THEN 1 ELSE 0 END) AS event_goals,
                    SUM(
                        CASE
                            WHEN e.action_type = 'CARD' AND e.subtype = 'YELLOW' THEN 1
                            WHEN e.action_type = 'CARD'
                                 AND e.subtype = 'RED'
                                 AND COALESCE(
                                     TRY_CAST(json_extract_string(e.qualifiers, '$.also_yellow') AS BOOLEAN),
                                     FALSE
                                 ) THEN 1
                            ELSE 0
                        END
                    ) AS event_yellow_cards,
                    SUM(CASE WHEN e.action_type = 'CARD' AND e.subtype = 'RED' THEN 1 ELSE 0 END) AS event_red_cards
                FROM player_match pm
                LEFT JOIN match_events e
                  ON e.match_id = pm.match_id
                 AND e.player_id = pm.player_id
                GROUP BY pm.match_id, pm.player_id
            )
            SELECT
                pm.match_id,
                pm.player_id,
                pm.minutes_played,
                pm.primary_role,
                r.shots_total,
                r.goals,
                r.yellow_cards,
                r.red_cards,
                ec.event_shots_total,
                ec.event_goals,
                ec.event_yellow_cards,
                ec.event_red_cards
            FROM player_match pm
            JOIN player_match_raw_stats r
              ON r.match_id = pm.match_id
             AND r.player_id = pm.player_id
             AND r.source_type = 'opta_player_stats'
            JOIN event_counts ec
              ON ec.match_id = pm.match_id
             AND ec.player_id = pm.player_id
            ORDER BY pm.match_id, pm.player_id
            """
        ).fetchdf()

    diagnostics: list[dict] = []
    candidates: list[str] = []
    blocked: list[str] = []

    played_mask = pd.to_numeric(frame["minutes_played"], errors="coerce").fillna(0) > 0

    for raw_name, event_name in METRICS.items():
        raw = pd.to_numeric(frame[raw_name], errors="coerce")
        event = pd.to_numeric(frame[event_name], errors="coerce").fillna(0)

        null_mask = raw.isna()
        nonnull_mask = raw.notna()
        interpreted = raw.fillna(0)
        mismatch = interpreted != event
        nonnull_mismatch = nonnull_mask & (raw != event)
        null_event_positive = null_mask & (event > 0)

        played_null = null_mask & played_mask
        played_null_event_zero = played_null & (event == 0)
        played_null_event_positive = played_null & (event > 0)

        candidate = bool((~mismatch).all() and not null_event_positive.any())
        status = (
            "EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATE"
            if candidate
            else "NULL_AS_ZERO_NOT_VALIDATED"
        )
        if candidate:
            candidates.append(raw_name)
        else:
            blocked.append(raw_name)

        diagnostics.append(
            {
                "raw_metric": raw_name,
                "event_metric": event_name,
                "rows": int(len(frame)),
                "raw_null_rows": int(null_mask.sum()),
                "raw_zero_rows": int((raw == 0).sum()),
                "raw_positive_rows": int((raw > 0).sum()),
                "event_zero_rows": int((event == 0).sum()),
                "event_positive_rows": int((event > 0).sum()),
                "raw_null_event_zero_rows": int((null_mask & (event == 0)).sum()),
                "raw_null_event_positive_rows": int(null_event_positive.sum()),
                "raw_nonnull_event_mismatch_rows": int(nonnull_mismatch.sum()),
                "mismatch_rows_after_null_as_zero": int(mismatch.sum()),
                "played_rows": int(played_mask.sum()),
                "played_raw_null_rows": int(played_null.sum()),
                "played_raw_null_event_zero_rows": int(played_null_event_zero.sum()),
                "played_raw_null_event_positive_rows": int(played_null_event_positive.sum()),
                "signed_feature_impact": SIGNED_FEATURE_IMPACT[raw_name],
                "status": status,
            }
        )

    conclusion = (
        "EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATES_FOUND"
        if candidates
        else "NO_EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATES"
    )

    return {
        "version": VERSION,
        "status": "AUDIT_ONLY_NO_DATA_MUTATION",
        "summary": {
            "player_match_rows": int(len(frame)),
            "played_rows": int(played_mask.sum()),
            "audited_metrics": len(METRICS),
            "validated_null_as_zero_candidates": len(candidates),
            "blocked_metrics": len(blocked),
            "conclusion": conclusion,
        },
        "validated_null_as_zero_candidates": sorted(candidates),
        "blocked_metrics": sorted(blocked),
        "diagnostics": diagnostics,
        "methodological_context": [
            "DATA-04 preserves provider NULL values in the raw table.",
            "The DATA-04 importer already validates shots_total and goals against DATA-03 by interpreting source NULL as zero for the cross-check.",
            "FEATURE-01 currently keeps any raw NULL as feature NULL.",
            "This audit tests whether atomic events support a provider-specific observed-zero interpretation for selected count metrics.",
        ],
        "guardrails": [
            "No global fillna(0) policy is authorized.",
            "Only metrics with independent atomic evidence and zero contradictions can become candidates.",
            "A validated count-zero policy does not make a ratio with denominator zero defined.",
            "No raw table, feature table or score output is modified.",
            "Metrics without independent atomic evidence remain unchanged.",
            "No weight, threshold, ranking or recommendation is created.",
        ],
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# PERF-11 — NULL vs zero semantics audit",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: {value}")

    lines.extend([
        "",
        "## Metric diagnostics",
        "",
        "| Raw metric | Raw NULL | NULL + event 0 | NULL + event >0 | Non-null mismatch | All mismatch after NULL→0 | Status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ])
    for row in result["diagnostics"]:
        lines.append(
            f"| {row['raw_metric']} | {row['raw_null_rows']} | "
            f"{row['raw_null_event_zero_rows']} | {row['raw_null_event_positive_rows']} | "
            f"{row['raw_nonnull_event_mismatch_rows']} | "
            f"{row['mismatch_rows_after_null_as_zero']} | {row['status']} |"
        )

    lines.extend(["", "## Validated candidates"])
    if result["validated_null_as_zero_candidates"]:
        for name in result["validated_null_as_zero_candidates"]:
            lines.append(f"- `{name}`")
    else:
        lines.append("- none")

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

    print("PERF-11 NULL VS ZERO SEMANTICS AUDIT: COMPLETE")
    print(f"version={VERSION}")
    print(f"db: {db_path}")
    print(
        f"player_match_rows={s['player_match_rows']} played_rows={s['played_rows']} "
        f"audited_metrics={s['audited_metrics']} validated_candidates={s['validated_null_as_zero_candidates']} "
        f"blocked={s['blocked_metrics']}"
    )
    for row in result["diagnostics"]:
        print(
            f"{row['raw_metric']}: raw_null={row['raw_null_rows']} "
            f"null_event_zero={row['raw_null_event_zero_rows']} "
            f"null_event_positive={row['raw_null_event_positive_rows']} "
            f"nonnull_mismatch={row['raw_nonnull_event_mismatch_rows']} "
            f"all_mismatch_after_null0={row['mismatch_rows_after_null_as_zero']} "
            f"status={row['status']}"
        )
    print("validated_null_as_zero_candidates=" + ",".join(result["validated_null_as_zero_candidates"]))
    print(f"conclusion={s['conclusion']}")
    print("No raw data, FEATURE-01, score policy, weights, thresholds, ranking or recommendation were modified.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "performance_null_zero_semantics_audit.json"
        md_path = OUTPUT_DIR / "performance_null_zero_semantics_audit.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
