"""Validate the normalized demo database after each import stage.

The checks are intentionally conservative. Hard failures protect the core demo
contract; later-stage tables (player_match, match_events) are reported as pending
until their importers are added.

Usage:
    python data/validate_demo_database.py
    python data/validate_demo_database.py --db C:/path/to/football_performance.duckdb
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

import duckdb


HERE = Path(__file__).resolve().parent
DEFAULT_DB = HERE / "football_performance.duckdb"
DEFAULT_OUTPUT = HERE / "validation_report.json"
DEFAULT_TEAM_SOURCE_ID = "4dtdjgnpdq9uw4sdutti0vaar"
EXPECTED_MATCHES = 38


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate FPS demo database")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--team-source-id", default=DEFAULT_TEAM_SOURCE_ID)
    parser.add_argument("--expected-matches", type=int, default=EXPECTED_MATCHES)
    return parser.parse_args()


def stable_id(entity: str, source_id: object) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:{entity}:{source_id}"))


def scalar(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None):
    return con.execute(sql, params or []).fetchone()[0]


def check(report: dict, name: str, value, expected=None, severity: str = "hard") -> None:
    ok = bool(value) if expected is None else value == expected
    report["checks"].append(
        {
            "name": name,
            "ok": ok,
            "value": value,
            "expected": expected,
            "severity": severity,
        }
    )


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    demo_team_id = stable_id("team", args.team_source_id)
    report = {
        "database": str(db_path),
        "team_source_id": args.team_source_id,
        "team_id": demo_team_id,
        "checks": [],
    }

    with duckdb.connect(str(db_path), read_only=True) as con:
        team_exists = scalar(
            con,
            "SELECT COUNT(*) FROM teams WHERE team_id = ? AND source_team_id = ?",
            [demo_team_id, args.team_source_id],
        )
        check(report, "demo_team_exists", team_exists, 1)

        match_count = scalar(
            con,
            "SELECT COUNT(*) FROM team_match WHERE team_id = ?",
            [demo_team_id],
        )
        check(report, "demo_match_count", match_count, args.expected_matches)

        distinct_match_count = scalar(
            con,
            "SELECT COUNT(DISTINCT match_id) FROM team_match WHERE team_id = ?",
            [demo_team_id],
        )
        check(
            report,
            "demo_distinct_match_count",
            distinct_match_count,
            args.expected_matches,
        )

        duplicate_source_matches = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM (
                SELECT source_match_id
                FROM matches
                WHERE source_match_id IS NOT NULL
                GROUP BY source_match_id
                HAVING COUNT(*) > 1
            ) d
            """,
        )
        check(report, "duplicate_source_match_ids", duplicate_source_matches, 0)

        malformed_demo_matches = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM matches m
            JOIN team_match tm ON tm.match_id = m.match_id
            WHERE tm.team_id = ?
              AND NOT (m.home_team_id = ? OR m.away_team_id = ?)
            """,
            [demo_team_id, demo_team_id, demo_team_id],
        )
        check(report, "demo_team_present_in_fixture", malformed_demo_matches, 0)

        missing_opponents = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM team_match
            WHERE team_id = ? AND opponent_team_id IS NULL
            """,
            [demo_team_id],
        )
        check(report, "missing_opponents", missing_opponents, 0)

        missing_source_match_ids = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM matches m
            JOIN team_match tm ON tm.match_id = m.match_id
            WHERE tm.team_id = ?
              AND (m.source_match_id IS NULL OR TRIM(m.source_match_id) = '')
            """,
            [demo_team_id],
        )
        check(report, "missing_source_match_ids", missing_source_match_ids, 0)

        player_match_rows = scalar(
            con,
            "SELECT COUNT(*) FROM player_match WHERE team_id = ?",
            [demo_team_id],
        )
        check(
            report,
            "player_match_rows_present",
            player_match_rows > 0,
            True,
            severity="stage",
        )

        event_rows = scalar(
            con,
            "SELECT COUNT(*) FROM match_events WHERE team_id = ?",
            [demo_team_id],
        )
        check(
            report,
            "match_event_rows_present",
            event_rows > 0,
            True,
            severity="stage",
        )

        if player_match_rows > 0:
            matches_with_player_rows = scalar(
                con,
                "SELECT COUNT(DISTINCT match_id) FROM player_match WHERE team_id = ?",
                [demo_team_id],
            )
            check(
                report,
                "player_match_fixture_coverage",
                matches_with_player_rows,
                args.expected_matches,
            )

            invalid_minutes = scalar(
                con,
                """
                SELECT COUNT(*)
                FROM player_match
                WHERE team_id = ?
                  AND (minutes_played < 0 OR minutes_played > 130)
                """,
                [demo_team_id],
            )
            check(report, "invalid_minutes", invalid_minutes, 0)

        if event_rows > 0:
            orphan_events = scalar(
                con,
                """
                SELECT COUNT(*)
                FROM match_events e
                LEFT JOIN matches m ON m.match_id = e.match_id
                WHERE e.team_id = ? AND m.match_id IS NULL
                """,
                [demo_team_id],
            )
            check(report, "orphan_match_events", orphan_events, 0)

            duplicate_source_events = scalar(
                con,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT match_id, source_type, source_event_id
                    FROM match_events
                    WHERE team_id = ? AND source_event_id IS NOT NULL
                    GROUP BY match_id, source_type, source_event_id
                    HAVING COUNT(*) > 1
                ) d
                """,
                [demo_team_id],
            )
            check(report, "duplicate_source_events", duplicate_source_events, 0)

    hard_failures = [
        item for item in report["checks"]
        if item["severity"] == "hard" and not item["ok"]
    ]
    stage_pending = [
        item for item in report["checks"]
        if item["severity"] == "stage" and not item["ok"]
    ]
    report["hard_failure_count"] = len(hard_failures)
    report["stage_pending_count"] = len(stage_pending)
    report["status"] = "PASS" if not hard_failures else "FAIL"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    for item in report["checks"]:
        prefix = "OK" if item["ok"] else ("PENDING" if item["severity"] == "stage" else "FAIL")
        print(
            f"{prefix:7} {item['name']}: value={item['value']!r} "
            f"expected={item['expected']!r}"
        )

    print(f"Validation status: {report['status']}")
    print(f"Report: {output}")
    if hard_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
