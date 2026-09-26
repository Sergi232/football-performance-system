"""Low-latency local Coach Copilot: deterministic routing + compact Ollama synthesis.

Architecture:
QUESTION -> LOCAL ROUTER -> READ-ONLY TOOLS -> COMPACT EVIDENCE -> OLLAMA -> COACH

Critical football analytics are never calculated by the LLM. If local synthesis is
too slow, a deterministic evidence-grounded fallback is returned instead of failing.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

from app.data_access import get_squad_summary, get_team_matches
from llm import coach_agent as _core
from llm.coach_agent_fast import DEFAULT_MODEL, DEFAULT_OLLAMA_URL, ollama_status

CoachAgentResult = _core.CoachAgentResult

SYSTEM_PROMPT = """You are Coach Copilot for football staff.
Answer ONLY from the compact EVIDENCE supplied.
Never invent values, metrics, thresholds, causes or recommendations.
Do not recalculate Match Rating, Performance Index or expert-system outputs.
If evidence is insufficient, say what is missing.
Answer in the user's language in at most 6 short sentences.
"""

UNSUPPORTED_PATTERNS = (
    "qui hauria de ser titular", "qui ha de ser titular", "alineacio ideal",
    "alineació ideal", "onze ideal", "millor onze", "risc de lesio",
    "risc de lesió", "injury risk", "fatiga", "readiness", "qui hauria de jugar",
)


def _norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().strip().split())


def _history_text(history: list[dict[str, str]] | None) -> str:
    parts: list[str] = []
    for item in (history or [])[-2:]:
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            parts.append(content[:350])
    return " ".join(parts)


def _find_players(db_path: Path, team_id: str, text: str) -> list[str]:
    squad = get_squad_summary(db_path, team_id)
    if squad.empty:
        return []
    target = _norm(text)
    names = squad["player"].dropna().astype(str).tolist()
    found: list[str] = []
    for name in sorted(names, key=len, reverse=True):
        if _norm(name) and _norm(name) in target:
            found.append(name)
    token_to_names: dict[str, list[str]] = {}
    for name in names:
        for token in _norm(name).split():
            if len(token) >= 4:
                token_to_names.setdefault(token, []).append(name)
    for token, owners in token_to_names.items():
        if len(owners) == 1 and re.search(rf"\b{re.escape(token)}\b", target):
            if owners[0] not in found:
                found.append(owners[0])
    return found[:6]


def _resolve_match_query(db_path: Path, team_id: str, text: str) -> str | None:
    matches = get_team_matches(db_path, team_id)
    if matches.empty:
        return None
    target = _norm(text)
    if any(token in target for token in ("ultim partit", "darrer partit", "last match")):
        return str(matches.iloc[0]["match_id"])
    for row in matches.head(20).itertuples(index=False):
        opponent = str(getattr(row, "opponent", "") or "")
        if opponent and _norm(opponent) in target:
            return str(getattr(row, "match_id"))
    return None


def _scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _pick_scalars(mapping: Any, limit: int = 10) -> dict[str, Any]:
    if not isinstance(mapping, dict):
        return {}
    out: dict[str, Any] = {}
    for key, value in mapping.items():
        if _scalar(value):
            out[str(key)] = value
            if len(out) >= limit:
                break
    return out


def _pick_row(row: Any, preferred: tuple[str, ...], fallback_limit: int = 8) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    selected = {k: row.get(k) for k in preferred if k in row and _scalar(row.get(k))}
    if selected:
        return selected
    return _pick_scalars(row, fallback_limit)


def _compact_payload(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if name == "get_team_snapshot":
        players = payload.get("player_recent_form") or []
        player_keys = (
            "player", "position", "role", "latest_match_rating", "avg_last5",
            "avg_previous5", "trend_delta_5v5", "n_last5", "n_previous5",
            "latest_confidence", "appearances",
        )
        history_keys = (
            "match_date", "opponent", "score_for", "score_against", "result",
            "team_avg_rating", "avg_match_rating", "rated_players",
        )
        return {
            "overview": _pick_scalars(payload.get("overview"), 10),
            "match_rating_version": payload.get("match_rating_version"),
            "recent_team_rating_history": [
                _pick_row(r, history_keys) for r in (payload.get("recent_team_rating_history") or [])[-4:]
            ],
            "player_recent_form": [_pick_row(r, player_keys) for r in players[:6]],
            "definition": payload.get("definition"),
        }
    if name == "get_data_quality":
        summary = payload.get("attention_summary") or []
        flags = payload.get("recent_flags") or []
        return {
            "attention_summary": [_pick_scalars(r, 8) for r in summary[:6] if isinstance(r, dict)],
            "recent_flags": [_pick_scalars(r, 6) for r in flags[:5] if isinstance(r, dict)],
            "attention_error": payload.get("attention_error"),
            "gps_status": _pick_scalars(payload.get("gps_status"), 8),
            "policy": payload.get("policy"),
        }
    if name == "get_player_profile":
        ratings = payload.get("recent_match_ratings") or []
        rating_keys = (
            "match_date", "opponent", "minutes", "role", "position",
            "match_rating", "rating", "confidence", "route", "rating_route",
        )
        return {
            "player": payload.get("player"),
            "summary": _pick_scalars(payload.get("summary"), 12),
            "recent_match_ratings": [_pick_row(r, rating_keys) for r in ratings[-5:]],
            "latest_performance_index": _pick_scalars(payload.get("latest_performance_index"), 10),
            "latest_expert_gate": _pick_scalars(payload.get("latest_expert_gate"), 10),
        }
    if name == "get_player_match_stats":
        rows = payload.get("rows") or []
        return {
            "player": payload.get("player"),
            "rows": [_pick_scalars(r, 12) for r in rows[:5] if isinstance(r, dict)],
            "note": payload.get("note"),
        }
    if name == "get_match_detail":
        ratings = payload.get("ratings") or []
        rating_keys = (
            "player", "role", "position", "minutes", "match_rating", "rating",
            "confidence", "route", "rating_route",
        )
        return {
            "match": _pick_scalars(payload.get("match"), 10),
            "ratings": [_pick_row(r, rating_keys) for r in ratings[:12]],
            "observations": payload.get("observations") if isinstance(payload.get("observations"), (str, int, float, bool, type(None))) else str(payload.get("observations"))[:800],
            "note": payload.get("note"),
        }
    if name == "compare_players":
        return {
            "players": [_pick_scalars(r, 12) for r in (payload.get("players") or [])[:6] if isinstance(r, dict)],
            "unresolved": (payload.get("unresolved") or [])[:6],
            "comparison_policy": payload.get("comparison_policy"),
        }
    if name == "get_player_gps":
        return {
            "player": payload.get("player"),
            "gps_history": [_pick_scalars(r, 10) for r in (payload.get("gps_history") or [])[-5:] if isinstance(r, dict)],
            "interpretation": payload.get("interpretation"),
            "error": payload.get("error"),
        }
    return _pick_scalars(payload, 12)


def _plan_tools(question: str, *, db_path: Path, team_id: str, history: list[dict[str, str]] | None) -> tuple[list[tuple[str, dict[str, Any]]], str | None]:
    combined = f"{_history_text(history)} {question}".strip()
    q = _norm(question)

    if any(_norm(pattern) in q for pattern in UNSUPPORTED_PATTERNS):
        return [], "No puc donar aquesta recomanació perquè el sistema no té una política validada per convertir aquestes dades en una decisió d'alineació, tàctica, fatiga o risc de lesió. Puc descriure l'evidència disponible sense convertir-la en una recomanació no validada."

    players = _find_players(db_path, team_id, combined)
    plan: list[tuple[str, dict[str, Any]]] = []

    if len(players) >= 2 and any(term in q for term in ("compara", "comparar", "diferencies", "diferències", "versus", " vs ")):
        plan.append(("compare_players", {"players": players[:6]}))

    if any(term in q for term in ("gps", "fisic", "físic", "distancia", "distància", "velocitat", "carrega", "càrrega")):
        if players:
            plan.append(("get_player_gps", {"player": players[0]}))
        else:
            plan.append(("get_data_quality", {}))

    match_query = _resolve_match_query(db_path, team_id, combined)
    if match_query and any(term in q for term in ("partit", "match", "contra", "rival", "ultim", "últim", "darrer")):
        plan.append(("get_match_detail", {"match": match_query}))

    if players and not any(name == "compare_players" for name, _ in plan):
        plan.append(("get_player_profile", {"player": players[0]}))
        if any(term in q for term in ("per que", "per què", "evoluc", "canvi", "accions", "estad", "rendiment recent")):
            plan.append(("get_player_match_stats", {"player": players[0], "last_n": 5}))

    if any(term in q for term in ("limitacions", "qualitat", "missing", "dades falten", "disponible", "evidencia", "evidència")):
        if not any(name == "get_data_quality" for name, _ in plan):
            plan.append(("get_data_quality", {}))

    if any(term in q for term in ("equip", "forma", "millorant", "empitjorant", "canvi recent", "tendencia", "tendència", "qui presenta")) and not players:
        plan.append(("get_team_snapshot", {}))

    if not plan:
        plan.append(("get_team_snapshot", {}))

    deduped: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for name, args in plan:
        key = name + json.dumps(args, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            deduped.append((name, args))
    return deduped[:3], None


def _flatten_lines(value: Any, prefix: str = "", depth: int = 0) -> list[str]:
    if depth > 2:
        return []
    lines: list[str] = []
    if isinstance(value, dict):
        for key, val in value.items():
            p = f"{prefix}.{key}" if prefix else str(key)
            if _scalar(val):
                lines.append(f"{p}={val}")
            elif isinstance(val, (dict, list)):
                lines.extend(_flatten_lines(val, p, depth + 1))
    elif isinstance(value, list):
        for idx, item in enumerate(value[:6]):
            lines.extend(_flatten_lines(item, f"{prefix}[{idx}]", depth + 1))
    return lines


def _deterministic_fallback(question: str, evidence: dict[str, Any], tools_used: list[str]) -> str:
    lines = _flatten_lines(evidence)
    useful = [line for line in lines if not line.endswith("=None")][:12]
    if not useful:
        return "No hi ha prou evidència estructurada disponible per respondre aquesta pregunta."
    body = "\n".join(f"- {line}" for line in useful)
    return (
        "Síntesi local no disponible dins del límit de temps. Dades estructurades disponibles:\n"
        f"{body}\n"
        f"Evidència consultada: {', '.join(tools_used)}."
    )


def _synthesize(question: str, evidence: dict[str, Any], *, history: list[dict[str, str]] | None, model: str, base_url: str) -> str:
    lines = _flatten_lines(evidence)
    max_lines = max(8, int(os.environ.get("FPS_AGENT_EVIDENCE_LINES", "28")))
    max_chars = max(800, int(os.environ.get("FPS_AGENT_EVIDENCE_CHARS", "2800")))
    evidence_text = "\n".join(lines[:max_lines])[:max_chars]

    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        last = history[-1]
        if last.get("role") in {"user", "assistant"} and last.get("content"):
            messages.append({"role": str(last["role"]), "content": str(last["content"])[:200]})
    messages.append({"role": "user", "content": f"QUESTION:\n{question[:400]}\n\nEVIDENCE:\n{evidence_text}"})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.1,
            "num_ctx": int(os.environ.get("FPS_AGENT_NUM_CTX", "1536")),
            "num_predict": int(os.environ.get("FPS_AGENT_NUM_PREDICT", "128")),
        },
    }
    timeout = int(os.environ.get("FPS_AGENT_TIMEOUT", "18"))
    response = _core._request_json(f"{base_url.rstrip('/')}/api/chat", payload=payload, timeout=timeout)
    message = response.get("message") or {}
    text = str(message.get("content") or "").strip()
    return text or "No hi ha prou evidència per generar una resposta fiable."


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

    status = ollama_status(selected_url)
    if not status.get("available"):
        return CoachAgentResult("Ollama no està disponible localment.", selected_model, 0, (), status.get("error"))
    if selected_model not in (status.get("models") or []):
        return CoachAgentResult(f"El model local `{selected_model}` no està instal·lat.", selected_model, 0, (), "MODEL_NOT_INSTALLED")

    plan, guardrail = _plan_tools(question, db_path=runtime.db_path, team_id=runtime.team_id, history=history)
    if guardrail:
        return CoachAgentResult(guardrail, selected_model, 0, (), None)

    evidence: dict[str, Any] = {}
    tools_used: list[str] = []
    for name, args in plan:
        fn = _core.TOOL_FUNCTIONS.get(name)
        if fn is None:
            continue
        try:
            payload = fn(runtime, args)
        except Exception as exc:
            payload = {"error": f"{type(exc).__name__}: {exc}"}
        evidence[name] = _compact_payload(name, payload)
        tools_used.append(name)

    try:
        text = _synthesize(question, evidence, history=history, model=selected_model, base_url=selected_url)
        return CoachAgentResult(text, selected_model, 1 if tools_used else 0, tuple(tools_used), None)
    except Exception as exc:
        fallback = _deterministic_fallback(question, evidence, tools_used)
        return CoachAgentResult(
            fallback,
            selected_model,
            1 if tools_used else 0,
            tuple(tools_used),
            f"SYNTHESIS_FALLBACK:{type(exc).__name__}: {exc}",
        )


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    return run_coach_agent_turn(*args, **kwargs).text
