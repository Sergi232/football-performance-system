"""Run FEATURE-03 twice for idempotence, then validate."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DB = ROOT / "data" / "football_performance.duckdb"


def run(title: str, script: Path) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    args = [PY, str(script), "--db", str(DB)]
    print("$ " + " ".join(args))
    subprocess.run(args, check=True)


def main() -> None:
    build = ROOT / "features" / "build_role_temporal_features.py"
    validate = ROOT / "features" / "validate_stage3.py"
    run("FEATURE-03 — ROLE-CONDITIONED BUILD", build)
    run("FEATURE-03 — IDEMPOTENCE REBUILD", build)
    run("FEATURE-03 — VALIDATION", validate)
    print("\nFEATURE-03 LOCAL BUILD COMPLETE")


if __name__ == "__main__":
    main()
