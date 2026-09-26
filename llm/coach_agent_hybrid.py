"""Low-latency local Coach Copilot: deterministic tool routing + Ollama synthesis.

Why hybrid:
- analytics/tool selection stays local, auditable and read-only;
- only the compact evidence needed for the question is sent to Ollama localhost;
- the LLM explains materialized outputs but never calculates critical metrics;
- avoids the large all-tools prompt that was too slow on the target PC.
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

SYSTEM_PROMPT = """You are Coach Copilot, a local assistant for football staff.
Use ONLY the EVIDENCE supplied below. Never invent values, metrics, thresholds, causes or model outputs.
Match Rating, Performance Index, features and expert-system outputs are already calculated outside the LLM: do not recalculate them.
Descriptive comparisons are allowed only from materialized fields and must preserve role/sample-size limitations.
Do not recommend an ideal XI, starters, tactical changes, injury risk, fatigue or readiness unless the evidence explicitly contains a validated authorization.
If evidence is insufficient, state exactly what is missing. Answer in the user's language, concisely and without hidden reasoning.
"""

UNSUPPORTED_PATTERNS = (
    "qui hauria de ser titular",
    "qui ha de ser titular",
    "alineacio ideal",
    "alineació ideal",
    "onze ideal",
    "millor onze",
    "risc de lesio",
    "risc de lesió",
    "injury risk",
    "fatiga",
    "readiness",
    "qui hauria de jugar",
)


def _norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().strip().split())


def _history_text(history: list[dict[str, str]] | None) -> str:
    parts: list[str] = []
    for item in (history or [])[-4:]:
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            parts.append(content[:700])
    return " ".join(parts)


def _find_players(db_path: Path, team_id: str, text: str) -> list[str]:
    squad = get_squad_summary(db_path, team_id)
    if squad.empty:
        return []
    target = _norm(text)
    names = squad["player"].dropna().astype(str).tolist()
    found: list[str] = []

    # Full names first.
    for name in sorted(names, key=len, reverse=True):
        if _norm(name) and _norm(name) in target:
            found.append(name)

    # Then unique surname/meaningful token aliases for natural follow-ups.
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


def _bounded(value: Any, *, depth: int = 0) -> Any:
    if depth >= 4:
        return str(value)[:500]
    if isinstance(value, dict):
        items = list(value.items())[:30]
        return {str(k): _bounded(v, depth=depth + 1) for k, v in items}
    if isinstance(value, list):
        return [_bounded(v, depth=depth + 1) for v in value[:12]]
    if isinstance(value, tuple):
        return [_bounded(v, depth=depth + 1) for v in value[:12]]
    return value


def _compact_payload(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if name == "get_team_snapshot":
        players = payload.get("player_recent_form") or []
        wanted = {
            "player", "player_id", "position", "role", "latest_match_rating",
            "avg_last5", "avg_previous5", "trend_delta_5v5", "n_last5",
            "n_previous5", "latest_confidence", "appearances",
        }
        compact_players = [
            {k: v for k, v in row.items() if k in wanted}
            for row in players[:14]
            if isinstance(row, dict)
        ]
        return {
            "overview": payload.get("overview"),
            "match_rating_version": payload.get("match_rating_version"),
            "recent_team_rating_history": (payload.get("recent_team_rating_history") or [])[-8:],
            "player_recent_form": compact_players,
            "definition": payload.get("definition"),
        }
    if name == "get_player_profile":
        out = dict(payload)
        if isinstance(out.get("recent_match_ratings"), list):
            out["recent_match_ratings"] = out["recent_match_ratings"][-8:]
        return _bounded(out)
    if name == "get_player_match_stats":
        out = dict(payload)
        if isinstance(out.get("rows"), list):
            out["rows"] = [_bounded(row) for row in out["rows"][:8]]
        return out
    if name == "get_match_detail":
        out = dict(payload)
        if isinstance(out.get("ratings"), list):
            wanted = {"player", "player_id", "role", "position", "minutes", "match_rating", "rating", "confidence", "route", "rating_route"}
            out["ratings"] = [
                {k: v for k, v in row.items() if k in wanted} or _bounded(row)
                for row in out["ratings"][:20]
                if isinstance(row, dict)
            ]
        return _bounded(out)
    return _bounded(payload)


def _plan_tools(question: str, *, db_path: Path, team_id: str, history: list[dict[str, str]] | None) -> tuple[list[tuple[str, dict[str, Any]]], str | None]:
    combined = f"{_history_text(history)} {question}".strip()
    q = _norm(question)
    all_text = _norm(combined)

    if any(_norm(pattern) in q for pattern in UNSUPPORTED_PATTERNS):
        return [], "No puc donar aquesta recomanació perquè el sistema no té una política validada per convertir aquestes dades en una decisió d'alineació, tàctica, fatiga o risc de lesió. Puc descriure l'evidència disponible sense convertir-la en una recomanació no validada."

    players = _find_players(db_path, team_id, combined)
    plan: list[tuple[str, dict[str, Any]]] = []

    compare_terms = ("compara", "comparar", "diferencies", "diferències", "versus", " vs ")
    if len(players) >= 2 and any(term in q for term in compare_terms):
        plan.append(("compare_players", {"players": players[:6]}))

    gps_terms = ("gps", "fisic", "físic", "distancia", "distància", "velocitat", "carrega", "càrrega")
    if any(term in q for term in gps_terms):
        if players:
            for player in players[:2]:
                plan.append(("get_player_gps", {"player": player}))
        else:
            plan.append(("get_data_quality", {}))

    match_query = _resolve_match_query(db_path, team_id, combined)
    match_terms = ("partit", "match", "contra", "rival", "ultim", "últim", "darrer")
    if match_query and any(term in q for term in match_terms):
        plan.append(("get_match_detail", {"match": match_query}))

    if players and not any(name == "compare_players" for name, _ in plan):
        for player in players[:2]:
            plan.append(("get_player_profile", {"player": player}))
        detail_terms = ("per que", "per què", "evoluc", "canvi", "accions", "estad", "rendiment recent")
        if any(term in q for term in detail_terms):
            plan.append(("get_player_match_stats", {"player": players[0], "last_n": 8}))

    quality_terms = ("limitacions", "qualitat", "missing", "dades falten", "disponible", "evidencia", "evidència")
    if any(term in q for term in quality_terms) and not any(name == "get_data_quality" for name, _ in plan):
        plan.append(("get_data_quality", {}))

    team_terms = ("equip", "forma", "millorant", "empitjorant", "canvi recent", "tendencia", "tendència", "qui presenta")
    if any(term in q for term in team_terms) and not players:
        plan.append(("get_team_snapshot", {}))

    if not plan:
        # Open-question fallback: provide a compact team snapshot instead of guessing.
        plan.append(("get_team_snapshot", {}))

    # Remove exact duplicates and keep latency bounded.
    deduped: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for name, args in plan:
        key = name + json.dumps(args, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            deduped.append((name, args))
    return deduped[:4], None


def _synthesize(question: str, evidence: dict[str, Any], *, history: list[dict[str, str]] | None, model: str, base_url: str) -> str:
    evidence_text = json.dumps(evidence, ensure_ascii=False, separators=(",", ":"), default=str)
    if len(evidence_text) > 12000:
        evidence_text = evidence_text[:12000] + "\n[TRUNCATED: ask a narrower follow-up if more detail is needed]"

    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in (history or [])[-2:]:
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content[:600]})
    messages.append({
        "role": "user",
        "content": f"QUESTION:\n{question}\n\nEVIDENCE:\n{evidence_text}",
    })
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.1,
            "num_ctx": int(os.environ.get("FPS_AGENT_NUM_CTX", "4096")),
            "num_predict": int(os.environ.get("FPS_AGENT_NUM_PREDICT", "256")),
        },
    }
    timeout = int(os.environ.get("FPS_AGENT_TIMEOUT", "60"))
    response = _core._request_json(f"{base_url.rstrip('/')}/api/chat", payload=payload, timeout=timeout)
    message = response.get("message") or {}
    text = str(message.get("content") or "").strip()
    return text or "No he pogut generar una resposta fiable amb l'evidència disponible."


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
        text = _synthesize(
            question,
            evidence,
            history=history,
            model=selected_model,
            base_url=selected_url,
        )
    except Exception as exc:
        return CoachAgentResult(
            "No he pogut completar la síntesi local dins del temps límit. Les dades no s'han enviat fora del PC.",
            selected_model,
            1 if tools_used else 0,
            tuple(tools_used),
            f"{type(exc).__name__}: {exc}",
        )

    return CoachAgentResult(text, selected_model, 1 if tools_used else 0, tuple(tools_used), None)


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    return run_coach_agent_turn(*args, **kwargs).text
