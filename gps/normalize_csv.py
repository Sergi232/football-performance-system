"""Generic CSV -> canonical GPS sample normalizer.

The mapping JSON defines provider column names and units. This module does not
calculate analytical features such as sprint zones or load scores.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


CANONICAL_COLUMNS = [
    "source_player_key",
    "timestamp_ms",
    "x",
    "y",
    "distance_m",
    "speed_m_s",
    "acceleration_m_s2",
    "source_row_number",
    "quality_flags",
]

G = 9.80665


def _number(value: Any, decimal_separator: str = ".") -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    if decimal_separator == ",":
        text = text.replace(".", "").replace(",", ".")
    return float(text)


def _required_number(value: Any, field: str, row_number: int, decimal_separator: str) -> float:
    try:
        parsed = _number(value, decimal_separator)
    except ValueError as exc:
        raise ValueError(f"Row {row_number}: invalid required {field}: {value!r}") from exc
    if parsed is None:
        raise ValueError(f"Row {row_number}: missing required {field}")
    return parsed


def _convert_timestamp(value: float, unit: str) -> int:
    if unit == "ms":
        return int(round(value))
    if unit == "s":
        return int(round(value * 1000.0))
    raise ValueError(f"Unsupported timestamp unit: {unit}")


def _convert_distance(value: float, unit: str) -> float:
    if unit == "m":
        return value
    if unit == "km":
        return value * 1000.0
    raise ValueError(f"Unsupported distance unit: {unit}")


def _convert_speed(value: float, unit: str) -> float:
    if unit == "m_s":
        return value
    if unit == "km_h":
        return value / 3.6
    raise ValueError(f"Unsupported speed unit: {unit}")


def _convert_acceleration(value: float, unit: str) -> float:
    if unit == "m_s2":
        return value
    if unit == "g":
        return value * G
    raise ValueError(f"Unsupported acceleration unit: {unit}")


def _convert_coordinate(value: float, unit: str) -> float:
    if unit == "m":
        return value
    raise ValueError(
        f"Unsupported coordinate unit: {unit}. GPS-01 only imports coordinates already expressible in metres."
    )


def _optional_converted(
    row: dict[str, str],
    source_column: str | None,
    field_name: str,
    unit: str | None,
    converter,
    decimal_separator: str,
    flags: list[str],
) -> float | None:
    if not source_column:
        return None
    raw = row.get(source_column)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        value = _number(raw, decimal_separator)
        if value is None:
            return None
        return converter(value, unit)
    except (ValueError, TypeError):
        flags.append(f"INVALID_{field_name.upper()}")
        return None


def load_mapping(path: Path) -> dict[str, Any]:
    mapping = json.loads(path.read_text(encoding="utf-8"))
    columns = mapping.get("columns", {})
    for required in ("player_key", "timestamp"):
        if not columns.get(required):
            raise ValueError(f"Mapping missing required columns.{required}")
    mapping.setdefault("delimiter", ",")
    mapping.setdefault("encoding", "utf-8")
    mapping.setdefault("decimal_separator", ".")
    mapping.setdefault("distance_mode", "delta")
    mapping.setdefault("units", {})
    return mapping


def normalize_csv(input_path: Path, mapping_path: Path, output_path: Path) -> dict[str, int]:
    mapping = load_mapping(mapping_path)
    columns = mapping["columns"]
    units = mapping["units"]
    decimal_separator = mapping["decimal_separator"]
    distance_mode = mapping["distance_mode"]

    if distance_mode not in {"delta", "cumulative"}:
        raise ValueError("distance_mode must be 'delta' or 'cumulative'")

    previous_timestamp: dict[str, int] = {}
    previous_cumulative_distance: dict[str, float] = {}
    row_count = 0
    flagged_rows = 0
    players: set[str] = set()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding=mapping["encoding"], newline="") as src, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as dst:
        reader = csv.DictReader(src, delimiter=mapping["delimiter"])
        if reader.fieldnames is None:
            raise ValueError("Source CSV has no header")

        missing_source_columns = [
            source
            for source in columns.values()
            if source and source not in reader.fieldnames
        ]
        if missing_source_columns:
            raise ValueError(f"Source CSV missing mapped columns: {sorted(set(missing_source_columns))}")

        writer = csv.DictWriter(dst, fieldnames=CANONICAL_COLUMNS)
        writer.writeheader()

        for source_row_number, row in enumerate(reader, start=2):
            flags: list[str] = []
            player_key = str(row.get(columns["player_key"], "")).strip()
            if not player_key:
                raise ValueError(f"Row {source_row_number}: missing required player key")
            players.add(player_key)

            timestamp_raw = _required_number(
                row.get(columns["timestamp"]), "timestamp", source_row_number, decimal_separator
            )
            timestamp_ms = _convert_timestamp(timestamp_raw, units.get("timestamp", "ms"))

            previous_ts = previous_timestamp.get(player_key)
            if previous_ts is not None and timestamp_ms <= previous_ts:
                flags.append("NON_MONOTONIC_TIMESTAMP")
            previous_timestamp[player_key] = timestamp_ms

            x = _optional_converted(
                row, columns.get("x"), "x", units.get("x", "m"), _convert_coordinate,
                decimal_separator, flags
            )
            y = _optional_converted(
                row, columns.get("y"), "y", units.get("y", "m"), _convert_coordinate,
                decimal_separator, flags
            )
            speed = _optional_converted(
                row, columns.get("speed"), "speed", units.get("speed", "m_s"), _convert_speed,
                decimal_separator, flags
            )
            acceleration = _optional_converted(
                row, columns.get("acceleration"), "acceleration",
                units.get("acceleration", "m_s2"), _convert_acceleration,
                decimal_separator, flags
            )
            source_distance = _optional_converted(
                row, columns.get("distance"), "distance", units.get("distance", "m"), _convert_distance,
                decimal_separator, flags
            )

            distance = source_distance
            if source_distance is not None and distance_mode == "cumulative":
                previous_distance = previous_cumulative_distance.get(player_key)
                if previous_distance is None:
                    distance = None
                elif source_distance >= previous_distance:
                    distance = source_distance - previous_distance
                else:
                    distance = None
                    flags.append("CUMULATIVE_DISTANCE_RESET")
                previous_cumulative_distance[player_key] = source_distance

            if distance is not None and distance < 0:
                distance = None
                flags.append("NEGATIVE_DISTANCE")
            if speed is not None and speed < 0:
                speed = None
                flags.append("NEGATIVE_SPEED")

            writer.writerow(
                {
                    "source_player_key": player_key,
                    "timestamp_ms": timestamp_ms,
                    "x": "" if x is None else x,
                    "y": "" if y is None else y,
                    "distance_m": "" if distance is None else distance,
                    "speed_m_s": "" if speed is None else speed,
                    "acceleration_m_s2": "" if acceleration is None else acceleration,
                    "source_row_number": source_row_number,
                    "quality_flags": "|".join(flags),
                }
            )
            row_count += 1
            if flags:
                flagged_rows += 1

    return {"rows": row_count, "players": len(players), "flagged_rows": flagged_rows}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize provider GPS CSV to FPS canonical schema")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats = normalize_csv(args.input, args.mapping, args.output)
    print(f"GPS normalized: {args.output}")
    print(f"rows: {stats['rows']}")
    print(f"players: {stats['players']}")
    print(f"flagged_rows: {stats['flagged_rows']}")


if __name__ == "__main__":
    main()
