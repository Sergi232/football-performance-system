"""Repair demo match dates from the original Opta fixture source.

FEATURE-02 needs a real chronological key. The source export contains an explicit
`match_date` field whose values use Opta's date-only UTC notation, e.g.
`2025-09-27Z`. Pandas does not parse that representation automatically because
`Z` normally follows a time component, so this script handles that exact source
encoding explicitly and fails rather than inventing chronology.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

from import_demo_fixtures import (
    DEFAULT_COMPETITION,
    DEFAULT_DB,
    DEFAULT_INPUT,
    DEFAULT_SEASON,
    DEFAULT_TEAM_SOURCE_ID,
    FIELD_CANDIDATES,
    SEASON_END,
    SEASON_START,
    normalize_value,
    resolve_column,
    sql_path,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair demo match dates from opta_fixtures")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--team-source-id", default=DEFAULT_TEAM_SOURCE_ID)
    parser.add_argument("--season", default=DEFAULT_SEASON)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION)
    return parser.parse_args()


def to_naive(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    return parsed.dt.tz_convert(None)


def parse_source_match_date(series: pd.Series) -> tuple[pd.Series, str]:
    """Parse the explicit fixture `match_date` using auditable source formats."""
    text = series.astype("string").str.strip()
    attempts: list[tuple[str, pd.Series]] = []

    if pd.api.types.is_datetime64_any_dtype(series):
        attempts.append(("native_datetime", to_naive(series)))

    # Actual PannaData/Opta export observed in this project: 2025-09-27Z.
    attempts.append(
        (
            "YYYY-MM-DDZ",
            pd.to_datetime(text, format="%Y-%m-%dZ", errors="coerce", utc=True).dt.tz_convert(None),
        )
    )

    # Standard date-only representation, in case another export drops the Z.
    attempts.append(
        (
            "YYYY-MM-DD",
            pd.to_datetime(text, format="%Y-%m-%d", errors="coerce", utc=True).dt.tz_convert(None),
        )
    )

    # Standard full UTC timestamps.
    attempts.append(
        (
            "ISO_UTC_SECONDS",
            pd.to_datetime(text, format="%Y-%m-%dT%H:%M:%SZ", errors="coerce", utc=True).dt.tz_convert(None),
        )
    )

    compact = text.str.replace(r"\.0$", "", regex=True)
    for width, fmt, label in (
        (8, "%Y%m%d", "YYYYMMDD"),
        (12, "%Y%m%d%H%M", "YYYYMMDDHHMM"),
        (14, "%Y%m%d%H%M%S", "YYYYMMDDHHMMSS"),
    ):
        mask = compact.str.fullmatch(rf"\d{{{width}}}", na=False)
        parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
        if mask.any():
            parsed.loc[mask] = pd.to_datetime(compact.loc[mask], format=fmt, errors="coerce")
        attempts.append((label, parsed))

    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().any():
        for unit in ("s", "ms", "us", "ns"):
            attempts.append(
                (
                    f"epoch_{unit}",
                    pd.to_datetime(numeric, unit=unit, errors="coerce", utc=True).dt.tz_convert(None),
                )
            )

    scored: list[tuple[int, int, str, pd.Series]] = []
    for label, parsed in attempts:
        in_season = parsed.between(SEASON_START, SEASON_END)
        scored.append((int(in_season.sum()), int(parsed.notna().sum()), label, parsed))

    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    best = scored[0]
    return best[3], best[2]


def main() -> None:
    args = parse_args()
    source = args.input_dir.expanduser().resolve() / "opta_fixtures.parquet"
    db_path = args.db.expanduser().resolve()

    if not source.exists():
        raise FileNotFoundError(f"Missing fixture source: {source}")
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with duckdb.connect() as src:
        fixtures = src.execute(f"SELECT * FROM read_parquet('{sql_path(source)}')").fetchdf()

    cols = list(fixtures.columns)
    match_col = resolve_column(cols, FIELD_CANDIDATES["match_id"])
    date_col = resolve_column(cols, FIELD_CANDIDATES["match_date"])
    home_col = resolve_column(cols, FIELD_CANDIDATES["home_team_id"])
    away_col = resolve_column(cols, FIELD_CANDIDATES["away_team_id"])
    season_col = resolve_column(cols, FIELD_CANDIDATES["season"])
    competition_col = resolve_column(cols, FIELD_CANDIDATES["competition"])

    if not all((match_col, date_col, home_col, away_col)):
        raise RuntimeError(
            "Fixture source is missing required match/date/team fields. "
            f"Available columns: {cols}"
        )

    team = str(args.team_source_id)
    demo = fixtures[
        fixtures[home_col].astype("string").fillna("").eq(team)
        | fixtures[away_col].astype("string").fillna("").eq(team)
    ].copy()

    if season_col and not demo.empty:
        target = normalize_value(args.season)
        normalized = demo[season_col].map(normalize_value)
        tokens = ("202526", "20252026") if target in {"202526", "20252026"} else (target,)
        season_mask = normalized.apply(lambda value: any(token in value for token in tokens))
        if season_mask.any():
            demo = demo.loc[season_mask].copy()

    if competition_col and not demo.empty:
        target = normalize_value(args.competition)
        normalized = demo[competition_col].map(normalize_value)
        aliases = {target, "laliga", "primeradivision", "spanishlaliga"}
        competition_mask = normalized.isin(aliases) | normalized.str.contains("laliga", regex=False)
        if competition_mask.any():
            demo = demo.loc[competition_mask].copy()

    demo = demo.drop_duplicates(subset=[match_col]).copy()
    if len(demo) != 38:
        raise RuntimeError(f"Expected 38 demo fixtures, found {len(demo)}")

    parsed, parser_label = parse_source_match_date(demo[date_col])
    in_season = parsed.between(SEASON_START, SEASON_END)
    if int(in_season.sum()) != 38 or parsed.isna().any():
        sample = demo[date_col].head(8).tolist()
        raise RuntimeError(
            f"Explicit {date_col} could not be parsed safely for all 38 fixtures. "
            f"best_parser={parser_label}; in_season={int(in_season.sum())}/38; sample={sample}"
        )

    demo["__match_date"] = parsed

    with duckdb.connect(str(db_path)) as con:
        source_ids = demo[match_col].astype(str).tolist()
        existing = con.execute(
            """
            SELECT source_match_id, match_date
            FROM matches
            WHERE source_match_id IN (SELECT * FROM UNNEST(?))
            """,
            [source_ids],
        ).fetchdf()
        if len(existing) != 38:
            raise RuntimeError(f"Normalized DB contains {len(existing)}/38 demo matches")

        current = dict(zip(existing["source_match_id"].astype(str), existing["match_date"]))
        repaired = 0
        preserved = 0

        for source_match_id_raw, repaired_date in demo[[match_col, "__match_date"]].itertuples(index=False, name=None):
            source_match_id = str(source_match_id_raw)
            new_value = pd.Timestamp(repaired_date)
            old_value = current.get(source_match_id)

            if old_value is not None and not pd.isna(old_value):
                if pd.Timestamp(old_value) != new_value:
                    raise RuntimeError(
                        f"Existing match_date conflicts with source for {source_match_id}: "
                        f"{old_value} != {new_value}"
                    )
                preserved += 1
                continue

            con.execute(
                "UPDATE matches SET match_date = ? WHERE source_match_id = ?",
                [new_value.to_pydatetime(), source_match_id],
            )
            repaired += 1

        remaining = con.execute(
            """
            SELECT COUNT(*)
            FROM matches
            WHERE source_match_id IN (SELECT * FROM UNNEST(?))
              AND match_date IS NULL
            """,
            [source_ids],
        ).fetchone()[0]
        if remaining:
            raise RuntimeError(f"Match-date repair incomplete: {remaining} rows remain NULL")

    print("DATA MATCH-DATE REPAIR: PASS")
    print(f"source column: {date_col}")
    print(f"source encoding: {parser_label}")
    print("fixtures: 38/38")
    print(f"distinct dates: {parsed.nunique()}")
    print(f"dates repaired: {repaired}")
    print(f"existing matching dates preserved: {preserved}")
    print("No chronology inferred from IDs or row order.")


if __name__ == "__main__":
    main()
