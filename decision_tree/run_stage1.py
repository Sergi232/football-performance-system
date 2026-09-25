from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(title: str, args: list[str]) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print("$", " ".join(args))
    subprocess.run(args, check=True)


def main() -> None:
    py = sys.executable
    run("EXPERT-01 — FIRST BUILD", [py, str(ROOT / "decision_tree" / "build_stage1.py")])
    run("EXPERT-01 — IDEMPOTENCE REBUILD", [py, str(ROOT / "decision_tree" / "build_stage1.py")])
    run("EXPERT-01 — VALIDATION", [py, str(ROOT / "decision_tree" / "validate_stage1.py")])
    print("\nEXPERT-01 LOCAL BUILD COMPLETE")


if __name__ == "__main__":
    main()
