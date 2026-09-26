"""Validate Match Mode, deterministic insights and first-match PDF export."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import get_team_matches, list_teams
from app.match_insights import get_match_observations
from app.match_rating_access import get_match_ratings
from reports.data_builder import build_match_report_data
from reports.pdf_engine import render_pdf_bytes

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"


def main() -> None:
    db = Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(f"Database not found: {db}")

    teams = list_teams(db)
    if teams.empty:
        raise RuntimeError("No teams available")
    team_id = str(teams.iloc[0]["team_id"])

    matches = get_team_matches(db, team_id).copy()
    if matches.empty:
        raise RuntimeError("No matches available")
    matches["match_date"] = matches["match_date"].astype("datetime64[ns]")
    first = matches.sort_values(["match_date", "match_id"]).iloc[0]
    match_id = str(first["match_id"])

    ratings = get_match_ratings(db, team_id, match_id)
    if ratings.empty:
        raise RuntimeError("First match has no Match Rating rows")
    if ratings["match_rating_10"].isna().any():
        raise RuntimeError("First match contains null Match Rating values")

    observations = get_match_observations(db, team_id, match_id)
    if int(observations.get("players", 0)) != len(ratings):
        raise RuntimeError(
            f"Observed-player count differs from rating count: observations={observations.get('players')} ratings={len(ratings)}"
        )

    payload = build_match_report_data(db, team_id, match_id)
    if len(payload.get("ratings") or []) != len(ratings):
        raise RuntimeError("Match PDF payload does not include every rating row")

    pdf = render_pdf_bytes(payload)
    if len(pdf) < 1000:
        raise RuntimeError(f"Generated PDF is unexpectedly small: {len(pdf)} bytes")

    print("MATCH MODE CONTRACT: PASS")
    print(f"first_match_id={match_id}")
    print(f"first_match_rated_players={len(ratings)}")
    print(f"post_match_observation_players={observations['players']}")
    print(f"pdf_bytes={len(pdf)}")
    print("Match Mode is operational from the first available match.")


if __name__ == "__main__":
    main()
