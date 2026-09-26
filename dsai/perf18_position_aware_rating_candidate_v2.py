"""PERF-18 position-aware candidate v2.

Thin compatibility wrapper around perf18_position_aware_rating_candidate.py.
It fixes fixture-date discovery without changing rating logic.

The v1 experiment correctly refused to train when its chosen fixture date column
produced zero valid timestamps. This wrapper audits candidate fixture columns and
selects the parse strategy with real temporal coverage, preserving the leakage-safe
chronological split.

It also re-exports the audited v1 model symbols so downstream PERF-18 experiments
can use the corrected temporal loader without duplicating rating logic.
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb

import perf18_position_aware_rating_candidate as base


# Re-export audited model symbols for downstream experiments.
DIMENSIONS = base.DIMENSIONS
ROLE_ORDER = base.ROLE_ORDER
apply_dimension = base.apply_dimension
build_frame = base.build_frame
fit_dimension_reference = base.fit_dimension_reference
metric = base.metric
split_dates = base.split_dates


def _q(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _candidate_columns(schema) -> list[str]:
    names = schema["column_name"].astype(str).tolist()
    preferred = [
        "match_date", "matchDate", "date", "game_date", "gameDate",
        "start_date", "startDate", "start_time", "startTime",
        "kickoff", "kick_off", "kickoff_time", "kickoffTime",
        "timestamp", "match_timestamp", "matchTimestamp",
        "utc_date", "utcDate", "fixture_date", "fixtureDate",
    ]
    out: list[str] = []
    for c in preferred:
        if c in names and c not in out:
            out.append(c)
    for c in names:
        if re.search(r"date|time|kick|start", c, flags=re.I) and c not in out:
            out.append(c)
    return out


def _expressions(col: str) -> list[tuple[str, str]]:
    qc = _q(col)
    s = f"CAST({qc} AS VARCHAR)"
    n = f"TRY_CAST({qc} AS DOUBLE)"
    return [
        ("timestamp_cast", f"TRY_CAST({qc} AS TIMESTAMP)"),
        ("date_cast", f"CAST(TRY_CAST({qc} AS DATE) AS TIMESTAMP)"),
        ("iso_date", f"CAST(TRY_STRPTIME({s}, '%Y-%m-%d') AS TIMESTAMP)"),
        ("iso_datetime", f"TRY_STRPTIME({s}, '%Y-%m-%d %H:%M:%S')"),
        ("iso_t", f"TRY_STRPTIME({s}, '%Y-%m-%dT%H:%M:%S')"),
        ("dmy", f"CAST(TRY_STRPTIME({s}, '%d/%m/%Y') AS TIMESTAMP)"),
        ("ymd_compact", f"CAST(TRY_STRPTIME({s}, '%Y%m%d') AS TIMESTAMP)"),
        (
            "epoch_seconds",
            f"CASE WHEN {n} BETWEEN 315532800 AND 4102444800 "
            f"THEN CAST(to_timestamp({n}) AS TIMESTAMP) END",
        ),
        (
            "epoch_milliseconds",
            f"CASE WHEN {n} BETWEEN 315532800000 AND 4102444800000 "
            f"THEN epoch_ms(TRY_CAST({qc} AS BIGINT)) END",
        ),
    ]


def robust_fixture_date_expr(con: duckdb.DuckDBPyConnection, fixtures: Path) -> str:
    fixture_path = base.sql_path(fixtures)
    schema = con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{fixture_path}')"
    ).df()
    candidates = _candidate_columns(schema)
    if not candidates:
        raise RuntimeError(
            "No date/time-like columns found in opta_fixtures; cannot create leakage-safe split"
        )

    tested: list[dict[str, object]] = []
    best: tuple[int, int, str, str] | None = None

    for col in candidates:
        for method, expr in _expressions(col):
            try:
                row = con.execute(
                    f"""
                    SELECT
                        COUNT({expr}) AS non_null,
                        COUNT(DISTINCT CAST({expr} AS DATE)) AS distinct_dates
                    FROM read_parquet('{fixture_path}')
                    """
                ).fetchone()
                non_null = int(row[0] or 0)
                distinct_dates = int(row[1] or 0)
            except Exception:
                continue
            tested.append(
                {
                    "column": col,
                    "method": method,
                    "non_null": non_null,
                    "distinct_dates": distinct_dates,
                }
            )
            if distinct_dates >= 20:
                score = (distinct_dates, non_null)
                if best is None or score > (best[0], best[1]):
                    best = (distinct_dates, non_null, col, expr)

    if best is None:
        top = sorted(
            tested,
            key=lambda x: (int(x["distinct_dates"]), int(x["non_null"])),
            reverse=True,
        )[:12]
        raise RuntimeError(
            "Could not recover >=20 valid fixture dates for leakage-safe split. "
            f"Best attempts: {top}"
        )

    distinct_dates, non_null, col, expr = best
    print(
        "PERF-18 TEMPORAL DATE SOURCE: "
        f"column={col} non_null={non_null} distinct_dates={distinct_dates}"
    )
    qualified = expr.replace(_q(col), f'f.{_q(col)}')
    return qualified


# Patch only the date resolver; all model logic remains the audited v1 implementation.
base.fixture_date_expr = robust_fixture_date_expr


if __name__ == "__main__":
    base.main()
