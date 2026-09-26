"""PERF-17 — leakage-safe Match Rating V2 candidate.

V2 is intentionally current-match-only. It does not use historical percentiles,
season distributions, future matches, proprietary formulas or external ratings.

Design:
- 6.0 neutral display baseline;
- transparent current-match event impacts;
- broad role multipliers;
- bounded team-result context adjustment;
- missing source fields remain missing, never global zero;
- every played row receives a rating;
- v0.1 stays untouched until V2 validation passes.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
V1_VERSION = "match_rating_v0.1-experimental"
V2_VERSION = "match_rating_v0.2-candidate"
SOURCE_VERSION = "raw_current_match_v2"
BASE_RATING = 6.0
DIMENSIONS = [
    "attacking_threat",
    "creation_progression",
    "defensive_contribution",
    "finishing",
    "discipline",
]

ROLE_MULTIPLIERS: dict[str, dict[str, float]] = {
    "CB": {"attacking_threat": 0.35, "creation_progression": 0.70, "defensive_contribution": 1.25, "finishing": 0.55, "discipline": 1.00},
    "FB_WB": {"attacking_threat": 0.80, "creation_progression": 1.00, "defensive_contribution": 1.10, "finishing": 0.55, "discipline": 1.00},
    "DM_CM": {"attacking_threat": 0.55, "creation_progression": 1.15, "defensive_contribution": 1.00, "finishing": 0.55, "discipline": 1.00},
    "AM_W": {"attacking_threat": 1.15, "creation_progression": 1.15, "defensive_contribution": 0.45, "finishing": 1.00, "discipline": 1.00},
    "ST": {"attacking_threat": 1.15, "creation_progression": 0.65, "defensive_contribution": 0.30, "finishing": 1.25, "discipline": 1.00},
    "OTHER_OUTFIELD": {"attacking_threat": 0.80, "creation_progression": 0.80, "defensive_contribution": 0.80, "finishing": 0.80, "discipline": 1.00},
}

# Converts each net dimension impact to the final rating delta.
DIMENSION_STRENGTH = {
    "attacking_threat": 0.55,
    "creation_progression": 0.55,
    "defensive_contribution": 0.55,
    "finishing": 0.90,
    "discipline": 1.00,
}

RAW_COLUMNS = [
    "passes_total", "passes_completed", "assists",
    "long_balls_total", "long_balls_completed",
    "crosses_total", "crosses_completed",
    "dribbles_total", "dribbles_won", "turnovers", "dispossessed",
    "shots_total", "shots_blocked", "goals",
    "tackles_total", "tackles_won", "interceptions", "blocked_passes", "clearances",
    "fouls_committed", "fouls_received", "yellow_cards", "red_cards",
    "penalties_conceded", "penalties_won", "saves", "goals_conceded",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build Match Rating V2 candidate")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    return p.parse_args()


def num(row: pd.Series, key: str) -> float | None:
    value = row.get(key)
    if value is None or pd.isna(value):
        return None
    return float(value)


def observed_sum(terms: list[tuple[float, float | None]]) -> tuple[float | None, int]:
    values = [coef * value for coef, value in terms if value is not None]
    if not values:
        return None, 0
    return float(sum(values)), len(values)


def pass_accuracy_adjustment(row: pd.Series) -> tuple[float | None, int]:
    total = num(row, "passes_total")
    completed = num(row, "passes_completed")
    if total is None or completed is None:
        return None, 0
    if total <= 0:
        return 0.0, 1
    # Accuracy is a secondary signal, deliberately bounded to avoid rewarding
    # low-risk possession more than concrete progressive/creative actions.
    accuracy = max(0.0, min(1.0, completed / total))
    return float(np.clip((accuracy - 0.75) * 0.8, -0.25, 0.25)), 1


def dimension_impacts(row: pd.Series) -> tuple[dict[str, float | None], dict[str, int]]:
    attack, n_attack = observed_sum([
        (0.18, num(row, "dribbles_won")),
        (0.35, num(row, "penalties_won")),
        (-0.05, num(row, "turnovers")),
        (-0.07, num(row, "dispossessed")),
    ])

    creation, n_creation = observed_sum([
        (0.008, num(row, "passes_completed")),
        (0.04, num(row, "long_balls_completed")),
        (0.06, num(row, "crosses_completed")),
        (0.70, num(row, "assists")),
    ])
    acc_adj, n_acc = pass_accuracy_adjustment(row)
    if acc_adj is not None:
        creation = (creation or 0.0) + acc_adj
        n_creation += n_acc

    defense, n_defense = observed_sum([
        (0.12, num(row, "tackles_won")),
        (0.14, num(row, "interceptions")),
        (0.08, num(row, "blocked_passes")),
        (0.05, num(row, "clearances")),
        (-0.05, num(row, "fouls_committed")),
        (-0.35, num(row, "penalties_conceded")),
    ])

    finishing, n_finishing = observed_sum([
        (1.00, num(row, "goals")),
        (0.08, num(row, "shots_total")),
        (-0.02, num(row, "shots_blocked")),
    ])

    discipline, n_discipline = observed_sum([
        (-0.15, num(row, "yellow_cards")),
        (-0.90, num(row, "red_cards")),
        (-0.04, num(row, "fouls_committed")),
        (0.03, num(row, "fouls_received")),
    ])

    impacts = {
        "attacking_threat": attack,
        "creation_progression": creation,
        "defensive_contribution": defense,
        "finishing": finishing,
        "discipline": discipline,
    }
    counts = {
        "attacking_threat": n_attack,
        "creation_progression": n_creation,
        "defensive_contribution": n_defense,
        "finishing": n_finishing,
        "discipline": n_discipline,
    }
    return impacts, counts


def impact_to_dimension_score(impact: float | None) -> float | None:
    if impact is None:
        return None
    # Neutral current-match evidence is 50; tanh keeps extreme event counts bounded.
    return float(np.clip(50.0 + 30.0 * np.tanh(float(impact) / 1.25), 0.0, 100.0))


def result_adjustment(score_for: Any, score_against: Any) -> float:
    if score_for is None or score_against is None or pd.isna(score_for) or pd.isna(score_against):
        return 0.0
    goal_diff = float(score_for) - float(score_against)
    return 0.12 * float(np.clip(goal_diff, -3.0, 3.0))


def confidence_pct(row: pd.Series, observed_terms: int, generic_role: bool) -> float:
    minutes = max(0.0, float(row.get("minutes_played") or 0.0))
    # 27 possible observable primitive terms across dimensions; confidence reflects
    # evidence availability + exposure, not probability that the rating is correct.
    field_coverage = min(1.0, observed_terms / 18.0)
    exposure = min(1.0, minutes / 60.0)
    confidence = 100.0 * (0.65 * field_coverage + 0.35 * exposure)
    if generic_role:
        confidence *= 0.80
    return float(np.clip(confidence, 0.0, 100.0))


def score_outfield(row: pd.Series) -> dict[str, Any]:
    impacts, counts = dimension_impacts(row)
    group = str(row.get("position_group") or "OTHER_OUTFIELD")
    if group not in ROLE_MULTIPLIERS:
        group = "OTHER_OUTFIELD"
    generic = group == "OTHER_OUTFIELD"
    multipliers = ROLE_MULTIPLIERS[group]

    delta = 0.0
    dims_used = 0
    observed_terms = 0
    for dim in DIMENSIONS:
        impact = impacts[dim]
        observed_terms += counts[dim]
        if impact is None:
            continue
        dims_used += 1
        delta += impact * DIMENSION_STRENGTH[dim] * multipliers[dim]

    context_delta = result_adjustment(row.get("score_for"), row.get("score_against"))
    if dims_used == 0:
        rating = BASE_RATING + context_delta
        status = "V2_NEUTRAL_INSUFFICIENT_EVIDENCE"
    else:
        rating = BASE_RATING + delta + context_delta
        status = "V2_RATED_GENERIC_ROLE_CONTEXT" if generic else "V2_RATED_POSITION_CONTEXT"
    rating = float(np.clip(rating, 4.0, 10.0))

    return {
        **{dim: impact_to_dimension_score(impacts[dim]) for dim in DIMENSIONS},
        "rating_path": "OUTFIELD",
        "match_rating_10": rating,
        "match_rating_100": (rating - 4.0) * 100.0 / 6.0,
        "match_rating_confidence": confidence_pct(row, observed_terms, generic),
        "match_rating_dimensions_used": dims_used,
        "match_rating_context": "GENERIC_ROLE_UNAVAILABLE" if generic else "POSITION_SPECIFIC_V2",
        "match_rating_status": status,
    }


def score_goalkeeper(row: pd.Series) -> dict[str, Any]:
    saves = num(row, "saves")
    conceded = num(row, "goals_conceded")
    observed = int(saves is not None) + int(conceded is not None)
    delta = 0.0
    if saves is not None:
        delta += 0.18 * saves
    if conceded is not None:
        delta -= 0.35 * conceded
    delta += result_adjustment(row.get("score_for"), row.get("score_against"))
    rating = float(np.clip(BASE_RATING + delta, 4.0, 10.0))
    minutes = max(0.0, float(row.get("minutes_played") or 0.0))
    confidence = 100.0 * (0.65 * (observed / 2.0) + 0.35 * min(1.0, minutes / 60.0))
    return {
        **{dim: None for dim in DIMENSIONS},
        "rating_path": "GOALKEEPER",
        "match_rating_10": rating,
        "match_rating_100": (rating - 4.0) * 100.0 / 6.0,
        "match_rating_confidence": float(np.clip(confidence, 0.0, 100.0)),
        "match_rating_dimensions_used": 1 if observed else 0,
        "match_rating_context": "GOALKEEPER_SEPARATE_V2",
        "match_rating_status": "V2_RATED_GOALKEEPER" if observed else "V2_NEUTRAL_INSUFFICIENT_GOALKEEPER_EVIDENCE",
    }


def load_source(db_path: Path, max_match_date: Any | None = None) -> pd.DataFrame:
    raw_cols = ",\n               ".join(f"rs.{c}" for c in RAW_COLUMNS)
    cutoff_sql = "" if max_match_date is None else "AND m.match_date <= ?"
    params: list[Any] = [V1_VERSION]
    if max_match_date is not None:
        params.append(max_match_date)

    with duckdb.connect(str(db_path), read_only=True) as con:
        return con.execute(
            f"""
            SELECT
                pm.match_id, m.match_date, pm.team_id, pm.player_id,
                pm.minutes_played, pm.started, pm.primary_role,
                COALESCE(v1.position_group,
                    CASE WHEN lower(COALESCE(pm.primary_role,'')) LIKE '%goalkeeper%' THEN 'GK' ELSE 'OTHER_OUTFIELD' END
                ) AS position_group,
                COALESCE(v1.position_mapping_status, 'V2_ROLE_METADATA_FALLBACK') AS position_mapping_status,
                tm.score_for, tm.score_against,
                {raw_cols}
            FROM player_match pm
            JOIN matches m ON m.match_id=pm.match_id
            JOIN team_match tm ON tm.match_id=pm.match_id AND tm.team_id=pm.team_id
            LEFT JOIN player_match_raw_stats rs
              ON rs.match_id=pm.match_id AND rs.player_id=pm.player_id AND rs.team_id=pm.team_id
            LEFT JOIN player_match_rating v1
              ON v1.match_id=pm.match_id AND v1.player_id=pm.player_id
             AND v1.team_id=pm.team_id AND v1.match_rating_version=?
            WHERE pm.minutes_played > 0 {cutoff_sql}
            ORDER BY m.match_date, pm.match_id, pm.player_id
            """,
            params,
        ).df()


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
            **{dim: scored[dim] for dim in DIMENSIONS},
            "fallback_dimension_count": 0,
            "rating_path": scored["rating_path"],
            "match_rating_100": scored["match_rating_100"],
            "match_rating_10": scored["match_rating_10"],
            "match_rating_confidence": scored["match_rating_confidence"],
            "match_rating_dimensions_used": scored["match_rating_dimensions_used"],
            "match_rating_context": scored["match_rating_context"],
            "match_rating_status": scored["match_rating_status"],
            "match_rating_version": V2_VERSION,
            "source_score_version": SOURCE_VERSION,
        })
    frame = pd.DataFrame(rows)
    if frame.duplicated(["match_id", "player_id"]).any():
        raise RuntimeError("Duplicate V2 match/player rows")
    return frame


def materialize(db_path: Path, frame: pd.DataFrame) -> None:
    with duckdb.connect(str(db_path)) as con:
        # PERF-16 already created this schema. Fail explicitly if absent rather than
        # silently redefining the production table during a candidate experiment.
        exists = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='main' AND table_name='player_match_rating'"
        ).fetchone()[0]
        if not exists:
            raise RuntimeError("player_match_rating missing; materialize PERF-16 first")
        con.execute("DELETE FROM player_match_rating WHERE match_rating_version=?", [V2_VERSION])
        con.register("v2_df", frame)
        cols = list(frame.columns)
        con.execute(
            f"INSERT INTO player_match_rating ({', '.join(cols)}) SELECT {', '.join(cols)} FROM v2_df"
        )
        con.unregister("v2_df")


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    frame = build_rating_frame(db_path)
    materialize(db_path, frame)
    print("PERF-17 MATCH RATING V2 CANDIDATE: MATERIALIZED")
    print(f"version={V2_VERSION}")
    print(f"rows={len(frame)} matches={frame['match_id'].nunique()}")
    print(f"mean={frame['match_rating_10'].mean():.3f} median={frame['match_rating_10'].median():.3f}")
    print(f"min={frame['match_rating_10'].min():.3f} max={frame['match_rating_10'].max():.3f}")
    print("V1 remains active until PERF-17 validation passes.")


if __name__ == "__main__":
    main()
