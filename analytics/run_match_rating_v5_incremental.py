"""Run the unchanged Match Rating materializers against an explicit DuckDB path."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script: str, *args: str) -> None:
    subprocess.run([sys.executable, str(ROOT / script), *args], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize the existing V5 route on a selected database")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    db = args.db.expanduser().resolve()
    output = args.output_dir.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)
    output.mkdir(parents=True, exist_ok=True)
    common = ["--db", str(db)]
    run("analytics/build_match_rating.py", *common)
    run("analytics/build_match_rating_v2.py", *common)
    reference = [] if args.input_dir is None else ["--input-dir", str(args.input_dir.expanduser().resolve())]
    run("analytics/build_match_rating_v4_experimental.py", *common, *reference, "--output-dir", str(output / "v4"))
    run("analytics/build_on_pitch_goal_context_collector.py", *common)
    run("analytics/build_match_rating_v4_onpitch_experimental.py", *common)
    run("analytics/build_match_rating_v5_candidate.py", *common, *reference, "--output-dir", str(output / "v5"))
    print("MATCH RATING V5 INCREMENTAL RUN: PASS")


if __name__ == "__main__":
    main()
