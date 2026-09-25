"""Run FEATURE-02 temporal build and validation."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"


def run(title: str, args: list[str]) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print("$", " ".join(args))
    subprocess.run(args, check=True)


def main() -> None:
    py = sys.executable
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    with duckdb.connect(str(DB), read_only=True) as con:
        missing_dates = con.execute(
            "SELECT COUNT(*) FROM matches WHERE match_date IS NULL"
        ).fetchone()[0]

    if missing_dates:
        raise RuntimeError(
            f"FEATURE-02 blocked: {missing_dates} matches have NULL match_date. "
            "Run `python data/repair_demo_match_dates.py` first; chronology must come "
            "from the original fixture source and will not be inferred from IDs or row order."
        )

    run(
        "FEATURE-02 — TEMPORAL BUILD",
        [py, str(ROOT / "features" / "build_temporal_features.py"), "--db", str(DB)],
    )
    run(
        "FEATURE-02 — IDEMPOTENCE REBUILD",
        [py, str(ROOT / "features" / "build_temporal_features.py"), "--db", str(DB)],
    )
    run(
        "FEATURE-02 — VALIDATION",
        [py, str(ROOT / "features" / "validate_stage2.py"), "--db", str(DB)],
    )
    print("\nFEATURE-02 LOCAL BUILD COMPLETE")


if __name__ == "__main__":
    main()
