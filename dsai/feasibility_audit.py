"""DSAI-01A: audit feasibility of candidate Data Science / ML experiments.

This script does not train models and does not create new football metrics. It
summarises sample size, coverage, temporal structure, target availability and
known methodological constraints so the project can decide which experiments
are defensible before modelling.
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
BASE_FEATURE_VERSION = "0.1.0"
ANALYTICS_VERSION = "analytics_0.1.0"
EXPERT_VERSION = "expert_0.7.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit DS/AI experiment feasibility")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--no-write", action="store_true", help="Do not write local JSON/Markdown outputs")
    return parser.parse_args()


def table_exists(con: duckdb.DuckDBPyConnection, name: str) -> bool:
    return bool(
        con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='main' AND table_name=?",
            [name],
        ).fetchone()[0]
    )


def scalar(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None):
    return con.execute(sql, params or []).fetchone()[0]


def qframe(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> pd.DataFrame:
    return con.execute(sql, params or []).fetchdf()


def clean_for_json(value):
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


def rows_as_dicts(df: pd.DataFrame) -> list[dict]:
    return [
        {column: clean_for_json(value) for column, value in row.items()}
        for row in df.to_dict(orient="records")
    ]


def audit(con: duckdb.DuckDBPyConnection) -> dict:
    required = ["matches", "players", "player_match", "player_match_features", "decision_results"]
    missing = [name for name in required if not table_exists(con, name)]
    if missing:
        raise RuntimeError(f"Missing required tables: {missing}")

    dataset = con.execute(
        """
        SELECT COUNT(DISTINCT m.match_id) AS matches,
               COUNT(DISTINCT pm.player_id) AS players,
               COUNT(*) AS player_match_rows,
               MIN(m.match_date) AS first_match,
               MAX(m.match_date) AS last_match,
               COUNT(DISTINCT m.season) AS seasons
        FROM player_match pm
        JOIN matches m ON m.match_id = pm.match_id
        """
    ).fetchdf().iloc[0].to_dict()
    dataset = {k: clean_for_json(v) for k, v in dataset.items()}

    role_distribution = qframe(
        con,
        """
        SELECT TRIM(primary_role) AS role,
               COUNT(*) AS player_match_rows,
               COUNT(DISTINCT player_id) AS players,
               SUM(CASE WHEN minutes_played > 0 THEN 1 ELSE 0 END) AS played_rows
        FROM player_match
        WHERE primary_role IS NOT NULL AND TRIM(primary_role) <> ''
        GROUP BY 1
        ORDER BY player_match_rows DESC, role
        """,
    )

    role_sequences = qframe(
        con,
        """
        SELECT player_id, TRIM(primary_role) AS role,
               COUNT(*) FILTER (WHERE minutes_played > 0) AS played_matches
        FROM player_match
        WHERE primary_role IS NOT NULL AND TRIM(primary_role) <> ''
        GROUP BY player_id, TRIM(primary_role)
        HAVING COUNT(*) FILTER (WHERE minutes_played > 0) > 0
        """,
    )
    seq_values = role_sequences["played_matches"] if not role_sequences.empty else pd.Series(dtype=float)
    sequence_summary = {
        "player_role_sequences": int(len(role_sequences)),
        "min_played_matches": int(seq_values.min()) if len(seq_values) else 0,
        "median_played_matches": float(seq_values.median()) if len(seq_values) else 0.0,
        "max_played_matches": int(seq_values.max()) if len(seq_values) else 0,
        "sequences_with_repeated_observations": int((seq_values >= 2).sum()) if len(seq_values) else 0,
    }

    feature_summary = con.execute(
        """
        SELECT COUNT(*) AS feature_rows,
               COUNT(DISTINCT feature_name) AS feature_names,
               COUNT(feature_value) AS non_null_values,
               COUNT(DISTINCT match_id || '|' || player_id) AS player_match_units
        FROM player_match_features
        WHERE feature_version = ?
        """,
        [BASE_FEATURE_VERSION],
    ).fetchdf().iloc[0].to_dict()
    feature_summary = {k: clean_for_json(v) for k, v in feature_summary.items()}

    feature_coverage = qframe(
        con,
        """
        SELECT feature_name,
               COUNT(*) AS rows,
               COUNT(feature_value) AS non_null,
               ROUND(100.0 * COUNT(feature_value) / NULLIF(COUNT(*),0), 2) AS non_null_pct
        FROM player_match_features
        WHERE feature_version = ?
        GROUP BY feature_name
        ORDER BY non_null_pct ASC, feature_name
        """,
        [BASE_FEATURE_VERSION],
    )

    role_target = con.execute(
        """
        SELECT COUNT(*) AS labeled_rows,
               COUNT(DISTINCT TRIM(primary_role)) AS classes,
               COUNT(DISTINCT player_id) AS labeled_players
        FROM player_match
        WHERE primary_role IS NOT NULL AND TRIM(primary_role) <> '' AND minutes_played > 0
        """
    ).fetchdf().iloc[0].to_dict()
    role_target = {k: clean_for_json(v) for k, v in role_target.items()}

    analytics = {
        "table_present": table_exists(con, "analytics_evidence"),
        "rows": 0,
        "evidence_available_by_scope": {},
    }
    if analytics["table_present"]:
        analytics["rows"] = int(
            scalar(con, "SELECT COUNT(*) FROM analytics_evidence WHERE analytics_version = ?", [ANALYTICS_VERSION])
        )
        evidence = con.execute(
            """
            SELECT comparison_scope, COUNT(*)
            FROM analytics_evidence
            WHERE analytics_version = ? AND evidence_state = 'EVIDENCE_AVAILABLE'
            GROUP BY comparison_scope
            ORDER BY comparison_scope
            """,
            [ANALYTICS_VERSION],
        ).fetchall()
        analytics["evidence_available_by_scope"] = {scope: int(count) for scope, count in evidence}

    gps = {
        "imports": int(scalar(con, "SELECT COUNT(*) FROM gps_imports")) if table_exists(con, "gps_imports") else 0,
        "observations": int(scalar(con, "SELECT COUNT(*) FROM gps_observations")) if table_exists(con, "gps_observations") else 0,
    }

    n13000 = qframe(
        con,
        """
        SELECT result_value, COUNT(*) AS rows
        FROM decision_results
        WHERE engine_version = ? AND node_id = 'N13000.120'
        GROUP BY result_value
        ORDER BY rows DESC, result_value
        """,
        [EXPERT_VERSION],
    )

    # These statuses are methodological, not performance judgements. No numeric
    # threshold is used to decide whether a footballer is good/bad or fit/unfit.
    experiments = [
        {
            "experiment": "player_similarity_profiles",
            "status": "GO_EXPLORATORY",
            "unit": "player-role profile aggregated from validated features",
            "target": None,
            "baseline": "standardised feature distance / nearest neighbours",
            "validation": "stability across resampling/time windows + qualitative role coherence",
            "reason": "No supervised target is required; validated role labels and FEATURE-01 exist.",
            "main_risk": "small number of distinct players and repeated player-match observations",
        },
        {
            "experiment": "change_detection_evolution",
            "status": "GO_EXPERIMENT",
            "unit": "player-role-feature temporal sequence",
            "target": "no natural ground-truth change-point label",
            "baseline": "strict-past delta/slope already available",
            "validation": "synthetic shift injection + temporal robustness + false-alert analysis",
            "reason": "Strict-past temporal history and Analytics evidence are available.",
            "main_risk": "short sequences for some player-role combinations and no labelled change points",
        },
        {
            "experiment": "observed_role_classification",
            "status": "CANDIDATE_SUPERVISED",
            "unit": "player-match with observed primary_role",
            "target": "primary_role (observed, not inferred)",
            "baseline": "majority-role / simple linear or tree classifier",
            "validation": "temporal split; player leakage check; macro metrics and confusion matrix",
            "reason": "An independent observed role label exists and can test whether performance features contain role signal.",
            "main_risk": "23 raw role labels may be sparse/imbalanced; label space must be reviewed before training",
        },
        {
            "experiment": "role_player_fit",
            "status": "REFORMULATE_TARGET",
            "unit": "player-role over time",
            "target": None,
            "baseline": None,
            "validation": None,
            "reason": "The database contains observed role and descriptive fit evidence, but no independent ground-truth fit outcome.",
            "main_risk": "using N12000/N13000 as the ML target would be circular and invalid as independent validation",
        },
        {
            "experiment": "expert_vs_ml",
            "status": "BLOCKED_SHARED_TARGET",
            "unit": None,
            "target": None,
            "baseline": "expert system",
            "validation": None,
            "reason": "A direct comparison requires an independent target that both approaches predict; N13000 itself cannot be that target.",
            "main_risk": "circular evaluation",
        },
        {
            "experiment": "n13000_recommendation_calibration",
            "status": "BLOCKED_GROUND_TRUTH",
            "unit": "player-match recommendation decision",
            "target": None,
            "baseline": "current safe no-recommendation gate",
            "validation": None,
            "reason": "No coach-labelled recommendation outcome or validated downstream success target exists yet.",
            "main_risk": "inventing confidence/thresholds from the same evidence used to generate the recommendation",
        },
    ]

    return {
        "audit_version": "dsai_feasibility_0.1.0",
        "dataset": dataset,
        "roles": {
            "distribution": rows_as_dicts(role_distribution),
            "sequence_summary": sequence_summary,
            "observed_role_target": role_target,
        },
        "features": {
            "summary": feature_summary,
            "coverage": rows_as_dicts(feature_coverage),
        },
        "analytics": analytics,
        "gps": gps,
        "n13000_states": rows_as_dicts(n13000),
        "experiments": experiments,
        "rules": [
            "No model is trained by this audit.",
            "No football score, threshold, weight or recommendation is created.",
            "Observed primary_role is the only supervised label identified as directly available at this stage.",
            "N12000/N13000 outputs are not accepted as independent ML ground truth.",
            "Temporal experiments must remain strict-past and use time-aware validation.",
        ],
    }


def render_markdown(result: dict) -> str:
    d = result["dataset"]
    r = result["roles"]
    f = result["features"]["summary"]
    lines = [
        "# DSAI-01A — Feasibility audit",
        "",
        f"Audit version: `{result['audit_version']}`",
        "",
        "## Dataset",
        f"- Matches: {d['matches']}",
        f"- Players: {d['players']}",
        f"- Player-match rows: {d['player_match_rows']}",
        f"- Date range: {d['first_match']} → {d['last_match']}",
        f"- Seasons: {d['seasons']}",
        f"- FEATURE-01 names: {f['feature_names']}",
        f"- FEATURE-01 non-null values: {f['non_null_values']} / {f['feature_rows']}",
        f"- Observed-role rows: {r['observed_role_target']['labeled_rows']}",
        f"- Observed role labels: {r['observed_role_target']['classes']}",
        f"- Player-role sequences: {r['sequence_summary']['player_role_sequences']}",
        f"- Repeated player-role sequences: {r['sequence_summary']['sequences_with_repeated_observations']}",
        f"- GPS observations: {result['gps']['observations']}",
        "",
        "## Experiment decisions",
        "",
        "| Experiment | Status | Target | Main risk |",
        "|---|---|---|---|",
    ]
    for exp in result["experiments"]:
        lines.append(
            f"| {exp['experiment']} | **{exp['status']}** | {exp['target'] or '—'} | {exp['main_risk']} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "The audit reports feasibility only. GO does not mean a model is valid or production-ready; it means the experiment can be designed without inventing a target or violating the current data contract.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with duckdb.connect(str(db_path), read_only=True) as con:
        result = audit(con)

    print("DSAI-01A FEASIBILITY AUDIT: COMPLETE")
    print(f"db: {db_path}")
    d = result["dataset"]
    print(f"matches={d['matches']} players={d['players']} player_match={d['player_match_rows']}")
    role = result["roles"]["observed_role_target"]
    seq = result["roles"]["sequence_summary"]
    print(f"observed-role rows={role['labeled_rows']} labels={role['classes']} labeled_players={role['labeled_players']}")
    print(
        "player-role sequences="
        f"{seq['player_role_sequences']} repeated={seq['sequences_with_repeated_observations']} "
        f"median_matches={seq['median_played_matches']} max_matches={seq['max_played_matches']}"
    )
    fs = result["features"]["summary"]
    print(f"FEATURE-01 names={fs['feature_names']} non-null={fs['non_null_values']}/{fs['feature_rows']}")
    print(f"analytics rows={result['analytics']['rows']} GPS observations={result['gps']['observations']}")
    print("EXPERIMENT STATUS")
    for exp in result["experiments"]:
        print(f"- {exp['experiment']}: {exp['status']}")
    print("ROLE DISTRIBUTION")
    for row in result["roles"]["distribution"]:
        print(f"- {row['role']}: rows={row['player_match_rows']} players={row['players']} played_rows={row['played_rows']}")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "feasibility_audit.json"
        md_path = OUTPUT_DIR / "feasibility_audit.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")

    print("No model was trained and no new score, threshold, ranking or recommendation was created.")


if __name__ == "__main__":
    main()
