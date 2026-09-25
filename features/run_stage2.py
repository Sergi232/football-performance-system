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


def count_missing_dates() -> int:
    with duckdb.connect(str(DB), read_only=True) as con:
        return int(
            con.execute("SELECT COUNT(*) FROM matches WHERE match_date IS NULL").fetchone()[0]
        )


def main() -> None:
    py = sys.executable
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    missing_dates = count_missing_dates()
    if missing_dates:
        run(
            "FEATURE-02 — REPAIR SOURCE MATCH DATES",
            [py, str(ROOT / "data" / "repair_demo_match_dates.py"), "--db", str(DB)],
        )
        remaining = count_missing_dates()
        if remaining:
            raise RuntimeError(
                f"FEATURE-02 blocked: {remaining} matches still have NULL match_date after source repair."
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
