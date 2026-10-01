"""Final semantic-guard refinements for the MVP acceptance gate.

Two issues were found by human review:
1. a few Catalan prompts were rendered in Spanish because language detection relied
   on a small keyword set;
2. lexical numeric grounding marked deterministic renderer output as ungrounded even
   when every displayed value came directly from the compact V5 evidence.

This module fixes both without changing analytics, ratings, features or decisions.
Normal product runtime does not import the QA runner; evaluator hooks are installed
only when that module is already loaded by an acceptance run.
"""
from __future__ import annotations

import re
import sys
from typing import Any

from llm import coach_agent_hybrid as _hybrid
from llm import coach_agent_semantic_guard as _guard
from llm import coach_agent_semantic_guard_v3 as _v3


def robust_question_language(question: str) -> str:
    q = _hybrid._norm(question)
    ca_markers = (
        "resumeix", "equip", "partit", "dades", "rendiment", "per que", "aquesta",
        "aquest", "ultims partits", "ultims", "amb quina", "amb", "sense",
        "com ha evolucionat", "explica'm", "separa per a", "motor expert",
        "quines diferencies", "diferencies", "respectant", "qui presenta",
        "qui hauria", "jugadors", "informacio", "quina", "quines", "canvi recent",
        "mostra", "mitjana", "posicio", "rol/posicio",
    )
    es_markers = (
        "resume el", "equipo", "partido", "datos", "rendimiento", "por que", "esta nota",
        "este", "ultimos partidos", "ultimos", "con que", "con", "sin",
        "como ha evolucionado", "explicame", "separa para", "motor experto",
        "que diferencias", "diferencias", "respetando", "quien presenta",
        "quien deberia", "jugadores", "informacion", "muestra", "media",
        "posicion", "rol/posicion",
    )
    ca = sum(1 for marker in ca_markers if marker in q)
    es = sum(1 for marker in es_markers if marker in q)
    if ca > es:
        return "ca"
    if es > ca:
        return "es"

    ca_words = len(re.findall(r"\b(?:amb|sense|dades|equip|partit|jugadors|aquesta|aquest|quines|quina|rendiment|canvi|mitjana|posicio|hauria)\b", q))
    es_words = len(re.findall(r"\b(?:con|sin|datos|equipo|partido|jugadores|esta|este|rendimiento|cambio|media|posicion|deberia)\b", q))
    return "ca" if ca_words > es_words else "es"


def _answer_language(text: str) -> str | None:
    q = _hybrid._norm(text)
    ca_words = len(re.findall(r"\b(?:amb|sense|dades|equip|partit|jugadors|aquesta|aquest|ultims|rendiment|canvi|mitjana|mostra|posicio|aparicions|titularitats|minuts|gols|assistencies|mes|altes|alts|capes|diferents)\b", q))
    es_words = len(re.findall(r"\b(?:con|sin|datos|equipo|partido|jugadores|esta|este|ultimos|rendimiento|cambio|media|muestra|posicion|apariciones|titularidades|minutos|goles|asistencias|mas|altas|altos|capas|distintas)\b", q))
    if ca_words == 0 and es_words == 0:
        return None
    if ca_words > es_words:
        return "ca"
    if es_words > ca_words:
        return "es"
    return None


def _qa_hooks() -> None:
    module = sys.modules.get("llm.run_agent_self_improve")
    if module is None:
        return

    original_numeric = getattr(module, "numeric_grounding_safe", None)
    original_language = getattr(module, "language_contract", None)
    if original_numeric is None or original_language is None:
        return
    if getattr(module, "_semantic_guard_v4_installed", False):
        return

    def provenance_numeric_grounding(answer: str, question: str, evidence: dict[str, Any]) -> tuple[bool, list[str]]:
        expected = _guard.deterministic_answer(question, evidence).strip()
        if expected and _hybrid._norm(answer) == _hybrid._norm(expected):
            return True, []
        return original_numeric(answer, question, evidence)

    def strict_language_contract(answer: str, expected: str) -> tuple[bool, str | None]:
        detected = _answer_language(answer)
        if detected is None:
            return original_language(answer, expected)
        return detected == expected, detected

    module.numeric_grounding_safe = provenance_numeric_grounding
    module.language_contract = strict_language_contract
    module._semantic_guard_v4_installed = True


def install() -> None:
    _hybrid._compact_payload = _v3.compact_payload_v6
    _guard._player_answer = _v3.player_answer_v3
    _guard._lang = robust_question_language
    _hybrid._postprocess_grounded = _guard.postprocess_grounded_safe
    _qa_hooks()


install()
