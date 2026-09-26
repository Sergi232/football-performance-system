"""PERF-18 — Collector fidelity against reconstructed public Opta Points.

Purpose
-------
Measure how much of the fully reconstructed public Opta Points benchmark can be
reproduced using only variables available to the Football Performance System
collector / deterministic feature layer.

This is a benchmark audit, not the final rating model. Opta Points is used as an
external transparent reference; the final product remains position-aware and
methodologically distinct from proprietary Opta Player Rating.

Official public reference:
https://opta-points.statsperform.com/explainer

No production rating is changed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from perf18_opta_points_benchmark_audit import (
    ALIASES,
    ROOT,
    WEIGHTS_GK,
    WEIGHTS_OUTFIELD,
    choose_aliases,
    discover_input_dir,
    sql_path,
)

DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_collector_fidelity"

# These public Opta Points inputs are not direct manual Collector variables.
# - own_goals: not in the approved Collector event set;
# - offsides: not in the approved Collector event set;
# - penalty_saves: a save is collected, but penalty-save subtype is not required.
# shots_off_target is reconstructed deterministically from total shots, shots on
# target and blocked shots, all of which are available to the system.
EXCLUDED_DIRECT_INPUTS = {"own_goals", "offsides", "penalty_saves"}

TOTAL_SHOT_ALIASES = ["totalScoringAtt", "totalShots", "shotsTotal", "shots_total"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-18 Collector vs Opta Points fidelity")
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--min-minutes", type=float, default=1.0)
    p.add_argument("--rank-sample", type=int, default=300000)
    return p.parse_args()


def qcol(source: str) -> str:
    escaped = source.replace('"', '""')
    return f'COALESCE(TRY_CAST(s."{escaped}" AS DOUBLE), 0.0)'


def clamp(expr: str) -> str:
    return f"LEAST(10.0, GREATEST(3.0, ({expr})))"


def metric_summary(con: duckdb.DuckDBPyConnection, where: str = "TRUE") -> dict[str, float | int | None]:
    row = con.execute(
        f"""
        SELECT
            COUNT(*) AS n,
            AVG(ABS(collector_score - full_score)) AS mae,
            SQRT(AVG(POWER(collector_score - full_score, 2))) AS rmse,
            CORR(collector_score, full_score) AS pearson,
            AVG(CASE WHEN ABS(collector_score - full_score) <= 0.10 THEN 1.0 ELSE 0.0 END) AS within_010,
            AVG(CASE WHEN ABS(collector_score - full_score) <= 0.25 THEN 1.0 ELSE 0.0 END) AS within_025,
            AVG(CASE WHEN ABS(collector_score - full_score) <= 0.50 THEN 1.0 ELSE 0.0 END) AS within_050,
            AVG(collector_score - full_score) AS bias,
            AVG(full_score) AS full_mean,
            AVG(collector_score) AS collector_mean
        FROM perf18_fidelity
        WHERE {where}
        """
    ).fetchone()
    labels = [
        "n", "mae", "rmse", "pearson", "within_010", "within_025",
        "within_050", "bias", "full_mean", "collector_mean",
    ]
    result: dict[str, float | int | None] = {}
    for name, value in zip(labels, row):
        if value is None:
            result[name] = None
        elif name == "n":
            result[name] = int(value)
        else:
            result[name] = float(value)
    return result


def spearman(a: pd.Series, b: pd.Series) -> float:
    valid = a.notna() & b.notna()
    if int(valid.sum()) < 3:
        return float("nan")
    return float(a[valid].rank(method="average").corr(b[valid].rank(method="average")))


def decile_overlap(a: pd.Series, b: pd.Series, top: bool) -> float:
    valid = a.notna() & b.notna()
    aa, bb = a[valid], b[valid]
    if aa.empty:
        return float("nan")
    k = max(1, int(round(len(aa) * 0.10)))
    if top:
        ia = set(aa.nlargest(k).index)
        ib = set(bb.nlargest(k).index)
    else:
        ia = set(aa.nsmallest(k).index)
        ib = set(bb.nsmallest(k).index)
    return float(len(ia & ib) / k)


def main() -> None:
    args = parse_args()
    input_dir = discover_input_dir(args.input_dir)
    out = args.output_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    stats = input_dir / "opta_player_stats.parquet"
    lineups = input_dir / "opta_lineups.parquet"

    with duckdb.connect() as con:
        schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{sql_path(stats)}')").df()
        available = schema["column_name"].astype(str).tolist()
        mapping, missing = choose_aliases(available)
        if missing:
            raise RuntimeError(
                "Full Opta Points reconstruction is no longer possible; missing=" + str(missing)
            )

        total_shots_source = next((c for c in TOTAL_SHOT_ALIASES if c in set(available)), None)
        if total_shots_source is None:
            raise RuntimeError("No total-shots source column available for Collector off-target derivation")

        def src(logical: str) -> str:
            return qcol(mapping[logical])

        is_gk = (
            "(LOWER(COALESCE(CAST(l.position AS VARCHAR), '')) = 'gk' "
            "OR LOWER(COALESCE(CAST(l.position AS VARCHAR), '')) LIKE '%goalkeeper%' "
            "OR LOWER(COALESCE(CAST(l.position AS VARCHAR), '')) = 'keeper')"
        )

        full_outfield_terms = [f"({src(k)}) * ({float(w)})" for k, w in WEIGHTS_OUTFIELD.items()]
        full_gk_terms = [f"({src(k)}) * ({float(w)})" for k, w in WEIGHTS_GK.items()]
        full_outfield = clamp("5.5 + " + " + ".join(full_outfield_terms))
        full_gk = clamp("5.5 + " + " + ".join(full_gk_terms))

        total_shots = qcol(total_shots_source)
        derived_off = (
            f"GREATEST(0.0, ({total_shots}) - ({src('shots_on_target')}) - ({src('blocked_shots')}))"
        )

        collector_out_terms: list[str] = []
        collector_gk_terms: list[str] = []
        for logical, w in WEIGHTS_OUTFIELD.items():
            if logical in EXCLUDED_DIRECT_INPUTS:
                continue
            expr = derived_off if logical == "shots_off_target" else src(logical)
            collector_out_terms.append(f"({expr}) * ({float(w)})")
        for logical, w in WEIGHTS_GK.items():
            if logical in EXCLUDED_DIRECT_INPUTS:
                continue
            expr = derived_off if logical == "shots_off_target" else src(logical)
            collector_gk_terms.append(f"({expr}) * ({float(w)})")
        collector_out = clamp("5.5 + " + " + ".join(collector_out_terms))
        collector_gk = clamp("5.5 + " + " + ".join(collector_gk_terms))

        off_target_exact = src("shots_off_target")
        con.execute(
            f"""
            CREATE TEMP TABLE perf18_fidelity AS
            SELECT
                CAST(s.match_id AS VARCHAR) AS match_id,
                CAST(s.team_id AS VARCHAR) AS team_id,
                CAST(s.player_id AS VARCHAR) AS player_id,
                TRY_CAST(s.minsPlayed AS DOUBLE) AS minutes_played,
                COALESCE(CAST(l.position AS VARCHAR), 'UNKNOWN') AS position,
                {is_gk} AS is_gk,
                CASE WHEN {is_gk} THEN {full_gk} ELSE {full_outfield} END AS full_score,
                CASE WHEN {is_gk} THEN {collector_gk} ELSE {collector_out} END AS collector_score,
                {off_target_exact} AS source_shots_off_target,
                {derived_off} AS derived_shots_off_target,
                {src('own_goals')} AS own_goals,
                {src('offsides')} AS offsides,
                {src('penalty_saves')} AS penalty_saves
            FROM read_parquet('{sql_path(stats)}') s
            LEFT JOIN read_parquet('{sql_path(lineups)}') l
              ON CAST(l.match_id AS VARCHAR)=CAST(s.match_id AS VARCHAR)
             AND CAST(l.team_id AS VARCHAR)=CAST(s.team_id AS VARCHAR)
             AND CAST(l.player_id AS VARCHAR)=CAST(s.player_id AS VARCHAR)
            WHERE TRY_CAST(s.minsPlayed AS DOUBLE) >= {float(args.min_minutes)}
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY CAST(s.match_id AS VARCHAR), CAST(s.team_id AS VARCHAR), CAST(s.player_id AS VARCHAR)
                ORDER BY CAST(l.position AS VARCHAR) NULLS LAST
            ) = 1
            """
        )

        overall = metric_summary(con)
        goalkeeper = metric_summary(con, "is_gk")
        outfield = metric_summary(con, "NOT is_gk")

        position_df = con.execute(
            """
            SELECT
                position,
                COUNT(*) AS n,
                AVG(ABS(collector_score-full_score)) AS mae,
                SQRT(AVG(POWER(collector_score-full_score, 2))) AS rmse,
                CORR(collector_score, full_score) AS pearson,
                AVG(collector_score-full_score) AS bias
            FROM perf18_fidelity
            GROUP BY position
            ORDER BY n DESC
            LIMIT 20
            """
        ).df()

        shot_row = con.execute(
            """
            SELECT
                COUNT(*) AS n,
                AVG(ABS(derived_shots_off_target-source_shots_off_target)) AS mae,
                AVG(CASE WHEN derived_shots_off_target=source_shots_off_target THEN 1.0 ELSE 0.0 END) AS exact_share,
                MAX(ABS(derived_shots_off_target-source_shots_off_target)) AS max_abs_error
            FROM perf18_fidelity
            """
        ).fetchone()
        shot_derivation = {
            "n": int(shot_row[0]),
            "mae": float(shot_row[1]),
            "exact_share": float(shot_row[2]),
            "max_abs_error": float(shot_row[3]),
        }

        missing_event_row = con.execute(
            """
            SELECT
                AVG(CASE WHEN own_goals > 0 THEN 1.0 ELSE 0.0 END),
                AVG(CASE WHEN offsides > 0 THEN 1.0 ELSE 0.0 END),
                AVG(CASE WHEN penalty_saves > 0 THEN 1.0 ELSE 0.0 END),
                SUM(own_goals), SUM(offsides), SUM(penalty_saves)
            FROM perf18_fidelity
            """
        ).fetchone()
        excluded_event_prevalence = {
            "own_goal_positive_row_share": float(missing_event_row[0]),
            "offside_positive_row_share": float(missing_event_row[1]),
            "penalty_save_positive_row_share": float(missing_event_row[2]),
            "own_goals_total": float(missing_event_row[3]),
            "offsides_total": float(missing_event_row[4]),
            "penalty_saves_total": float(missing_event_row[5]),
        }

        sample_n = min(int(args.rank_sample), int(overall["n"] or 0))
        rank_df = con.execute(
            f"""
            SELECT full_score, collector_score
            FROM perf18_fidelity
            ORDER BY hash(match_id, team_id, player_id)
            LIMIT {sample_n}
            """
        ).df()

    rank_metrics = {
        "sample_rows": int(len(rank_df)),
        "spearman": spearman(rank_df["full_score"], rank_df["collector_score"]),
        "top10_overlap": decile_overlap(rank_df["full_score"], rank_df["collector_score"], True),
        "bottom10_overlap": decile_overlap(rank_df["full_score"], rank_df["collector_score"], False),
    }

    result = {
        "status": "COMPLETE_OPTA_POINTS_REFERENCE_VS_COLLECTOR_APPROXIMATION",
        "input_dir": str(input_dir),
        "min_minutes": float(args.min_minutes),
        "opta_points_source": "https://opta-points.statsperform.com/explainer",
        "full_reference_inputs": list(ALIASES.keys()),
        "collector_excluded_direct_inputs": sorted(EXCLUDED_DIRECT_INPUTS),
        "collector_derived_input": {
            "shots_off_target": "max(0, shots_total - shots_on_target - blocked_shots)",
            "total_shots_source": total_shots_source,
        },
        "overall": overall,
        "goalkeeper": goalkeeper,
        "outfield": outfield,
        "rank_metrics": rank_metrics,
        "shots_off_target_derivation": shot_derivation,
        "excluded_event_prevalence": excluded_event_prevalence,
        "position_summary_top20": position_df.to_dict(orient="records"),
        "interpretation_guardrail": (
            "High fidelity would show that the Collector retains most information in the public Opta Points benchmark. "
            "It does not prove equivalence to proprietary Opta Player Rating and does not define the final position-aware model."
        ),
        "production_status": "EXPERIMENT_ONLY",
    }

    artifact = out / "collector_opta_fidelity.json"
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("PERF-18 COLLECTOR -> OPTA POINTS FIDELITY")
    print(f"rows={overall['n']}")
    print("overall=" + str(overall))
    print("goalkeeper=" + str(goalkeeper))
    print("outfield=" + str(outfield))
    print("rank_metrics=" + str(rank_metrics))
    print("shots_off_target_derivation=" + str(shot_derivation))
    print("excluded_event_prevalence=" + str(excluded_event_prevalence))
    print("position_summary_top20=")
    print(position_df.to_string(index=False))
    print(f"artifact={artifact}")
    print("No production rating was changed.")


if __name__ == "__main__":
    main()
