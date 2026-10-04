from pathlib import Path

import pytest

from llm import coach_agent_external as external
from llm import coach_agent_general as agent


def test_openai_tool_surface_matches_bounded_fps_tools():
    names = {tool["name"] for tool in external.OPENAI_TOOLS}
    assert names == agent.ALLOWED


def test_openai_function_calls_are_revalidated_by_local_contract():
    class Call:
        type = "function_call"
        name = "rank_players"
        arguments = '{"metric":"goals","aggregation":"sum","order":"desc","limit":99}'

    class Response:
        output = [Call()]

    calls = external._response_calls(Response())
    assert len(calls) == 1
    name, args = calls[0]
    assert name == "rank_players"
    assert args["metric"] == "goals"
    assert args["aggregation"] == "sum"
    assert args["order"] == "desc"
    assert args["limit"] == 10


def test_unknown_external_tool_is_dropped():
    class Call:
        type = "function_call"
        name = "delete_database"
        arguments = "{}"

    class Response:
        output = [Call()]

    assert external._response_calls(Response()) == []


def test_missing_user_api_key_fails_before_network_call():
    with pytest.raises(ValueError, match="OPENAI_API_KEY_MISSING"):
        external._client("")


def test_role_comparison_is_deterministic_and_does_not_use_openai(monkeypatch):
    monkeypatch.setattr(
        external._role_analysis,
        "try_role_query",
        lambda *args, **kwargs: {
            "text": "Comparación descriptiva de centrales: Jugador X.",
            "tool": "compare_role_players",
        },
    )

    def _network_must_not_run(*args, **kwargs):
        raise AssertionError("OpenAI must not run for deterministic role comparison")

    monkeypatch.setattr(external, "_openai_route", _network_must_not_run)
    result = external.run_coach_agent_turn(
        "Compara los centrales",
        db_path=Path("not-needed.duckdb"),
        team_id="TEAM",
        api_key="sk-test",
        model="test-model",
    )
    assert result.tools_used == ("compare_role_players",)
    assert result.tool_rounds == 0
    assert "centrales" in result.text
