import pytest

from llm import coach_agent_general as agent
from llm import coach_role_analysis as role


@pytest.mark.parametrize(
    ("question", "metric"),
    [
        ("¿Quién tiene más goles?", "goals"),
        ("¿Quién lleva más asistencias?", "assists"),
        ("¿Quién acumula más remates?", "shots"),
        ("¿Quién tiene más pases completados?", "passes_completed"),
        ("¿Quién tiene más entradas ganadas?", "tackles_won"),
        ("¿Quién suma más intercepciones?", "interceptions"),
        ("¿Quién ha jugado más minutos?", "minutes"),
        ("¿Quién tiene más apariciones?", "appearances"),
        ("¿Quién recorre más distancia por partido?", "total_distance_m"),
        ("¿Quién tiene mayor velocidad máxima?", "peak_speed_m_s"),
        ("¿Quién tiene mejor rating?", "latest_match_rating"),
        ("¿Quién tiene mejor rating medio?", "avg_last5"),
        ("¿Quién tiene mayor tendencia?", "trend_delta_5v5"),
    ],
)
def test_metric_queries_compose_without_sentence_specific_rules(question, metric):
    calls = agent._deterministic_rank_calls(question)
    assert calls
    assert calls[0][0] == "rank_players"
    assert calls[0][1]["metric"] == metric


@pytest.mark.parametrize(
    ("question", "aggregation"),
    [
        ("¿Quién tiene más goles acumulados?", "sum"),
        ("¿Quién hace más distancia por partido?", "mean"),
        ("¿Quién tiene mayor velocidad máxima?", "max"),
        ("¿Quién tiene menos intercepciones?", "sum"),
    ],
)
def test_aggregation_signals_are_compositional(question, aggregation):
    calls = agent._deterministic_rank_calls(question)
    assert calls
    assert calls[0][1]["aggregation"] == aggregation


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("porteros", "GK"),
        ("guardameta", "GK"),
        ("centrales", "CB"),
        ("defensa central", "CB"),
        ("laterales", "FB"),
        ("carrileros", "FB"),
        ("pivotes", "DM"),
        ("mediocentro defensivo", "DM"),
        ("interiores", "CM"),
        ("centrocampistas", "CM"),
        ("mediapuntas", "AM"),
        ("extremos", "W"),
        ("delanteros", "ST"),
        ("punta", "ST"),
    ],
)
def test_role_alias_space(text, expected):
    assert role.role_from_text(text) == expected


@pytest.mark.parametrize(
    "question",
    [
        "Compara los delanteros",
        "Muéstrame las métricas de los centrales",
        "¿Cómo están rindiendo los mediocentros defensivos?",
        "¿Quién ha rendido mejor entre los porteros?",
        "Dime las estadísticas de los extremos",
    ],
)
def test_role_intent_recognizes_natural_coach_wording(question):
    assert role._is_role_query(question)


def test_temporal_window_and_ordinal_are_generic():
    assert agent._window("en los últimos 7 partidos") == 7
    assert agent._ordinal("¿y el cuarto?") == 3


def test_role_followup_language_is_supported():
    assert role._is_compare_followup("Sí, compáralos")
    assert role._is_compare_followup("Muéstrame las métricas")
    assert role._is_evidence_followup("¿En qué te basas?")
