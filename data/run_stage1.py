"""Run Stage 1 of the local demo-data pipeline with one command.

Stage 1 contract:
    1. initialize/update DuckDB schema;
    2. audit the available PannaData/Opta parquet schemas;
    3. import Deportivo Alavés 2025/26 fixtures;
    4. validate the normalized database.

Usage from repository root:
    python data/run_stage1.py

If a step fails, the process stops immediately. No later stage is executed on a
known-bad database.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = Path(r"C:\Users\sergi\Desktop\analisi_futbol\input\pannadata")
DEFAULT_DB = HERE / "football_performance.duckdb"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FPS data Stage 1")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    return parser.parse_args()


def run(label: str, args: list[str]) -> None:
    print("\n" + "=" * 80)
    print(label)
    print("=" * 80)
    print("$ " + " ".join(args))
    subprocess.run(args, check=True)


def main() -> None:
    args = parse_args()
    python = sys.executable
    input_dir = str(args.input_dir.expanduser().resolve())
    db_path = str(args.db.expanduser().resolve())

    run(
        "1/4 INITIALIZE DATABASE",
        [python, str(HERE / "init_database.py"), "--db", db_path],
    )
    run(
        "2/4 AUDIT SOURCE SCHEMAS",
        [
            python,
            str(HERE / "audit_pannadata_sources.py"),
            "--input-dir",
            input_dir,
        ],
    )
    run(
        "3/4 IMPORT DEMO FIXTURES",
        [
            python,
            str(HERE / "import_demo_fixtures.py"),
            "--input-dir",
            input_dir,
            "--db",
            db_path,
        ],
    )
    run(
        "4/4 VALIDATE DATABASE",
        [python, str(HERE / "validate_demo_database.py"), "--db", db_path],
    )

    print("\nSTAGE 1 COMPLETE")
    print(f"Database: {db_path}")
    print(f"Source audit: {HERE / 'source_schema_audit.json'}")
    print(f"Validation: {HERE / 'validation_report.json'}")


if __name__ == "__main__":
    main()
