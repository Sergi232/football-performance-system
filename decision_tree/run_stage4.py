"""Run EXPERT-04 build twice for idempotence, then validate."""
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
    build = ROOT / "decision_tree" / "build_stage4.py"
    validate = ROOT / "decision_tree" / "validate_stage4.py"
    run("EXPERT-04 — FIRST BUILD", build)
    run("EXPERT-04 — IDEMPOTENCE REBUILD", build)
    run("EXPERT-04 — VALIDATION", validate)
    print("\nEXPERT-04 LOCAL BUILD COMPLETE")


if __name__ == "__main__":
    main()
