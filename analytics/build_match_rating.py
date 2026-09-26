"""PERF-16 — materialize an immediate player-match rating.

The Match Rating is the post-match score used from match 1. Historical Performance
Score, form and trends are downstream layers and are not required to create it.

Principles:
- one row per played player-match;
- use available PERF-15 dimensions for outfield players;
- mapped roles use positional relevance priors;
- source-role-unavailable substitute rows use equal available-dimension weighting,
  explicitly marked GENERIC_ROLE_UNAVAILABLE (not tactical-role evidence);
- if an outfield appearance has no usable dimension evidence, display the mathematical
  midpoint with confidence 0 and an explicit insufficient-evidence status rather than
  fabricating actions;
- goalkeeper path is separate: when saves and goals conceded are both observed and at
  least one shot on target was faced, the evidence signal is save_rate; zero-opportunity
  or incomplete GK evidence receives the midpoint with reduced confidence;
- internal rating_100 stays 0-100. rating_10 is presentation only, mapped linearly to
  4.0-10.0 so the internal midpoint (50) displays as 7.0. This preserves order and does
  not copy a proprietary rating formula;
- no good/bad thresholds and no tactical recommendation.
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
NEUTRAL_100 = 50.0
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


def display_rating_10(score_100: float | int | None) -> float | None:
    if score_100 is None or pd.isna(score_100):
        return None
    value = max(0.0, min(100.0, float(score_100)))
    return 4.0 + 0.06 * value


def weighted_available(row: pd.Series, levels: dict[str, float]) -> tuple[float | None, float, int]:
    available = [d for d in DIMENSIONS if pd.notna(row.get(d))]
    if not available:
        return None, 0.0, 0
    intended = float(sum(levels[d] for d in DIMENSIONS))
    observed = float(sum(levels[d] for d in available))
    score = sum(float(row[d]) * levels[d] for d in available) / observed
    confidence = 100.0 * observed / intended if intended > 0 else 0.0
    return float(score), float(confidence), len(available)


def build_outfield(db_path: Path, meta: pd.DataFrame) -> pd.DataFrame:
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
    frame = frame.merge(
        meta[["match_id", "player_id", "team_id", "minutes_played", "started", "match_date"]],
        on=["match_id", "player_id"], how="left", validate="one_to_one",
    )
    if frame["team_id"].isna().any():
        raise RuntimeError("Could not resolve metadata for every outfield rating row")

    rows: list[dict] = []
    for _, row in frame.iterrows():
        group = str(row["position_group"])
        if group != "OTHER_OUTFIELD" and group in priors:
            levels = {d: float(priors[group]["relevance_levels"][d]) for d in DIMENSIONS}
            context = "POSITION_SPECIFIC"
        else:
            levels = {d: 1.0 for d in DIMENSIONS}
            context = "GENERIC_ROLE_UNAVAILABLE"

        score, confidence, n_dims = weighted_available(row, levels)
        if score is None:
            score = NEUTRAL_100
            confidence = 0.0
            status = "NEUTRAL_INSUFFICIENT_OUTFIELD_EVIDENCE"
        elif context == "GENERIC_ROLE_UNAVAILABLE":
            status = "RATED_GENERIC_ROLE_CONTEXT"
        else:
            status = "RATED_POSITION_CONTEXT"

        out = {k: row.get(k) for k in [
            "match_id", "match_date", "team_id", "player_id", "minutes_played", "started",
            "primary_role", "position_group", "position_mapping_status", *DIMENSIONS,
            "fallback_dimension_count",
        ]}
        out.update({
            "rating_path": "OUTFIELD",
            "match_rating_100": float(score),
            "match_rating_10": display_rating_10(score),
            "match_rating_confidence": float(confidence),
            "match_rating_dimensions_used": int(n_dims),
            "match_rating_context": context,
            "match_rating_status": status,
            "match_rating_version": RATING_VERSION,
            "source_score_version": SOURCE_SCORE_VERSION,
        })
        rows.append(out)
    return pd.DataFrame(rows)


def build_goalkeepers(db_path: Path, meta: pd.DataFrame) -> pd.DataFrame:
    gk_meta = meta[meta["primary_role"].fillna("").str.contains("Goalkeeper", case=False, regex=False)].copy()
    if gk_meta.empty:
        return pd.DataFrame()

    with duckdb.connect(str(db_path), read_only=True) as con:
        raw = con.execute(
            """
            SELECT match_id, player_id, saves, goals_conceded
            FROM player_match_raw_stats
            """
        ).fetchdf()
    gk = gk_meta.merge(raw, on=["match_id", "player_id"], how="left")
    rows: list[dict] = []
    for _, row in gk.iterrows():
        saves = pd.to_numeric(pd.Series([row.get("saves")]), errors="coerce").iloc[0]
        conceded = pd.to_numeric(pd.Series([row.get("goals_conceded")]), errors="coerce").iloc[0]
        observed_fields = int(pd.notna(saves)) + int(pd.notna(conceded))
        confidence = 50.0 * observed_fields

        if pd.notna(saves) and pd.notna(conceded):
            faced = float(saves) + float(conceded)
            if faced > 0:
                score = 100.0 * float(saves) / faced
                status = "RATED_GOALKEEPER_SAVE_RATE"
                dimensions_used = 1
            else:
                score = NEUTRAL_100
                status = "NEUTRAL_GOALKEEPER_NO_SHOTS_FACED"
                dimensions_used = 0
        else:
            score = NEUTRAL_100
            status = "NEUTRAL_INCOMPLETE_GOALKEEPER_EVIDENCE"
            dimensions_used = 0

        rows.append({
            "match_id": row["match_id"], "match_date": row["match_date"],
            "team_id": row["team_id"], "player_id": row["player_id"],
            "minutes_played": row["minutes_played"], "started": row["started"],
            "primary_role": row["primary_role"], "position_group": "GK",
            "position_mapping_status": "GOALKEEPER_SEPARATE_PATH",
            "attacking_threat": np.nan, "creation_progression": np.nan,
            "defensive_contribution": np.nan, "finishing": np.nan, "discipline": np.nan,
            "fallback_dimension_count": 0,
            "rating_path": "GOALKEEPER",
            "match_rating_100": float(score), "match_rating_10": display_rating_10(score),
            "match_rating_confidence": float(confidence),
            "match_rating_dimensions_used": int(dimensions_used),
            "match_rating_context": "GOALKEEPER_SEPARATE",
            "match_rating_status": status,
            "match_rating_version": RATING_VERSION,
            "source_score_version": SOURCE_SCORE_VERSION,
        })
    return pd.DataFrame(rows)


def build_rating_frame(db_path: Path) -> tuple[pd.DataFrame, dict]:
    with duckdb.connect(str(db_path), read_only=True) as con:
        meta = con.execute(
            """
            SELECT pm.match_id, pm.player_id, pm.team_id, pm.minutes_played,
                   pm.started, pm.primary_role, m.match_date
            FROM player_match pm
            JOIN matches m ON m.match_id = pm.match_id
            WHERE pm.minutes_played > 0
            """
        ).fetchdf()

    outfield = build_outfield(db_path, meta)
    gk = build_goalkeepers(db_path, meta)
    combined = pd.concat([outfield, gk], ignore_index=True, sort=False)

    if combined.duplicated(["match_id", "player_id"]).any():
        dup = combined.loc[combined.duplicated(["match_id", "player_id"], keep=False), ["match_id", "player_id", "rating_path"]]
        raise RuntimeError("Duplicate Match Rating rows:\n" + dup.head(20).to_string(index=False))

    played_keys = set(map(tuple, meta[["match_id", "player_id"]].to_numpy()))
    rating_keys = set(map(tuple, combined[["match_id", "player_id"]].to_numpy()))
    missing_keys = played_keys - rating_keys
    extra_keys = rating_keys - played_keys
    if missing_keys or extra_keys:
        raise RuntimeError(f"Match Rating key mismatch: missing={len(missing_keys)} extra={len(extra_keys)}")

    summary = {
        "rating_version": RATING_VERSION,
        "played_rows": int(len(meta)),
        "rated_rows": int(combined["match_rating_10"].notna().sum()),
        "rating_coverage": float(combined["match_rating_10"].notna().mean()) if len(combined) else None,
        "outfield_rows": int((combined["rating_path"] == "OUTFIELD").sum()),
        "goalkeeper_rows": int((combined["rating_path"] == "GOALKEEPER").sum()),
        "generic_role_unavailable_rows": int((combined["match_rating_context"] == "GENERIC_ROLE_UNAVAILABLE").sum()),
        "neutral_insufficient_evidence_rows": int(combined["match_rating_status"].str.startswith("NEUTRAL_").sum()),
        "first_match_capable": True,
        "history_required_for_match_rating": False,
    }
    cols = [
        "match_id", "match_date", "team_id", "player_id", "minutes_played", "started",
        "primary_role", "position_group", "position_mapping_status", *DIMENSIONS,
        "fallback_dimension_count", "rating_path", "match_rating_100", "match_rating_10",
        "match_rating_confidence", "match_rating_dimensions_used", "match_rating_context",
        "match_rating_status", "match_rating_version", "source_score_version",
    ]
    return combined[cols].copy(), summary


def ensure_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DROP TABLE IF EXISTS player_match_rating")
    con.execute(
        """
        CREATE TABLE player_match_rating (
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
            rating_path VARCHAR NOT NULL,
            match_rating_100 DOUBLE NOT NULL,
            match_rating_10 DOUBLE NOT NULL,
            match_rating_confidence DOUBLE NOT NULL,
            match_rating_dimensions_used BIGINT NOT NULL,
            match_rating_context VARCHAR NOT NULL,
            match_rating_status VARCHAR NOT NULL,
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
        con.register("rating_df", frame)
        insert_cols = list(frame.columns)
        con.execute(
            f"INSERT INTO player_match_rating ({', '.join(insert_cols)}) SELECT {', '.join(insert_cols)} FROM rating_df"
        )
        con.unregister("rating_df")

    print("PERF-16 MATCH RATING MATERIALIZATION: COMPLETE")
    for key, value in summary.items():
        print(f"{key}={value}")
    print("rating_10 is presentation-only: 4.0 + 0.06 * rating_100; midpoint 50 -> 7.0.")
    print("Every played row receives a rating; insufficient evidence is exposed through confidence/status, never hidden.")


if __name__ == "__main__":
    main()
