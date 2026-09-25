"""DSAI-04: audit observed role labels before supervised modelling.

This script is descriptive only. It does not train a classifier, merge role labels,
create a football score, select a threshold, rank players or issue recommendations.
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
AUDIT_VERSION = "dsai_role_labels_0.1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit primary_role label semantics and sparsity")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def qframe(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> pd.DataFrame:
    return con.execute(sql, params or []).fetchdf()


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


def audit(con: duckdb.DuckDBPyConnection) -> dict:
    distribution = qframe(
        con,
        """
        SELECT TRIM(primary_role) AS role,
               COUNT(*) AS rows,
               COUNT(DISTINCT player_id) AS players,
               SUM(CASE WHEN started THEN 1 ELSE 0 END) AS starter_rows,
               SUM(CASE WHEN NOT started THEN 1 ELSE 0 END) AS nonstarter_rows,
               SUM(CASE WHEN minutes_played > 0 THEN 1 ELSE 0 END) AS played_rows,
               SUM(CASE WHEN minutes_played = 0 THEN 1 ELSE 0 END) AS zero_minute_rows,
               AVG(minutes_played) AS avg_minutes,
               MIN(minutes_played) AS min_minutes,
               MAX(minutes_played) AS max_minutes
        FROM player_match
        WHERE primary_role IS NOT NULL AND TRIM(primary_role) <> ''
        GROUP BY 1
        ORDER BY rows DESC, role
        """,
    )

    substitute = qframe(
        con,
        """
        WITH sub_players AS (
            SELECT DISTINCT player_id
            FROM player_match
            WHERE TRIM(primary_role) = 'Substitute'
        ), tactical AS (
            SELECT pm.player_id,
                   COUNT(*) AS tactical_rows,
                   COUNT(DISTINCT TRIM(pm.primary_role)) AS tactical_role_labels
            FROM player_match pm
            JOIN sub_players s USING (player_id)
            WHERE pm.primary_role IS NOT NULL
              AND TRIM(pm.primary_role) <> ''
              AND TRIM(pm.primary_role) <> 'Substitute'
            GROUP BY pm.player_id
        )
        SELECT
            COUNT(*) AS substitute_rows,
            COUNT(DISTINCT pm.player_id) AS substitute_players,
            SUM(CASE WHEN pm.started THEN 1 ELSE 0 END) AS starter_rows,
            SUM(CASE WHEN NOT pm.started THEN 1 ELSE 0 END) AS nonstarter_rows,
            SUM(CASE WHEN pm.minutes_played > 0 THEN 1 ELSE 0 END) AS played_rows,
            SUM(CASE WHEN pm.minutes_played = 0 THEN 1 ELSE 0 END) AS zero_minute_rows,
            AVG(pm.minutes_played) AS avg_minutes,
            COUNT(DISTINCT CASE WHEN t.player_id IS NOT NULL THEN pm.player_id END) AS players_also_with_tactical_role
        FROM player_match pm
        LEFT JOIN tactical t USING (player_id)
        WHERE TRIM(pm.primary_role) = 'Substitute'
        """,
    )

    substitute_other_roles = qframe(
        con,
        """
        WITH sub_players AS (
            SELECT DISTINCT player_id
            FROM player_match
            WHERE TRIM(primary_role) = 'Substitute'
        )
        SELECT TRIM(pm.primary_role) AS role,
               COUNT(*) AS rows,
               COUNT(DISTINCT pm.player_id) AS players
        FROM player_match pm
        JOIN sub_players s USING (player_id)
        WHERE pm.primary_role IS NOT NULL
          AND TRIM(pm.primary_role) <> ''
          AND TRIM(pm.primary_role) <> 'Substitute'
        GROUP BY 1
        ORDER BY rows DESC, role
        """,
    )

    transitions = qframe(
        con,
        """
        WITH ordered AS (
            SELECT pm.player_id,
                   m.match_date,
                   pm.match_id,
                   TRIM(pm.primary_role) AS role,
                   LAG(TRIM(pm.primary_role)) OVER (
                       PARTITION BY pm.player_id ORDER BY m.match_date, pm.match_id
                   ) AS previous_role
            FROM player_match pm
            JOIN matches m ON m.match_id = pm.match_id
            WHERE pm.primary_role IS NOT NULL
              AND TRIM(pm.primary_role) <> ''
              AND pm.minutes_played > 0
        )
        SELECT previous_role, role,
               COUNT(*) AS transitions,
               COUNT(DISTINCT player_id) AS players
        FROM ordered
        WHERE previous_role IS NOT NULL
        GROUP BY 1, 2
        ORDER BY transitions DESC, previous_role, role
        """,
    )

    player_label_counts = qframe(
        con,
        """
        SELECT player_id,
               COUNT(DISTINCT TRIM(primary_role)) AS distinct_labels,
               COUNT(*) AS labeled_played_rows
        FROM player_match
        WHERE primary_role IS NOT NULL
          AND TRIM(primary_role) <> ''
          AND minutes_played > 0
        GROUP BY player_id
        ORDER BY distinct_labels DESC, labeled_played_rows DESC
        """,
    )

    total_labeled = int(distribution["rows"].sum()) if not distribution.empty else 0
    label_count = int(len(distribution))
    players = int(con.execute(
        """
        SELECT COUNT(DISTINCT player_id)
        FROM player_match
        WHERE primary_role IS NOT NULL AND TRIM(primary_role) <> '' AND minutes_played > 0
        """
    ).fetchone()[0])

    sub = substitute.iloc[0].to_dict() if not substitute.empty else {}
    sub = {k: clean(v) for k, v in sub.items()}

    findings = []
    if sub.get("substitute_rows", 0):
        findings.append("The raw target contains 'Substitute', which is not a tactical role in the validated lineup source semantics.")
    if sub.get("players_also_with_tactical_role", 0):
        findings.append("Players labelled 'Substitute' also appear with tactical role labels in other matches, confirming mixed target semantics.")
    if label_count > players:
        findings.append("The number of raw labels is high relative to the number of labelled players, increasing sparsity and class-fragmentation risk.")

    conclusion = "RAW_TARGET_REQUIRES_SOURCE_BASED_CLEANING_BEFORE_SUPERVISED_MODELLING"
    if not sub.get("substitute_rows", 0):
        conclusion = "RAW_TARGET_STILL_REQUIRES_SPARSITY_AND_STABILITY_REVIEW"

    return {
        "audit_version": AUDIT_VERSION,
        "status": "DESCRIPTIVE_AUDIT_ONLY",
        "summary": {
            "labeled_rows": total_labeled,
            "raw_labels": label_count,
            "labeled_players": players,
            "conclusion": conclusion,
        },
        "role_distribution": records(distribution),
        "substitute_diagnostic": sub,
        "substitute_players_other_roles": records(substitute_other_roles),
        "role_transitions": records(transitions),
        "player_label_counts": records(player_label_counts),
        "findings": findings,
        "rules": [
            "No labels are merged or redefined by this audit.",
            "No model is trained.",
            "No threshold, ranking, quality score, fit score or recommendation is created.",
            "Any future target cleaning must be justified by source semantics, not by convenience for modelling.",
        ],
    }


def render_markdown(result: dict) -> str:
    s = result["summary"]
    sub = result["substitute_diagnostic"]
    lines = [
        "# DSAI-04 — Role-label audit",
        "",
        f"Version: `{result['audit_version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
        f"- Labeled rows: {s['labeled_rows']}",
        f"- Raw labels: {s['raw_labels']}",
        f"- Labeled players: {s['labeled_players']}",
        f"- Conclusion: **{s['conclusion']}**",
        "",
        "## Substitute diagnostic",
    ]
    for key, value in sub.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Findings"])
    for item in result["findings"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Role distribution", "", "| Role | Rows | Players | Starters | Nonstarters | Avg min |", "|---|---:|---:|---:|---:|---:|"])
    for row in result["role_distribution"]:
        lines.append(
            f"| {row['role']} | {row['rows']} | {row['players']} | {row['starter_rows']} | "
            f"{row['nonstarter_rows']} | {row['avg_minutes']:.2f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with duckdb.connect(str(db_path), read_only=True) as con:
        result = audit(con)

    s = result["summary"]
    sub = result["substitute_diagnostic"]
    print("DSAI-04 ROLE LABEL AUDIT: COMPLETE")
    print(f"db: {db_path}")
    print(f"labeled_rows={s['labeled_rows']} raw_labels={s['raw_labels']} labeled_players={s['labeled_players']}")
    print(
        "Substitute: "
        f"rows={sub.get('substitute_rows', 0)} players={sub.get('substitute_players', 0)} "
        f"starters={sub.get('starter_rows', 0)} nonstarters={sub.get('nonstarter_rows', 0)} "
        f"played_rows={sub.get('played_rows', 0)} zero_minute_rows={sub.get('zero_minute_rows', 0)} "
        f"players_also_with_tactical_role={sub.get('players_also_with_tactical_role', 0)}"
    )
    print(f"conclusion={s['conclusion']}")
    print("No model was trained and no labels were merged by the audit.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "role_label_audit.json"
        md_path = OUTPUT_DIR / "role_label_audit.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
