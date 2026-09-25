"""Build and validate the local anonymized public-demo database."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import get_engine_status, get_team_overview, list_teams  # noqa: E402
from publication.build_public_demo import (  # noqa: E402
    DEFAULT_OUTPUT,
    DEFAULT_SOURCE,
    PUBLIC_TABLES,
    build_public_demo,
)


def source_sensitive_values(source: Path) -> tuple[set[str], set[str]]:
    with duckdb.connect(str(source), read_only=True) as con:
        ids: set[str] = set()
        names: set[str] = set()
        for table, id_col in (("teams", "team_id"), ("players", "player_id"), ("matches", "match_id")):
            ids.update(str(row[0]) for row in con.execute(f'SELECT "{id_col}" FROM "{table}" WHERE "{id_col}" IS NOT NULL').fetchall())
        names.update(str(row[0]) for row in con.execute("SELECT display_name FROM teams WHERE display_name IS NOT NULL").fetchall())
        names.update(str(row[0]) for row in con.execute("SELECT source_name FROM teams WHERE source_name IS NOT NULL").fetchall())
        names.update(str(row[0]) for row in con.execute("SELECT display_name FROM players WHERE display_name IS NOT NULL").fetchall())
        names.update(str(row[0]) for row in con.execute("SELECT source_name FROM players WHERE source_name IS NOT NULL").fetchall())
        ids.update(str(row[0]) for row in con.execute("SELECT source_team_id FROM teams WHERE source_team_id IS NOT NULL").fetchall())
        ids.update(str(row[0]) for row in con.execute("SELECT source_player_id FROM players WHERE source_player_id IS NOT NULL").fetchall())
        ids.update(str(row[0]) for row in con.execute("SELECT source_match_id FROM matches WHERE source_match_id IS NOT NULL").fetchall())
    return ids, names


def public_text_columns(con: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    rows = con.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'main' AND table_name = ?
        ORDER BY ordinal_position
        """,
        [table],
    ).fetchall()
    return [name for name, dtype in rows if "CHAR" in dtype.upper() or "VARCHAR" in dtype.upper()]


def assert_no_sensitive_strings(output: Path, ids: set[str], names: set[str]) -> int:
    # Long IDs catch embedded provenance without creating false matches on ordinary numbers.
    tokens = {token for token in ids if len(token) >= 8}
    tokens.update(token for token in names if len(token) >= 4)
    if not tokens:
        return 0
    pattern = "(?:" + "|".join(sorted((re.escape(token) for token in tokens), key=len, reverse=True)) + ")"

    checked = 0
    with duckdb.connect(str(output), read_only=True) as con:
        for table in PUBLIC_TABLES:
            for column in public_text_columns(con, table):
                quoted = '"' + column.replace('"', '""') + '"'
                count = con.execute(
                    f'SELECT COUNT(*) FROM "{table}" WHERE {quoted} IS NOT NULL AND regexp_matches(CAST({quoted} AS VARCHAR), ?)',
                    [pattern],
                ).fetchone()[0]
                checked += 1
                if count:
                    raise AssertionError(f"Sensitive source token remains in {table}.{column}: {count} rows")
    return checked


def assert_source_provenance_neutralized(output: Path) -> None:
    with duckdb.connect(str(output), read_only=True) as con:
        checks = [
            ("teams", "source_team_id"),
            ("players", "source_player_id"),
            ("matches", "source_match_id"),
        ]
        for table, column in checks:
            count = con.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NOT NULL'
            ).fetchone()[0]
            if count:
                raise AssertionError(f"Source provenance ID remains in {table}.{column}: {count} rows")

        team_flag = con.execute("SELECT COUNT(*) FROM teams WHERE is_anonymized IS DISTINCT FROM TRUE").fetchone()[0]
        player_flag = con.execute("SELECT COUNT(*) FROM players WHERE is_anonymized IS DISTINCT FROM TRUE").fetchone()[0]
        if team_flag or player_flag:
            raise AssertionError("is_anonymized flag is not TRUE for every public team/player row")


def validate(source: Path, output: Path) -> None:
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Source database not found: {source}")

    with duckdb.connect(str(source), read_only=True) as con:
        source_counts = {
            table: con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in PUBLIC_TABLES
        }

    output_counts = build_public_demo(source, output)
    if output_counts != source_counts:
        raise AssertionError(f"Row-count mismatch: source={source_counts}, output={output_counts}")

    ids, names = source_sensitive_values(source)
    columns_checked = assert_no_sensitive_strings(output, ids, names)
    assert_source_provenance_neutralized(output)

    with duckdb.connect(str(output), read_only=True) as con:
        team_ids = [row[0] for row in con.execute("SELECT team_id FROM teams ORDER BY team_id").fetchall()]
        player_ids = [row[0] for row in con.execute("SELECT player_id FROM players ORDER BY player_id").fetchall()]
        match_ids = [row[0] for row in con.execute("SELECT match_id FROM matches ORDER BY match_id").fetchall()]
        player_names = [row[0] for row in con.execute("SELECT display_name FROM players ORDER BY display_name").fetchall()]
        team_names = [row[0] for row in con.execute("SELECT display_name FROM teams ORDER BY display_name").fetchall()]
        metadata = con.execute("SELECT demo_version, data_status, redistribution_note FROM public_demo_metadata").fetchone()

    if "TEAM_001" not in team_ids:
        raise AssertionError("TEAM_001 missing")
    if not all(re.fullmatch(r"(?:TEAM|OPP)_\d{3,}", value) for value in team_ids):
        raise AssertionError("Unexpected public team identifier")
    if not all(re.fullmatch(r"PLAYER_\d{3,}", value) for value in player_ids):
        raise AssertionError("Unexpected public player identifier")
    if not all(re.fullmatch(r"MATCH_\d{3,}", value) for value in match_ids):
        raise AssertionError("Unexpected public match identifier")
    if not all(re.fullmatch(r"PLAYER \d{3,}", value) for value in player_names):
        raise AssertionError("Unexpected public player display name")
    if "TEAM 001" not in team_names or not all(re.fullmatch(r"(?:TEAM|OPP) \d{3,}", value) for value in team_names):
        raise AssertionError("Unexpected public team display name")

    teams = list_teams(output)
    if len(teams) != 1 or teams.iloc[0]["team_id"] != "TEAM_001":
        raise AssertionError("Dashboard team selection contract failed")
    overview = get_team_overview(output, "TEAM_001")
    engine = get_engine_status(output)
    if engine["unsafe_final_states"] != 0:
        raise AssertionError("Public demo contains unsafe final recommendation states")

    print("PUBLICATION-01 ANONYMIZED DEMO CONTRACT: PASS")
    print(f"output: {output}")
    print(f"team: {teams.iloc[0]['display_name']}")
    print(f"matches: {overview['matches']}")
    print(f"players: {overview['players']}")
    print(f"decision rows: {engine['engine_rows']}")
    print(f"N13000 rows: {engine['n13000_rows']}")
    print(f"sensitive text columns checked: {columns_checked}")
    print("source/output row-count identity: PASS")
    print("source identifiers/names absent from public tables: PASS")
    print("source provenance IDs neutralized: PASS")
    print("is_anonymized flags: PASS")
    print("recommendation gate safety: PASS")
    print(f"metadata: {metadata[0]} / {metadata[1]}")
    print("REDISTRIBUTION STATUS: NOT CLEARED — keep this generated DB local unless the source-data licence explicitly permits redistribution.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and validate local anonymized public demo")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    validate(args.source, args.output)


if __name__ == "__main__":
    main()
