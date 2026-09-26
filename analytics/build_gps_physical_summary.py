"""Materialize descriptive player-match GPS summaries.

GPS remains optional. This layer aggregates only canonical GPS observations already
normalized by GPS-01. It does NOT define sprint/HSR zones, fatigue, workload or any
other threshold-based physical interpretation.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
SUMMARY_VERSION = "gps_physical_summary_v0.1-descriptive"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Materialize descriptive GPS player-match summaries")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    return p.parse_args()


def materialize(db_path: Path) -> dict[str, int]:
    db_path = Path(db_path).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with duckdb.connect(str(db_path)) as con:
        con.execute(
            f"""
            CREATE OR REPLACE TABLE player_match_gps_summary AS
            WITH aggregated AS (
                SELECT
                    o.gps_import_id,
                    o.match_id,
                    o.player_id,
                    pm.team_id,
                    m.match_date,
                    gi.provider,
                    gi.source_filename,
                    gi.imported_at,
                    COUNT(*)::BIGINT AS sample_count,
                    COUNT(o.distance_m)::BIGINT AS distance_sample_count,
                    COUNT(o.speed_m_s)::BIGINT AS speed_sample_count,
                    COUNT(o.acceleration_m_s2)::BIGINT AS acceleration_sample_count,
                    SUM(o.distance_m) AS total_distance_m,
                    MAX(o.speed_m_s) AS peak_speed_m_s,
                    MAX(o.acceleration_m_s2) AS max_acceleration_m_s2,
                    MIN(o.acceleration_m_s2) AS min_acceleration_m_s2,
                    (MAX(o.timestamp_ms) - MIN(o.timestamp_ms)) / 1000.0 AS observation_duration_s,
                    COUNT(*) FILTER (WHERE o.quality_flags IS NOT NULL)::BIGINT AS quality_metadata_sample_count
                FROM gps_observations o
                JOIN gps_imports gi ON gi.gps_import_id = o.gps_import_id
                JOIN player_match pm
                  ON pm.match_id = o.match_id
                 AND pm.player_id = o.player_id
                JOIN matches m ON m.match_id = o.match_id
                GROUP BY
                    o.gps_import_id, o.match_id, o.player_id, pm.team_id,
                    m.match_date, gi.provider, gi.source_filename, gi.imported_at
            ), ranked AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY match_id, player_id
                        ORDER BY imported_at DESC NULLS LAST, gps_import_id DESC
                    ) AS import_rank
                FROM aggregated
            )
            SELECT
                *,
                CASE WHEN sample_count > 0 THEN 100.0 * distance_sample_count / sample_count ELSE NULL END AS distance_coverage_pct,
                CASE WHEN sample_count > 0 THEN 100.0 * speed_sample_count / sample_count ELSE NULL END AS speed_coverage_pct,
                CASE WHEN sample_count > 0 THEN 100.0 * acceleration_sample_count / sample_count ELSE NULL END AS acceleration_coverage_pct,
                '{SUMMARY_VERSION}'::VARCHAR AS summary_version,
                CURRENT_TIMESTAMP AS computed_at
            FROM ranked
            """
        )

        row = con.execute(
            """
            SELECT
                COUNT(*) AS summary_rows,
                COUNT(*) FILTER (WHERE import_rank = 1) AS latest_rows,
                COUNT(DISTINCT match_id) FILTER (WHERE import_rank = 1) AS matches,
                COUNT(DISTINCT player_id) FILTER (WHERE import_rank = 1) AS players,
                COUNT(DISTINCT gps_import_id) AS imports
            FROM player_match_gps_summary
            """
        ).fetchone()

    keys = ["summary_rows", "latest_rows", "matches", "players", "imports"]
    return dict(zip(keys, [int(v or 0) for v in row]))


def main() -> None:
    args = parse_args()
    summary = materialize(args.db)
    print("GPS PHYSICAL SUMMARY MATERIALIZATION: COMPLETE")
    print(f"summary_version={SUMMARY_VERSION}")
    for key, value in summary.items():
        print(f"{key}={value}")
    print("No HSR/sprint zone, workload, fatigue or readiness threshold was created.")


if __name__ == "__main__":
    main()
