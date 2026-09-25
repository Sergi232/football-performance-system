"""Build a local anonymized DuckDB demo for the public product.

This script never modifies the source database and never uploads generated data.
The output is a presentation/demo database for the Streamlit app, not a substitute
for the licensed/raw development sources.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "football_performance.duckdb"
DEFAULT_OUTPUT = ROOT / "publication" / "output" / "football_performance_public_demo.duckdb"

PUBLIC_TABLES = (
    "teams",
    "players",
    "matches",
    "team_match",
    "player_match",
    "player_match_raw_stats",
    "player_match_features",
    "decision_results",
)


def alias_map(values: list[str], prefix: str) -> dict[str, str]:
    clean = sorted({str(v) for v in values if v is not None})
    width = max(3, len(str(len(clean))))
    return {value: f"{prefix}_{idx:0{width}d}" for idx, value in enumerate(clean, start=1)}


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def case_map(column: str, mapping: dict[str, str]) -> str:
    parts = [f"WHEN {sql_literal(src)} THEN {sql_literal(dst)}" for src, dst in mapping.items()]
    return f"CASE CAST({column} AS VARCHAR) {' '.join(parts)} ELSE CAST({column} AS VARCHAR) END"


def available_tables(con: duckdb.DuckDBPyConnection, schema: str = "main") -> set[str]:
    rows = con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = ? AND table_type = 'BASE TABLE'
        """,
        [schema],
    ).fetchall()
    return {row[0] for row in rows}


def table_columns(con: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    return [row[1] for row in con.execute(f"PRAGMA table_info('{table}')").fetchall()]


def build_mappings(con: duckdb.DuckDBPyConnection) -> tuple[dict[str, str], dict[str, str], dict[str, str], str | None]:
    team_rows = con.execute("SELECT team_id FROM teams ORDER BY team_id").fetchall()
    team_ids = [str(r[0]) for r in team_rows]

    main_team = None
    if "player_match" in available_tables(con):
        row = con.execute(
            """
            SELECT team_id, COUNT(*) AS n
            FROM player_match
            GROUP BY team_id
            ORDER BY n DESC, team_id
            LIMIT 1
            """
        ).fetchone()
        if row:
            main_team = str(row[0])

    team_map: dict[str, str] = {}
    if main_team is not None:
        team_map[main_team] = "TEAM_001"
    opponents = [value for value in sorted(team_ids) if value != main_team]
    for idx, value in enumerate(opponents, start=1):
        team_map[value] = f"OPP_{idx:03d}"

    player_rows = con.execute("SELECT player_id FROM players ORDER BY player_id").fetchall()
    player_map = alias_map([str(r[0]) for r in player_rows], "PLAYER")

    match_rows = con.execute(
        "SELECT match_id FROM matches ORDER BY match_date NULLS LAST, match_id"
    ).fetchall()
    match_map = alias_map([str(r[0]) for r in match_rows], "MATCH")
    return team_map, player_map, match_map, main_team


def transformed_select(
    con: duckdb.DuckDBPyConnection,
    table: str,
    team_map: dict[str, str],
    player_map: dict[str, str],
    match_map: dict[str, str],
    main_team: str | None,
) -> str:
    columns = table_columns(con, table)
    expressions: list[str] = []

    for col in columns:
        quoted = f'"{col}"'
        if col in {"team_id", "opponent_team_id", "home_team_id", "away_team_id"}:
            expressions.append(f"{case_map(quoted, team_map)} AS {quoted}")
        elif col in {"player_id", "penalty_taker_player_id"}:
            expressions.append(f"{case_map(quoted, player_map)} AS {quoted}")
        elif col == "match_id":
            expressions.append(f"{case_map(quoted, match_map)} AS {quoted}")
        elif table == "teams" and col == "display_name":
            team_id_expr = case_map('"team_id"', team_map)
            expressions.append(
                f"CASE WHEN {team_id_expr} = 'TEAM_001' THEN 'TEAM 001' "
                f"ELSE replace({team_id_expr}, '_', ' ') END AS {quoted}"
            )
        elif table == "players" and col == "display_name":
            player_id_expr = case_map('"player_id"', player_map)
            expressions.append(f"replace({player_id_expr}, '_', ' ') AS {quoted}")
        elif table == "decision_results" and col == "decision_id":
            expressions.append(
                "'DECISION_' || lpad(CAST(row_number() OVER (ORDER BY match_id, player_id, node_id, decision_id) AS VARCHAR), 9, '0') "
                f"AS {quoted}"
            )
        else:
            expressions.append(quoted)

    return "SELECT\n  " + ",\n  ".join(expressions) + f'\nFROM src.main."{table}"'


def build_public_demo(source: Path, output: Path) -> dict[str, int]:
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Source database not found: {source}")
    if source == output:
        raise ValueError("Output must be different from the source database")

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    with duckdb.connect(str(source), read_only=True) as src:
        source_tables = available_tables(src)
        missing = [name for name in PUBLIC_TABLES if name not in source_tables]
        if missing:
            raise RuntimeError(f"Required public-demo tables missing: {missing}")
        team_map, player_map, match_map, main_team = build_mappings(src)

    with duckdb.connect(str(output)) as dst:
        dst.execute(f"ATTACH {sql_literal(str(source))} AS src (READ_ONLY)")
        for table in PUBLIC_TABLES:
            query = transformed_select(dst, table, team_map, player_map, match_map, main_team)
            dst.execute(f'CREATE TABLE "{table}" AS {query}')
        dst.execute(
            """
            CREATE TABLE public_demo_metadata AS
            SELECT
                'public_demo_0.1.0'::VARCHAR AS demo_version,
                'ANONYMIZED_LOCAL_EXPORT'::VARCHAR AS data_status,
                'Not cleared for redistribution unless source-data licence permits it.'::VARCHAR AS redistribution_note
            """
        )
        counts = {
            table: dst.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in PUBLIC_TABLES
        }
        dst.execute("DETACH src")

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Build local anonymized FPS demo database")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    counts = build_public_demo(args.source, args.output)
    print("PUBLICATION-01 BUILD: PASS")
    print(f"source: {args.source.expanduser().resolve()}")
    print(f"output: {args.output.expanduser().resolve()}")
    for table, count in counts.items():
        print(f"{table}: {count}")
    print("Generated database remains local and must not be published until redistribution rights are confirmed.")


if __name__ == "__main__":
    main()
