from llm import coach_agent_general as agent


def test_rank_players_accepts_generic_gps_metric_per_match():
    plan = {
        "calls": [
            {
                "tool": "rank_players",
                "args": {"metric": "distancia", "aggregation": "mean", "limit": 5},
            }
        ]
    }
    calls = agent._validated(plan)
    assert calls == [
        (
            "rank_players",
            {"metric": "total_distance_m", "aggregation": "mean", "order": "desc", "limit": 5},
        )
    ]


def test_rank_players_rejects_unknown_metric():
    plan = {"calls": [{"tool": "rank_players", "args": {"metric": "xg"}}]}
    assert agent._validated(plan) == []


def test_evidence_followup_is_detected():
    assert agent._is_evidence("que evidencias tienes?")
    assert agent._is_evidence("¿En qué te basas para decir eso?")


def test_ordinal_followup_is_detected():
    assert agent._ordinal("y el segundo?") == 1
    assert agent._ordinal("¿y el tercero?") == 2


def test_window_followup_is_detected():
    assert agent._window("y en los últimos 5 partidos?") == 5


def test_followup_modifies_existing_rank_without_new_metric_logic():
    calls = [
        (
            "rank_players",
            {"metric": "total_distance_m", "aggregation": "mean", "order": "desc", "limit": 5},
        )
    ]
    out = agent._modify(calls, "y en los últimos 5 partidos?")
    assert out[0][1]["last_n_matches"] == 5
    assert out[0][1]["metric"] == "total_distance_m"


def test_evidence_answer_exposes_source_and_aggregation():
    evidence = {
        "rank_players": {
            "source": "player_match_gps_summary",
            "metric_label": "distancia",
            "aggregation": "mean",
            "rows": [{"player": "Jugador 01", "value": 10000, "sample_matches": 5}],
        }
    }
    text = agent._evidence_answer(evidence)
    assert "player_match_gps_summary" in text
    assert "mean" in text
    assert "Python/DuckDB" in text
