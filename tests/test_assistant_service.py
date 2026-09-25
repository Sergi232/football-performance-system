from llm.assistant_service import answer_from_context


def test_blocks_unvalidated_ranking_question():
    context = {"scope": "team", "overview": {}}
    answer = answer_from_context("Qui està millorant més?", context)
    assert "ranking" in answer.lower() or "recoman" in answer.lower()


def test_player_role_answer_keeps_gate_provenance():
    context = {
        "scope": "player",
        "summary": {"player": "PLAYER_001"},
        "latest_role_fit_gate": {
            "observed_role": "CM",
            "same_role_history": "4",
            "evaluable_signals": "12",
            "evidence_coverage": "0.5",
            "final_status": "RECOMMENDATION_NOT_ISSUED_POLICY_UNVALIDATED",
        },
    }
    answer = answer_from_context("Quin és el rol i encaix?", context)
    assert "N12000/N13000" in answer
    assert "RECOMMENDATION_NOT_ISSUED_POLICY_UNVALIDATED" in answer


def test_feature_evolution_is_descriptive_not_evaluative():
    context = {
        "scope": "player",
        "summary": {"player": "PLAYER_001"},
        "latest_role_fit_gate": {},
        "feature_name": "shots_total_per90",
        "feature_history": [
            {"match_date": "2026-01-01", "feature_value": 1.0},
            {"match_date": "2026-02-01", "feature_value": 2.0},
        ],
    }
    answer = answer_from_context("Com ha evolucionat aquesta mètrica?", context)
    assert "millora" not in answer.lower()
    assert "empitjorament" in answer.lower()
