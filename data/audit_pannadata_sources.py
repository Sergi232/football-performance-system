"""Audit the local PannaData/Opta parquet sources used by the TFM.

This script does not modify the source data. It inventories row counts, columns and
types so the importer can be built against the real local schema instead of guessed
field names.

Usage:
    python data/audit_pannadata_sources.py
    python data/audit_pannadata_sources.py --input-dir C:/path/to/pannadata

Output:
    data/source_schema_audit.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


DEFAULT_INPUT = Path(r"C:\Users\sergi\Desktop\analisi_futbol\input\pannadata")
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "source_schema_audit.json"

EXPECTED_FILES = [
    "opta_fixtures.parquet",
    "opta_lineups.parquet",
    "opta_player_stats.parquet",
    "opta_players.parquet",
    "opta_events.parquet",
    "opta_shot_events.parquet",
    "opta_shots.parquet",
    "opta_match_xg.parquet",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit PannaData/Opta parquet schemas")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def inspect_parquet(con: duckdb.DuckDBPyConnection, path: Path) -> dict:
    escaped = sql_path(path)
    row_count = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{escaped}')"
    ).fetchone()[0]

    schema_rows = con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{escaped}')"
    ).fetchall()

    columns = [
        {
            "name": row[0],
            "type": row[1],
            "null": row[2],
            "key": row[3],
            "default": row[4],
            "extra": row[5],
        }
        for row in schema_rows
    ]

    return {
        "file": path.name,
        "path": str(path.resolve()),
        "exists": True,
        "row_count": row_count,
        "column_count": len(columns),
        "columns": columns,
    }


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    audit: dict = {
        "input_dir": str(input_dir),
        "sources": [],
    }

    with duckdb.connect() as con:
        for filename in EXPECTED_FILES:
            path = input_dir / filename
            if not path.exists():
                audit["sources"].append(
                    {
                        "file": filename,
                        "path": str(path),
                        "exists": False,
                    }
                )
                continue

            audit["sources"].append(inspect_parquet(con, path))

    output.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Source audit written to: {output}")
    for source in audit["sources"]:
        if source["exists"]:
            print(
                f"OK  {source['file']}: "
                f"{source['row_count']:,} rows / {source['column_count']} columns"
            )
        else:
            print(f"MISS {source['file']}")


if __name__ == "__main__":
    main()
