"""Static compatibility gate for the Streamlit product UI."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


def main() -> None:
    deprecated: list[tuple[str, int, str]] = []
    invalid_known_icons: list[tuple[str, int, str]] = []

    for path in sorted(APP.rglob("*.py")):
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if "use_container_width" in line:
                deprecated.append((str(path.relative_to(ROOT)), line_no, line.strip()))
            if 'icon="⚑"' in line or "icon='⚑'" in line:
                invalid_known_icons.append((str(path.relative_to(ROOT)), line_no, line.strip()))

    print("STREAMLIT UI COMPATIBILITY")
    print(f"deprecated_use_container_width={len(deprecated)}")
    print(f"known_invalid_navigation_icons={len(invalid_known_icons)}")

    if deprecated:
        print("\nDeprecated width API:")
        for path, line_no, line in deprecated:
            print(f"- {path}:{line_no}: {line}")
    if invalid_known_icons:
        print("\nKnown invalid navigation icons:")
        for path, line_no, line in invalid_known_icons:
            print(f"- {path}:{line_no}: {line}")

    if deprecated or invalid_known_icons:
        raise SystemExit("STREAMLIT UI COMPATIBILITY: FAIL")

    print("STREAMLIT UI COMPATIBILITY: PASS")


if __name__ == "__main__":
    main()
