"""Validate the immediate Match Rating product contract."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.match_rating_access import MATCH_RATING_VERSION, get_match_rating_status  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"


def main() -> None:
    db = Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(f"Database not found: {db}")

    status = get_match_rating_status(db)
    with duckdb.connect(str(db), read_only=True) as con:
        played_rows = con.execute("SELECT COUNT(*) FROM player_match WHERE minutes_played > 0").fetchone()[0]
        missing = con.execute(
            """
            SELECT COUNT(*)
            FROM player_match pm
            LEFT JOIN player_match_rating r
              ON r.match_id=pm.match_id AND r.player_id=pm.player_id
             AND r.match_rating_version=?
            WHERE pm.minutes_played > 0 AND r.player_id IS NULL
            """,
            [MATCH_RATING_VERSION],
        ).fetchone()[0]
        null_ratings = con.execute(
            """
            SELECT COUNT(*)
            FROM player_match_rating
            WHERE match_rating_version=? AND match_rating_10 IS NULL
            """,
            [MATCH_RATING_VERSION],
        ).fetchone()[0]
        first_match_rows = con.execute(
            """
            WITH first_match AS (
                SELECT team_id, MIN(match_date) AS first_date
                FROM player_match_rating
                WHERE match_rating_version=?
                GROUP BY team_id
            )
            SELECT COUNT(*)
            FROM player_match_rating r
            JOIN first_match f ON f.team_id=r.team_id AND f.first_date=r.match_date
            WHERE r.match_rating_version=? AND r.match_rating_10 IS NOT NULL
            """,
            [MATCH_RATING_VERSION, MATCH_RATING_VERSION],
        ).fetchone()[0]

    if status["rows"] != played_rows:
        raise RuntimeError(f"Expected one rating row per played row: ratings={status['rows']} played={played_rows}")
    if status["rated_rows"] != played_rows or null_ratings != 0 or missing != 0:
        raise RuntimeError(
            f"Match Rating coverage must be 100%: rated={status['rated_rows']} played={played_rows} missing={missing} null={null_ratings}"
        )
    if first_match_rows <= 0:
        raise RuntimeError("No ratings found for the first available team match")

    print("MATCH RATING CONTRACT: PASS")
    print(f"match_rating_version={MATCH_RATING_VERSION}")
    print(f"played_rows={played_rows}")
    print(f"rated_rows={status['rated_rows']}")
    print("rating_coverage=1.0000")
    print(f"matches={status['matches']}")
    print(f"goalkeeper_rows={status['goalkeeper_rows']}")
    print(f"generic_role_rows={status['generic_role_rows']}")
    print(f"neutral_insufficient_evidence_rows={status['neutral_rows']}")
    print(f"first_match_rated_rows={first_match_rows}")


if __name__ == "__main__":
    main()
