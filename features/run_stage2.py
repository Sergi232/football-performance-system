from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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
