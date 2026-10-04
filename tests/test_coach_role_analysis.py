from pathlib import Path

from llm import coach_role_analysis as role


ROWS = [
    {
        "player": "Central A",
        "appearances": 20,
        "minutes": 1700,
        "avg_rating": 6.82,
        "latest_rating": 7.1,
        "goals": 1,
        "assists": 0,
        "shots": 8,
        "passes_total": 900,
        "passes_completed": 810,
        "pass_accuracy": 90.0,
        "tackles_total": 50,
        "tackles_won": 40,
        "interceptions": 35,
        "turnovers": 12,
        "dispossessed": 2,
        "saves": 0,
        "goals_conceded": 0,
    },
    {
        "player": "Central B",
        "appearances": 18,
        "minutes": 1500,
        "avg_rating": 6.55,
        "latest_rating": 6.4,
        "goals": 0,
        "assists": 1,
        "shots": 5,
        "passes_total": 820,
        "passes_completed": 730,
        "pass_accuracy": 89.0,
        "tackles_total": 48,
        "tackles_won": 36,
        "interceptions": 31,
        "turnovers": 15,
        "dispossessed": 3,
        "saves": 0,
        "goals_conceded": 0,
    },
]


def test_role_aliases_cover_common_spanish_coach_language():
    assert role.role_from_text("los delanteros") == "ST"
    assert role.role_from_text("posición de central") == "CB"
    assert role.role_from_text("los extremos") == "W"
    assert role.role_from_text("los laterales") == "FB"
    assert role.role_from_text("el portero") == "GK"


def test_role_best_query_uses_explicit_match_rating_criterion(monkeypatch):
    monkeypatch.setattr(role, "_fetch_role_rows", lambda *args, **kwargs: ROWS)
    result = role.try_role_query(
        "quien ha rendido mejor en la posicion de central muestrame las metricas",
        db_path=Path("dummy.duckdb"),
        team_id="TEAM",
    )
    assert result is not None
    assert result["tool"] == "compare_role_players"
    assert "Match Rating medio" in result["text"]
    assert "Central A" in result["text"]
    assert "entradas ganadas" in result["text"]
    assert "intercepciones" in result["text"]


def test_role_comparison_followup_recovers_previous_role_query(monkeypatch):
    monkeypatch.setattr(role, "_fetch_role_rows", lambda *args, **kwargs: ROWS)
    history = [
        {"role": "user", "content": "comparame las principales estadisticas de los centrales"},
        {"role": "assistant", "content": "respuesta previa"},
        {"role": "user", "content": "no puedes hacer nada"},
        {"role": "assistant", "content": "limitacion"},
    ]
    result = role.try_role_query(
        "si comparalos",
        db_path=Path("dummy.duckdb"),
        team_id="TEAM",
        history=history,
    )
    assert result is not None
    assert "Comparación descriptiva de centrales" in result["text"]
    assert "Central A" in result["text"]
    assert "Central B" in result["text"]


def test_general_best_player_without_role_is_not_claimed_here():
    assert role.try_role_query(
        "quien es el mejor jugador",
        db_path=Path("dummy.duckdb"),
        team_id="TEAM",
    ) is None
