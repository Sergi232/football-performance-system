"""DSAI-05: reconstruct an auditable tactical-role target from source semantics.

This phase separates participation status from tactical role. It does not infer a
substitute's match role, forward/back-fill labels, merge classes, train a model,
create thresholds, rank players or issue recommendations.

Validated DATA-02 semantics:
- starter lineup rows expose a directly observed position (+ side when available);
- bench rows expose position='Substitute' and do not provide a reliable tactical
  match role;
- therefore non-starter appearances are kept as participation observations but
  their tactical role is intentionally missing.
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
VERSION = "dsai_role_target_0.1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconstruct a source-observed tactical-role target without inference"
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


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


def build_target(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute(
        """
        WITH base AS (
            SELECT
                pm.match_id,
                pm.team_id,
                pm.player_id,
                m.match_date,
                pm.started,
                pm.minutes_played,
                NULLIF(TRIM(pm.primary_role), '') AS raw_primary_role
            FROM player_match pm
            JOIN matches m ON m.match_id = pm.match_id
        )
        SELECT
            match_id,
            team_id,
            player_id,
            match_date,
            started,
            minutes_played,
            raw_primary_role,
            CASE
                WHEN started IS TRUE THEN 'STARTER'
                WHEN started IS FALSE AND minutes_played > 0 THEN 'SUBSTITUTE_APPEARANCE'
                WHEN started IS FALSE AND minutes_played = 0 THEN 'UNUSED_BENCH'
                ELSE 'UNKNOWN_PARTICIPATION'
            END AS participation_status,
            CASE
                WHEN started IS TRUE
                 AND raw_primary_role IS NOT NULL
                 AND LOWER(raw_primary_role) <> 'substitute'
                THEN raw_primary_role
                ELSE NULL
            END AS tactical_role,
            CASE
                WHEN started IS TRUE
                 AND raw_primary_role IS NOT NULL
                 AND LOWER(raw_primary_role) <> 'substitute'
                THEN 'OBSERVED_TACTICAL_ROLE'
                WHEN started IS TRUE
                THEN 'STARTER_ROLE_MISSING_OR_INVALID'
                WHEN started IS FALSE AND minutes_played > 0
                THEN 'TACTICAL_ROLE_UNAVAILABLE_FOR_SUBSTITUTE'
                WHEN started IS FALSE AND minutes_played = 0
                THEN 'NOT_APPLICABLE_UNUSED_BENCH'
                ELSE 'PARTICIPATION_STATUS_UNKNOWN'
            END AS target_state,
            'DATA-02_SOURCE_SEMANTICS' AS provenance
        FROM base
        ORDER BY match_date, match_id, started DESC, player_id
        """
    ).fetchdf()


def summarize(frame: pd.DataFrame) -> dict:
    target = frame[frame["target_state"].eq("OBSERVED_TACTICAL_ROLE")].copy()
    played = frame[frame["minutes_played"].fillna(0).gt(0)]

    role_distribution = (
        target.groupby("tactical_role", dropna=False)
        .agg(
            rows=("match_id", "size"),
            players=("player_id", "nunique"),
            matches=("match_id", "nunique"),
            first_date=("match_date", "min"),
            last_date=("match_date", "max"),
        )
        .reset_index()
        .sort_values(["rows", "tactical_role"], ascending=[False, True])
    )

    dependence_rows: list[dict] = []
    if not target.empty:
        counts = (
            target.groupby(["tactical_role", "player_id"])
            .size()
            .rename("player_rows")
            .reset_index()
        )
        for role, group in counts.groupby("tactical_role"):
            total = int(group["player_rows"].sum())
            top = int(group["player_rows"].max())
            dependence_rows.append(
                {
                    "tactical_role": role,
                    "rows": total,
                    "players": int(group["player_id"].nunique()),
                    "top_player_rows": top,
                    "top_player_share": (top / total) if total else None,
                }
            )
    dependence = pd.DataFrame(dependence_rows)
    if not dependence.empty:
        dependence = dependence.sort_values(
            ["players", "rows", "tactical_role"], ascending=[True, True, True]
        )

    invalid_starter = frame["target_state"].eq("STARTER_ROLE_MISSING_OR_INVALID")
    nonstarter_non_sub = (
        frame["participation_status"].eq("SUBSTITUTE_APPEARANCE")
        & frame["raw_primary_role"].notna()
        & frame["raw_primary_role"].astype(str).str.lower().ne("substitute")
    )
    substitute_remaining = (
        target["tactical_role"].astype(str).str.lower().eq("substitute").sum()
        if not target.empty
        else 0
    )

    if int(invalid_starter.sum()) > 0 or int(substitute_remaining) > 0:
        conclusion = "RECONSTRUCTION_INCONSISTENT_REVIEW_REQUIRED"
    elif target.empty:
        conclusion = "NO_CLEAN_TACTICAL_TARGET_AVAILABLE"
    else:
        conclusion = "CLEAN_TARGET_RECONSTRUCTED_SUPERVISED_FEASIBILITY_STILL_REQUIRED"

    summary = {
        "all_player_match_rows": int(len(frame)),
        "played_rows": int(len(played)),
        "starter_rows": int(frame["participation_status"].eq("STARTER").sum()),
        "substitute_appearance_rows": int(
            frame["participation_status"].eq("SUBSTITUTE_APPEARANCE").sum()
        ),
        "unused_bench_rows": int(frame["participation_status"].eq("UNUSED_BENCH").sum()),
        "unknown_participation_rows": int(
            frame["participation_status"].eq("UNKNOWN_PARTICIPATION").sum()
        ),
        "clean_target_rows": int(len(target)),
        "clean_target_labels": int(target["tactical_role"].nunique()),
        "clean_target_players": int(target["player_id"].nunique()),
        "withheld_substitute_appearances": int(
            frame["target_state"].eq("TACTICAL_ROLE_UNAVAILABLE_FOR_SUBSTITUTE").sum()
        ),
        "invalid_starter_rows": int(invalid_starter.sum()),
        "nonstarter_rows_with_non_substitute_raw_role": int(nonstarter_non_sub.sum()),
        "substitute_labels_remaining_in_clean_target": int(substitute_remaining),
        "single_player_labels": int((dependence["players"] == 1).sum()) if not dependence.empty else 0,
        "conclusion": conclusion,
    }

    return {
        "version": VERSION,
        "status": "TARGET_RECONSTRUCTION_ONLY",
        "summary": summary,
        "role_distribution": records(role_distribution),
        "role_player_dependence": records(dependence),
        "rules": [
            "Participation status and tactical role are separate variables.",
            "Non-starter tactical roles are not inferred from another match, default position or player history.",
            "No forward-fill, back-fill or modal-role imputation is used.",
            "No tactical labels are merged or regrouped.",
            "The normalized database is not modified by this script.",
            "No model, threshold, ranking, fit score or recommendation is created.",
        ],
    }


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# DSAI-05 — Tactical-role target reconstruction",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
    ]
    for key, value in s.items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## Role distribution",
            "",
            "| Tactical role | Rows | Players | Matches | First date | Last date |",
            "|---|---:|---:|---:|---|---|",
        ]
    )
    for row in result["role_distribution"]:
        lines.append(
            f"| {row['tactical_role']} | {row['rows']} | {row['players']} | "
            f"{row['matches']} | {row['first_date']} | {row['last_date']} |"
        )

    lines.extend(
        [
            "",
            "## Player dependence by role",
            "",
            "| Tactical role | Rows | Players | Top-player rows | Top-player share |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in result["role_player_dependence"]:
        share = row["top_player_share"]
        share_text = "" if share is None else f"{share:.4f}"
        lines.append(
            f"| {row['tactical_role']} | {row['rows']} | {row['players']} | "
            f"{row['top_player_rows']} | {share_text} |"
        )

    lines.extend(["", "## Rules"])
    for rule in result["rules"]:
        lines.append(f"- {rule}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with duckdb.connect(str(db_path), read_only=True) as con:
        frame = build_target(con)
    result = summarize(frame)
    s = result["summary"]

    print("DSAI-05 ROLE TARGET RECONSTRUCTION: COMPLETE")
    print(f"db: {db_path}")
    print(
        f"rows={s['all_player_match_rows']} played={s['played_rows']} "
        f"starters={s['starter_rows']} substitute_appearances={s['substitute_appearance_rows']} "
        f"unused_bench={s['unused_bench_rows']}"
    )
    print(
        f"clean_target_rows={s['clean_target_rows']} labels={s['clean_target_labels']} "
        f"players={s['clean_target_players']} single_player_labels={s['single_player_labels']}"
    )
    print(
        f"withheld_substitute_appearances={s['withheld_substitute_appearances']} "
        f"invalid_starter_rows={s['invalid_starter_rows']} "
        f"substitute_labels_remaining={s['substitute_labels_remaining_in_clean_target']}"
    )
    print(f"conclusion={s['conclusion']}")
    print("No role was inferred for substitutes; no model or label merge was created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = OUTPUT_DIR / "role_target_reconstruction.csv"
        json_path = OUTPUT_DIR / "role_target_reconstruction.json"
        md_path = OUTPUT_DIR / "role_target_reconstruction.md"
        frame.to_csv(csv_path, index=False)
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"csv: {csv_path}")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
