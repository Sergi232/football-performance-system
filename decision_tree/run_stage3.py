"""Run EXPERT-03 build twice for idempotence, then validate."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(title: str, script: Path) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    args = [PY, str(script)]
    print("$ " + " ".join(args))
    subprocess.run(args, check=True)


def main() -> None:
    build = ROOT / "decision_tree" / "build_stage3.py"
    validate = ROOT / "decision_tree" / "validate_stage3.py"
    run("EXPERT-03 — FIRST BUILD", build)
    run("EXPERT-03 — IDEMPOTENCE REBUILD", build)
    run("EXPERT-03 — VALIDATION", validate)
    print("\nEXPERT-03 LOCAL BUILD COMPLETE")


if __name__ == "__main__":
    main()
