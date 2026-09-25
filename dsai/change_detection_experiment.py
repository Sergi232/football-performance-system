"""DSAI-02: leakage-safe change-detection experiment.

Purpose
-------
Evaluate whether role-conditioned temporal evidence can distinguish controlled
synthetic shifts from the original current observation without using future
information and without selecting a product threshold.

The experiment does NOT create a football rating, alert threshold, ranking or
recommendation. Synthetic shifts are used only as an evaluation device because
there is no labelled ground-truth change-point dataset.
"""
from __future__ import annotations

import argparse
import bisect
import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
OUTPUT_DIR = Path(__file__).with_name("output")
BASE_VERSION = "0.1.0"
ROLE_VERSION = "0.3.0"
EXPERIMENT_VERSION = "dsai_change_0.1.0"
SHIFT_MULTIPLIERS = (0.5, 1.0, 1.5, 2.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DSAI-02 change-detection experiment")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def auc_rank(negative_scores: list[float], positive_scores: list[float]) -> float | None:
    """Mann-Whitney interpretation of ROC-AUC in O(n log n)."""
    if not negative_scores or not positive_scores:
        return None
    negatives = sorted(negative_scores)
    wins = 0.0
    for pos in positive_scores:
        less = bisect.bisect_left(negatives, pos)
        right = bisect.bisect_right(negatives, pos)
        equal = right - less
        wins += less + 0.5 * equal
    return wins / (len(negative_scores) * len(positive_scores))


def median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(pd.Series(values, dtype="float64").median())


def qframe(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> pd.DataFrame:
    return con.execute(sql, params or []).fetchdf()


def load_candidates(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Load observations with a valid strict-past same-role mean/std.

    FEATURE-03 guarantees prior quantities use dates strictly before the current
    match. Two prior observations are the mathematical minimum needed for the
    validated population standard deviation; this is not a football threshold.
    """
    return qframe(
        con,
        """
        WITH base AS (
            SELECT f.match_id, f.player_id, f.feature_name AS base_feature,
                   f.feature_value AS current_value,
                   m.match_date, TRIM(pm.primary_role) AS primary_role
            FROM player_match_features f
            JOIN matches m ON m.match_id = f.match_id
            JOIN player_match pm
              ON pm.match_id = f.match_id AND pm.player_id = f.player_id
            WHERE f.feature_version = ?
              AND f.feature_value IS NOT NULL
              AND pm.minutes_played > 0
              AND pm.primary_role IS NOT NULL
              AND TRIM(pm.primary_role) <> ''
        ),
        role_mean AS (
            SELECT match_id, player_id,
                   REPLACE(feature_name, '__role_prior_mean', '') AS base_feature,
                   feature_value AS prior_mean
            FROM player_match_features
            WHERE feature_version = ?
              AND RIGHT(feature_name, LENGTH('__role_prior_mean')) = '__role_prior_mean'
        ),
        role_std AS (
            SELECT match_id, player_id,
                   REPLACE(feature_name, '__role_prior_std', '') AS base_feature,
                   feature_value AS prior_std
            FROM player_match_features
            WHERE feature_version = ?
              AND RIGHT(feature_name, LENGTH('__role_prior_std')) = '__role_prior_std'
        ),
        role_n AS (
            SELECT match_id, player_id,
                   REPLACE(feature_name, '__role_history_n', '') AS base_feature,
                   feature_value AS history_n
            FROM player_match_features
            WHERE feature_version = ?
              AND RIGHT(feature_name, LENGTH('__role_history_n')) = '__role_history_n'
        )
        SELECT b.*, rm.prior_mean, rs.prior_std, rn.history_n
        FROM base b
        JOIN role_mean rm USING (match_id, player_id, base_feature)
        JOIN role_std rs USING (match_id, player_id, base_feature)
        JOIN role_n rn USING (match_id, player_id, base_feature)
        WHERE rm.prior_mean IS NOT NULL
          AND rs.prior_std IS NOT NULL
          AND rs.prior_std > 0
          AND rn.history_n >= 2
        ORDER BY b.player_id, b.primary_role, b.base_feature, b.match_date, b.match_id
        """,
        [BASE_VERSION, ROLE_VERSION, ROLE_VERSION, ROLE_VERSION],
    )


def run_experiment(frame: pd.DataFrame) -> dict:
    if frame.empty:
        raise RuntimeError("No evaluable strict-past role-conditioned observations were found")

    frame = frame.copy()
    frame["original_score"] = (
        (frame["current_value"] - frame["prior_mean"]).abs() / frame["prior_std"]
    )

    negative_scores = [float(v) for v in frame["original_score"].dropna().tolist()]
    shift_results: list[dict] = []

    for multiplier in SHIFT_MULTIPLIERS:
        # The injected observation is placed exactly k prior-standard-deviations
        # from the strict-past same-role mean. The prior baseline is unchanged.
        # Positive and negative directions have the same absolute score, so one
        # direction is sufficient for this sensitivity experiment.
        shifted_value = frame["prior_mean"] + multiplier * frame["prior_std"]
        shifted_score = ((shifted_value - frame["prior_mean"]).abs() / frame["prior_std"])
        positives = [float(v) for v in shifted_score.dropna().tolist()]

        paired_uplift = shifted_score - frame["original_score"]
        shift_results.append(
            {
                "shift_std_multiplier": multiplier,
                "rows": int(len(positives)),
                "original_score_median": median(negative_scores),
                "shifted_score_median": median(positives),
                "paired_score_uplift_median": median(
                    [float(v) for v in paired_uplift.dropna().tolist()]
                ),
                "roc_auc_original_vs_injected": auc_rank(negative_scores, positives),
            }
        )

    by_history = []
    history_groups = [(2, 2), (3, 4), (5, 7), (8, 10_000)]
    for lo, hi in history_groups:
        sub = frame[(frame["history_n"] >= lo) & (frame["history_n"] <= hi)]
        by_history.append(
            {
                "history_n_from": lo,
                "history_n_to": None if hi == 10_000 else hi,
                "rows": int(len(sub)),
                "median_original_score": median(
                    [float(v) for v in sub["original_score"].dropna().tolist()]
                ),
            }
        )

    feature_coverage = (
        frame.groupby("base_feature", dropna=False)
        .agg(rows=("match_id", "size"), players=("player_id", "nunique"))
        .reset_index()
        .sort_values(["rows", "base_feature"], ascending=[False, True])
    )

    role_coverage = (
        frame.groupby("primary_role", dropna=False)
        .agg(rows=("match_id", "size"), players=("player_id", "nunique"))
        .reset_index()
        .sort_values(["rows", "primary_role"], ascending=[False, True])
    )

    return {
        "experiment_version": EXPERIMENT_VERSION,
        "status": "EXPERIMENTAL_NOT_DEPLOYED",
        "method": {
            "score": "abs(current - strict_past_same_role_mean) / strict_past_same_role_std",
            "synthetic_validation": "set synthetic current = prior_mean + k * prior_std; strict-past baseline unchanged",
            "shift_multipliers": list(SHIFT_MULTIPLIERS),
            "threshold_selection": "NONE",
            "ground_truth": "synthetic injected shifts only; no natural labelled change points",
        },
        "coverage": {
            "evaluable_rows": int(len(frame)),
            "players": int(frame["player_id"].nunique()),
            "roles": int(frame["primary_role"].nunique()),
            "features": int(frame["base_feature"].nunique()),
            "first_date": str(frame["match_date"].min()),
            "last_date": str(frame["match_date"].max()),
        },
        "shift_results": shift_results,
        "history_sensitivity": by_history,
        "feature_coverage": feature_coverage.to_dict(orient="records"),
        "role_coverage": role_coverage.to_dict(orient="records"),
        "limitations": [
            "Injected shifts are evaluation devices, not real labelled performance changes.",
            "Original observations can contain genuine changes, so they are not guaranteed stable negatives.",
            "No operational alert threshold is selected by this experiment.",
            "Short and sparse player-role-feature sequences reduce evaluable coverage.",
            "The experiment assesses detection behaviour, not whether a change is tactically good or bad.",
        ],
    }


def render_markdown(result: dict) -> str:
    c = result["coverage"]
    lines = [
        "# DSAI-02 — Change detection experiment",
        "",
        f"Version: `{result['experiment_version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Coverage",
        f"- Evaluable rows: {c['evaluable_rows']}",
        f"- Players: {c['players']}",
        f"- Roles: {c['roles']}",
        f"- Features: {c['features']}",
        f"- Date range: {c['first_date']} → {c['last_date']}",
        "",
        "## Synthetic shift validation",
        "",
        "| Shift (prior std) | Rows | Original median score | Shifted median score | Median uplift | ROC-AUC |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["shift_results"]:
        auc = row["roc_auc_original_vs_injected"]
        lines.append(
            f"| {row['shift_std_multiplier']:.1f} | {row['rows']} | "
            f"{row['original_score_median']:.4f} | {row['shifted_score_median']:.4f} | "
            f"{row['paired_score_uplift_median']:.4f} | {auc:.4f} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "This is an experimental sensitivity study. It does not choose a deployment threshold and it does not label a detected change as good or bad.",
        "",
        "## Limitations",
    ])
    for item in result["limitations"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with duckdb.connect(str(db_path), read_only=True) as con:
        frame = load_candidates(con)
    result = run_experiment(frame)

    print("DSAI-02 CHANGE DETECTION EXPERIMENT: COMPLETE")
    print(f"db: {db_path}")
    c = result["coverage"]
    print(
        f"evaluable_rows={c['evaluable_rows']} players={c['players']} "
        f"roles={c['roles']} features={c['features']}"
    )
    for row in result["shift_results"]:
        print(
            f"shift={row['shift_std_multiplier']:.1f}std "
            f"auc={row['roc_auc_original_vs_injected']:.4f} "
            f"median_uplift={row['paired_score_uplift_median']:.4f}"
        )
    print("No deployment threshold, football rating, ranking or recommendation was created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "change_detection_experiment.json"
        md_path = OUTPUT_DIR / "change_detection_experiment.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
