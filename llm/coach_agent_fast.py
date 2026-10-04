"""Compatibility entry point for the local Coach Copilot.

The public API delegates to the hybrid generic-query agent, with a thin safety and
normalization layer for real UI/CLI usage. High-confidence questions stay
deterministic; only genuinely ambiguous supported language falls back to Qwen.
"""
from __future__ import annotations

import re
from typing import Any

from llm.coach_agent_general import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    CoachAgentResult,
    ollama_status,
)

# Windows PowerShell 5 can replace non-ASCII characters with '?' when piping a
# here-string into Python. The browser does not have this problem, but repairing a
# small set of common Spanish football/query tokens keeps CLI validation faithful.
_MOJIBAKE_REPAIRS = (
    ("?qui?n", "quien"),
    ("?qu?", "que"),
    ("?c?mo", "como"),
    ("?cu?l", "cual"),
    ("?cu?nt", "cuant"),
    ("m?s", "mas"),
    ("?ltim", "ultim"),
    ("d?a", "dia"),
    ("d?as", "dias"),
    ("est?", "esta"),
    ("pas?", "paso"),
    ("lesi?n", "lesion"),
    ("deber?a", "deberia"),
    ("alineaci?n", "alineacion"),
    ("teor?a", "teoria"),
    ("evoluci?n", "evolucion"),
    ("comparaci?n", "comparacion"),
    ("m?ximo", "maximo"),
    ("m?nimo", "minimo"),
    ("f?sic", "fisic"),
    ("aceleraci?n", "aceleracion"),
    ("desaceleraci?n", "desaceleracion"),
    ("ens??ame", "ensename"),
)

_UNVALIDATED_CRITERION_MESSAGE = (
    "No puedo determinar quién es el jugador más completo, más determinante o mejor en general "
    "porque ese criterio no tiene una definición analítica única y validada en el sistema. "
    "Puedo compararlos con métricas concretas como Match Rating, tendencia, goles, asistencias, "
    "remates, minutos o GPS descriptivo."
)


def _repair_console_text(value: object) -> str:
    text = str(value or "").strip()
    if not text or "?" not in text:
        return text
    out = text
    for bad, good in _MOJIBAKE_REPAIRS:
        out = re.sub(re.escape(bad), good, out, flags=re.IGNORECASE)
    # PowerShell may also replace the leading inverted question mark only.
    out = re.sub(r"^\?+(?=[A-Za-zÁÉÍÓÚÜÑáéíóúüñ])", "", out)
    return out


def _policy_block(question: str) -> str | None:
    from llm import coach_agent_general as agent
    from llm import coach_role_analysis as role_analysis

    q = agent._norm(question)
    # If the user already names an approved metric, words such as "mejor" are only
    # ordering language (e.g. "mejor rating") and must remain supported.
    if agent._metric_in_text(question) is not None:
        return None
    # A role-specific performance question is handled by the deterministic role
    # comparator, which makes Match Rating medio the explicit ordering criterion.
    if role_analysis.role_from_text(question) is not None:
        return None
    ambiguous = (
        "mas completo",
        "mas determinante",
        "mejor jugador",
        "mejor en general",
        "mas importante",
        "rinde mejor",
        "ha rendido mejor",
        "mejor rendimiento",
    )
    if any(token in q for token in ambiguous):
        return _UNVALIDATED_CRITERION_MESSAGE
    return None


def _canonicalize_supported_profile_query(question: str) -> str:
    """Map broad but unambiguous player-profile wording to an existing tool family.

    This is intent normalization, not a new football rule: the underlying answer is
    still generated from get_player_profile and already-materialized analytics.
    """
    from llm import coach_agent_general as agent

    q = agent._norm(question)
    profile_phrases = (
        "ponme al dia sobre ",
        "hablame de ",
        "dame un resumen de ",
        "resumeme a ",
        "que tal va ",
        "como va ",
    )
    if any(phrase in q for phrase in profile_phrases):
        return f"perfil y evolucion del jugador: {question}"
    return question


def _repair_history(history: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    if not history:
        return history
    repaired: list[dict[str, Any]] = []
    for item in history:
        current = dict(item)
        if str(current.get("role") or "") == "user" and current.get("content") is not None:
            current["content"] = _repair_console_text(current["content"])
        repaired.append(current)
    return repaired


def _collapse_followup_history(question: str, history: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    """Keep the latest substantive user query as the anchor for chained follow-ups."""
    if not history:
        return history

    from llm import coach_agent_general as agent

    if not agent._followup(question):
        return history

    trimmed = list(history)
    while trimmed:
        last_user_idx = None
        for idx in range(len(trimmed) - 1, -1, -1):
            item = trimmed[idx]
            if str(item.get("role") or "") == "user" and str(item.get("content") or "").strip():
                last_user_idx = idx
                break
        if last_user_idx is None:
            break
        last_user_text = str(trimmed[last_user_idx].get("content") or "").strip()
        if not agent._followup(last_user_text):
            break
        # Remove the previous follow-up and its assistant response. The remaining
        # history ends at the substantive anchor query/answer pair.
        trimmed = trimmed[:last_user_idx]
    return trimmed


def _prepare_call(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[tuple[Any, ...], dict[str, Any], str | None]:
    prepared_args = list(args)
    prepared_kwargs = dict(kwargs)

    raw_question = str(prepared_args[0]) if prepared_args else str(prepared_kwargs.get("question") or "")
    repaired_question = _repair_console_text(raw_question)
    blocked = _policy_block(repaired_question)
    routed_question = _canonicalize_supported_profile_query(repaired_question)

    if prepared_args:
        prepared_args[0] = routed_question
    else:
        prepared_kwargs["question"] = routed_question
    prepared_kwargs.setdefault("model", DEFAULT_MODEL)

    if "history" in prepared_kwargs:
        history = _repair_history(prepared_kwargs.get("history"))
        prepared_kwargs["history"] = _collapse_followup_history(routed_question, history)

    return tuple(prepared_args), prepared_kwargs, blocked


def run_coach_agent_turn(*args: Any, **kwargs: Any) -> CoachAgentResult:
    from llm import coach_role_analysis as role_analysis
    from llm.coach_agent_general import run_coach_agent_turn as _run

    # Role comparisons are a common coaching query and should not depend on an LLM.
    # Run this bounded descriptive route before the broad "best player" policy guard.
    raw_question = str(args[0]) if args else str(kwargs.get("question") or "")
    repaired_question = _repair_console_text(raw_question)
    repaired_history = _repair_history(kwargs.get("history"))
    if kwargs.get("db_path") is not None and kwargs.get("team_id") is not None:
        role_result = role_analysis.try_role_query(
            repaired_question,
            db_path=kwargs["db_path"],
            team_id=str(kwargs["team_id"]),
            history=repaired_history,
        )
        if role_result is not None:
            selected_model = str(kwargs.get("model") or DEFAULT_MODEL)
            return CoachAgentResult(
                str(role_result["text"]),
                selected_model,
                0,
                (str(role_result.get("tool") or "compare_role_players"),),
                None,
            )

    prepared_args, prepared_kwargs, blocked = _prepare_call(args, kwargs)
    if blocked:
        return CoachAgentResult(blocked, str(prepared_kwargs.get("model") or DEFAULT_MODEL), 0, (), None)
    return _run(*prepared_args, **prepared_kwargs)


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    return run_coach_agent_turn(*args, **kwargs).text