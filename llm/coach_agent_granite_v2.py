"""Structured-intent Granite runtime for the Spanish Coach Copilot MVP.

Granite interprets natural-language questions into a small validated JSON plan.
Python validates and executes bounded read-only tools. Football metrics and expert
outputs remain outside the LLM. A second compact Granite call may verbalize the
structured evidence, protected by the existing numeric guard.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from llm import coach_agent as _core
from llm import coach_agent_granite as _base

DEFAULT_MODEL = os.environ.get("FPS_LOCAL_LLM_MODEL", "granite4.2:3b")
DEFAULT_OLLAMA_URL = _core.DEFAULT_OLLAMA_URL
CoachAgentResult = _core.CoachAgentResult
ollama_status = _core.ollama_status

_ALLOWED_TOOLS = {
    "query_team_stats",
    "get_team_snapshot",
    "get_player_profile",
    "get_player_gps",
    "get_match_detail",
    "get_data_quality",
    "compare_players",
}

INTENT_PROMPT = """Eres un router de consultas para un asistente de fútbol. Devuelve SOLO JSON válido.
Formato: {"calls":[{"tool":"NOMBRE","args":{...}}]}.
Herramientas permitidas:
- query_team_stats: ranking observado del equipo. args: metric=goals|assists|shots|minutes|appearances, limit opcional.
- get_team_snapshot: estado/forma/tendencia reciente del equipo. args={}.
- get_player_profile: perfil, rendimiento o evolución de un jugador. args={"player":"texto del jugador"}.
- get_player_gps: datos físicos/GPS descriptivos de un jugador. args={"player":"texto del jugador"}.
- get_match_detail: datos de un partido o rival concreto. args={"match":"texto del rival/partido"}.
- get_data_quality: cobertura, limitaciones o calidad de datos. args={}.
- compare_players: comparación descriptiva de jugadores. args={"players":["jugador1","jugador2"]}.
Si la pregunta no puede responderse con estas herramientas, devuelve {"calls":[]}.
No respondas la pregunta. No inventes nombres ni datos.
Ejemplos:
"¿Quién es el máximo goleador?" -> {"calls":[{"tool":"query_team_stats","args":{"metric":"goals","limit":5}}]}
"¿Quién lleva más asistencias?" -> {"calls":[{"tool":"query_team_stats","args":{"metric":"assists","limit":5}}]}
"¿Cómo ha evolucionado Jugador 07?" -> {"calls":[{"tool":"get_player_profile","args":{"player":"Jugador 07"}}]}
"Enséñame el GPS de Jugador 07" -> {"calls":[{"tool":"get_player_gps","args":{"player":"Jugador 07"}}]}
"¿Qué pasó contra Rival 09?" -> {"calls":[{"tool":"get_match_detail","args":{"match":"Rival 09"}}]}
"¿Qué limitaciones de datos tenemos?" -> {"calls":[{"tool":"get_data_quality","args":{}}]}
"Resume el estado reciente del equipo" -> {"calls":[{"tool":"get_team_snapshot","args":{}}]}
"Explícame la teoría de juegos" -> {"calls":[]}.
"""

SYNTHESIS_PROMPT = """Responde a un entrenador en castellano usando EXCLUSIVAMENTE la evidencia JSON.
Sé breve: máximo 4 frases. No inventes números, causas, umbrales ni recomendaciones.
No recalcules métricas. Si falta evidencia, indícalo. No hables de ti mismo como IA.
"""


def _request_json_plan(
    model: str,
    question: str,
    *,
    history: list[dict[str, str]] | None,
    base_url: str,
) -> dict[str, Any]:
    context_parts: list[str] = []
    for item in (history or [])[-3:]:
        role = str(item.get("role") or "")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            context_parts.append(f"{role}: {content[:260]}")
    context = "\n".join(context_parts)
    user_text = f"CONTEXTO PREVIO:\n{context}\n\nPREGUNTA ACTUAL:\n{question[:500]}" if context else question[:500]
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": INTENT_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "stream": False,
        "think": False,
        "format": "json",
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "num_ctx": int(os.environ.get("FPS_AGENT_NUM_CTX", "1536")),
            "num_predict": 120,
        },
    }
    timeout = int(os.environ.get("FPS_AGENT_TIMEOUT", "45"))
    response = _core._request_json(f"{base_url.rstrip('/')}/api/chat", payload=payload, timeout=timeout)
    text = str((response.get("message") or {}).get("content") or "").strip()
    if not text:
        return {"calls": []}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {"calls": []}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {"calls": []}
    return parsed if isinstance(parsed, dict) else {"calls": []}


def _metric(value: object) -> str | None:
    raw = _base._norm(value)
    aliases = {
        "goal": "goals", "goals": "goals", "gol": "goals", "goles": "goals",
        "assist": "assists", "assists": "assists", "asistencia": "assists", "asistencias": "assists",
        "shot": "shots", "shots": "shots", "remate": "shots", "remates": "shots",
        "minute": "minutes", "minutes": "minutes", "minuto": "minutes", "minutos": "minutes",
        "appearance": "appearances", "appearances": "appearances", "aparicion": "appearances", "apariciones": "appearances",
    }
    return aliases.get(raw)


def _validated_calls(plan: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    raw_calls = plan.get("calls")
    if not isinstance(raw_calls, list):
        return []
    out: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for item in raw_calls[:3]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("tool") or "").strip()
        if name not in _ALLOWED_TOOLS or name in seen:
            continue
        args = item.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        args = dict(args)
        if name == "query_team_stats":
            metric = _metric(args.get("metric"))
            if metric is None:
                continue
            args["metric"] = metric
            try:
                args["limit"] = max(1, min(int(args.get("limit", 5)), 10))
            except (TypeError, ValueError):
                args["limit"] = 5
        elif name in {"get_player_profile", "get_player_gps"}:
            if not str(args.get("player") or "").strip():
                continue
        elif name == "get_match_detail":
            if not str(args.get("match") or "").strip():
                continue
        elif name == "compare_players":
            players = args.get("players")
            if not isinstance(players, list) or len([p for p in players if str(p).strip()]) < 2:
                continue
            args["players"] = [str(p) for p in players if str(p).strip()][:6]
        else:
            args = {}
        seen.add(name)
        out.append((name, args))
    return out


def _pick(row: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    return {key: row.get(key) for key in keys if row.get(key) is not None}


def _compact_evidence(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if name == "query_team_stats":
        metric = str(payload.get("metric") or "")
        rows = []
        for row in (payload.get("rows") or [])[:5]:
            rows.append(_pick(row, ("player", metric, "minutes", "appearances")))
        return {"metric": metric, "rows": rows, "error": payload.get("error")}

    if name == "get_player_profile":
        summary = _pick(payload.get("summary"), ("player", "appearances", "starts", "minutes", "goals", "assists", "observed_roles"))
        ratings = [
            _pick(row, ("match_date", "opponent", "minutes_played", "primary_role", "position_group", "match_rating_10", "match_rating_confidence"))
            for row in (payload.get("recent_match_ratings") or [])[-4:]
        ]
        return {
            "player": payload.get("player"),
            "summary": summary,
            "recent_match_ratings": ratings,
            "performance_index": _pick(payload.get("latest_performance_index"), ("match_date", "primary_role", "performance_score", "score_evidence_confidence", "score_status")),
            "expert_gate": _pick(payload.get("latest_expert_gate"), ("match_date", "observed_role", "evidence_coverage", "recommendation_gate", "policy_status", "final_status")),
            "error": payload.get("error"),
        }

    if name == "get_player_gps":
        rows = [
            _pick(row, (
                "match_date", "opponent", "minutes_played", "effective_role",
                "total_distance_m", "peak_speed_m_s", "max_acceleration_m_s2",
                "min_acceleration_m_s2", "distance_coverage_pct", "speed_coverage_pct",
            ))
            for row in (payload.get("gps_history") or [])[-3:]
        ]
        return {
            "player": payload.get("player"),
            "gps_history": rows,
            "interpretation": payload.get("interpretation"),
            "error": payload.get("error"),
        }

    if name == "get_match_detail":
        match = _pick(payload.get("match"), ("match_id", "match_date", "venue", "opponent", "score_for", "score_against", "starting_formation"))
        ratings = []
        for row in (payload.get("ratings") or [])[:15]:
            ratings.append(_pick(row, ("player", "minutes_played", "primary_role", "position_group", "match_rating_10", "match_rating_confidence")))
        ratings.sort(key=lambda row: float(row.get("match_rating_10") or -999), reverse=True)
        return {
            "match": match,
            "top_ratings": ratings[:5],
            "observations": payload.get("observations"),
            "error": payload.get("error"),
        }

    if name == "get_team_snapshot":
        history = [
            _pick(row, ("match_date", "opponent", "score_for", "score_against", "median_match_rating", "median_confidence"))
            for row in (payload.get("recent_team_rating_history") or [])[-3:]
        ]
        form = [
            _pick(row, ("player", "latest_position_group", "latest_match_rating", "avg_last5", "avg_previous5", "trend_delta_5v5", "n_last5", "n_previous5"))
            for row in (payload.get("player_recent_form") or [])[:4]
        ]
        return {"overview": payload.get("overview"), "recent_team": history, "player_recent_form": form}

    if name == "get_data_quality":
        return {
            "attention_summary": (payload.get("attention_summary") or [])[:5],
            "gps_status": payload.get("gps_status"),
            "policy": payload.get("policy"),
            "attention_error": payload.get("attention_error"),
        }

    if name == "compare_players":
        players = []
        for row in (payload.get("players") or [])[:6]:
            players.append(_pick(row, ("player", "latest_position_group", "rated_matches", "latest_match_rating", "avg_last5", "trend_delta_5v5", "n_last5")))
        return {"players": players, "unresolved": payload.get("unresolved"), "comparison_policy": payload.get("comparison_policy")}

    return _base._compact(name, payload)


def _synthesize(
    model: str,
    question: str,
    evidence: dict[str, Any],
    *,
    base_url: str,
) -> str:
    evidence_text = json.dumps(evidence, ensure_ascii=False, default=str, separators=(",", ":"))[:3600]
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYNTHESIS_PROMPT},
            {"role": "user", "content": f"PREGUNTA:\n{question[:450]}\n\nEVIDENCIA:\n{evidence_text}"},
        ],
        "stream": False,
        "think": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "num_ctx": int(os.environ.get("FPS_AGENT_NUM_CTX", "1536")),
            "num_predict": 120,
        },
    }
    timeout = int(os.environ.get("FPS_AGENT_TIMEOUT", "45"))
    response = _core._request_json(f"{base_url.rstrip('/')}/api/chat", payload=payload, timeout=timeout)
    return str((response.get("message") or {}).get("content") or "").strip()


def run_coach_agent_turn(
    question: str,
    *,
    db_path: Path,
    team_id: str,
    history: list[dict[str, str]] | None = None,
    model: str | None = None,
    base_url: str | None = None,
    max_tool_rounds: int | None = None,
) -> CoachAgentResult:
    selected_model = model or DEFAULT_MODEL
    selected_url = (base_url or DEFAULT_OLLAMA_URL).rstrip("/")
    runtime = _core.CoachAgentRuntime(Path(db_path).expanduser().resolve(), str(team_id))

    blocked = _base._guardrail(question)
    if blocked:
        return CoachAgentResult(blocked, selected_model, 0, (), None)

    status = ollama_status(selected_url)
    if not status.get("available"):
        return CoachAgentResult("Ollama no está disponible localmente.", selected_model, 0, (), status.get("error"))
    if selected_model not in (status.get("models") or []):
        return CoachAgentResult(f"El modelo local `{selected_model}` no está instalado.", selected_model, 0, (), "MODEL_NOT_INSTALLED")

    try:
        plan = _request_json_plan(selected_model, question, history=history, base_url=selected_url)
    except Exception as exc:
        return CoachAgentResult(_base.UNSUPPORTED_MESSAGE, selected_model, 0, (), f"INTENT_SELECTION:{type(exc).__name__}: {exc}")

    calls = _validated_calls(plan)
    if not calls:
        return CoachAgentResult(_base.UNSUPPORTED_MESSAGE, selected_model, 0, (), None)

    evidence: dict[str, Any] = {}
    tools_used: list[str] = []
    for name, args in calls:
        payload = _base._execute_tool(runtime, name, args)
        evidence[name] = _compact_evidence(name, payload)
        tools_used.append(name)

    try:
        raw = _synthesize(selected_model, question, evidence, base_url=selected_url)
        text = _base._numeric_guard(raw, evidence)
        if not text:
            text = _base._fallback(evidence)
        return CoachAgentResult(text, selected_model, 1, tuple(tools_used), None)
    except Exception as exc:
        return CoachAgentResult(
            _base._fallback(evidence),
            selected_model,
            1,
            tuple(tools_used),
            f"SYNTHESIS_FALLBACK:{type(exc).__name__}: {exc}",
        )


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    return run_coach_agent_turn(*args, **kwargs).text
