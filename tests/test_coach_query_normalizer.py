from llm.coach_query_normalizer import canonicalize_question


def test_max_scorer_without_accents_is_canonicalized():
    assert canonicalize_question("Quien es el maximo goleador") == "¿Quién es el máximo goleador?"


def test_natural_scorer_paraphrase_is_canonicalized():
    assert canonicalize_question("quien ha marcado mas goles") == "¿Quién es el máximo goleador?"


def test_common_domain_typo_is_canonicalized():
    assert canonicalize_question("quien es el maximo goleadr") == "¿Quién es el máximo goleador?"


def test_assists_without_punctuation_is_canonicalized():
    assert canonicalize_question("quien tiene mas asistencias") == "¿Quién lleva más asistencias?"


def test_demo_player_gps_shorthand_is_canonicalized():
    assert canonicalize_question("gps jugador 7") == "Enséñame los datos GPS de Jugador 07."


def test_demo_player_evolution_without_accents_is_canonicalized():
    assert canonicalize_question("como ha evolucionado jugador 7") == "¿Cómo ha evolucionado Jugador 07 últimamente?"


def test_match_shorthand_is_canonicalized():
    assert canonicalize_question("q paso contra rival 9") == "¿Qué pasó contra Rival 09?"


def test_policy_sensitive_question_is_not_rewritten():
    q = "quien esta mas cansado para el proximo partido"
    assert canonicalize_question(q) == q


def test_unknown_question_is_not_forced_into_a_tool_intent():
    q = "explicame la teoria de juegos"
    assert canonicalize_question(q) == q
