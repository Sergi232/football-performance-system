"""Hardened launcher for Product Spiral Lab.

Automatically selects:
- real-DB spiral when football_performance.duckdb is available;
- true iterative DB-free UI/PDF optimizer otherwise.

The DB-free optimizer uses the real GitHub presentation code, contract-compatible
synthetic fixtures and an already-installed Chrome/Edge when available. It does not
download a browser, model or private dataset.
"""
from __future__ import annotations

import csv
import os
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


def _private_db_available() -> bool:
    default_db = ROOT / "data" / "football_performance.duckdb"
    db = Path(os.environ.get("FPS_DB_PATH", default_db)).expanduser().resolve()
    return db.exists()


if __name__ == "__main__":
    if _private_db_available():
        print("Product Spiral launcher: REAL-DB mode")
        spiral.main()
    else:
        print("Product Spiral launcher: TRUE ITERATIVE DB-FREE OPTIMIZER")
        from product import run_product_spiral_optimizer as optimizer

        optimizer.main()
