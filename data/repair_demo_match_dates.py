"""Repair missing demo match dates from the original fixture parquet.

FEATURE-02 requires a chronological key. This utility never invents chronology:
it reads the original fixture source and only accepts a source representation that
parses all 38 demo fixtures inside the 2025/26 season.
"""
from __future__ import annotations

import argparse
import warnings
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


def _naive(parsed: pd.Series) -> pd.Series:
    """Return timezone-naive datetime64 while preserving the original index."""
    result = pd.Series(pd.NaT, index=parsed.index, dtype="datetime64[ns]")
    good = parsed.notna()
    if not good.any():
        return result
    values = pd.to_datetime(parsed.loc[good], errors="coerce", utc=True)
    result.loc[good] = values.dt.tz_convert(None)
    return result


def _score(parsed: pd.Series) -> tuple[int, int]:
    parsed = _naive(parsed)
    return int(parsed.between(SEASON_START, SEASON_END).sum()), int(parsed.notna().sum())


def parse_candidate(series: pd.Series) -> tuple[pd.Series, str]:
    """Parse a potential date column using explicit, auditable encodings.

    The winning parser is the one that produces the most values in the demo
    season. No representation is accepted later unless it covers all 38 fixtures.
    """
    attempts: list[tuple[str, pd.Series]] = []

    if pd.api.types.is_datetime64_any_dtype(series):
        attempts.append(("native_datetime", pd.to_datetime(series, errors="coerce", utc=True)))

    text = series.astype("string").str.strip()
    compact = text.str.replace(r"\.0$", "", regex=True)

    # Common compact calendar encodings frequently stored as numeric parquet values.
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

    # Text dates, including ISO and common slash-separated forms.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        try:
            mixed = pd.to_datetime(text, errors="coerce", utc=True, format="mixed")
        except (TypeError, ValueError):
            mixed = pd.to_datetime(text, errors="coerce", utc=True)
        attempts.append(("text_mixed", mixed))
        attempts.append(("text_dayfirst", pd.to_datetime(text, errors="coerce", utc=True, dayfirst=True)))

    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().any():
        # Unix-like epochs.
        for unit in ("s", "ms", "us", "ns"):
            attempts.append(
                (
                    f"epoch_{unit}",
                    pd.to_datetime(numeric, unit=unit, errors="coerce", utc=True),
                )
            )

        # Excel serial dates are explicit day counts from 1899-12-30.
        excel_mask = numeric.between(30000, 60000)
        excel = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
        if excel_mask.any():
            excel.loc[excel_mask] = pd.to_datetime(
                numeric.loc[excel_mask], unit="D", origin="1899-12-30", errors="coerce"
            )
        attempts.append(("excel_serial", excel))

    ranked: list[tuple[int, int, str, pd.Series]] = []
    for label, parsed in attempts:
        naive = _naive(parsed)
        in_season, non_null = _score(naive)
        ranked.append((in_season, non_null, label, naive))

    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best = ranked[0] if ranked else (0, 0, "none", pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]"))
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

    # First inspect the explicitly mapped date field. Other columns are only a
    # fallback and must independently cover all 38 fixtures.
    candidate_rows: list[tuple[str, pd.Series, int, int, int, str]] = []
    ordered_cols: list[str] = []
    if explicit_date_col:
        ordered_cols.append(explicit_date_col)
    ordered_cols.extend(
        c for c in cols
        if c not in ordered_cols
        and c not in {match_col, home_col, away_col}
        and any(k in c.lower() for k in ("date", "time", "kick", "start", "utc"))
    )

    for col in ordered_cols:
        parsed, parser_label = parse_candidate(demo[col])
        in_season = parsed.between(SEASON_START, SEASON_END)
        plausible = int(in_season.sum())
        non_null = int(parsed.notna().sum())
        distinct = int(parsed[in_season].nunique())
        candidate_rows.append((col, parsed, plausible, non_null, distinct, parser_label))

    chosen = None
    if explicit_date_col:
        for item in candidate_rows:
            if item[0] == explicit_date_col and item[2] == 38:
                chosen = item
                break

    if chosen is None:
        full = [x for x in candidate_rows if x[2] == 38]
        if not full:
            diag = ", ".join(
                f"{c}: parser={label} in_season={p}/38 non_null={n} distinct={d}"
                for c, _, p, n, d, label in sorted(candidate_rows, key=lambda x: -x[2])[:10]
            )
            explicit_diag = ""
            if explicit_date_col:
                sample = demo[explicit_date_col].head(8).tolist()
                explicit_diag = (
                    f" Explicit {explicit_date_col}: dtype={demo[explicit_date_col].dtype}; "
                    f"sample={sample}."
                )
            raise RuntimeError(
                "No source column safely provides 38 in-season match dates. "
                f"Date-like diagnostics: {diag or '<none>'}.{explicit_diag}"
            )

        signatures: dict[tuple, list[tuple[str, pd.Series, int, int, int, str]]] = {}
        for item in full:
            signature = tuple(item[1].astype("string").fillna("<NULL>").tolist())
            signatures.setdefault(signature, []).append(item)
        if len(signatures) > 1:
            diag = ", ".join(f"{c}(parser={label}, distinct={d})" for c, _, _, _, d, label in full)
            raise RuntimeError(
                "Multiple different source date columns cover all 38 fixtures; refusing to guess. "
                f"Candidates: {diag}"
            )
        group = next(iter(signatures.values()))
        chosen = sorted(group, key=lambda x: x[0].lower())[0]

    chosen_col, parsed, plausible, _, distinct, parser_label = chosen
    if plausible != 38:
        raise RuntimeError("Internal date-selection error")

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
        for source_match_id_raw, repaired_date in demo[[match_col, "__repaired_match_date"]].itertuples(index=False, name=None):
            source_match_id = str(source_match_id_raw)
            value = pd.Timestamp(repaired_date).to_pydatetime()
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
    print(f"source encoding: {parser_label}")
    print("fixtures: 38/38")
    print(f"distinct parsed timestamps: {distinct}")
    print(f"dates repaired: {repaired}")
    print(f"existing matching dates preserved: {preserved}")
    print("No chronology was inferred from match IDs, row order or future data.")


if __name__ == "__main__":
    main()
