from llm import coach_agent_fast as fast
from llm import coach_agent_general as agent


def test_default_runtime_model_is_qwen35_4b():
    assert agent.DEFAULT_MODEL == "qwen3.5:4b"


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


def test_natural_rating_question_uses_generic_rank_without_llm():
    calls = agent._deterministic_rank_calls("que jugador tiene mas rating")
    assert calls == [
        (
            "rank_players",
            {"metric": "latest_match_rating", "aggregation": "latest", "order": "desc", "limit": 5},
        )
    ]


def test_natural_gps_distance_question_uses_mean_per_match():
    calls = agent._deterministic_rank_calls("que jugador corre más distancia por partido")
    assert calls == [
        (
            "rank_players",
            {"metric": "total_distance_m", "aggregation": "mean", "order": "desc", "limit": 5},
        )
    ]


def test_natural_goals_and_assists_rankings_are_generic():
    goals = agent._deterministic_rank_calls("quien tiene mas goles")
    assists = agent._deterministic_rank_calls("quien lleva más asistencias")
    assert goals[0][1]["metric"] == "goals"
    assert assists[0][1]["metric"] == "assists"


def test_top_limit_and_lower_order_are_parsed_generically():
    top = agent._deterministic_rank_calls("top 3 jugadores con mas remates")
    low = agent._deterministic_rank_calls("quien tiene menos minutos")
    assert top[0][1]["limit"] == 3
    assert top[0][1]["metric"] == "shots"
    assert low[0][1]["order"] == "asc"


def test_evidence_followup_is_detected():
    assert agent._is_evidence("que evidencias tienes?")
    assert agent._is_evidence("¿En qué te basas para decir eso?")
    assert agent._is_evidence("de donde sale ese dato?")


def test_ordinal_followup_is_detected():
    assert agent._ordinal("y el segundo?") == 1
    assert agent._ordinal("¿y el tercero?") == 2


def test_window_followup_is_detected():
    assert agent._window("y en los últimos 5 partidos?") == 5


def test_followup_modifies_existing_rank_without_new_model_call():
    calls = [
        (
            "rank_players",
            {"metric": "total_distance_m", "aggregation": "mean", "order": "desc", "limit": 5},
        )
    ]
    out = agent._modify(calls, "y en los últimos 5 partidos?")
    assert out[0][1]["last_n_matches"] == 5
    assert out[0][1]["metric"] == "total_distance_m"


def test_chained_evidence_followup_keeps_substantive_anchor():
    history = [
        {"role": "user", "content": "que jugador corre más distancia por partido"},
        {"role": "assistant", "content": "Jugador 01 lidera distancia."},
        {"role": "user", "content": "y el segundo?"},
        {"role": "assistant", "content": "2. Jugador 02: 10000 m."},
    ]
    trimmed = fast._collapse_followup_history("que evidencias tienes?", history)
    assert trimmed is not None
    users = [item["content"] for item in trimmed if item.get("role") == "user"]
    assert users == ["que jugador corre más distancia por partido"]


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


def test_rank_answer_is_deterministic_and_factual():
    evidence = {
        "rank_players": {
            "metric_label": "Match Rating más reciente",
            "aggregation": "latest",
            "unit": "/10",
            "rows": [
                {"player": "Jugador 07", "value": 8.4, "sample_matches": 10},
                {"player": "Jugador 03", "value": 8.1, "sample_matches": 10},
            ],
        }
    }
    text = agent._rank_answer("que jugador tiene mas rating", evidence)
    assert "Jugador 07" in text
    assert "8.4" in text
    assert "Jugador 03" not in text


def test_guardrails_still_block_unvalidated_conclusions():
    fatigue = agent._base._guardrail("quien esta mas cansado?")
    injury = agent._base._guardrail("quien tiene riesgo de lesion?")
    lineup = agent._base._guardrail("quien deberia ser titular?")
    assert fatigue and "no puedo determinar" in fatigue.casefold()
    assert injury and "no puedo estimar" in injury.casefold()
    assert lineup and "no puedo recomendar" in lineup.casefold()
