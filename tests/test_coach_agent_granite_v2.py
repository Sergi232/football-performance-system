from llm import coach_agent_granite_v2 as agent


def test_structured_plan_validates_team_stats():
    plan = {"calls": [{"tool": "query_team_stats", "args": {"metric": "goles", "limit": 3}}]}
    assert agent._validated_calls(plan) == [("query_team_stats", {"metric": "goals", "limit": 3})]


def test_structured_plan_keeps_explicit_gps_tool():
    plan = {"calls": [{"tool": "get_player_gps", "args": {"player": "07"}}]}
    assert agent._validated_calls(plan) == [("get_player_gps", {"player": "07"})]


def test_structured_plan_keeps_match_detail():
    plan = {"calls": [{"tool": "get_match_detail", "args": {"match": "Rival 09"}}]}
    assert agent._validated_calls(plan) == [("get_match_detail", {"match": "Rival 09"})]


def test_unknown_or_invalid_tools_are_rejected():
    plan = {"calls": [{"tool": "invented_tool", "args": {}}, {"tool": "query_team_stats", "args": {"metric": "xg"}}]}
    assert agent._validated_calls(plan) == []


def test_gps_evidence_is_compact():
    payload = {
        "player": "Jugador 07",
        "gps_history": [
            {
                "match_date": "2026-01-01",
                "opponent": "Rival 01",
                "minutes_played": 90,
                "total_distance_m": 10123.4,
                "peak_speed_m_s": 8.7,
                "source_filename": "should_not_leak.csv",
            }
        ],
        "interpretation": "descriptive only",
    }
    out = agent._compact_evidence("get_player_gps", payload)
    row = out["gps_history"][0]
    assert row["total_distance_m"] == 10123.4
    assert "source_filename" not in row
