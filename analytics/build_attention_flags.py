"""Build auditable attention flags from explicit system/data states only.

No performance threshold, fatigue inference or tactical recommendation is created.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ATTENTION_VERSION = "attention_flags_v0.1-auditable"


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

        # Explicit limitation already carried by the Match Rating layer.
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
                'La font no informa del rol tàctic fiable d’aquesta aparició; no s’ha imputat cap posició.',
                ?
            FROM player_match_rating
            WHERE match_rating_context='GENERIC_ROLE_UNAVAILABLE'
            """,
            [ATTENTION_VERSION],
        )

        # Explicit insufficient-evidence status from the rating engine.
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
                'El Match Rating s’ha mantingut neutral perquè l’evidència disponible és insuficient.',
                ?
            FROM player_match_rating
            WHERE match_rating_status LIKE 'NEUTRAL_%'
            """,
            [ATTENTION_VERSION],
        )

        # GPS QC flags are provider/input quality observations, not performance judgements.
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
                    'Hi ha mostres GPS amb quality_flags; revisar la qualitat de l’import abans d’interpretar el component físic.',
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
    print(f"rows={total}")
    for code, n in counts:
        print(f"{code}={n}")
    print("No performance, fatigue, injury-risk or tactical threshold was created.")


if __name__ == "__main__":
    main()
