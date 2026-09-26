"""Validate the materialized performance-score contract used by the dashboard."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.performance_score_access import SCORE_VERSION, get_score_status, list_score_teams  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def high_participation_without_score(path: Path) -> list[tuple]:
    """Data-quality audit, not a performance threshold.

    A regularly starting outfield player should not have zero eligible scores merely
    because sparse signed features left dimensions blank. Goalkeepers are excluded.
    """
    with duckdb.connect(str(path), read_only=True) as con:
        return con.execute(
            """
            WITH participation AS (
                SELECT
                    pm.team_id,
                    pm.player_id,
                    p.display_name AS player,
                    COUNT(*) FILTER (WHERE pm.minutes_played > 0) AS appearances,
                    SUM(CASE WHEN pm.started THEN 1 ELSE 0 END) AS starts,
                    SUM(pm.minutes_played) AS minutes,
                    BOOL_OR(
                        pm.primary_role IS NOT NULL
                        AND pm.primary_role <> 'Substitute'
                        AND LOWER(pm.primary_role) NOT LIKE '%goalkeeper%'
                    ) AS has_outfield_role,
                    BOOL_OR(LOWER(COALESCE(pm.primary_role, '')) LIKE '%goalkeeper%') AS has_gk_role
                FROM player_match pm
                JOIN players p ON p.player_id = pm.player_id
                GROUP BY pm.team_id, pm.player_id, p.display_name
            ),
            scored AS (
                SELECT team_id, player_id, COUNT(*) AS scored_matches
                FROM player_match_performance_score
                WHERE score_version = ?
                  AND position_group <> 'OTHER_OUTFIELD'
                  AND performance_score IS NOT NULL
                GROUP BY team_id, player_id
            )
            SELECT
                p.player, p.appearances, p.starts, p.minutes,
                COALESCE(s.scored_matches, 0) AS scored_matches
            FROM participation p
            LEFT JOIN scored s
              ON s.team_id = p.team_id AND s.player_id = p.player_id
            WHERE p.starts >= 10
              AND p.has_outfield_role
              AND NOT p.has_gk_role
              AND COALESCE(s.scored_matches, 0) = 0
            ORDER BY p.starts DESC, p.minutes DESC, p.player
            """,
            [SCORE_VERSION],
        ).fetchall()


def main() -> None:
    path = db_path()
    teams = list_score_teams(path)
    if teams.empty:
        raise RuntimeError(f"No rows found for {SCORE_VERSION}")

    status = get_score_status(path)
    if status["rows"] <= 0:
        raise RuntimeError("Performance-score table is empty")
    if status["observable_rows"] <= 0:
        raise RuntimeError("No observable positional-role rows found")
    if status["eligible_rows"] <= 0:
        raise RuntimeError("No eligible performance scores found")
    if status["eligible_rows"] > status["observable_rows"]:
        raise RuntimeError("Eligible rows cannot exceed observable positional-role rows")

    coverage = status["eligible_rows"] / status["observable_rows"]
    if coverage < 0.8:
        raise RuntimeError(f"PERF-15 regressed below PERF-14 coverage 0.8: {coverage}")
    if status["role_unavailable_rows"] != 172:
        raise RuntimeError(
            f"Role-observability semantics changed unexpectedly: {status['role_unavailable_rows']} != 172"
        )

    missing_regulars = high_participation_without_score(path)
    if missing_regulars:
        text = "; ".join(
            f"{player} ({starts} starts/{apps} apps)"
            for player, apps, starts, _minutes, _scores in missing_regulars
        )
        raise RuntimeError(
            "Regular outfield players still have zero eligible scores after PERF-15: " + text
        )

    print("PERFORMANCE SCORE DASHBOARD CONTRACT: PASS")
    print(f"score_version={SCORE_VERSION}")
    print(f"teams={len(teams)}")
    print(f"rows={status['rows']}")
    print(f"observable_role_rows={status['observable_rows']}")
    print(f"eligible_scores={status['eligible_rows']}")
    print(f"coverage_observable_roles={coverage:.4f}")
    print(f"source_role_unavailable_rows={status['role_unavailable_rows']}")
    print(f"fallback_score_rows={status['fallback_score_rows']}")
    print("high_participation_outfield_players_without_score=0")


if __name__ == "__main__":
    main()
