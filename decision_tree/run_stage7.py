"""Local runner for EXPERT-07 / N13000."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(title: str, args: list[str]) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print("$ " + " ".join(args))
    subprocess.run(args, check=True)


def main() -> None:
    py = sys.executable
    build = str(ROOT / "decision_tree" / "build_stage7.py")
    validate = str(ROOT / "decision_tree" / "validate_stage7.py")

    run("EXPERT-07 — FIRST BUILD", [py, build])
    run("EXPERT-07 — IDEMPOTENCE REBUILD", [py, build])
    run("EXPERT-07 — VALIDATION", [py, validate])
    print("\nEXPERT-07 LOCAL BUILD COMPLETE")


if __name__ == "__main__":
    main()
