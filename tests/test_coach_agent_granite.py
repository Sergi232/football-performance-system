from pathlib import Path

import pandas as pd

from llm import coach_agent_granite as agent


def test_default_model_is_granite():
    assert agent.DEFAULT_MODEL == "granite4.2:3b"


def test_guardrail_blocks_cansancio_and_lineup():
    fatigue = agent._guardrail("¿Quién presenta más cansancio para el próximo partido?")
    lineup = agent._guardrail("¿Quién debería ser titular el próximo partido?")
    assert fatigue is not None
    assert "fatiga" in fatigue.lower() or "cansancio" in fatigue.lower()
    assert lineup is not None
    assert "titular" in lineup.lower() or "once" in lineup.lower()


def test_player_alias_normalizes_numeric_fragment(monkeypatch):
    squad = pd.DataFrame(
        [
            {"player_id": "p1", "player": "Jugador 07"},
            {"player_id": "p2", "player": "Jugador 12"},
        ]
    )
    monkeypatch.setattr(agent, "get_squad_summary", lambda *_: squad)
    assert agent._canonical_player(Path("dummy.duckdb"), "team", "07") == "Jugador 07"
    assert agent._canonical_player(Path("dummy.duckdb"), "team", "7") == "Jugador 07"


def test_match_alias_normalizes_numeric_fragment(monkeypatch):
    matches = pd.DataFrame(
        [
            {"match_id": "m9", "opponent": "Rival 09"},
            {"match_id": "m2", "opponent": "Rival 02"},
        ]
    )
    monkeypatch.setattr(agent, "get_team_matches", lambda *_: matches)
    assert agent._canonical_match(Path("dummy.duckdb"), "team", "Rival 09") == "m9"
    assert agent._canonical_match(Path("dummy.duckdb"), "team", "09") == "m9"


def test_numeric_guard_removes_unsupported_number():
    evidence = {
        "query_team_stats": {
            "metric": "goals",
            "rows": [{"player": "Jugador 07", "goals": 8}],
        }
    }
    answer = "Jugador 07 suma 8 goles. Tiene además 99 asistencias."
    safe = agent._numeric_guard(answer, evidence)
    assert "8 goles" in safe
    assert "99" not in safe


def test_unknown_tool_is_not_executed():
    runtime = agent._core.CoachAgentRuntime(Path("dummy.duckdb"), "team")
    out = agent._execute_tool(runtime, "invented_tool", {})
    assert "error" in out
    assert "no disponible" in out["error"].lower()


def test_tools_include_observed_stat_ranking():
    names = {row["function"]["name"] for row in agent.TOOLS}
    assert "query_team_stats" in names
    assert "get_player_profile" in names
    assert "get_player_gps" in names
    assert "get_match_detail" in names
