"""Validate assistant access to materialized Match Rating contexts."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import get_squad_summary, get_team_matches, list_teams
from llm.assistant_service import answer_from_context
from llm.context_builder import build_match_context, build_player_context, build_team_context

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"


def main() -> None:
    db = Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()
    teams = list_teams(db)
    if teams.empty:
        raise RuntimeError("No teams available")
    team_id = str(teams.iloc[0]["team_id"])

    team_context = build_team_context(db, team_id)
    if not team_context.get("match_rating_snapshot"):
        raise RuntimeError("Team context has no Match Rating snapshot")

    squad = get_squad_summary(db, team_id)
    player_id = str(squad.iloc[0]["player_id"])
    player_context = build_player_context(db, team_id, player_id)
    if not player_context.get("latest_match_rating"):
        raise RuntimeError("Player context has no latest Match Rating")
    player_answer = answer_from_context("Per què té aquest Match Rating?", player_context)
    if "Match Rating" not in player_answer:
        raise RuntimeError("Player assistant answer does not explain Match Rating")

    matches = get_team_matches(db, team_id).copy()
    matches["match_date"] = pd.to_datetime(matches["match_date"])
    match_id = str(matches.sort_values(["match_date", "match_id"]).iloc[0]["match_id"])
    match_context = build_match_context(db, team_id, match_id)
    ratings = match_context.get("match_ratings") or []
    if not ratings:
        raise RuntimeError("Match context has no materialized Match Ratings")
    if int((match_context.get("observations") or {}).get("players", 0)) != len(ratings):
        raise RuntimeError("Match observations and ratings have different player counts")
    match_answer = answer_from_context("Resumeix què ha passat en aquest partit.", match_context)
    if not match_answer:
        raise RuntimeError("Match assistant produced an empty answer")

    print("LLM MATCH RATING CONTEXT: PASS")
    print(f"team_snapshot_players={len(team_context['match_rating_snapshot'])}")
    print(f"player_latest_rating={player_context['latest_match_rating']['match_rating_10']}")
    print(f"first_match_rating_rows={len(ratings)}")
    print("Assistant explains materialized analytics; it does not recalculate ratings.")


if __name__ == "__main__":
    main()
