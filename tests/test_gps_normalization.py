import csv
import math
from pathlib import Path

from gps.normalize_csv import CANONICAL_COLUMNS, normalize_csv


ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "gps" / "mapping_schema.example.json"


def test_gps_normalizer_converts_units_and_cumulative_distance(tmp_path):
    source = tmp_path / "provider.csv"
    output = tmp_path / "normalized.csv"
    source.write_text(
        "athlete_id;time_s;pos_x_m;pos_y_m;distance_total_km;speed_kmh;acc_g\n"
        "P01;0;10;20;0;0;0\n"
        "P01;1;11;20;0.005;18;0.1\n",
        encoding="utf-8",
    )

    stats = normalize_csv(source, MAPPING, output)
    assert stats == {"rows": 2, "players": 1, "flagged_rows": 0}

    with output.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    assert list(rows[0].keys()) == CANONICAL_COLUMNS
    assert rows[0]["distance_m"] == ""
    assert int(rows[1]["timestamp_ms"]) == 1000
    assert math.isclose(float(rows[1]["distance_m"]), 5.0, rel_tol=1e-9)
    assert math.isclose(float(rows[1]["speed_m_s"]), 5.0, rel_tol=1e-9)
    assert math.isclose(float(rows[1]["acceleration_m_s2"]), 0.980665, rel_tol=1e-9)


def test_gps_normalizer_flags_bad_samples_without_inventing_values(tmp_path):
    source = tmp_path / "provider.csv"
    output = tmp_path / "normalized.csv"
    source.write_text(
        "athlete_id;time_s;pos_x_m;pos_y_m;distance_total_km;speed_kmh;acc_g\n"
        "P01;1;10;20;0.005;18;0\n"
        "P01;0.5;11;20;0.002;-3;0\n",
        encoding="utf-8",
    )

    stats = normalize_csv(source, MAPPING, output)
    assert stats["flagged_rows"] == 1

    with output.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    flags = set(rows[1]["quality_flags"].split("|"))
    assert "NON_MONOTONIC_TIMESTAMP" in flags
    assert "CUMULATIVE_DISTANCE_RESET" in flags
    assert "NEGATIVE_SPEED" in flags
    assert rows[1]["distance_m"] == ""
    assert rows[1]["speed_m_s"] == ""
