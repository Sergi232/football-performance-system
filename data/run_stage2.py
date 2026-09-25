"""Run the local demo-data pipeline through Stage 2A.

Usage from repository root:
    python data/run_stage2.py
    python data/run_stage2.py --reset

`--reset` deletes only the generated demo DuckDB file passed with --db before
rebuilding it from the source Parquet files. Use it during development when the
schema/import logic changes. It never deletes the PannaData/Opta source files.
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
    parser = argparse.ArgumentParser(description="Run FPS data pipeline through Stage 2A")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the generated target DuckDB before rebuilding Stage 1/2A.",
    )
    return parser.parse_args()


def run(label: str, args: list[str]) -> None:
    print("\n" + "=" * 80)
    print(label)
    print("=" * 80)
    print("$ " + " ".join(args))
    subprocess.run(args, check=True)


def reset_database(db_path: Path) -> None:
    db_path = db_path.expanduser().resolve()
    if db_path.exists():
        db_path.unlink()
        print(f"RESET demo database: {db_path}")

    # DuckDB may leave a WAL after an interrupted local run.
    wal_path = Path(str(db_path) + ".wal")
    if wal_path.exists():
        wal_path.unlink()
        print(f"RESET WAL: {wal_path}")


def main() -> None:
    args = parse_args()
    python = sys.executable
    input_path = args.input_dir.expanduser().resolve()
    target_db = args.db.expanduser().resolve()

    if args.reset:
        reset_database(target_db)

    input_dir = str(input_path)
    db_path = str(target_db)

    run(
        "STAGE 1 — SCHEMA / AUDIT / FIXTURES / VALIDATION",
        [
            python,
            str(HERE / "run_stage1.py"),
            "--input-dir",
            input_dir,
            "--db",
            db_path,
        ],
    )
    run(
        "STAGE 2A — PLAYER MATCH PARTICIPATION",
        [
            python,
            str(HERE / "import_demo_player_match.py"),
            "--input-dir",
            input_dir,
            "--db",
            db_path,
        ],
    )
    run(
        "STAGE 2A — VALIDATION",
        [python, str(HERE / "validate_demo_database.py"), "--db", db_path],
    )

    print("\nSTAGE 2A COMPLETE")
    print(f"Database: {db_path}")


if __name__ == "__main__":
    main()
