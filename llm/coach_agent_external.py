"""Optional external-LLM Coach Copilot using the user's own OpenAI API key.

Architecture:
question -> deterministic high-confidence router when possible -> OpenAI semantic
router only when needed -> bounded read-only FPS tools -> structured evidence ->
OpenAI synthesis for semantic cases -> numeric grounding guard -> coach.

The OpenAI model never receives direct DuckDB access and never calculates football
metrics. Clear supported questions stay deterministic, so external API usage is
reserved for genuinely ambiguous language.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from llm import coach_agent_fast as _fast
from llm import coach_agent_general as _agent
from llm import coach_agent_granite as _grounding
from llm import coach_role_analysis as _role_analysis

DEFAULT_OPENAI_MODEL = os.environ.get("FPS_OPENAI_MODEL", "gpt-5.6-luna")
DEFAULT_OPENAI_TIMEOUT = float(os.environ.get("FPS_OPENAI_TIMEOUT", "45"))

CoachAgentResult = _agent.CoachAgentResult


OPENAI_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "rank_players",
        "description": "Rank players using one approved FPS metric calculated by Python/DuckDB.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "enum": list(_agent.METRICS)},
                "aggregation": {"type": "string", "enum": ["sum", "mean", "max", "min", "latest"]},
                "last_n_matches": {"type": "integer", "minimum": 1, "maximum": 50},
                "role": {"type": "string"},
                "min_minutes": {"type": "number", "minimum": 0},
                "order": {"type": "string", "enum": ["asc", "desc"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["metric"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_team_snapshot",
        "description": "Get the structured team overview and recent descriptive trends.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "get_player_profile",
        "description": "Get a player's structured profile, participation and materialized analytics.",
        "parameters": {
            "type": "object",
            "properties": {"player": {"type": "string"}},
            "required": ["player"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_player_match_stats",
        "description": "Get recent observed player-match statistics for one player.",
        "parameters": {
            "type": "object",
            "properties": {
                "player": {"type": "string"},
                "last_n": {"type": "integer", "minimum": 1, "maximum": 30},
            },
            "required": ["player"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_player_gps",
        "description": "Get descriptive normalized GPS data for one player. Do not infer fatigue or injury risk.",
        "parameters": {
            "type": "object",
            "properties": {"player": {"type": "string"}},
            "required": ["player"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_match_detail",
        "description": "Get observed data and materialized ratings for a match or opponent.",
        "parameters": {
            "type": "object",
            "properties": {"match": {"type": "string"}},
            "required": ["match"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_data_quality",
        "description": "Get data coverage, quality limitations and GPS status.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "compare_players",
        "description": "Compare two or more players descriptively using already materialized FPS fields.",
        "parameters": {
            "type": "object",
            "properties": {
                "players": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 6,
                }
            },
            "required": ["players"],
            "additionalProperties": False,
        },
    },
]


ROUTER_INSTRUCTIONS = """Eres el router semántico del Football Performance System.
Tu única función en esta llamada es decidir qué herramientas de SOLO LECTURA hacen falta para responder la pregunta del entrenador.
Usa únicamente las herramientas disponibles. No respondas la pregunta directamente y no inventes nombres, métricas, filtros, resultados ni recomendaciones.
No infieras fatiga, readiness, riesgo de lesión, XI ideal, jugador 'más completo', jugador 'más determinante' ni recomendaciones tácticas si no existe una salida validada que lo autorice.
Si ninguna herramienta disponible puede responder de forma fundamentada, no llames ninguna herramienta.
"""

SYNTHESIS_INSTRUCTIONS = """Responde como asistente de un cuerpo técnico de fútbol usando EXCLUSIVAMENTE la EVIDENCIA JSON proporcionada por Football Performance System.
No inventes números, causas, métricas, umbrales, posiciones, recomendaciones ni hechos que no estén en la evidencia.
Match Rating, Performance Index, rankings y demás cálculos ya vienen calculados por Python/DuckDB: no los recalcules.
Si falta información para una parte de la pregunta, indícalo de forma explícita.
No conviertas GPS descriptivo en fatiga, readiness o riesgo de lesión.
No recomiendes XI ideal ni táctica automática sin una policy validada.
Responde en el idioma de la pregunta, de forma breve y útil, con un máximo de 6 frases.
"""


def _client(api_key: str) -> OpenAI:
    key = str(api_key or "").strip()
    if not key:
        raise ValueError("OPENAI_API_KEY_MISSING")
    return OpenAI(api_key=key, timeout=DEFAULT_OPENAI_TIMEOUT)


def _history_input(history: list[dict[str, Any]] | None, question: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for item in (history or [])[-6:]:
        role = str(item.get("role") or "")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            items.append({"role": role, "content": content[:800]})
    items.append({"role": "user", "content": str(question)[:800]})
    return items


def _response_calls(response: Any) -> list[tuple[str, dict[str, Any]]]:
    plan_items: list[dict[str, Any]] = []
    for item in getattr(response, "output", []) or []:
        item_type = getattr(item, "type", None)
        if item_type is None and isinstance(item, dict):
            item_type = item.get("type")
        if item_type != "function_call":
            continue
        name = getattr(item, "name", None)
        arguments = getattr(item, "arguments", None)
        if isinstance(item, dict):
            name = name or item.get("name")
            arguments = arguments if arguments is not None else item.get("arguments")
        try:
            args = json.loads(arguments or "{}") if isinstance(arguments, str) else dict(arguments or {})
        except Exception:
            args = {}
        plan_items.append({"tool": str(name or ""), "args": args})
    return _agent._validated({"calls": plan_items})


def _openai_route(
    *,
    api_key: str,
    model: str,
    question: str,
    history: list[dict[str, Any]] | None,
) -> list[tuple[str, dict[str, Any]]]:
    response = _client(api_key).responses.create(
        model=model,
        instructions=ROUTER_INSTRUCTIONS,
        input=_history_input(history, question),
        tools=OPENAI_TOOLS,
        tool_choice="auto",
    )
    return _response_calls(response)


def _synthesise(
    *,
    api_key: str,
    model: str,
    question: str,
    evidence: dict[str, Any],
) -> str:
    evidence_text = json.dumps(evidence, ensure_ascii=False, default=str)
    response = _client(api_key).responses.create(
        model=model,
        instructions=SYNTHESIS_INSTRUCTIONS,
        input=(
            f"PREGUNTA:\n{question[:800]}\n\n"
            f"EVIDENCIA JSON:\n{evidence_text[:12000]}"
        ),
    )
    text = str(getattr(response, "output_text", "") or "").strip()
    return _grounding._numeric_guard(text, evidence)


def run_coach_agent_turn(
    question: str,
    *,
    db_path: Path,
    team_id: str,
    api_key: str,
    history: list[dict[str, Any]] | None = None,
    model: str | None = None,
) -> CoachAgentResult:
    selected_model = str(model or DEFAULT_OPENAI_MODEL)

    # The same deterministic role analysis must behave identically in local and
    # external-provider modes. It is a product capability, not an LLM capability.
    repaired_question = _fast._repair_console_text(question)
    repaired_history = _fast._repair_history(history)
    role_result = _role_analysis.try_role_query(
        repaired_question,
        db_path=Path(db_path),
        team_id=str(team_id),
        history=repaired_history,
    )
    if role_result is not None:
        return CoachAgentResult(
            str(role_result["text"]),
            selected_model,
            0,
            (str(role_result.get("tool") or "compare_role_players"),),
            None,
        )

    prepared_args, prepared_kwargs, policy_block = _fast._prepare_call(
        (question,),
        {"history": history, "model": selected_model},
    )
    routed_question = str(prepared_args[0])
    prepared_history = prepared_kwargs.get("history")

    if policy_block:
        return CoachAgentResult(policy_block, selected_model, 0, (), None)

    blocked = _agent._base._guardrail(routed_question)
    if blocked:
        return CoachAgentResult(blocked, selected_model, 0, (), None)

    runtime = _agent._core.CoachAgentRuntime(Path(db_path).expanduser().resolve(), str(team_id))
    previous = _agent._last_user(prepared_history)
    is_follow = bool(previous and _agent._followup(routed_question))
    route_question = previous if is_follow else routed_question

    calls = _agent._deterministic_route(runtime, route_question)
    external_used = False

    if is_follow:
        calls = _agent._modify(calls, routed_question)

    if not calls:
        try:
            semantic_question = routed_question
            if is_follow and previous:
                semantic_question = f"Consulta anterior: {previous}\nSeguimiento: {routed_question}"
            calls = _openai_route(
                api_key=api_key,
                model=selected_model,
                question=semantic_question,
                history=prepared_history,
            )
            external_used = True
        except Exception as exc:
            return CoachAgentResult(
                _agent._base.UNSUPPORTED_MESSAGE,
                selected_model,
                0,
                (),
                f"OPENAI_ROUTER:{type(exc).__name__}: {exc}",
            )

    if not calls:
        return CoachAgentResult(_agent._base.UNSUPPORTED_MESSAGE, selected_model, 1 if external_used else 0, (), None)

    evidence: dict[str, Any] = {}
    tools: list[str] = []
    for name, args in calls:
        payload = _agent._execute(runtime, name, args)
        evidence[name] = (
            _agent._compact_rank(payload)
            if name == "rank_players"
            else _agent._legacy._compact_evidence(name, payload)
        )
        tools.append(name)

    if _agent._is_evidence(routed_question):
        return CoachAgentResult(
            _agent._evidence_answer(evidence), selected_model, 1 if external_used else 0, tuple(tools), None
        )

    idx = _agent._ordinal(routed_question) if is_follow else None
    if idx is not None:
        ordinal = _agent._ordinal_answer(evidence, idx)
        if ordinal:
            return CoachAgentResult(ordinal, selected_model, 1 if external_used else 0, tuple(tools), None)

    # Clear supported questions remain fully deterministic and incur no API cost.
    if not external_used:
        return CoachAgentResult(
            _agent._answer_from_evidence(routed_question, evidence), selected_model, 0, tuple(tools), None
        )

    try:
        text = _synthesise(
            api_key=api_key,
            model=selected_model,
            question=routed_question,
            evidence=evidence,
        )
        if not text:
            text = _agent._answer_from_evidence(routed_question, evidence)
        return CoachAgentResult(text, selected_model, 2, tuple(tools), None)
    except Exception as exc:
        return CoachAgentResult(
            _agent._answer_from_evidence(routed_question, evidence),
            selected_model,
            1,
            tuple(tools),
            f"OPENAI_SYNTHESIS:{type(exc).__name__}: {exc}",
        )


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    return run_coach_agent_turn(*args, **kwargs).text
