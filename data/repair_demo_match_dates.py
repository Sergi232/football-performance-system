"""Repair missing demo match dates from the original fixture parquet.

This utility exists because FEATURE-02 requires a chronological key and the
current normalized demo DB contains NULL `matches.match_date` values.

The script does not invent chronology. It reads the original fixture source,
filters the same 38 demo fixtures, and searches for a source column that can be
parsed unambiguously as dates inside the 2025/26 season. If no unique safe
candidate exists, it fails and prints diagnostics instead of guessing.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

from import_demo_fixtures import (
    DEFAULT_DB,
    DEFAULT_INPUT,
    DEFAULT_TEAM_SOURCE_ID,
    DEFAULT_SEASON,
    DEFAULT_COMPETITION,
    FIELD_CANDIDATES,
    SEASON_START,
    SEASON_END,
    normalize_value,
    resolve_column,
    sql_path,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Repair demo match dates from opta_fixtures")
    p.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--team-source-id", default=DEFAULT_TEAM_SOURCE_ID)
    p.add_argument("--season", default=DEFAULT_SEASON)
    p.add_argument("--competition", default=DEFAULT_COMPETITION)
    return p.parse_args()


def parse_candidate(series: pd.Series) -> pd.Series:
    # Strings / native date-like values.
    if not pd.api.types.is_numeric_dtype(series):
        parsed = pd.to_datetime(series, errors="coerce", utc=True)
        return parsed.dt.tz_convert(None)

    # Numeric epochs: select the unit that produces the most values in-season.
    numeric = pd.to_numeric(series, errors="coerce")
    best = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    best_count = -1
    for unit in ("s", "ms", "us", "ns"):
        parsed = pd.to_datetime(numeric, unit=unit, errors="coerce", utc=True).dt.tz_convert(None)
        count = int(parsed.between(SEASON_START, SEASON_END).sum())
        if count > best_count:
            best = parsed
            best_count = count
    return best


def main() -> None:
    args = parse_args()
    source = args.input_dir.expanduser().resolve() / "opta_fixtures.parquet"
    db_path = args.db.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Missing fixture source: {source}")
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with duckdb.connect() as src:
        frame = src.execute(f"SELECT * FROM read_parquet('{sql_path(source)}')").fetchdf()

    cols = list(frame.columns)
    match_col = resolve_column(cols, FIELD_CANDIDATES["match_id"])
    home_col = resolve_column(cols, FIELD_CANDIDATES["home_team_id"])
    away_col = resolve_column(cols, FIELD_CANDIDATES["away_team_id"])
    season_col = resolve_column(cols, FIELD_CANDIDATES["season"])
    competition_col = resolve_column(cols, FIELD_CANDIDATES["competition"])
    explicit_date_col = resolve_column(cols, FIELD_CANDIDATES["match_date"])
    if not match_col or not home_col or not away_col:
        raise RuntimeError(f"Could not resolve fixture ids. Available columns: {cols}")

    team = str(args.team_source_id)
    demo = frame[
        frame[home_col].astype("string").fillna("").eq(team)
        | frame[away_col].astype("string").fillna("").eq(team)
    ].copy()

    if season_col and not demo.empty:
        target = normalize_value(args.season)
        norm = demo[season_col].map(normalize_value)
        tokens = ("202526", "20252026") if target in {"202526", "20252026"} else (target,)
        mask = norm.apply(lambda x: any(t in x for t in tokens))
        if mask.any():
            demo = demo[mask].copy()

    if competition_col and not demo.empty:
        target_comp = normalize_value(args.competition)
        norm = demo[competition_col].map(normalize_value)
        aliases = {target_comp, "laliga", "primeradivision", "spanishlaliga"}
        mask = norm.isin(aliases) | norm.str.contains("laliga", regex=False)
        if mask.any():
            demo = demo[mask].copy()

    demo = demo.drop_duplicates(subset=[match_col]).copy()
    if len(demo) != 38:
        raise RuntimeError(f"Expected 38 demo fixtures before date repair, found {len(demo)}")

    skip = {match_col, home_col, away_col}
    candidate_rows: list[tuple[str, pd.Series, int, int, int]] = []
    for col in cols:
        if col in skip:
            continue
        parsed = parse_candidate(demo[col])
        in_season = parsed.between(SEASON_START, SEASON_END)
        plausible = int(in_season.sum())
        if plausible == 0:
            continue
        non_null = int(parsed.notna().sum())
        distinct = int(parsed[in_season].nunique())
        candidate_rows.append((col, parsed, plausible, non_null, distinct))

    # Exact mapped field wins only if it safely covers all 38 fixtures.
    chosen = None
    if explicit_date_col:
        for item in candidate_rows:
            if item[0] == explicit_date_col and item[2] == 38:
                chosen = item
                break

    if chosen is None:
        full = [x for x in candidate_rows if x[2] == 38]
        if not full:
            diag = ", ".join(f"{c}: in_season={p}/38 distinct={d}" for c, _, p, _, d in sorted(candidate_rows, key=lambda x: -x[2])[:10])
            raise RuntimeError(
                "No source column safely provides 38 in-season match dates. "
                f"Available columns={cols}. Date-like diagnostics: {diag or '<none>'}"
            )

        # Several columns are acceptable only if they encode exactly the same chronology.
        signatures: dict[tuple, list[tuple[str, pd.Series, int, int, int]]] = {}
        for item in full:
            signature = tuple(item[1].astype("string").fillna("<NULL>").tolist())
            signatures.setdefault(signature, []).append(item)
        if len(signatures) > 1:
            diag = ", ".join(f"{c}(distinct={d})" for c, _, _, _, d in full)
            raise RuntimeError(
                "Multiple different source date columns cover all 38 fixtures; refusing to guess. "
                f"Candidates: {diag}"
            )
        group = next(iter(signatures.values()))
        # Prefer names that explicitly suggest kickoff/date/time when equivalent.
        def name_rank(item):
            name = item[0].lower()
            return (0 if any(k in name for k in ("kick", "match", "date", "start", "time", "utc")) else 1, name)
        chosen = sorted(group, key=name_rank)[0]

    chosen_col, parsed, plausible, _, distinct = chosen
    if plausible != 38:
        raise RuntimeError("Internal date-selection error")

    demo = demo.copy()
    demo["__repaired_match_date"] = parsed
    if demo["__repaired_match_date"].isna().any():
        raise RuntimeError("Chosen source date column still contains NULL parsed values")

    with duckdb.connect(str(db_path)) as con:
        existing = con.execute(
            """
            SELECT source_match_id, match_date
            FROM matches
            WHERE source_match_id IN (SELECT * FROM UNNEST(?))
            """,
            [demo[match_col].astype(str).tolist()],
        ).fetchdf()
        if len(existing) != 38:
            raise RuntimeError(f"Normalized DB contains {len(existing)}/38 demo matches")

        current = dict(zip(existing["source_match_id"].astype(str), existing["match_date"]))
        repaired = 0
        preserved = 0
        for row in demo[[match_col, "__repaired_match_date"]].itertuples(index=False, name=None):
            source_match_id = str(row[0])
            value = pd.Timestamp(row[1]).to_pydatetime()
            old = current.get(source_match_id)
            if old is not None and not pd.isna(old):
                old_ts = pd.Timestamp(old)
                if old_ts != pd.Timestamp(value):
                    raise RuntimeError(
                        f"Existing match_date conflicts with source for {source_match_id}: {old_ts} != {value}"
                    )
                preserved += 1
                continue
            con.execute(
                "UPDATE matches SET match_date = ? WHERE source_match_id = ?",
                [value, source_match_id],
            )
            repaired += 1

        remaining = con.execute(
            """
            SELECT COUNT(*)
            FROM matches
            WHERE source_match_id IN (SELECT * FROM UNNEST(?))
              AND match_date IS NULL
            """,
            [demo[match_col].astype(str).tolist()],
        ).fetchone()[0]
        if remaining:
            raise RuntimeError(f"Match-date repair incomplete: {remaining} demo matches remain NULL")

    print("DATA MATCH-DATE REPAIR: PASS")
    print(f"source column: {chosen_col}")
    print(f"fixtures: 38/38")
    print(f"distinct parsed timestamps: {distinct}")
    print(f"dates repaired: {repaired}")
    print(f"existing matching dates preserved: {preserved}")
    print("No chronology was inferred from match IDs, row order or future data.")


if __name__ == "__main__":
    main()
