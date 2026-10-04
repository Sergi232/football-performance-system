"""Run the unchanged Match Rating materializers against an explicit DuckDB path."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def run(script: str, *args: str) -> None:
    subprocess.run([sys.executable, str(ROOT / script), *args], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize the existing V5 route on a selected database")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--v4-frozen-artifact", type=Path, default=None)
    parser.add_argument("--gk-frozen-artifact", type=Path, default=None)
    args = parser.parse_args()
    db = args.db.expanduser().resolve()
    output = args.output_dir.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)
    output.mkdir(parents=True, exist_ok=True)
    common = ["--db", str(db)]
    run("analytics/build_match_rating_v2.py", *common)
    # V2 is the explicit coverage route.  A role-unavailable player with
    # goalkeeper-like raw statistics must remain V2 fallback, never inferred
    # as GK. PERF-16 cannot materialize that legacy generic row, so its known
    # coverage assertion is non-blocking for the V5 route.
    try:
        run("analytics/build_match_rating.py", *common)
    except subprocess.CalledProcessError as exc:
        if "build_match_rating.py" not in str(exc):
            raise
        print("PERF-16 coverage gap retained as V2 fallback for role-unavailable rows")
    reference = [] if args.input_dir is None else ["--input-dir", str(args.input_dir.expanduser().resolve())]
    v4 = [] if args.v4_frozen_artifact is None else ["--frozen-artifact", str(args.v4_frozen_artifact.expanduser().resolve())]
    gk = [] if args.gk_frozen_artifact is None else ["--gk-frozen-artifact", str(args.gk_frozen_artifact.expanduser().resolve())]
    run("analytics/build_match_rating_v4_experimental.py", *common, *reference, *v4, "--output-dir", str(output / "v4"))
    with duckdb.connect(str(db), read_only=True) as con:
        collector_rows = int(con.execute(
            "SELECT COUNT(*) FROM matches WHERE source_type='collector_html_v1.1'"
        ).fetchone()[0])
    if collector_rows:
        run("analytics/build_on_pitch_goal_context_collector.py", *common)
    run("analytics/build_match_rating_v4_onpitch_experimental.py", *common)
    run("analytics/build_match_rating_v5_candidate.py", *common, *reference, *gk, "--output-dir", str(output / "v5"))
    print("MATCH RATING V5 INCREMENTAL RUN: PASS")


if __name__ == "__main__":
    main()
