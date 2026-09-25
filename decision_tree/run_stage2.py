"""Run EXPERT-02 build twice for idempotence, then validate."""
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
    build = ROOT / "decision_tree" / "build_stage2.py"
    validate = ROOT / "decision_tree" / "validate_stage2.py"
    run("EXPERT-02 — FIRST BUILD", build)
    run("EXPERT-02 — IDEMPOTENCE REBUILD", build)
    run("EXPERT-02 — VALIDATION", validate)
    print("\nEXPERT-02 LOCAL BUILD COMPLETE")


if __name__ == "__main__":
    main()
