"""Compatibility entry point for the local Coach Copilot.

The public API delegates to the hybrid generic-query agent, with a thin safety and
normalization layer for real UI/CLI usage. High-confidence questions stay
deterministic; only genuinely ambiguous supported language falls back to Qwen.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from llm.coach_agent_general import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    CoachAgentResult,
    ollama_status,
)

_MOJIBAKE_REPAIRS = (
    ("?qui?n", "quien"), ("?qu?", "que"), ("?c?mo", "como"), ("?cu?l", "cual"),
    ("?cu?nt", "cuant"), ("m?s", "mas"), ("?ltim", "ultim"), ("d?a", "dia"),
    ("d?as", "dias"), ("est?", "esta"), ("pas?", "paso"), ("lesi?n", "lesion"),
    ("deber?a", "deberia"), ("alineaci?n", "alineacion"), ("teor?a", "teoria"),
    ("evoluci?n", "evolucion"), ("comparaci?n", "comparacion"), ("m?ximo", "maximo"),
    ("m?nimo", "minimo"), ("f?sic", "fisic"), ("aceleraci?n", "aceleracion"),
    ("desaceleraci?n", "desaceleracion"), ("ens??ame", "ensename"),
)

_UNVALIDATED_CRITERION_MESSAGE = (
    "No puedo determinar quién es el jugador más completo, más determinante o mejor en general "
    "porque ese criterio no tiene una definición analítica única y validada en el sistema. "
    "Puedo compararlos con métricas concretas como Match Rating, tendencia, goles, asistencias, "
    "remates, minutos o GPS descriptivo."
)
_CLARIFY_MESSAGE = (
    "No he podido identificar una consulta futbolística concreta. Puedes preguntarme por jugadores, "
    "posiciones, partidos, estadísticas, evolución, GPS o calidad de los datos."
)
_CAPABILITIES_MESSAGE = (
    "Puedo consultar y comparar jugadores y posiciones, crear rankings por métricas disponibles, "
    "resumir partidos y equipo, revisar evolución, GPS descriptivo y calidad de datos. "
    "No invento fatiga, riesgo de lesión, XI ideal ni criterios de rendimiento no validados."
)

_DOMAIN_STEMS = (
    "equipo", "plantilla", "jugador", "partido", "rival", "dato", "estadistic", "metrica",
    "rating", "rend", "evolu", "forma", "tendencia", "gps", "fisic", "distancia", "velocidad",
    "aceler", "desaceler", "gol", "asisten", "remat", "disparo", "pase", "entrada", "intercep",
    "perdida", "desposes", "minuto", "aparicion", "posicion", "rol", "central", "lateral",
    "carrilero", "pivote", "mediocentro", "interior", "mediapunta", "extremo", "delanter",
    "punta", "portero", "guardameta", "compar", "ranking", "calidad", "cobertura", "limitacion",
    "evidencia", "temporada", "ultim", "fatiga", "cansad", "lesion", "titular", "alineacion",
)


def _repair_console_text(value: object) -> str:
    text = str(value or "").strip()
    if not text or "?" not in text:
        return text
    out = text
    for bad, good in _MOJIBAKE_REPAIRS:
        out = re.sub(re.escape(bad), good, out, flags=re.IGNORECASE)
    out = re.sub(r"^\?+(?=[A-Za-zÁÉÍÓÚÜÑáéíóúüñ])", "", out)
    return out


def _policy_block(question: str) -> str | None:
    from llm import coach_agent_general as agent
    from llm import coach_role_analysis as role_analysis

    q = agent._norm(question)
    if agent._metric_in_text(question) is not None:
        return None
    if role_analysis.role_from_text(question) is not None:
        return None
    ambiguous = (
        "mas completo", "mas determinante", "mejor jugador", "mejor en general",
        "mas importante", "rinde mejor", "ha rendido mejor", "mejor rendimiento",
    )
    if any(token in q for token in ambiguous):
        return _UNVALIDATED_CRITERION_MESSAGE
    return None


def _canonicalize_supported_profile_query(question: str) -> str:
    from llm import coach_agent_general as agent

    q = agent._norm(question)
    profile_phrases = (
        "ponme al dia sobre ", "hablame de ", "dame un resumen de ",
        "resumeme a ", "que tal va ", "como va ",
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
        trimmed = trimmed[:last_user_idx]
    return trimmed


def _try_role_pre_route(
    question: str,
    *,
    db_path: Path,
    team_id: str,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    from llm import coach_agent_general as agent
    from llm import coach_role_analysis as role_analysis

    runtime = agent._core.CoachAgentRuntime(Path(db_path).expanduser().resolve(), str(team_id))
    if agent._player_mentions(runtime, question):
        return None
    return role_analysis.try_role_query(
        question,
        db_path=Path(db_path),
        team_id=str(team_id),
        history=history,
    )


def _looks_like_gibberish(question: str) -> bool:
    from llm import coach_agent_general as agent
    q = agent._norm(question)
    if not q:
        return True
    compact = re.sub(r"[^a-z0-9]", "", q)
    if len(compact) <= 2:
        return True
    words = q.split()
    return len(words) <= 2 and all(len(w) >= 3 and len(set(w)) <= 1 for w in words)


def _meta_message(question: str) -> str | None:
    from llm import coach_agent_general as agent
    q = agent._norm(question)
    if any(token in q for token in (
        "no puedes hacer nada", "no sabes hacer nada", "que puedes hacer", "que sabes hacer",
        "que me puedes decir", "ayuda del asistente", "help",
    )):
        return _CAPABILITIES_MESSAGE
    return None


def _is_domain_candidate(
    question: str,
    *,
    db_path: Path,
    team_id: str,
    history: list[dict[str, Any]] | None = None,
) -> bool:
    from llm import coach_agent_general as agent
    from llm import coach_role_analysis as role_analysis

    q = agent._norm(question)
    if agent._metric_in_text(question) is not None or role_analysis.role_from_text(question) is not None:
        return True
    runtime = agent._core.CoachAgentRuntime(Path(db_path).expanduser().resolve(), str(team_id))
    if agent._player_mentions(runtime, question) or agent._match_mention(runtime, question):
        return True
    if history and agent._followup(question):
        return True
    return any(stem in q for stem in _DOMAIN_STEMS)


def _preflight_message(
    question: str,
    *,
    db_path: Path,
    team_id: str,
    history: list[dict[str, Any]] | None = None,
) -> str | None:
    meta = _meta_message(question)
    if meta:
        return meta
    if _looks_like_gibberish(question):
        return _CLARIFY_MESSAGE
    if not _is_domain_candidate(question, db_path=db_path, team_id=team_id, history=history):
        from llm import coach_agent_general as agent
        return agent._base.UNSUPPORTED_MESSAGE
    return None


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
    from llm.coach_agent_general import run_coach_agent_turn as _run

    raw_question = str(args[0]) if args else str(kwargs.get("question") or "")
    repaired_question = _repair_console_text(raw_question)
    repaired_history = _repair_history(kwargs.get("history"))
    selected_model = str(kwargs.get("model") or DEFAULT_MODEL)

    if kwargs.get("db_path") is not None and kwargs.get("team_id") is not None:
        role_result = _try_role_pre_route(
            repaired_question,
            db_path=kwargs["db_path"],
            team_id=str(kwargs["team_id"]),
            history=repaired_history,
        )
        if role_result is not None:
            return CoachAgentResult(
                str(role_result["text"]), selected_model, 0,
                (str(role_result.get("tool") or "compare_role_players"),), None,
            )
        preflight = _preflight_message(
            repaired_question,
            db_path=kwargs["db_path"],
            team_id=str(kwargs["team_id"]),
            history=repaired_history,
        )
        if preflight:
            return CoachAgentResult(preflight, selected_model, 0, (), None)

    prepared_args, prepared_kwargs, blocked = _prepare_call(args, kwargs)
    if blocked:
        return CoachAgentResult(blocked, str(prepared_kwargs.get("model") or DEFAULT_MODEL), 0, (), None)
    return _run(*prepared_args, **prepared_kwargs)


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    return run_coach_agent_turn(*args, **kwargs).text
