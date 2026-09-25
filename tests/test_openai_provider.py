from llm.openai_provider import answer_question


def test_blocked_question_never_routes_to_provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-that-must-not-be-used")
    context = {
        "scope": "team",
        "overview": {},
        "guardrails": {
            "recommendation_policy_validated": False,
            "cross_player_ranking_allowed": False,
        },
    }
    result = answer_question("Qui rendeix millor com a interior?", context)
    assert result.mode == "guardrail"
    assert "ranking" in result.text.lower() or "recoman" in result.text.lower()


def test_explicit_deterministic_mode_never_requires_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    context = {
        "scope": "team",
        "overview": {"matches": 38, "players": 36, "player_minutes": 100, "goals": 10, "assists": 8},
    }
    result = answer_question("Resumeix l'equip", context, prefer_llm=False)
    assert result.mode == "deterministic"
    assert result.text


def test_missing_key_falls_back_deterministically(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    context = {"scope": "match", "match": {"opponent": "OPP_001"}}
    result = answer_question("Resumeix aquest partit", context)
    assert result.mode == "deterministic_no_key"
    assert result.text
