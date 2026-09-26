"""Read-only access to auditable attention flags."""
from __future__ import annotations

from pathlib import Path
import duckdb
import pandas as pd

ATTENTION_VERSION = "attention_flags_v0.2-auditable"


def _connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(Path(db_path).expanduser().resolve()), read_only=True)


def get_team_attention_flags(db_path: Path, team_id: str) -> pd.DataFrame:
    with _connect(db_path) as con:
        return con.execute(
            """
            SELECT
                a.attention_group,
                a.attention_code,
                a.message,
                a.match_id,
                m.match_date,
                a.player_id,
                p.display_name AS player,
                a.source_layer
            FROM attention_flags a
            LEFT JOIN matches m ON m.match_id=a.match_id
            LEFT JOIN players p ON p.player_id=a.player_id
            WHERE a.attention_version=? AND a.team_id=?
            ORDER BY m.match_date DESC NULLS LAST, p.display_name, a.attention_code
            """,
            [ATTENTION_VERSION, team_id],
        ).df()


def get_attention_summary(db_path: Path, team_id: str) -> pd.DataFrame:
    with _connect(db_path) as con:
        return con.execute(
            """
            SELECT attention_group, attention_code, COUNT(*) AS rows
            FROM attention_flags
            WHERE attention_version=? AND team_id=?
            GROUP BY attention_group, attention_code
            ORDER BY attention_group, attention_code
            """,
            [ATTENTION_VERSION, team_id],
        ).df()
