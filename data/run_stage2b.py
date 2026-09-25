"""Run DATA-02 lineup enrichment on top of a validated DATA-01 database.

Usage from repository root:
    python data/run_stage2b.py
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
    parser = argparse.ArgumentParser(description="Run FPS DATA-02 lineup enrichment")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cmd = [
        sys.executable,
        str(HERE / "import_demo_lineups.py"),
        "--input-dir",
        str(args.input_dir.expanduser().resolve()),
        "--db",
        str(args.db.expanduser().resolve()),
    ]
    print("=" * 80)
    print("DATA-02 — LINEUPS / STARTERS / ROLES")
    print("=" * 80)
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)
    print("\nDATA-02 LOCAL IMPORT COMPLETE")


if __name__ == "__main__":
    main()
