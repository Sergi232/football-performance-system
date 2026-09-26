"""PERF-16 — materialize a player-match rating for immediate post-match use.

This layer is intentionally different from the historical/role-profile Performance
Score. A Match Rating is produced from the evidence available in that single match,
so it can be used from match 1. Historical trends are downstream consumers.

Current prototype reference semantics:
- consumes PERF-15 dimensions already normalized against the frozen experimental
  benchmark workflow;
- mapped outfield roles use the existing positional relevance priors;
- source-role-unavailable substitute rows use an explicitly generic equal-dimension
  fallback only for match reporting; they are NOT used as tactical-role evidence;
- rating_10 is a transparent linear display transform: rating_100 / 10;
- no good/bad threshold or tactical recommendation is created here.

Goalkeepers remain a separate path and are reported explicitly by the validator until
PERF-16-GK is materialized. The final product contract requires a GK match rating too.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DSAI = ROOT / "dsai"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(DSAI) not in sys.path:
    sys.path.insert(0, str(DSAI))

import performance_position_score_experiment_v3 as perf15  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
PRIORS_FILE = DSAI / "performance_position_weight_priors.json"
RATING_VERSION = "match_rating_v0.1-experimental"
SOURCE_SCORE_VERSION = "performance_score_v0.2-experimental"
DIMENSIONS = [
    "attacking_threat",
    "creation_progression",
    "defensive_contribution",
    "finishing",
    "discipline",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Materialize per-match rating")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    return p.parse_args()


def load_priors() -> dict:
    return json.loads(PRIORS_FILE.read_text(encoding="utf-8"))["position_groups"]


def weighted_available(row: pd.Series, levels: dict[str, float]) -> tuple[float, float, int]:
    available = [d for d in DIMENSIONS if pd.notna(row.get(d))]
    if not available:
        return np.nan, 0.0, 0
    intended = float(sum(levels[d] for d in DIMENSIONS))
    observed = float(sum(levels[d] for d in available))
    score = sum(float(row[d]) * levels[d] for d in available) / observed
    confidence = 100.0 * observed / intended if intended > 0 else 0.0
    return float(score), float(confidence), len(available)


def build_rating_frame(db_path: Path) -> tuple[pd.DataFrame, dict]:
    _result, export = perf15.build_experiment_v3(db_path)
    priors = load_priors()

    rename = {
        "role_aware__dimension__attacking_threat": "attacking_threat",
        "role_aware__dimension__creation_progression": "creation_progression",
        "role_aware__dimension__defensive_contribution": "defensive_contribution",
        "role_aware__dimension__finishing": "finishing",
        "role_aware__dimension__discipline": "discipline",
    }
    frame = export.rename(columns=rename).copy()

    with duckdb.connect(str(db_path), read_only=True) as con:
        meta = con.execute(
            """
            SELECT pm.match_id, pm.player_id, pm.team_id, pm.minutes_played,
                   pm.started, m.match_date
            FROM player_match pm
            JOIN matches m ON m.match_id = pm.match_id
            WHERE pm.minutes_played > 0
            """
        ).fetchdf()
        goalkeeper_rows = con.execute(
            """
            SELECT COUNT(*)
            FROM player_match
            WHERE minutes_played > 0
              AND primary_role ILIKE 'Goalkeeper%'
            """
        ).fetchone()[0]

    frame = frame.merge(meta, on=["match_id", "player_id"], how="left", validate="one_to_one")
    if frame["team_id"].isna().any():
        raise RuntimeError("Could not resolve player_match metadata for every outfield rating row")

    rating_100 = []
    confidence = []
    dimensions_used = []
    contexts = []
    statuses = []

    for _, row in frame.iterrows():
        group = str(row["position_group"])
        if group != "OTHER_OUTFIELD" and group in priors:
            levels = {d: float(priors[group]["relevance_levels"][d]) for d in DIMENSIONS}
            context = "POSITION_SPECIFIC"
        else:
            levels = {d: 1.0 for d in DIMENSIONS}
            context = "GENERIC_ROLE_UNAVAILABLE"

        score, conf, n = weighted_available(row, levels)
        rating_100.append(score)
        confidence.append(conf)
        dimensions_used.append(n)
        contexts.append(context)
        if pd.isna(score):
            statuses.append("NO_OBSERVABLE_DIMENSION_EVIDENCE")
        elif context == "GENERIC_ROLE_UNAVAILABLE":
            statuses.append("RATED_GENERIC_ROLE_CONTEXT")
        else:
            statuses.append("RATED_POSITION_CONTEXT")

    frame["match_rating_100"] = rating_100
    frame["match_rating_10"] = frame["match_rating_100"] / 10.0
    frame["match_rating_confidence"] = confidence
    frame["match_rating_dimensions_used"] = dimensions_used
    frame["match_rating_context"] = contexts
    frame["match_rating_status"] = statuses
    frame["match_rating_version"] = RATING_VERSION
    frame["source_score_version"] = SOURCE_SCORE_VERSION

    outfield_rows = len(frame)
    rated_rows = int(frame["match_rating_100"].notna().sum())
    generic_rows = int(
        (frame["match_rating_100"].notna() & frame["match_rating_context"].eq("GENERIC_ROLE_UNAVAILABLE")).sum()
    )
    mapped_rows = int(frame["position_group"].ne("OTHER_OUTFIELD").sum())
    mapped_rated = int(
        (frame["position_group"].ne("OTHER_OUTFIELD") & frame["match_rating_100"].notna()).sum()
    )

    summary = {
        "rating_version": RATING_VERSION,
        "outfield_played_rows": outfield_rows,
        "outfield_rated_rows": rated_rows,
        "outfield_rating_coverage": rated_rows / outfield_rows if outfield_rows else None,
        "mapped_role_rows": mapped_rows,
        "mapped_role_rated_rows": mapped_rated,
        "generic_role_unavailable_rated_rows": generic_rows,
        "goalkeeper_played_rows_pending_separate_rating": int(goalkeeper_rows),
        "first_match_capable": True,
        "history_required_for_match_rating": False,
    }

    cols = [
        "match_id", "match_date", "team_id", "player_id", "minutes_played", "started",
        "primary_role", "position_group", "position_mapping_status",
        *DIMENSIONS,
        "fallback_dimension_count",
        "match_rating_100", "match_rating_10", "match_rating_confidence",
        "match_rating_dimensions_used", "match_rating_context", "match_rating_status",
        "match_rating_version", "source_score_version",
    ]
    return frame[cols].copy(), summary


def ensure_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS player_match_rating (
            match_id VARCHAR NOT NULL,
            match_date DATE,
            team_id VARCHAR NOT NULL,
            player_id VARCHAR NOT NULL,
            minutes_played DOUBLE,
            started BOOLEAN,
            primary_role VARCHAR,
            position_group VARCHAR,
            position_mapping_status VARCHAR,
            attacking_threat DOUBLE,
            creation_progression DOUBLE,
            defensive_contribution DOUBLE,
            finishing DOUBLE,
            discipline DOUBLE,
            fallback_dimension_count BIGINT,
            match_rating_100 DOUBLE,
            match_rating_10 DOUBLE,
            match_rating_confidence DOUBLE,
            match_rating_dimensions_used BIGINT,
            match_rating_context VARCHAR,
            match_rating_status VARCHAR,
            match_rating_version VARCHAR NOT NULL,
            source_score_version VARCHAR NOT NULL,
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (match_id, player_id, match_rating_version)
        )
        """
    )


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    frame, summary = build_rating_frame(db_path)
    with duckdb.connect(str(db_path)) as con:
        ensure_table(con)
        con.execute("DELETE FROM player_match_rating WHERE match_rating_version = ?", [RATING_VERSION])
        con.register("rating_df", frame)
        insert_cols = list(frame.columns)
        con.execute(
            f"INSERT INTO player_match_rating ({', '.join(insert_cols)}) SELECT {', '.join(insert_cols)} FROM rating_df"
        )
        con.unregister("rating_df")

    print("PERF-16 MATCH RATING MATERIALIZATION: COMPLETE")
    for key, value in summary.items():
        print(f"{key}={value}")
    print("rating_10 is a linear presentation transform of rating_100; no proprietary rating formula is copied.")
    print("Goalkeepers are intentionally reported as pending separate PERF-16-GK coverage.")


if __name__ == "__main__":
    main()
