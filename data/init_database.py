"""Create or upgrade the local Football Performance System DuckDB database.

Usage:
    python data/init_database.py
    python data/init_database.py --db path/to/football_performance.duckdb

The database file is local and must not be committed to GitHub.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


HERE = Path(__file__).resolve().parent
DEFAULT_DB = HERE / "football_performance.duckdb"
SCHEMA_FILE = HERE / "schema.sql"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize the FPS DuckDB database")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"DuckDB file path (default: {DEFAULT_DB})",
    )
    return parser.parse_args()


def initialize_database(db_path: Path) -> None:
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_FILE}")

    db_path = db_path.expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")

    with duckdb.connect(str(db_path)) as con:
        con.execute(schema_sql)

        tables = [
            row[0]
            for row in con.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
                ORDER BY table_name
                """
            ).fetchall()
        ]

        versions = con.execute(
            "SELECT schema_version FROM schema_meta ORDER BY applied_at"
        ).fetchall()

    print(f"Database ready: {db_path}")
    print(f"Schema versions: {[v[0] for v in versions]}")
    print(f"Tables/views: {', '.join(tables)}")


if __name__ == "__main__":
    initialize_database(parse_args().db)
