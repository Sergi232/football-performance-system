"""PERF-17: audit provider files for a usable external match-rating benchmark.

This script is read-only. It does not modify DuckDB and does not import any external
rating into the product. A provider rating, if found, is benchmark evidence only.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
DEFAULT_INPUT = Path(r"C:\Users\sergi\Desktop\analisi_futbol\pannadata")
FILES = ["opta_player_stats.parquet", "opta_lineups.parquet", "opta_events.parquet"]
PATTERN = re.compile(r"rating|score|performance|index", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit provider files for external player-match rating columns")
    p.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    return p.parse_args()


def describe_file(con: duckdb.DuckDBPyConnection, path: Path) -> list[str]:
    schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet(?)", [str(path)]).fetchdf()
    return schema["column_name"].astype(str).tolist()


def summarize_candidate(con: duckdb.DuckDBPyConnection, path: Path, col: str) -> dict:
    q = f'''SELECT
        COUNT(*) AS rows,
        COUNT("{col}") AS non_null,
        TRY_CAST(MIN("{col}") AS DOUBLE) AS min_value,
        TRY_CAST(MAX("{col}") AS DOUBLE) AS max_value,
        TRY_CAST(AVG(TRY_CAST("{col}" AS DOUBLE)) AS DOUBLE) AS mean_value
    FROM read_parquet(?)'''
    try:
        row = con.execute(q, [str(path)]).fetchone()
        return {
            "column": col,
            "rows": int(row[0] or 0),
            "non_null": int(row[1] or 0),
            "min": row[2],
            "max": row[3],
            "mean": row[4],
        }
    except Exception:
        return {"column": col, "rows": None, "non_null": None, "min": None, "max": None, "mean": None}


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.expanduser().resolve()
    db_path = args.db.expanduser().resolve()

    print("PERF-17 EXTERNAL RATING REFERENCE AUDIT")
    print(f"input_dir={input_dir}")
    print(f"db={db_path}")

    found_any = False
    with duckdb.connect() as con:
        for name in FILES:
            path = input_dir / name
            if not path.exists():
                print(f"\n{name}: MISSING")
                continue
            cols = describe_file(con, path)
            candidates = [c for c in cols if PATTERN.search(c)]
            print(f"\n{name}: columns={len(cols)} candidate_columns={len(candidates)}")
            if not candidates:
                print("  no rating/score/performance/index column found")
                continue
            found_any = True
            for col in candidates:
                s = summarize_candidate(con, path, col)
                print(
                    f"  {s['column']}: non_null={s['non_null']}/{s['rows']} "
                    f"min={s['min']} max={s['max']} mean={s['mean']}"
                )

    print("\nRESULT")
    if found_any:
        print("candidate_external_reference_found=True")
        print("Next: inspect candidate semantics and use only as validation benchmark, never as product input.")
    else:
        print("candidate_external_reference_found=False")
        print("Next: calibrate Match Rating V2 with internal sanity gates and documented expert priors only.")


if __name__ == "__main__":
    main()
