"""Run FEATURE-01 build twice (idempotence smoke test) and validate it."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FEATURE-01")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    return parser.parse_args()


def run(title: str, args: list[str]) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print("$ " + " ".join(args))
    subprocess.run(args, check=True)


def main() -> None:
    args = parse_args()
    db = str(args.db.expanduser().resolve())
    python = sys.executable

    run(
        "FEATURE-01 — FIRST DETERMINISTIC BUILD",
        [python, str(ROOT / "features" / "build_player_match_features.py"), "--db", db],
    )
    run(
        "FEATURE-01 — IDEMPOTENCE REBUILD",
        [python, str(ROOT / "features" / "build_player_match_features.py"), "--db", db],
    )
    run(
        "FEATURE-01 — VALIDATION",
        [python, str(ROOT / "features" / "validate_stage1.py"), "--db", db],
    )
    print("\nFEATURE-01 LOCAL BUILD COMPLETE")


if __name__ == "__main__":
    main()
