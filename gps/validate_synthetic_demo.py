"""Validate that synthetic demo GPS follows the canonical GPS pipeline safely."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.build_gps_physical_summary import SUMMARY_VERSION  # noqa: E402
from gps.generate_synthetic_demo import GENERATOR_VERSION, PROVIDER, SOURCE_FORMAT  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"


def validate(db_path: Path) -> dict[str, int]:
    db_path = Path(db_path).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with duckdb.connect(str(db_path), read_only=True) as con:
        tables = {
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
        }
        required = {"gps_imports", "gps_player_map", "gps_observations", "player_match_gps_summary", "player_match"}
        missing = sorted(required - tables)
        if missing:
            raise AssertionError(f"Missing GPS pipeline tables: {missing}")

        imports = int(con.execute(
            "SELECT COUNT(*) FROM gps_imports WHERE provider=? AND source_format=?",
            [PROVIDER, SOURCE_FORMAT],
        ).fetchone()[0])
        if imports <= 0:
            raise AssertionError("No synthetic demo GPS imports found")

        wrong_provenance = int(con.execute(
            """
            SELECT COUNT(*)
            FROM gps_imports
            WHERE provider=? AND source_format=?
              AND (
                    mapping_version<>?
                    OR notes IS NULL
                    OR NOT contains(upper(notes), 'SYNTHETIC DEMO')
                    OR mapping_config IS NULL
                  )
            """,
            [PROVIDER, SOURCE_FORMAT, GENERATOR_VERSION],
        ).fetchone()[0])
        if wrong_provenance:
            raise AssertionError(f"Synthetic provenance metadata failures: {wrong_provenance}")

        maps = int(con.execute(
            """
            SELECT COUNT(*)
            FROM gps_player_map gpm
            JOIN gps_imports gi USING(gps_import_id)
            WHERE gi.provider=? AND gi.source_format=?
              AND gpm.mapping_method='SYNTHETIC_DEMO_EXACT'
            """,
            [PROVIDER, SOURCE_FORMAT],
        ).fetchone()[0])
        if maps <= 0:
            raise AssertionError("No explicit synthetic player mappings found")

        observations = int(con.execute(
            """
            SELECT COUNT(*)
            FROM gps_observations o
            JOIN gps_imports gi USING(gps_import_id)
            WHERE gi.provider=? AND gi.source_format=?
            """,
            [PROVIDER, SOURCE_FORMAT],
        ).fetchone()[0])
        if observations <= 0:
            raise AssertionError("No synthetic GPS observations found")

        orphan_observations = int(con.execute(
            """
            SELECT COUNT(*)
            FROM gps_observations o
            JOIN gps_imports gi USING(gps_import_id)
            LEFT JOIN player_match pm
              ON pm.match_id=o.match_id AND pm.player_id=o.player_id
            WHERE gi.provider=? AND gi.source_format=?
              AND pm.player_id IS NULL
            """,
            [PROVIDER, SOURCE_FORMAT],
        ).fetchone()[0])
        if orphan_observations:
            raise AssertionError(f"Synthetic GPS observations without player_match link: {orphan_observations}")

        invalid_values = int(con.execute(
            """
            SELECT COUNT(*)
            FROM gps_observations o
            JOIN gps_imports gi USING(gps_import_id)
            WHERE gi.provider=? AND gi.source_format=?
              AND (o.distance_m < 0 OR o.speed_m_s < 0 OR o.timestamp_ms < 0)
            """,
            [PROVIDER, SOURCE_FORMAT],
        ).fetchone()[0])
        if invalid_values:
            raise AssertionError(f"Invalid negative synthetic GPS values: {invalid_values}")

        duplicate_samples = int(con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT o.gps_import_id, o.player_id, o.timestamp_ms, COUNT(*) n
                FROM gps_observations o
                JOIN gps_imports gi USING(gps_import_id)
                WHERE gi.provider=? AND gi.source_format=?
                GROUP BY o.gps_import_id, o.player_id, o.timestamp_ms
                HAVING COUNT(*) > 1
            )
            """,
            [PROVIDER, SOURCE_FORMAT],
        ).fetchone()[0])
        if duplicate_samples:
            raise AssertionError(f"Duplicate synthetic GPS samples: {duplicate_samples}")

        mapped_appearances = int(con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT DISTINCT gi.match_id, gpm.player_id
                FROM gps_player_map gpm
                JOIN gps_imports gi USING(gps_import_id)
                WHERE gi.provider=? AND gi.source_format=?
            )
            """,
            [PROVIDER, SOURCE_FORMAT],
        ).fetchone()[0])

        summary_rows = int(con.execute(
            """
            SELECT COUNT(*)
            FROM player_match_gps_summary
            WHERE summary_version=? AND provider=?
            """,
            [SUMMARY_VERSION, PROVIDER],
        ).fetchone()[0])
        if summary_rows != mapped_appearances:
            raise AssertionError(
                f"Synthetic mappings/summary mismatch: mappings={mapped_appearances}, summary={summary_rows}"
            )

        duplicate_synthetic = int(con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT match_id, player_id, COUNT(*) n
                FROM player_match_gps_summary
                WHERE summary_version=? AND provider=?
                GROUP BY match_id, player_id
                HAVING COUNT(*) > 1
            )
            """,
            [SUMMARY_VERSION, PROVIDER],
        ).fetchone()[0])
        if duplicate_synthetic:
            raise AssertionError(f"Duplicate synthetic GPS summaries: {duplicate_synthetic}")

        duplicate_latest = int(con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT match_id, player_id, COUNT(*) n
                FROM player_match_gps_summary
                WHERE summary_version=? AND import_rank=1
                GROUP BY match_id, player_id
                HAVING COUNT(*) > 1
            )
            """,
            [SUMMARY_VERSION],
        ).fetchone()[0])
        if duplicate_latest:
            raise AssertionError(f"Duplicate latest GPS summaries: {duplicate_latest}")

        synthetic_over_real = int(con.execute(
            """
            SELECT COUNT(*)
            FROM player_match_gps_summary s
            WHERE s.summary_version=?
              AND s.provider=?
              AND s.import_rank=1
              AND EXISTS (
                    SELECT 1
                    FROM player_match_gps_summary r
                    WHERE r.summary_version=s.summary_version
                      AND r.match_id=s.match_id
                      AND r.player_id=s.player_id
                      AND r.provider<>?
              )
            """,
            [SUMMARY_VERSION, PROVIDER, PROVIDER],
        ).fetchone()[0])
        if synthetic_over_real:
            raise AssertionError(f"Synthetic GPS incorrectly outranks real GPS: {synthetic_over_real}")

        distance_bounds = con.execute(
            """
            SELECT MIN(total_distance_m), MAX(total_distance_m),
                   MIN(peak_speed_m_s*3.6), MAX(peak_speed_m_s*3.6)
            FROM player_match_gps_summary
            WHERE summary_version=? AND provider=?
            """,
            [SUMMARY_VERSION, PROVIDER],
        ).fetchone()

    return {
        "imports": imports,
        "player_maps": maps,
        "observations": observations,
        "player_match_summaries": summary_rows,
        "min_distance_m": int(round(distance_bounds[0] or 0)),
        "max_distance_m": int(round(distance_bounds[1] or 0)),
        "min_peak_speed_kmh": int(round(distance_bounds[2] or 0)),
        "max_peak_speed_kmh": int(round(distance_bounds[3] or 0)),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate synthetic GPS canonical flow")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    return p.parse_args()


def main() -> None:
    result = validate(parse_args().db)
    print("GPS SYNTHETIC DEMO CONTRACT: PASS")
    print(f"generator_version={GENERATOR_VERSION}")
    print(f"summary_version={SUMMARY_VERSION}")
    print("provenance=SYNTHETIC_DEMO_EXPLICIT")
    print("canonical_flow=PASS")
    print("player_match_linkage=PASS")
    print("source_precedence=REAL_OVER_SYNTHETIC")
    print("duplicate_samples=0")
    print("duplicate_latest_summaries=0")
    for key, value in result.items():
        print(f"{key}={value}")
    print("Synthetic GPS is demo data only; it does not modify Match Rating, Performance Index or expert decisions.")


if __name__ == "__main__":
    main()
