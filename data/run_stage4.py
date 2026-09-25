from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
DEFAULT_INPUT = Path(r"C:\Users\sergi\Desktop\analisi_futbol\input\pannadata")
DEFAULT_DB = DATA_DIR / "football_performance.duckdb"


def run(label: str, args: list[str]) -> None:
    print("\n" + "=" * 80)
    print(label)
    print("=" * 80)
    print("$ " + " ".join(args))
    subprocess.run(args, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DATA-04 raw player-match import")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    run(
        "DATA-04 — APPLY DATABASE MIGRATIONS",
        [sys.executable, str(DATA_DIR / "init_database.py"), "--db", str(args.db)],
    )

    run(
        "DATA-04 — IMPORT RAW PLAYER-MATCH AGGREGATES V2",
        [
            sys.executable,
            str(DATA_DIR / "import_demo_player_match_stats_v2.py"),
            "--input-dir",
            str(args.input_dir),
            "--db",
            str(args.db),
        ],
    )

    run(
        "DATA-04 — DATABASE VALIDATION",
        [sys.executable, str(DATA_DIR / "validate_demo_database.py"), "--db", str(args.db)],
    )

    print("\nDATA-04 LOCAL IMPORT COMPLETE")


if __name__ == "__main__":
    main()
