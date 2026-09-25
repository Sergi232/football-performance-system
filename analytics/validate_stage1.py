"""Validate ANALYTICS-01 strict-past self/peer evidence contract."""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
BUILD_SCRIPT = Path(__file__).with_name("build_stage1.py")
ANALYTICS_VERSION = "analytics_0.1.0"
BASE_VERSION = "0.1.0"
ROLE_VERSION = "0.3.0"
ALLOWED_STATES = {
    "ROLE_UNKNOWN",
    "CURRENT_VALUE_MISSING",
    "NO_PRIOR_EVIDENCE",
    "EVIDENCE_AVAILABLE",
}
ALLOWED_DIRECTIONS = {None, "ABOVE_MEAN", "BELOW_MEAN", "EQUAL_MEAN"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ANALYTICS-01")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    return parser.parse_args()


def close_enough(left: float | None, right: float | None, tol: float = 1e-10) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return math.isclose(float(left), float(right), rel_tol=tol, abs_tol=tol)


def rebuild(db_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(BUILD_SCRIPT), "--db", str(db_path)],
        check=True,
    )


def validate_peer_samples(con: duckdb.DuckDBPyConnection, limit: int = 30) -> int:
    samples = con.execute(
        """
        SELECT a.match_id, a.team_id, a.player_id, a.primary_role,
               a.feature_name, a.baseline_players_n, a.baseline_observations_n,
               a.baseline_mean, a.baseline_median, a.baseline_std, m.match_date
        FROM analytics_evidence a
        JOIN matches m ON m.match_id = a.match_id
        WHERE a.analytics_version = ?
          AND a.comparison_scope = 'PEER_ROLE_PRIOR'
          AND a.evidence_state = 'EVIDENCE_AVAILABLE'
        ORDER BY a.match_id, a.player_id, a.feature_name
        LIMIT ?
        """,
        [ANALYTICS_VERSION, limit],
    ).fetchall()

    for sample in samples:
        (
            match_id,
            team_id,
            player_id,
            role,
            feature_name,
            expected_players,
            expected_obs,
            expected_mean,
            expected_median,
            expected_std,
            match_date,
        ) = sample
        observed = con.execute(
            """
            WITH peer_prior AS (
                SELECT f.player_id,
                       AVG(f.feature_value) AS peer_mean,
                       COUNT(*) AS obs_n
                FROM player_match_features f
                JOIN player_match pm
                  ON pm.match_id = f.match_id AND pm.player_id = f.player_id
                JOIN matches m ON m.match_id = f.match_id
                WHERE f.feature_version = ?
                  AND pm.team_id = ?
                  AND TRIM(pm.primary_role) = ?
                  AND f.feature_name = ?
                  AND m.match_date < ?
                  AND f.player_id <> ?
                  AND f.feature_value IS NOT NULL
                GROUP BY f.player_id
            )
            SELECT COUNT(*) AS players_n,
                   COALESCE(SUM(obs_n), 0) AS observations_n,
                   AVG(peer_mean) AS peer_mean,
                   MEDIAN(peer_mean) AS peer_median,
                   STDDEV_POP(peer_mean) AS peer_std
            FROM peer_prior
            """,
            [BASE_VERSION, team_id, role, feature_name, match_date, player_id],
        ).fetchone()
        players_n, observations_n, mean_value, median_value, std_value = observed
        if int(players_n) != int(expected_players):
            raise AssertionError(f"Peer player count mismatch for {match_id}/{player_id}/{feature_name}")
        if int(observations_n) != int(expected_obs):
            raise AssertionError(f"Peer observation count mismatch for {match_id}/{player_id}/{feature_name}")
        if not close_enough(mean_value, expected_mean):
            raise AssertionError(f"Peer mean mismatch for {match_id}/{player_id}/{feature_name}")
        if not close_enough(median_value, expected_median):
            raise AssertionError(f"Peer median mismatch for {match_id}/{player_id}/{feature_name}")
        if not close_enough(std_value, expected_std):
            raise AssertionError(f"Peer std mismatch for {match_id}/{player_id}/{feature_name}")
    return len(samples)


def validate(db_path: Path) -> None:
    rebuild(db_path)

    with duckdb.connect(str(db_path), read_only=True) as con:
        base_rows = con.execute(
            "SELECT COUNT(*) FROM player_match_features WHERE feature_version = ?",
            [BASE_VERSION],
        ).fetchone()[0]
        analytics_rows = con.execute(
            "SELECT COUNT(*) FROM analytics_evidence WHERE analytics_version = ?",
            [ANALYTICS_VERSION],
        ).fetchone()[0]
        if analytics_rows != base_rows * 2:
            raise AssertionError(f"Expected {base_rows * 2} analytics rows, found {analytics_rows}")

        scopes = dict(
            con.execute(
                """
                SELECT comparison_scope, COUNT(*)
                FROM analytics_evidence
                WHERE analytics_version = ?
                GROUP BY comparison_scope
                """,
                [ANALYTICS_VERSION],
            ).fetchall()
        )
        if scopes != {"SELF_ROLE_PRIOR": base_rows, "PEER_ROLE_PRIOR": base_rows}:
            raise AssertionError(f"Unexpected comparison-scope counts: {scopes}")

        states = {
            row[0]
            for row in con.execute(
                "SELECT DISTINCT evidence_state FROM analytics_evidence WHERE analytics_version = ?",
                [ANALYTICS_VERSION],
            ).fetchall()
        }
        if not states.issubset(ALLOWED_STATES):
            raise AssertionError(f"Unexpected evidence states: {sorted(states - ALLOWED_STATES)}")

        directions = {
            row[0]
            for row in con.execute(
                "SELECT DISTINCT comparison_direction FROM analytics_evidence WHERE analytics_version = ?",
                [ANALYTICS_VERSION],
            ).fetchall()
        }
        if not directions.issubset(ALLOWED_DIRECTIONS):
            raise AssertionError(f"Unexpected comparison directions: {directions - ALLOWED_DIRECTIONS}")

        # SELF_ROLE_PRIOR must be a faithful Analytics representation of FEATURE-03,
        # not a second independent temporal calculation.
        parity_errors = con.execute(
            """
            SELECT COUNT(*)
            FROM analytics_evidence a
            LEFT JOIN player_match_features h
              ON h.match_id = a.match_id
             AND h.player_id = a.player_id
             AND h.feature_version = ?
             AND h.feature_name = a.feature_name || '__role_history_n'
            LEFT JOIN player_match_features mu
              ON mu.match_id = a.match_id
             AND mu.player_id = a.player_id
             AND mu.feature_version = ?
             AND mu.feature_name = a.feature_name || '__role_prior_mean'
            LEFT JOIN player_match_features sd
              ON sd.match_id = a.match_id
             AND sd.player_id = a.player_id
             AND sd.feature_version = ?
             AND sd.feature_name = a.feature_name || '__role_prior_std'
            LEFT JOIN player_match_features sl
              ON sl.match_id = a.match_id
             AND sl.player_id = a.player_id
             AND sl.feature_version = ?
             AND sl.feature_name = a.feature_name || '__role_prior_slope'
            LEFT JOIN player_match_features de
              ON de.match_id = a.match_id
             AND de.player_id = a.player_id
             AND de.feature_version = ?
             AND de.feature_name = a.feature_name || '__role_delta_prior_mean'
            WHERE a.analytics_version = ?
              AND a.comparison_scope = 'SELF_ROLE_PRIOR'
              AND (
                   a.baseline_observations_n IS DISTINCT FROM CAST(COALESCE(h.feature_value, 0) AS BIGINT)
                OR a.baseline_mean IS DISTINCT FROM mu.feature_value
                OR a.baseline_std IS DISTINCT FROM sd.feature_value
                OR a.baseline_slope IS DISTINCT FROM sl.feature_value
                OR a.delta_from_mean IS DISTINCT FROM de.feature_value
              )
            """,
            [ROLE_VERSION, ROLE_VERSION, ROLE_VERSION, ROLE_VERSION, ROLE_VERSION, ANALYTICS_VERSION],
        ).fetchone()[0]
        if parity_errors:
            raise AssertionError(f"SELF_ROLE_PRIOR / FEATURE-03 parity errors: {parity_errors}")

        # Missing-role rows must never acquire a peer baseline.
        unsafe_role_rows = con.execute(
            """
            SELECT COUNT(*)
            FROM analytics_evidence
            WHERE analytics_version = ?
              AND primary_role IS NULL
              AND (
                   evidence_state <> 'ROLE_UNKNOWN'
                OR baseline_players_n <> 0
                OR baseline_observations_n <> 0
                OR baseline_mean IS NOT NULL
              )
            """,
            [ANALYTICS_VERSION],
        ).fetchone()[0]
        if unsafe_role_rows:
            raise AssertionError(f"Unsafe role-unknown analytics rows: {unsafe_role_rows}")

        forbidden_columns = {
            "score",
            "rank",
            "ranking",
            "percentile",
            "recommendation",
            "confidence",
        }
        columns = {
            row[1].lower()
            for row in con.execute("PRAGMA table_info('analytics_evidence')").fetchall()
        }
        if columns.intersection(forbidden_columns):
            raise AssertionError(f"Forbidden evaluative columns present: {columns.intersection(forbidden_columns)}")

        peer_samples = validate_peer_samples(con)
        summary = con.execute(
            """
            SELECT comparison_scope, evidence_state, COUNT(*)
            FROM analytics_evidence
            WHERE analytics_version = ?
            GROUP BY comparison_scope, evidence_state
            ORDER BY comparison_scope, evidence_state
            """,
            [ANALYTICS_VERSION],
        ).fetchall()

    print("ANALYTICS-01 EVIDENCE CONTRACT: PASS")
    print(f"base FEATURE-01 rows: {base_rows}")
    print(f"analytics rows: {analytics_rows}")
    print(f"SELF_ROLE_PRIOR rows: {scopes['SELF_ROLE_PRIOR']}")
    print(f"PEER_ROLE_PRIOR rows: {scopes['PEER_ROLE_PRIOR']}")
    print(f"peer strict-past samples independently checked: {peer_samples}")
    for scope, state, count in summary:
        print(f"{scope} / {state}: {count}")
    print("FEATURE-03 self-history provenance: PASS")
    print("Peer-role strict-past / current-player exclusion / equal-player weighting: PASS")
    print("No score, ranking, recommendation, sample threshold or good/bad label: PASS")


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    validate(db_path)


if __name__ == "__main__":
    main()
