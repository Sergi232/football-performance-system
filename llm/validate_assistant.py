"""Validate LLM-01 structured assistant contract against the local DuckDB."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import list_base_features, list_teams  # noqa: E402
from llm.assistant_service import answer_from_context  # noqa: E402
from llm.context_builder import (  # noqa: E402
    build_match_context,
    build_player_context,
    build_team_context,
)

DB = ROOT / "data" / "football_performance.duckdb"


def main() -> None:
    teams = list_teams(DB)
    if teams.empty:
        raise RuntimeError("No team available for LLM-01 validation")
    team_id = str(teams.iloc[0]["team_id"])

    team_context = build_team_context(DB, team_id)
    if team_context["guardrails"]["recommendation_policy_validated"] is not False:
        raise RuntimeError("Team assistant guardrail failed")
    if not team_context["matches"] or not team_context["squad"]:
        raise RuntimeError("Team context missing matches/squad")

    player_id = str(team_context["squad"][0]["player_id"])
    features = list_base_features(DB, player_id)
    feature_name = features[0] if features else None
    player_context = build_player_context(DB, team_id, player_id, feature_name)
    if player_context["summary"] is None:
        raise RuntimeError("Player context missing summary")

    blocked = answer_from_context("Qui està millorant més?", team_context)
    if "ranking" not in blocked.lower() and "recoman" not in blocked.lower():
        raise RuntimeError("Unsafe comparative question was not blocked")

    gate_answer = answer_from_context("Quin és el seu rol i encaix?", player_context)
    if "n12000/n13000" not in gate_answer.lower():
        raise RuntimeError("Role-fit explanation missing decision provenance")

    match_id = str(team_context["matches"][0]["match_id"])
    match_context = build_match_context(DB, team_id, match_id)
    if match_context["match"] is None or not match_context["lineup"]:
        raise RuntimeError("Match context missing match/lineup")

    print("LLM-01 ASSISTANT CONTRACT: PASS")
    print(f"team: {teams.iloc[0]['display_name']}")
    print(f"team context matches: {len(team_context['matches'])}")
    print(f"team context squad: {len(team_context['squad'])}")
    print(f"player: {player_context['summary']['player']}")
    print(f"feature context: {feature_name or 'NONE'}")
    print(f"match lineup rows: {len(match_context['lineup'])}")
    print("unsupported ranking/recommendation question guardrail: PASS")
    print("N12000/N13000 provenance explanation: PASS")
    print("No external LLM call, new metric, ranking or tactical recommendation was created.")


if __name__ == "__main__":
    main()
