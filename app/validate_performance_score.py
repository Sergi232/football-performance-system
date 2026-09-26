"""Validate the materialized performance-score contract used by the dashboard."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.performance_score_access import SCORE_VERSION, get_score_status, list_score_teams  # noqa: E402

DB = ROOT / "data" / "football_performance.duckdb"


def main() -> None:
    teams = list_score_teams(DB)
    if teams.empty:
        raise RuntimeError(f"No rows found for {SCORE_VERSION}")

    status = get_score_status(DB)
    if status["rows"] <= 0:
        raise RuntimeError("Performance-score table is empty")
    if status["observable_rows"] <= 0:
        raise RuntimeError("No observable positional-role rows found")
    if status["eligible_rows"] <= 0:
        raise RuntimeError("No eligible performance scores found")
    if status["eligible_rows"] > status["observable_rows"]:
        raise RuntimeError("Eligible rows cannot exceed observable positional-role rows")

    coverage = status["eligible_rows"] / status["observable_rows"]
    if abs(coverage - 0.8) > 1e-9:
        raise RuntimeError(f"Expected PERF-14 observable-role coverage 0.8, found {coverage}")
    if status["role_unavailable_rows"] != 172:
        raise RuntimeError(
            f"Expected 172 source-role-unavailable rows from PERF-14 validation, found {status['role_unavailable_rows']}"
        )

    print("PERFORMANCE SCORE DASHBOARD CONTRACT: PASS")
    print(f"score_version={SCORE_VERSION}")
    print(f"teams={len(teams)}")
    print(f"rows={status['rows']}")
    print(f"observable_role_rows={status['observable_rows']}")
    print(f"eligible_scores={status['eligible_rows']}")
    print(f"coverage_observable_roles={coverage:.4f}")
    print(f"source_role_unavailable_rows={status['role_unavailable_rows']}")


if __name__ == "__main__":
    main()
