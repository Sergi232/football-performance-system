"""Hardened launcher for Product Spiral Lab.

Keeps the core runner unchanged while making CSV case logging schema-stable even when
a later failing case contains extra diagnostic fields.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import run_product_spiral as spiral  # noqa: E402

CASE_FIELDS = [
    "timestamp",
    "kind",
    "team_id",
    "entity_id",
    "label",
    "pass",
    "classification",
    "pdf_bytes",
    "approx_pages",
    "elapsed_s",
    "unsafe_guardrail",
    "match_rating_version",
    "engine_version",
    "error",
]


def _append_csv_safe(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    normalized = {field: row.get(field, "") for field in CASE_FIELDS}
    with path.open("a", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=CASE_FIELDS, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(normalized)


spiral._append_csv = _append_csv_safe

if __name__ == "__main__":
    spiral.main()
