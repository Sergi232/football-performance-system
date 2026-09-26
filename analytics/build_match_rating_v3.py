"""PERF-17 Match Rating V3 candidate with on-pitch goal context.

V3 keeps the validated current-match/role logic from V2 but replaces the final-score
context adjustment with the goal differential observed while the player was actually
on the pitch. This remains a small team-context adjustment, not causal attribution.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics import build_match_rating_v2 as v2  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
V3_VERSION = "match_rating_v0.3-candidate-onpitch"
CONTEXT_VERSION = "on_pitch_goal_context_v0.1"
SOURCE_VERSION = "raw_current_match_on_pitch_v3"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build Match Rating V3 on-pitch candidate")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    return p.parse_args()


def on_pitch_adjustment(row: pd.Series) -> float:
    value = row.get("goal_diff_on_pitch")
    if value is None or pd.isna(value):
        raise RuntimeError("Missing goal_diff_on_pitch in V3 source row")
    return 0.12 * float(np.clip(float(value), -3.0, 3.0))


def score_outfield(row: pd.Series) -> dict[str, Any]:
    impacts, counts = v2.dimension_impacts(row)
    group = str(row.get("position_group") or "OTHER_OUTFIELD")
    if group not in v2.ROLE_MULTIPLIERS:
        group = "OTHER_OUTFIELD"
    generic = group == "OTHER_OUTFIELD"
    multipliers = v2.ROLE_MULTIPLIERS[group]

    delta = 0.0
    dims_used = 0
    observed_terms = 0
    for dim in v2.DIMENSIONS:
        impact = impacts[dim]
        observed_terms += counts[dim]
        if impact is None:
            continue
        dims_used += 1
        delta += impact * v2.DIMENSION_STRENGTH[dim] * multipliers[dim]

    context_delta = on_pitch_adjustment(row)
    if dims_used == 0:
        rating = v2.BASE_RATING + context_delta
        status = "V3_NEUTRAL_INSUFFICIENT_EVIDENCE"
    else:
        rating = v2.BASE_RATING + delta + context_delta
        status = "V3_RATED_GENERIC_ROLE_CONTEXT" if generic else "V3_RATED_POSITION_CONTEXT"
    rating = float(np.clip(rating, 4.0, 10.0))

    return {
        **{dim: v2.impact_to_dimension_score(impacts[dim]) for dim in v2.DIMENSIONS},
        "rating_path": "OUTFIELD",
        "match_rating_10": rating,
        "match_rating_100": (rating - 4.0) * 100.0 / 6.0,
        "match_rating_confidence": v2.confidence_pct(row, observed_terms, generic),
        "match_rating_dimensions_used": dims_used,
        "match_rating_context": "GENERIC_ROLE_UNAVAILABLE" if generic else "POSITION_SPECIFIC_V3_ON_PITCH",
        "match_rating_status": status,
    }


def score_goalkeeper(row: pd.Series) -> dict[str, Any]:
    saves = v2.num(row, "saves")
    conceded = v2.num(row, "goals_conceded")
    observed = int(saves is not None) + int(conceded is not None)
    delta = 0.0
    if saves is not None:
        delta += 0.18 * saves
    if conceded is not None:
        delta -= 0.35 * conceded
    delta += on_pitch_adjustment(row)
    rating = float(np.clip(v2.BASE_RATING + delta, 4.0, 10.0))
    minutes = max(0.0, float(row.get("minutes_played") or 0.0))
    confidence = 100.0 * (0.65 * (observed / 2.0) + 0.35 * min(1.0, minutes / 60.0))
    return {
        **{dim: None for dim in v2.DIMENSIONS},
        "rating_path": "GOALKEEPER",
        "match_rating_10": rating,
        "match_rating_100": (rating - 4.0) * 100.0 / 6.0,
        "match_rating_confidence": float(np.clip(confidence, 0.0, 100.0)),
        "match_rating_dimensions_used": 1 if observed else 0,
        "match_rating_context": "GOALKEEPER_SEPARATE_V3_ON_PITCH",
        "match_rating_status": "V3_RATED_GOALKEEPER" if observed else "V3_NEUTRAL_INSUFFICIENT_GOALKEEPER_EVIDENCE",
    }


def load_source(db_path: Path, max_match_date: Any | None = None) -> pd.DataFrame:
    base = v2.load_source(db_path, max_match_date=max_match_date)
    with duckdb.connect(str(db_path), read_only=True) as con:
        context = con.execute(
            """
            SELECT match_id, team_id, player_id,
                   start_second, end_second, timing_precision,
                   goals_for_on_pitch, goals_against_on_pitch, goal_diff_on_pitch,
                   team_goals_for, team_goals_against, boundary_ambiguity_goals
            FROM player_match_on_pitch_context
            WHERE context_version=?
            """,
            [CONTEXT_VERSION],
        ).df()
    merged = base.merge(
        context,
        on=["match_id", "team_id", "player_id"],
        how="left",
        validate="one_to_one",
    )
    missing = int(merged["goal_diff_on_pitch"].isna().sum())
    if missing:
        raise RuntimeError(f"V3 missing on-pitch context for {missing} played rows")
    return merged


def build_rating_frame(db_path: Path, max_match_date: Any | None = None) -> pd.DataFrame:
    source = load_source(db_path, max_match_date=max_match_date)
    rows: list[dict[str, Any]] = []
    for _, row in source.iterrows():
        group = str(row.get("position_group") or "OTHER_OUTFIELD")
        scored = score_goalkeeper(row) if group == "GK" else score_outfield(row)
        rows.append({
            "match_id": row["match_id"],
            "match_date": row["match_date"],
            "team_id": row["team_id"],
            "player_id": row["player_id"],
            "minutes_played": row["minutes_played"],
            "started": row["started"],
            "primary_role": row["primary_role"],
            "position_group": group,
            "position_mapping_status": row["position_mapping_status"],
            **{dim: scored[dim] for dim in v2.DIMENSIONS},
            "fallback_dimension_count": 0,
            "rating_path": scored["rating_path"],
            "match_rating_100": scored["match_rating_100"],
            "match_rating_10": scored["match_rating_10"],
            "match_rating_confidence": scored["match_rating_confidence"],
            "match_rating_dimensions_used": scored["match_rating_dimensions_used"],
            "match_rating_context": scored["match_rating_context"],
            "match_rating_status": scored["match_rating_status"],
            "match_rating_version": V3_VERSION,
            "source_score_version": SOURCE_VERSION,
        })
    frame = pd.DataFrame(rows)
    if frame.duplicated(["match_id", "player_id"]).any():
        raise RuntimeError("Duplicate V3 match/player rows")
    return frame


def materialize(db_path: Path, frame: pd.DataFrame) -> None:
    with duckdb.connect(str(db_path)) as con:
        exists = con.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema='main' AND table_name='player_match_rating'
            """
        ).fetchone()[0]
        if not exists:
            raise RuntimeError("player_match_rating table missing; build PERF-16/V2 first")
        con.register("v3_frame", frame)
        cols = list(frame.columns)
        col_sql = ", ".join(cols)
        con.execute("DELETE FROM player_match_rating WHERE match_rating_version=?", [V3_VERSION])
        con.execute(f"INSERT INTO player_match_rating ({col_sql}) SELECT {col_sql} FROM v3_frame")
        con.unregister("v3_frame")


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)
    frame = build_rating_frame(db)
    materialize(db, frame)
    print("PERF-17 MATCH RATING V3 ON-PITCH: MATERIALIZED")
    print(f"version={V3_VERSION}")
    print(f"rows={len(frame)} matches={frame['match_id'].nunique()}")
    print(f"mean={frame['match_rating_10'].mean():.3f} median={frame['match_rating_10'].median():.3f}")
    print(f"min={frame['match_rating_10'].min():.3f} max={frame['match_rating_10'].max():.3f}")
    print("V2 remains active until V3 validation passes.")


if __name__ == "__main__":
    main()
