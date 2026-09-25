"""Apply GPS schema migration and run GPS-01 validation."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"


def run(title: str, args: list[str]) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print("$ " + " ".join(args))
    subprocess.run(args, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GPS-01 schema + contract validation")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()

    run(
        "GPS-01 — APPLY DATABASE MIGRATIONS",
        [sys.executable, str(ROOT / "data" / "init_database.py"), "--db", str(db)],
    )
    run(
        "GPS-01 — NORMALIZATION CONTRACT VALIDATION",
        [sys.executable, str(ROOT / "gps" / "validate_gps_stage1.py"), "--db", str(db)],
    )
    print("\nGPS-01 LOCAL VALIDATION COMPLETE")


if __name__ == "__main__":
    main()
