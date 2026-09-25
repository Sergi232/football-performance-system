"""Validate LLM-02 routing without making an external API call."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import list_base_features, list_teams  # noqa: E402
from llm.context_builder import build_player_context, build_team_context  # noqa: E402
from llm.openai_provider import answer_question, configured_model, provider_available  # noqa: E402

DB = ROOT / "data" / "football_performance.duckdb"


def main() -> None:
    teams = list_teams(DB)
    if teams.empty:
        raise RuntimeError("LLM-02 requires at least one team")
    team_id = str(teams.iloc[0]["team_id"])

    team_context = build_team_context(DB, team_id)
    squad = team_context.get("squad") or []
    if not squad:
        raise RuntimeError("LLM-02 requires a non-empty squad context")

    player_id = str(squad[0]["player_id"])
    features = list_base_features(DB, player_id)
    feature_name = features[0] if features else None
    player_context = build_player_context(DB, team_id, player_id, feature_name)

    blocked = answer_question("Qui rendeix millor com a interior?", team_context, prefer_llm=True)
    if blocked.mode != "guardrail":
        raise RuntimeError(f"Blocked question was not intercepted before provider routing: {blocked.mode}")

    deterministic = answer_question("Resumeix les dades disponibles", team_context, prefer_llm=False)
    if deterministic.mode != "deterministic" or not deterministic.text:
        raise RuntimeError("Deterministic fallback contract failed")

    role = answer_question("Quin és el seu rol i encaix?", player_context, prefer_llm=False)
    if "N12000/N13000" not in role.text:
        raise RuntimeError("Role/fit provenance was lost in LLM-02 routing")

    guardrails = team_context.get("guardrails") or {}
    if guardrails.get("recommendation_policy_validated") is not False:
        raise RuntimeError("Recommendation policy guardrail must remain false")
    if guardrails.get("cross_player_ranking_allowed") is not False:
        raise RuntimeError("Cross-player ranking guardrail must remain false")

    print("LLM-02 PROVIDER ROUTING CONTRACT: PASS")
    print(f"configured model: {configured_model()}")
    print(f"OpenAI API key configured: {'YES' if provider_available() else 'NO'}")
    print("blocked ranking/recommendation intercepted before external provider: PASS")
    print("deterministic fallback: PASS")
    print("N12000/N13000 provenance preserved: PASS")
    print("No external API call was made by this validation script.")


if __name__ == "__main__":
    main()
