"""Build auditable attention flags from explicit system/data states only.

No performance threshold, fatigue inference or tactical recommendation is created.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

MATCH_RATING_VERSION = "match_rating_v0.5-candidate"
ATTENTION_VERSION = "attention_flags_v0.3-auditable"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build auditable attention flags")
    parser.add_argument("--db", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)

    with duckdb.connect(str(db)) as con:
        con.execute("DROP TABLE IF EXISTS attention_flags")
        con.execute(
            """
            CREATE TABLE attention_flags (
                team_id VARCHAR,
                match_id VARCHAR,
                player_id VARCHAR,
                attention_code VARCHAR NOT NULL,
                attention_group VARCHAR NOT NULL,
                source_layer VARCHAR NOT NULL,
                message VARCHAR NOT NULL,
                attention_version VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        con.execute(
            """
            INSERT INTO attention_flags
            (team_id, match_id, player_id, attention_code, attention_group, source_layer, message, attention_version)
            SELECT
                team_id,
                match_id,
                player_id,
                'ROLE_CONTEXT_UNAVAILABLE',
                'CONTEXT_LIMITATION',
                'player_match_rating',
                'La fuente no informa de un rol táctico fiable en esta aparición; Match Rating V5 conserva un modelo de respaldo sin imputar ninguna posición.',
                ?
            FROM player_match_rating
            WHERE match_rating_version=?
              AND match_rating_context='ROLE_UNAVAILABLE_V2_FALLBACK'
            """,
            [ATTENTION_VERSION, MATCH_RATING_VERSION],
        )

        con.execute(
            """
            INSERT INTO attention_flags
            (team_id, match_id, player_id, attention_code, attention_group, source_layer, message, attention_version)
            SELECT
                team_id,
                match_id,
                player_id,
                'INSUFFICIENT_RATING_EVIDENCE',
                'EVIDENCE_LIMITATION',
                'player_match_rating',
                'El Match Rating se mantiene neutral porque la evidencia disponible es insuficiente.',
                ?
            FROM player_match_rating
            WHERE match_rating_version=?
              AND match_rating_status LIKE '%NEUTRAL_%'
            """,
            [ATTENTION_VERSION, MATCH_RATING_VERSION],
        )

        gps_tables = {
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
        }
        if 'gps_observations' in gps_tables:
            con.execute(
                """
                INSERT INTO attention_flags
                (team_id, match_id, player_id, attention_code, attention_group, source_layer, message, attention_version)
                SELECT
                    pm.team_id,
                    g.match_id,
                    g.player_id,
                    'GPS_QUALITY_FLAGS_PRESENT',
                    'DATA_QUALITY',
                    'gps_observations',
                    'Hay muestras GPS con indicadores de calidad; conviene revisar la importación antes de interpretar el componente físico.',
                    ?
                FROM gps_observations g
                LEFT JOIN player_match pm
                  ON pm.match_id=g.match_id AND pm.player_id=g.player_id
                WHERE g.quality_flags IS NOT NULL
                  AND lower(trim(CAST(g.quality_flags AS VARCHAR))) NOT IN ('', 'null', '[]', '{}')
                GROUP BY pm.team_id, g.match_id, g.player_id
                """,
                [ATTENTION_VERSION],
            )

        counts = con.execute(
            """
            SELECT attention_code, COUNT(*)
            FROM attention_flags
            GROUP BY attention_code
            ORDER BY attention_code
            """
        ).fetchall()
        total = con.execute("SELECT COUNT(*) FROM attention_flags").fetchone()[0]

    print("ATTENTION FLAGS MATERIALIZATION: COMPLETE")
    print(f"attention_version={ATTENTION_VERSION}")
    print(f"match_rating_version={MATCH_RATING_VERSION}")
    print(f"rows={total}")
    for code, n in counts:
        print(f"{code}={n}")
    print("No performance, fatigue, injury-risk or tactical threshold was created.")


if __name__ == "__main__":
    main()
