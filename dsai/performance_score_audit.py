"""PERF-01: audit the evidence needed for a defensible player-match performance score.

This stage deliberately does NOT create a score. It inventories:
- FEATURE-01 coverage on played player-match rows;
- coverage of the existing N4000-N7000 performance domains;
- tactical-role context availability;
- possible external holistic player-rating fields in the professional source that
  could be investigated as independent validation anchors;
- variables whose performance direction/weight is still unvalidated.

Important: lexical matches such as home_score, away_score or bigChanceScored are
not accepted as player-performance anchors. A candidate must pass semantic name
validation before it can affect the audit conclusion.

No weights, signs, thresholds, rankings or performance ratings are produced here.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
DEFAULT_INPUT = Path(r"C:\Users\sergi\Desktop\analisi_futbol\input\pannadata")
FEATURE_CATALOG = ROOT / "features" / "catalog.json"
DOMAIN_CATALOG = ROOT / "decision_tree" / "domain_catalog.json"
OUTPUT_DIR = Path(__file__).with_name("output")
VERSION = "performance_score_audit_0.2.0"

# Broad scan tokens are used only to inventory possible names. They do NOT make a
# field a valid anchor by themselves.
LEXICAL_SCAN_TOKENS = ("rating", "score", "grade", "index", "performance", "rank")

# Strong semantic anchor names. These describe a holistic player evaluation rather
# than a match result or an atomic football action.
EXACT_HOLISTIC_ANCHORS = {
    "rating",
    "player_rating",
    "match_rating",
    "performance_rating",
    "player_grade",
    "match_grade",
    "performance_grade",
    "player_score",
    "performance_score",
    "player_index",
    "performance_index",
    "player_rank",
    "performance_rank",
}

# Terms that indicate context/outcome/component statistics rather than an independent
# holistic player-performance evaluation.
ANCHOR_BLOCKERS = {
    "home",
    "away",
    "team",
    "opponent",
    "fixture",
    "matchscore",
    "goal",
    "goals",
    "scored",
    "chance",
    "chances",
    "shot",
    "shots",
    "assist",
    "assists",
    "pass",
    "passes",
    "card",
    "cards",
    "foul",
    "fouls",
    "save",
    "saves",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit performance-score feasibility")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


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


def feature_spec() -> tuple[str, list[dict]]:
    catalog = load_json(FEATURE_CATALOG)
    features = catalog.get("ratio_features", []) + catalog.get("per90_features", [])
    return str(catalog["feature_version"]), features


def domain_spec() -> list[dict]:
    return load_json(DOMAIN_CATALOG).get("domain_nodes", [])


def normalized_column_name(name: str) -> str:
    # bigChanceScored -> big_chance_scored; home-score -> home_score
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    value = re.sub(r"[^A-Za-z0-9]+", "_", value)
    return value.strip("_").lower()


def semantic_anchor_status(name: str) -> tuple[bool, str]:
    normalized = normalized_column_name(name)
    tokens = {token for token in normalized.split("_") if token}

    if normalized in EXACT_HOLISTIC_ANCHORS:
        return True, "EXACT_HOLISTIC_PLAYER_EVALUATION_NAME"

    if tokens & ANCHOR_BLOCKERS:
        return False, "REJECTED_CONTEXT_OR_COMPONENT_STAT"

    # rating/grade are strong enough when they are isolated semantic tokens.
    if "rating" in tokens or "grade" in tokens:
        return True, "HOLISTIC_RATING_OR_GRADE_NAME"

    # Generic score/index/rank are accepted only when explicitly qualified as a
    # player/performance construct. This prevents home_score / away_score false positives.
    if tokens & {"score", "index", "rank"} and tokens & {"player", "performance"}:
        return True, "QUALIFIED_HOLISTIC_SCORE_INDEX_OR_RANK"

    return False, "REJECTED_LEXICAL_MATCH_NOT_HOLISTIC"


def source_anchor_candidates(
    con: duckdb.DuckDBPyConnection,
    input_dir: Path,
    normalized_raw_columns: set[str],
) -> tuple[list[dict], list[dict], dict]:
    source_path = input_dir / "opta_player_stats.parquet"
    if not source_path.exists():
        return [], [], {"source_exists": False, "source_path": str(source_path)}

    escaped = sql_path(source_path)
    schema = con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{escaped}')"
    ).fetchdf()
    schema["column_name"] = schema["column_name"].astype(str)

    lexical = schema[
        schema["column_name"].str.lower().apply(
            lambda name: any(token in name for token in LEXICAL_SCAN_TOKENS)
        )
    ].copy()

    key_frame = con.execute(
        """
        SELECT
            CAST(m.source_match_id AS VARCHAR) AS source_match_id,
            CAST(p.source_player_id AS VARCHAR) AS source_player_id,
            pm.minutes_played
        FROM player_match pm
        JOIN matches m ON m.match_id = pm.match_id
        JOIN players p ON p.player_id = pm.player_id
        """
    ).fetchdf()
    con.register("performance_audit_keys", key_frame)

    accepted: list[dict] = []
    rejected: list[dict] = []
    try:
        for row in lexical.itertuples(index=False):
            column = str(row.column_name)
            qcol = quote_ident(column)
            stats = con.execute(
                f"""
                SELECT
                    COUNT(*) AS rows_joined,
                    COUNT(s.{qcol}) AS non_null_rows,
                    COUNT(DISTINCT s.{qcol}) AS distinct_values,
                    COUNT(s.{qcol}) FILTER (WHERE k.minutes_played > 0) AS non_null_played_rows
                FROM read_parquet('{escaped}') s
                JOIN performance_audit_keys k
                  ON CAST(s.match_id AS VARCHAR) = k.source_match_id
                 AND CAST(s.player_id AS VARCHAR) = k.source_player_id
                """
            ).fetchone()

            is_anchor, semantic_status = semantic_anchor_status(column)
            item = {
                "column": column,
                "normalized_name": normalized_column_name(column),
                "source_type": str(row.column_type),
                "rows_joined": int(stats[0]),
                "non_null_rows": int(stats[1]),
                "distinct_values": int(stats[2]),
                "non_null_played_rows": int(stats[3]),
                "already_in_normalized_raw_table": column in normalized_raw_columns,
                "semantic_status": semantic_status,
            }
            if is_anchor:
                item["status"] = "CANDIDATE_ONLY_REQUIRES_EMPIRICAL_VALIDATION"
                accepted.append(item)
            else:
                item["status"] = "REJECTED_NOT_AN_INDEPENDENT_HOLISTIC_PLAYER_ANCHOR"
                rejected.append(item)
    finally:
        con.unregister("performance_audit_keys")

    return accepted, rejected, {
        "source_exists": True,
        "source_path": str(source_path.resolve()),
        "source_columns": int(len(schema)),
        "lexical_matches": int(len(lexical)),
        "semantically_accepted_candidates": int(len(accepted)),
        "semantically_rejected_matches": int(len(rejected)),
    }


def build_audit(db_path: Path, input_dir: Path) -> dict:
    feature_version, features = feature_spec()
    feature_names = [item["name"] for item in features]
    feature_group = {item["name"]: item.get("group") for item in features}
    domain_nodes = domain_spec()

    with duckdb.connect(str(db_path), read_only=True) as con:
        played = con.execute(
            """
            SELECT match_id, player_id, minutes_played, started, primary_role
            FROM player_match
            WHERE minutes_played > 0
            """
        ).fetchdf()
        if played.empty:
            raise RuntimeError("No played player_match rows available")

        long = con.execute(
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

        normalized_raw_columns = {
            str(row[1]) for row in con.execute("PRAGMA table_info('player_match_raw_stats')").fetchall()
        }
        anchors, rejected_anchor_matches, source_meta = source_anchor_candidates(
            con, input_dir.expanduser().resolve(), normalized_raw_columns
        )

    total_played = int(len(played))
    tactical_role_mask = (
        played["primary_role"].notna()
        & played["primary_role"].astype(str).str.strip().ne("")
        & played["primary_role"].astype(str).str.strip().str.lower().ne("substitute")
    )

    coverage = (
        long[long["feature_name"].isin(feature_names)]
        .groupby("feature_name", as_index=False)
        .agg(non_null_rows=("feature_value", lambda s: int(s.notna().sum())))
    )
    all_features = pd.DataFrame({"feature_name": feature_names})
    coverage = all_features.merge(coverage, on="feature_name", how="left").fillna({"non_null_rows": 0})
    coverage["non_null_rows"] = coverage["non_null_rows"].astype(int)
    coverage["played_rows"] = total_played
    coverage["coverage_rate"] = coverage["non_null_rows"] / total_played
    coverage["group"] = coverage["feature_name"].map(feature_group)

    wide = long.pivot_table(
        index=["match_id", "player_id"],
        columns="feature_name",
        values="feature_value",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    for name in feature_names:
        if name not in wide.columns:
            wide[name] = pd.NA

    domain_rows: list[dict] = []
    for family in sorted({str(node["family"]) for node in domain_nodes}):
        nodes = [node for node in domain_nodes if str(node["family"]) == family]
        names = sorted({str(node["feature"]) for node in nodes})
        existing = [name for name in names if name in wide.columns]
        any_available = int(wide[existing].notna().any(axis=1).sum()) if existing else 0
        domain_rows.append(
            {
                "family": family,
                "nodes": len(nodes),
                "unique_features": len(names),
                "played_rows_with_any_evidence": any_available,
                "played_rows": total_played,
                "coverage_rate_any": any_available / total_played if total_played else None,
            }
        )

    metric_roles: dict[str, int] = {}
    for node in domain_nodes:
        role = str(node.get("metric_role", "unknown"))
        metric_roles[role] = metric_roles.get(role, 0) + 1

    anchor_with_values = [a for a in anchors if a["non_null_played_rows"] > 0]
    if not feature_names or int(coverage["non_null_rows"].sum()) == 0:
        conclusion = "INSUFFICIENT_COVERAGE"
    elif anchor_with_values:
        conclusion = "SUPERVISED_ANCHOR_CANDIDATE"
    else:
        conclusion = "EXPERT_WEIGHT_VALIDATION_REQUIRED"

    return {
        "version": VERSION,
        "status": "AUDIT_ONLY_NO_SCORE_CREATED",
        "summary": {
            "played_player_match_rows": total_played,
            "players": int(played["player_id"].nunique()),
            "matches": int(played["match_id"].nunique()),
            "feature_version": feature_version,
            "feature_names": len(feature_names),
            "feature_non_null_values": int(coverage["non_null_rows"].sum()),
            "feature_possible_values": int(total_played * len(feature_names)),
            "tactical_role_context_rows": int(tactical_role_mask.sum()),
            "rows_without_tactical_role_context": int(total_played - tactical_role_mask.sum()),
            "domain_nodes": len(domain_nodes),
            "external_anchor_candidates_with_values": len(anchor_with_values),
            "rejected_lexical_anchor_matches": len(rejected_anchor_matches),
            "conclusion": conclusion,
        },
        "feature_coverage": records(coverage.sort_values(["group", "feature_name"])),
        "domain_coverage": domain_rows,
        "domain_metric_roles": metric_roles,
        "direction_and_weight_status": {
            "status": "UNVALIDATED",
            "note": (
                "The existing expert catalog explicitly treats higher/lower as descriptive. "
                "No metric direction, domain weight or global-score weight is approved by this audit."
            ),
        },
        "source_anchor_scan": source_meta,
        "external_anchor_candidates": anchor_with_values,
        "rejected_anchor_matches": rejected_anchor_matches,
        "role_policy": (
            "Role/position may be used as contextual normalization/comparison when directly observed; "
            "it is not the primary prediction target of the performance score."
        ),
        "rules": [
            "No performance score, rating or ranking is created in PERF-01.",
            "No feature direction is assumed merely from volume or correlation.",
            "No weights or practical thresholds are invented.",
            "A lexical score/rating/index match is not sufficient: the field must represent a holistic player evaluation.",
            "Match scores and atomic/component statistics are rejected as external player-performance anchors.",
            "External provider fields, if found, are validation candidates only and are not product inputs.",
            "GPS remains optional and is excluded from the base score while the development dataset has no GPS observations.",
        ],
    }


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# PERF-01 — Performance score audit",
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
        "## Domain coverage",
        "",
        "| Family | Nodes | Unique features | Rows with evidence | Played rows | Coverage |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for row in result["domain_coverage"]:
        coverage = row["coverage_rate_any"]
        coverage_text = "NA" if coverage is None else f"{coverage:.4f}"
        lines.append(
            f"| {row['family']} | {row['nodes']} | {row['unique_features']} | "
            f"{row['played_rows_with_any_evidence']} | {row['played_rows']} | {coverage_text} |"
        )

    lines.extend(["", "## Accepted external anchor candidates"])
    if result["external_anchor_candidates"]:
        lines.extend([
            "",
            "| Column | Type | Non-null played rows | Distinct | Semantic status |",
            "|---|---|---:|---:|---|",
        ])
        for row in result["external_anchor_candidates"]:
            lines.append(
                f"| {row['column']} | {row['source_type']} | {row['non_null_played_rows']} | "
                f"{row['distinct_values']} | {row['semantic_status']} |"
            )
    else:
        lines.append("- No semantically valid holistic player-performance anchor was found with values on played rows.")

    lines.extend(["", "## Rejected lexical matches"])
    if result["rejected_anchor_matches"]:
        lines.extend([
            "",
            "| Column | Normalized name | Non-null played rows | Reason |",
            "|---|---|---:|---|",
        ])
        for row in result["rejected_anchor_matches"]:
            lines.append(
                f"| {row['column']} | {row['normalized_name']} | {row['non_null_played_rows']} | "
                f"{row['semantic_status']} |"
            )
    else:
        lines.append("- None.")

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

    result = build_audit(db_path, args.input_dir)
    s = result["summary"]

    print("PERF-01 PERFORMANCE SCORE AUDIT: COMPLETE")
    print(f"version={VERSION}")
    print(f"db: {db_path}")
    print(
        f"played_rows={s['played_player_match_rows']} players={s['players']} "
        f"matches={s['matches']} features={s['feature_names']}"
    )
    print(
        f"feature_values={s['feature_non_null_values']}/{s['feature_possible_values']} "
        f"role_context={s['tactical_role_context_rows']}/{s['played_player_match_rows']}"
    )
    print(
        f"domain_nodes={s['domain_nodes']} "
        f"external_anchor_candidates={s['external_anchor_candidates_with_values']} "
        f"rejected_lexical_matches={s['rejected_lexical_anchor_matches']}"
    )
    if result["external_anchor_candidates"]:
        print("accepted_anchor_columns=" + ",".join(row["column"] for row in result["external_anchor_candidates"]))
    if result["rejected_anchor_matches"]:
        print("rejected_anchor_columns=" + ",".join(row["column"] for row in result["rejected_anchor_matches"]))
    print(f"conclusion={s['conclusion']}")
    print("No score, weights, directions, ranking or recommendation was created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "performance_score_audit.json"
        md_path = OUTPUT_DIR / "performance_score_audit.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
