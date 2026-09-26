"""Materialize performance_score_v0.2-experimental.

Consumes PERF-15 / position-score v3. Existing signed dimensions remain primary;
transparent contribution fallbacks can fill otherwise empty dimensions using only
observed successful actions already present in the raw player-match layer.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DSAI_DIR = ROOT / "dsai"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(DSAI_DIR) not in sys.path:
    sys.path.insert(0, str(DSAI_DIR))

import performance_position_score_experiment_v3 as perf15  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
PRODUCT_SCORE_VERSION = "performance_score_v0.2-experimental"
METHOD = "POSITION_GROUP_ROLE_AWARE_WEIGHTED_3PLUS_SIGNED_WITH_CONTRIBUTION_FALLBACK"

DIMENSIONS = [
    "attacking_threat",
    "creation_progression",
    "defensive_contribution",
    "finishing",
    "discipline",
]
DIMENSION_COLUMNS = {d: f"role_aware__dimension__{d}" for d in DIMENSIONS}
EVIDENCE_COLUMNS = {d: f"dimension_evidence_source__{d}" for d in DIMENSIONS}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Materialize performance_score_v0.2-experimental")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    return p.parse_args()


def ensure_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS player_match_performance_score (
            match_id VARCHAR NOT NULL,
            team_id VARCHAR NOT NULL,
            player_id VARCHAR NOT NULL,
            primary_role VARCHAR,
            raw_source_position VARCHAR,
            position_group VARCHAR NOT NULL,
            position_mapping_status VARCHAR NOT NULL,
            dimension_coverage_count BIGINT NOT NULL,
            attacking_threat DOUBLE,
            creation_progression DOUBLE,
            defensive_contribution DOUBLE,
            finishing DOUBLE,
            discipline DOUBLE,
            performance_score DOUBLE,
            score_evidence_confidence DOUBLE,
            score_status VARCHAR NOT NULL,
            score_method VARCHAR NOT NULL,
            score_version VARCHAR NOT NULL,
            source_experiment_version VARCHAR NOT NULL,
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (match_id, player_id, score_version)
        )
        """
    )
    # PERF-15 provenance fields. ADD COLUMN keeps existing v0.1 rows intact.
    con.execute("ALTER TABLE player_match_performance_score ADD COLUMN IF NOT EXISTS fallback_dimension_count BIGINT")
    for dimension in DIMENSIONS:
        con.execute(
            f"ALTER TABLE player_match_performance_score ADD COLUMN IF NOT EXISTS {dimension}_evidence VARCHAR"
        )


def build_frame(db_path: Path) -> tuple[dict, pd.DataFrame]:
    result, export = perf15.build_experiment_v3(db_path)

    with duckdb.connect(str(db_path), read_only=True) as con:
        keys = con.execute(
            """
            SELECT match_id, player_id, team_id
            FROM player_match
            WHERE minutes_played > 0
            """
        ).fetchdf()

    if keys.duplicated(["match_id", "player_id"]).any():
        raise RuntimeError("player_match contains duplicate played match/player keys")

    frame = export.merge(keys, on=["match_id", "player_id"], how="left", validate="one_to_one")
    if frame["team_id"].isna().any():
        raise RuntimeError("Could not resolve team_id for every PERF-15 output row")

    rename = {
        "role_aware__dimension_coverage_count": "dimension_coverage_count",
        "performance_score_position_experimental": "performance_score",
    }
    rename.update({DIMENSION_COLUMNS[d]: d for d in DIMENSIONS})
    rename.update({EVIDENCE_COLUMNS[d]: f"{d}_evidence" for d in DIMENSIONS})
    frame = frame.rename(columns=rename)

    frame["score_method"] = METHOD
    frame["score_version"] = PRODUCT_SCORE_VERSION
    frame["source_experiment_version"] = result["version"]

    cols = [
        "match_id", "team_id", "player_id", "primary_role", "raw_source_position",
        "position_group", "position_mapping_status", "dimension_coverage_count",
        *DIMENSIONS,
        "performance_score", "score_evidence_confidence", "fallback_dimension_count",
        *[f"{d}_evidence" for d in DIMENSIONS],
        "score_status", "score_method", "score_version", "source_experiment_version",
    ]
    frame = frame[cols].copy()

    observable = frame["position_group"].ne("OTHER_OUTFIELD")
    eligible = observable & frame["performance_score"].notna()
    summary = result["summary"]

    if int(observable.sum()) != int(summary["observable_mapped_role_rows"]):
        raise RuntimeError("Observable-role count changed between PERF-15 and materialization")
    if int(eligible.sum()) != int(summary["eligible_rows_observable_roles"]):
        raise RuntimeError("Eligible-score count changed between PERF-15 and materialization")
    if int(eligible.sum()) < int(summary["eligible_rows_observable_roles_before"]):
        raise RuntimeError("PERF-15 coverage regressed versus PERF-14")

    return result, frame


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    result, frame = build_frame(db_path)

    with duckdb.connect(str(db_path)) as con:
        ensure_table(con)
        con.execute(
            "DELETE FROM player_match_performance_score WHERE score_version = ?",
            [PRODUCT_SCORE_VERSION],
        )
        con.register("score_df", frame)
        con.execute(
            """
            INSERT INTO player_match_performance_score (
                match_id, team_id, player_id, primary_role, raw_source_position,
                position_group, position_mapping_status, dimension_coverage_count,
                attacking_threat, creation_progression, defensive_contribution,
                finishing, discipline, performance_score, score_evidence_confidence,
                fallback_dimension_count, attacking_threat_evidence,
                creation_progression_evidence, defensive_contribution_evidence,
                finishing_evidence, discipline_evidence,
                score_status, score_method, score_version, source_experiment_version
            )
            SELECT
                match_id, team_id, player_id, primary_role, raw_source_position,
                position_group, position_mapping_status, dimension_coverage_count,
                attacking_threat, creation_progression, defensive_contribution,
                finishing, discipline, performance_score, score_evidence_confidence,
                fallback_dimension_count, attacking_threat_evidence,
                creation_progression_evidence, defensive_contribution_evidence,
                finishing_evidence, discipline_evidence,
                score_status, score_method, score_version, source_experiment_version
            FROM score_df
            """
        )
        con.unregister("score_df")

        written = con.execute(
            "SELECT COUNT(*) FROM player_match_performance_score WHERE score_version = ?",
            [PRODUCT_SCORE_VERSION],
        ).fetchone()[0]
        eligible = con.execute(
            """
            SELECT COUNT(*)
            FROM player_match_performance_score
            WHERE score_version = ? AND performance_score IS NOT NULL
              AND position_group <> 'OTHER_OUTFIELD'
            """,
            [PRODUCT_SCORE_VERSION],
        ).fetchone()[0]
        fallback_scores = con.execute(
            """
            SELECT COUNT(*)
            FROM player_match_performance_score
            WHERE score_version = ? AND performance_score IS NOT NULL
              AND COALESCE(fallback_dimension_count, 0) > 0
            """,
            [PRODUCT_SCORE_VERSION],
        ).fetchone()[0]

    s = result["summary"]
    print("PERFORMANCE SCORE MATERIALIZATION: COMPLETE")
    print(f"score_version={PRODUCT_SCORE_VERSION}")
    print(f"source_experiment_version={result['version']}")
    print(f"rows_written={written}")
    print(f"observable_role_rows={s['observable_mapped_role_rows']}")
    print(f"eligible_before={s['eligible_rows_observable_roles_before']}")
    print(f"eligible_observable_scores={eligible}")
    print(f"recovered_eligible_rows={s['recovered_eligible_rows']}")
    print(f"coverage_observable_roles={s['coverage_rate_observable_roles']:.4f}")
    print(f"eligible_scores_using_fallback={fallback_scores}")
    print(f"high_participation_without_score={s['high_participation_outfield_players_without_score']}")
    print("No threshold, good/bad label or tactical recommendation was created.")


if __name__ == "__main__":
    main()
