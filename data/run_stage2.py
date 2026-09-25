"""Run the local demo-data pipeline through Stage 2A.

This command is cumulative: it re-runs the idempotent Stage 1 pipeline, then imports
player-match participation and validates the result.

Usage from repository root:
    python data/run_stage2.py
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
