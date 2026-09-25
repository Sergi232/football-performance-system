"""DSAI-06: audit supervised tactical-role classification feasibility.

This stage is descriptive only. It uses the clean starter-only tactical target from
DSAI-05 semantics and FEATURE-01 current-match features. It does not train a model,
merge labels, invent sample thresholds, use player identity as a predictor, create a
football score, rank players or issue recommendations.

Key questions:
- Is each tactical label observed with enough structural diversity to avoid pure
  player-identity memorisation?
- Can rows be evaluated in strict-past time without exposing future labels?
- For a stronger identity-independent test, was the same label previously observed
  in another player?
- How much FEATURE-01 information is actually available on target rows?

FEATURE-02/03 are deliberately excluded because temporal role-conditioned features
may encode the target definition and would create circularity for this task.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
FEATURE_CATALOG = ROOT / "features" / "catalog.json"
OUTPUT_DIR = Path(__file__).with_name("output")
VERSION = "dsai_role_supervised_feasibility_0.1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit leakage-safe supervised feasibility for tactical-role classification"
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


def load_feature_version() -> tuple[str, list[str]]:
    catalog = json.loads(FEATURE_CATALOG.read_text(encoding="utf-8"))
    feature_names = [
        item["name"]
        for item in catalog.get("ratio_features", []) + catalog.get("per90_features", [])
    ]
    return str(catalog["feature_version"]), feature_names


def load_target(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute(
        """
        SELECT
            pm.match_id,
            pm.player_id,
            m.match_date,
            TRIM(pm.primary_role) AS tactical_role
        FROM player_match pm
        JOIN matches m ON m.match_id = pm.match_id
        WHERE pm.started IS TRUE
          AND pm.primary_role IS NOT NULL
          AND TRIM(pm.primary_role) <> ''
          AND LOWER(TRIM(pm.primary_role)) <> 'substitute'
        ORDER BY m.match_date, pm.match_id, pm.player_id
        """
    ).fetchdf()


def load_features(
    con: duckdb.DuckDBPyConnection,
    feature_version: str,
    expected_features: list[str],
) -> pd.DataFrame:
    frame = con.execute(
        """
        SELECT match_id, player_id, feature_name, feature_value
        FROM player_match_features
        WHERE feature_version = ?
        """,
        [feature_version],
    ).fetchdf()
    if frame.empty:
        return pd.DataFrame(columns=["match_id", "player_id", *expected_features])

    pivot = frame.pivot_table(
        index=["match_id", "player_id"],
        columns="feature_name",
        values="feature_value",
        aggfunc="first",
    ).reset_index()
    pivot.columns.name = None
    for feature in expected_features:
        if feature not in pivot.columns:
            pivot[feature] = pd.NA
    return pivot[["match_id", "player_id", *expected_features]]


def add_strict_past_flags(target: pd.DataFrame) -> pd.DataFrame:
    result = target.copy()
    result["label_seen_strict_past"] = False
    result["player_seen_strict_past"] = False
    result["same_label_other_player_strict_past"] = False

    seen_labels: set[str] = set()
    seen_players: set[str] = set()
    label_players: dict[str, set[str]] = defaultdict(set)

    for date, idx in result.groupby("match_date", sort=True).groups.items():
        indices = list(idx)
        for i in indices:
            role = str(result.at[i, "tactical_role"])
            player = str(result.at[i, "player_id"])
            result.at[i, "label_seen_strict_past"] = role in seen_labels
            result.at[i, "player_seen_strict_past"] = player in seen_players
            result.at[i, "same_label_other_player_strict_past"] = any(
                prior_player != player for prior_player in label_players.get(role, set())
            )

        # Same-date observations become available only after every row on that date
        # has been evaluated, preserving strict-past semantics.
        for i in indices:
            role = str(result.at[i, "tactical_role"])
            player = str(result.at[i, "player_id"])
            seen_labels.add(role)
            seen_players.add(player)
            label_players[role].add(player)

    return result


def summarize(
    target: pd.DataFrame,
    feature_frame: pd.DataFrame,
    feature_names: list[str],
    feature_version: str,
) -> dict:
    joined = target.merge(feature_frame, on=["match_id", "player_id"], how="left")
    joined = add_strict_past_flags(joined)

    if feature_names:
        joined["non_null_feature_count"] = joined[feature_names].notna().sum(axis=1)
    else:
        joined["non_null_feature_count"] = 0

    class_rows: list[dict] = []
    for role, group in joined.groupby("tactical_role", sort=True):
        class_rows.append(
            {
                "tactical_role": role,
                "rows": int(len(group)),
                "players": int(group["player_id"].nunique()),
                "matches": int(group["match_id"].nunique()),
                "first_date": clean(group["match_date"].min()),
                "last_date": clean(group["match_date"].max()),
                "strict_past_label_seen_rows": int(group["label_seen_strict_past"].sum()),
                "strict_past_other_player_same_label_rows": int(
                    group["same_label_other_player_strict_past"].sum()
                ),
                "median_non_null_features": float(group["non_null_feature_count"].median()),
                "min_non_null_features": int(group["non_null_feature_count"].min()),
                "max_non_null_features": int(group["non_null_feature_count"].max()),
            }
        )
    classes = pd.DataFrame(class_rows)
    if not classes.empty:
        classes = classes.sort_values(["rows", "tactical_role"], ascending=[False, True])

    single_player_labels = (
        classes.loc[classes["players"].eq(1), "tactical_role"].astype(str).tolist()
        if not classes.empty
        else []
    )
    labels_without_other_player_strict_past = (
        classes.loc[
            classes["strict_past_other_player_same_label_rows"].eq(0), "tactical_role"
        ].astype(str).tolist()
        if not classes.empty
        else []
    )
    labels_without_any_strict_past_test = (
        classes.loc[classes["strict_past_label_seen_rows"].eq(0), "tactical_role"].astype(str).tolist()
        if not classes.empty
        else []
    )

    rows = int(len(joined))
    strict_past_rows = int(joined["label_seen_strict_past"].sum()) if rows else 0
    identity_independent_rows = int(
        joined["same_label_other_player_strict_past"].sum()
    ) if rows else 0
    same_player_seen_rows = int(joined["player_seen_strict_past"].sum()) if rows else 0

    if rows == 0 or len(feature_names) == 0:
        conclusion = "NO_GO_SUPERVISED"
    elif strict_past_rows == 0:
        conclusion = "NO_GO_SUPERVISED"
    elif single_player_labels or labels_without_other_player_strict_past:
        # Structural limitation, not an arbitrary sample threshold: at least one
        # target class cannot be validated independently of player identity.
        conclusion = "LIMITED_EXPERIMENT_ONLY"
    else:
        conclusion = "GO_BASELINE_EXPERIMENT"

    feature_counts = joined["non_null_feature_count"]
    summary = {
        "target_rows": rows,
        "labels": int(joined["tactical_role"].nunique()) if rows else 0,
        "players": int(joined["player_id"].nunique()) if rows else 0,
        "matches": int(joined["match_id"].nunique()) if rows else 0,
        "feature_version": feature_version,
        "feature_names": len(feature_names),
        "feature_non_null_values": int(joined[feature_names].notna().sum().sum()) if feature_names else 0,
        "feature_possible_values": int(rows * len(feature_names)),
        "non_null_features_per_row_min": int(feature_counts.min()) if rows else 0,
        "non_null_features_per_row_median": float(feature_counts.median()) if rows else 0.0,
        "non_null_features_per_row_max": int(feature_counts.max()) if rows else 0,
        "strict_past_label_seen_rows": strict_past_rows,
        "strict_past_label_seen_share": (strict_past_rows / rows) if rows else None,
        "same_player_seen_strict_past_rows": same_player_seen_rows,
        "same_player_seen_strict_past_share": (same_player_seen_rows / rows) if rows else None,
        "identity_independent_strict_past_rows": identity_independent_rows,
        "identity_independent_strict_past_share": (
            identity_independent_rows / rows if rows else None
        ),
        "single_player_labels": len(single_player_labels),
        "labels_without_any_strict_past_test": len(labels_without_any_strict_past_test),
        "labels_without_other_player_strict_past": len(labels_without_other_player_strict_past),
        "conclusion": conclusion,
    }

    return {
        "version": VERSION,
        "status": "SUPERVISED_FEASIBILITY_AUDIT_ONLY",
        "summary": summary,
        "single_player_label_names": single_player_labels,
        "labels_without_any_strict_past_test_names": labels_without_any_strict_past_test,
        "labels_without_other_player_strict_past_names": labels_without_other_player_strict_past,
        "class_diagnostics": records(classes),
        "evaluation_design": {
            "allowed_predictors": "FEATURE-01 current-match numeric features only for baseline feasibility",
            "forbidden_predictors": [
                "player_id",
                "player name",
                "primary_role / tactical_role",
                "FEATURE-03 role-conditioned temporal features",
                "N12000/N13000 outputs",
                "any variable derived from the target role",
            ],
            "temporal_rule": "training observations must have match_date strictly earlier than evaluation observations",
            "identity_independent_rule": "report a separate evaluation where the target label was previously observed in another player",
            "same_date_rule": "same-date observations are never available to one another during strict-past eligibility checks",
        },
        "rules": [
            "No model is trained by DSAI-06.",
            "No labels are merged, removed or renamed for modelling convenience.",
            "No player identity field is allowed as a predictor.",
            "No arbitrary minimum-sample threshold is introduced.",
            "LIMITED_EXPERIMENT_ONLY is triggered only by structural impossibility of identity-independent validation for at least one class.",
            "No score, ranking, player fit or recommendation is created.",
        ],
    }


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# DSAI-06 — Supervised role-classification feasibility",
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
        "## Structural limitations",
        f"- Single-player labels: {', '.join(result['single_player_label_names']) or 'none'}",
        "- Labels without identity-independent strict-past support: "
        + (", ".join(result["labels_without_other_player_strict_past_names"]) or "none"),
        "- Labels without any strict-past evaluable row: "
        + (", ".join(result["labels_without_any_strict_past_test_names"]) or "none"),
        "",
        "## Class diagnostics",
        "",
        "| Role | Rows | Players | Matches | Strict-past rows | Other-player prior rows | Median features |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for row in result["class_diagnostics"]:
        lines.append(
            f"| {row['tactical_role']} | {row['rows']} | {row['players']} | {row['matches']} | "
            f"{row['strict_past_label_seen_rows']} | {row['strict_past_other_player_same_label_rows']} | "
            f"{row['median_non_null_features']:.1f} |"
        )

    lines.extend(["", "## Evaluation design"])
    for key, value in result["evaluation_design"].items():
        lines.append(f"- {key}: {value}")
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

    feature_version, feature_names = load_feature_version()
    with duckdb.connect(str(db_path), read_only=True) as con:
        target = load_target(con)
        feature_frame = load_features(con, feature_version, feature_names)

    result = summarize(target, feature_frame, feature_names, feature_version)
    s = result["summary"]

    print("DSAI-06 SUPERVISED ROLE FEASIBILITY: COMPLETE")
    print(f"db: {db_path}")
    print(
        f"target_rows={s['target_rows']} labels={s['labels']} players={s['players']} "
        f"matches={s['matches']} features={s['feature_names']}"
    )
    print(
        f"feature_values={s['feature_non_null_values']}/{s['feature_possible_values']} "
        f"features_per_row=min:{s['non_null_features_per_row_min']} "
        f"median:{s['non_null_features_per_row_median']} max:{s['non_null_features_per_row_max']}"
    )
    print(
        f"strict_past_label_seen={s['strict_past_label_seen_rows']}/{s['target_rows']} "
        f"identity_independent_strict_past={s['identity_independent_strict_past_rows']}/{s['target_rows']}"
    )
    print(
        f"single_player_labels={s['single_player_labels']} "
        f"labels_without_any_strict_past_test={s['labels_without_any_strict_past_test']} "
        f"labels_without_other_player_strict_past={s['labels_without_other_player_strict_past']}"
    )
    print(f"conclusion={s['conclusion']}")
    print("No model, label merge, arbitrary sample threshold, ranking or recommendation was created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "role_supervised_feasibility.json"
        md_path = OUTPUT_DIR / "role_supervised_feasibility.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
