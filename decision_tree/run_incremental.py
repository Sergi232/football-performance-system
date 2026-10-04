"""Run existing N1000–N13000 builders against an explicit DuckDB path."""
from __future__ import annotations
import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STAGES = [f"decision_tree.build_stage{i}" for i in range(1, 8)]

def main() -> None:
    parser = argparse.ArgumentParser(description="Run existing expert stages on an explicit DB")
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    for name in STAGES:
        module = importlib.import_module(name)
        module.DB = args.db.expanduser().resolve()
        module.main()
    print("EXPERT INCREMENTAL RUN: PASS")

if __name__ == "__main__": main()
