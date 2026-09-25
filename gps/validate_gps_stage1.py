"""Standalone validation for GPS-01 normalized contract."""

from __future__ import annotations

import argparse
import csv
import json
import math
import tempfile
from pathlib import Path

import duckdb

from normalize_csv import CANONICAL_COLUMNS, normalize_csv


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
MAPPING = HERE / "mapping_schema.example.json"


def validate_database(db_path: Path) -> None:
    required_import_columns = {
        "source_format",
        "sample_rate_hz",
        "time_basis",
        "coordinate_system",
        "distance_mode",
        "source_units",
        "mapping_config",
        "notes",
    }
    required_observation_columns = {"source_row_number", "quality_flags"}

    with duckdb.connect(str(db_path)) as con:
        tables = {
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
        }
        assert "gps_player_map" in tables, "gps_player_map table missing"

        import_columns = {
            row[0]
            for row in con.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name='gps_imports'"
            ).fetchall()
        }
        obs_columns = {
            row[0]
            for row in con.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name='gps_observations'"
            ).fetchall()
        }
        assert required_import_columns <= import_columns
        assert required_observation_columns <= obs_columns

        versions = {
            row[0]
            for row in con.execute("SELECT schema_version FROM schema_meta").fetchall()
        }
        assert "0.4.0" in versions, "GPS schema version 0.4.0 missing"


def validate_normalizer() -> dict[str, int]:
    source = """athlete_id;time_s;pos_x_m;pos_y_m;distance_total_km;speed_kmh;acc_g
P01;0;10;20;0;0;0
P01;1;11;20;0.005;18;0.1
P01;2;12;20;0.011;21.6;-0.2
P02;0;8;15;0;0;0
P02;1;8.5;15;0.004;14.4;0.05
P02;0.5;8.7;15;0.002;-3;0
"""

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "provider.csv"
        output_path = tmp_path / "normalized.csv"
        input_path.write_text(source, encoding="utf-8")

        stats = normalize_csv(input_path, MAPPING, output_path)
        assert stats == {"rows": 6, "players": 2, "flagged_rows": 1}

        with output_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        assert list(rows[0].keys()) == CANONICAL_COLUMNS
        assert rows[0]["distance_m"] == ""

        second = rows[1]
        assert second["source_player_key"] == "P01"
        assert int(second["timestamp_ms"]) == 1000
        assert math.isclose(float(second["distance_m"]), 5.0, rel_tol=1e-9)
        assert math.isclose(float(second["speed_m_s"]), 5.0, rel_tol=1e-9)
        assert math.isclose(float(second["acceleration_m_s2"]), 0.980665, rel_tol=1e-9)

        flagged = rows[-1]
        flags = set(flagged["quality_flags"].split("|"))
        assert {
            "NON_MONOTONIC_TIMESTAMP",
            "CUMULATIVE_DISTANCE_RESET",
            "NEGATIVE_SPEED",
        } <= flags
        assert flagged["speed_m_s"] == ""
        assert flagged["distance_m"] == ""

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate GPS-01 contract")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_database(args.db.expanduser().resolve())
    stats = validate_normalizer()
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))

    print("GPS-01 VALIDATION: PASS")
    print("schema_version: 0.4.0")
    print(f"mapping_version: {mapping['mapping_version']}")
    print(f"synthetic rows: {stats['rows']}")
    print(f"synthetic players: {stats['players']}")
    print(f"quality-control flagged rows: {stats['flagged_rows']}")
    print("unit conversions: PASS")
    print("cumulative -> delta distance: PASS")
    print("gps_player_map + import metadata schema: PASS")
    print("No sprint/HIE thresholds were invented.")


if __name__ == "__main__":
    main()
