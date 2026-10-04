from llm import coach_agent_fast as fast
from llm import coach_agent_general as agent


def test_repairs_common_windows_powershell_question_mark_corruption():
    assert fast._repair_console_text("?Qu? jugador tiene m?s rating?").casefold() == "que jugador tiene mas rating?"
    assert fast._repair_console_text("?Qui?n tiene m?s riesgo de lesi?n?").casefold() == "quien tiene mas riesgo de lesion?"
    assert fast._repair_console_text("Ponme al d?a sobre Jugador 01").casefold() == "ponme al dia sobre jugador 01"


def test_repaired_supported_queries_return_to_deterministic_router_shape():
    rating = fast._repair_console_text("?Qu? jugador tiene m?s rating?")
    distance = fast._repair_console_text("?Qui?n corre m?s distancia por partido?")
    assists = fast._repair_console_text("?Qui?n lleva m?s asistencias?")

    assert agent._deterministic_rank_calls(rating)[0][1]["metric"] == "latest_match_rating"
    assert agent._deterministic_rank_calls(distance)[0][1]["metric"] == "total_distance_m"
    assert agent._deterministic_rank_calls(distance)[0][1]["aggregation"] == "mean"
    assert agent._deterministic_rank_calls(assists)[0][1]["metric"] == "assists"
    assert agent._deterministic_rank_calls(assists)[0][1]["aggregation"] == "sum"


def test_repairs_allow_existing_policy_guardrails_to_fire():
    injury = fast._repair_console_text("?Qui?n tiene m?s riesgo de lesi?n?")
    lineup = fast._repair_console_text("?Qui?n deber?a ser titular?")

    assert agent._base._guardrail(injury)
    assert agent._base._guardrail(lineup)


def test_unvalidated_broad_superlatives_are_blocked_without_metric():
    assert fast._policy_block("¿Qué jugador es el más completo?")
    assert fast._policy_block("¿Quién está siendo más determinante?")
    assert fast._policy_block("¿Quién es el mejor jugador?")


def test_supported_metric_superlatives_are_not_blocked():
    assert fast._policy_block("¿Quién tiene mejor rating medio?") is None
    assert fast._policy_block("¿Quién tiene más goles?") is None


def test_common_profile_wording_is_canonicalized_without_new_sport_rule():
    out = fast._canonicalize_supported_profile_query("Ponme al día sobre Jugador 01")
    assert "perfil" in agent._norm(out)
    assert "jugador 01" in agent._norm(out)


def test_chained_followup_keeps_substantive_anchor_after_history_repair():
    history = [
        {"role": "user", "content": "?Qui?n corre m?s distancia por partido?"},
        {"role": "assistant", "content": "Jugador 01 lidera distancia."},
        {"role": "user", "content": "?Y el segundo?"},
        {"role": "assistant", "content": "2. Jugador B"},
    ]
    repaired = fast._repair_history(history)
    collapsed = fast._collapse_followup_history("Que evidencias tienes?", repaired)
    users = [x["content"].casefold() for x in collapsed if x.get("role") == "user"]
    assert users == ["quien corre mas distancia por partido?"]
