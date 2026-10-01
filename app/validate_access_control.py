"""Contract test for team-scoped application authorization.

This validates authorization only. It does not claim production authentication,
password storage, sessions or billing are implemented.
"""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.access_control import AccessDenied  # noqa: E402
from app.data_access import get_team_overview, list_teams  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
ACCESS_KEYS = (
    "FPS_ACCESS_USER_ID",
    "FPS_ACCESS_ROLE",
    "FPS_ORGANIZATION_ID",
    "FPS_ALLOWED_TEAM_IDS",
)


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


@contextmanager
def temporary_access(**values: str | None):
    old = {key: os.environ.get(key) for key in ACCESS_KEYS}
    try:
        for key in ACCESS_KEYS:
            value = values.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main() -> None:
    path = db_path()
    if not path.exists():
        raise SystemExit(f"ACCESS CONTROL: FAIL — database not found: {path}")

    with temporary_access(FPS_ACCESS_ROLE="SUPERADMIN", FPS_ACCESS_USER_ID="contract-admin"):
        all_teams = list_teams(path)
    if all_teams.empty:
        raise SystemExit("ACCESS CONTROL: FAIL — no teams available")

    team_ids = all_teams["team_id"].astype(str).tolist()
    first = team_ids[0]

    with temporary_access(
        FPS_ACCESS_ROLE="STAFF",
        FPS_ACCESS_USER_ID="staff-one-team",
        FPS_ALLOWED_TEAM_IDS=first,
    ):
        visible = list_teams(path)
        if visible["team_id"].astype(str).tolist() != [first]:
            raise SystemExit("ACCESS CONTROL: FAIL — STAFF can see unexpected teams")
        get_team_overview(path, first)

        if len(team_ids) > 1:
            denied = team_ids[1]
            try:
                get_team_overview(path, denied)
            except AccessDenied:
                pass
            else:
                raise SystemExit("ACCESS CONTROL: FAIL — unauthorized team query was not blocked")

    with temporary_access(
        FPS_ACCESS_ROLE="STAFF",
        FPS_ACCESS_USER_ID="staff-unassigned",
        FPS_ALLOWED_TEAM_IDS="",
    ):
        if not list_teams(path).empty:
            raise SystemExit("ACCESS CONTROL: FAIL — restricted user without teams did not fail closed")

    club_scope = team_ids[: min(2, len(team_ids))]
    with temporary_access(
        FPS_ACCESS_ROLE="CLUB_ADMIN",
        FPS_ACCESS_USER_ID="club-admin",
        FPS_ORGANIZATION_ID="club-demo",
        FPS_ALLOWED_TEAM_IDS=",".join(club_scope),
    ):
        visible = list_teams(path)
        visible_ids = visible["team_id"].astype(str).tolist()
        if set(visible_ids) != set(club_scope):
            raise SystemExit("ACCESS CONTROL: FAIL — CLUB_ADMIN scope mismatch")

    print("ACCESS CONTROL CONTRACT")
    print(f"all_teams={len(team_ids)}")
    print(f"example_staff_team_id={first}")
    print("superadmin=PASS")
    print("staff_single_team=PASS")
    print("staff_unauthorized_query_blocked=PASS")
    print("restricted_without_assignment_fail_closed=PASS")
    print(f"club_admin_scope={len(club_scope)} team(s) PASS")
    print("AUTHENTICATION=NOT_IMPLEMENTED (separate future layer)")
    print("ACCESS CONTROL: PASS")


if __name__ == "__main__":
    main()
