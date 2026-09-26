"""Local tool-using Coach Copilot over validated Football Performance System analytics.

Architecture:
DATA -> ANALYTICS -> DECISION ENGINE -> LOCAL TOOLS -> OLLAMA LLM -> COACH

No football metric is calculated by the LLM. The model only decides which read-only
analytics tools to call and explains their materialized outputs. By default every
LLM request goes to Ollama on localhost, so team/player data never leaves the PC.
"""
from __future__ import annotations

import json
import os
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.attention_access import get_attention_summary, get_team_attention_flags
from app.data_access import (
    get_latest_player_gate,
    get_player_match_history,
    get_squad_summary,
    get_team_matches,
    get_team_overview,
)
from app.gps_physical_access import get_gps_summary_status, get_player_gps_history
from app.match_insights import get_match_observations
from app.match_rating_access import (
    MATCH_RATING_VERSION,
    get_match_ratings,
    get_player_match_ratings,
    get_team_match_rating_history,
    get_team_player_rating_snapshot,
)
from app.performance_score_access import get_latest_player_score


DEFAULT_MODEL = os.environ.get("FPS_LOCAL_LLM_MODEL", "qwen3.5:4b")
DEFAULT_OLLAMA_URL = os.environ.get("FPS_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
MAX_TOOL_ROUNDS = int(os.environ.get("FPS_AGENT_MAX_TOOL_ROUNDS", "8"))

SYSTEM_PROMPT = """You are Coach Copilot, a local AI assistant for a football coaching staff.

You receive NO football data in this prompt. For every factual question about the
team, a player, a match, form, roles, GPS, ratings, trends or data quality, you MUST
call one or more tools before answering. You may chain several tools when needed.

NON-NEGOTIABLE RULES
1. Use only values returned by tools. Never invent observations, metrics, thresholds, weights or model outputs.
2. Match Rating, Performance Index, features and expert-system outputs are already calculated outside the LLM. Never recalculate them.
3. You may compare/sort fields already returned by tools, such as latest_match_rating, avg_last5 or trend_delta_5v5. Describe these as descriptive comparisons and mention sample size when available.
4. Never convert correlation or recent change into a causal explanation unless the data explicitly supports it.
5. Do not recommend an ideal XI, who should start, tactical changes, injury risk, fatigue or readiness unless a validated decision-engine output explicitly authorizes that conclusion. The current recommendation policy is NOT validated.
6. When evidence is missing, state exactly what is unavailable. Do not fill gaps.
7. Preserve role/context. Do not present different positions as directly equivalent without stating the limitation.
8. The goalkeeper branch is methodologically different from outfield. Do not interpret missing outfield dimensions for a goalkeeper as missing evidence.
9. Answer in the language used by the user. Be concise and useful to a coach.
10. Do not expose hidden reasoning. You may finish with a short 'Evidència consultada' line naming the tools used.
"""


@dataclass(frozen=True)
class CoachAgentRuntime:
    db_path: Path
    team_id: str


@dataclass(frozen=True)
class CoachAgentResult:
    text: str
    model: str
    tool_rounds: int
    tools_used: tuple[str, ...]
    error: str | None = None


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _records(frame: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if limit is not None:
        frame = frame.head(limit)
    return [{str(k): _clean(v) for k, v in row.items()} for row in frame.to_dict(orient="records")]


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def _norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().strip().split())


def _resolve_player(runtime: CoachAgentRuntime, query: str) -> tuple[str | None, str | None]:
    squad = get_squad_summary(runtime.db_path, runtime.team_id)
    if squad.empty:
        return None, None
    raw = str(query or "").strip()
    exact_id = squad.loc[squad["player_id"].astype(str) == raw]
    if len(exact_id) == 1:
        row = exact_id.iloc[0]
        return str(row["player_id"]), str(row["player"])
    target = _norm(raw)
    exact_name = squad.loc[squad["player"].map(_norm) == target]
    if len(exact_name) == 1:
        row = exact_name.iloc[0]
        return str(row["player_id"]), str(row["player"])
    partial = squad.loc[squad["player"].map(lambda x: target in _norm(x) or _norm(x) in target)] if target else squad.iloc[0:0]
    if len(partial) == 1:
        row = partial.iloc[0]
        return str(row["player_id"]), str(row["player"])
    return None, None


def _resolve_match(runtime: CoachAgentRuntime, query: str) -> tuple[str | None, dict[str, Any] | None]:
    matches = get_team_matches(runtime.db_path, runtime.team_id).copy()
    if matches.empty:
        return None, None
    raw = str(query or "").strip()
    exact_id = matches.loc[matches["match_id"].astype(str) == raw]
    if len(exact_id) == 1:
        row = exact_id.iloc[0]
        return str(row["match_id"]), _records(exact_id, 1)[0]
    target = _norm(raw)
    candidates = matches.loc[matches["opponent"].map(lambda x: target in _norm(x) or _norm(x) in target)] if target else matches.iloc[0:0]
    if len(candidates) >= 1:
        row = candidates.iloc[0]
        return str(row["match_id"]), _records(candidates, 1)[0]
    return None, None


def tool_get_team_snapshot(runtime: CoachAgentRuntime, args: dict[str, Any]) -> dict[str, Any]:
    overview = get_team_overview(runtime.db_path, runtime.team_id)
    history = get_team_match_rating_history(runtime.db_path, runtime.team_id).tail(12)
    trends = get_team_player_rating_snapshot(runtime.db_path, runtime.team_id).copy()
    if not trends.empty:
        for col in ["latest_match_rating", "avg_last5", "avg_previous5", "trend_delta_5v5", "latest_confidence"]:
            if col in trends.columns:
                trends[col] = pd.to_numeric(trends[col], errors="coerce")
        trends = trends.sort_values("trend_delta_5v5", ascending=False, na_position="last")
    return {
        "overview": {k: _clean(v) for k, v in overview.items()},
        "match_rating_version": MATCH_RATING_VERSION,
        "recent_team_rating_history": _records(history),
        "player_recent_form": _records(trends),
        "definition": "trend_delta_5v5 = mean latest five Match Ratings minus mean previous five; descriptive only; inspect n_last5 and n_previous5.",
    }


def tool_get_player_profile(runtime: CoachAgentRuntime, args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("player", ""))
    player_id, player_name = _resolve_player(runtime, query)
    if player_id is None:
        return {"error": f"No s'ha pogut identificar un únic jugador amb: {query!r}. Usa get_team_snapshot per veure els noms disponibles."}
    squad = get_squad_summary(runtime.db_path, runtime.team_id)
    selected = squad.loc[squad["player_id"].astype(str) == player_id]
    ratings = get_player_match_ratings(runtime.db_path, runtime.team_id, player_id)
    gate = get_latest_player_gate(runtime.db_path, runtime.team_id, player_id)
    index = get_latest_player_score(runtime.db_path, runtime.team_id, player_id)
    return {
        "player": player_name,
        "summary": None if selected.empty else _records(selected, 1)[0],
        "recent_match_ratings": _records(ratings.tail(12)),
        "latest_performance_index": None if index is None else {k: _clean(v) for k, v in index.items()},
        "latest_expert_gate": None if gate is None else {k: _clean(v) for k, v in gate.items()},
    }


def tool_get_player_match_stats(runtime: CoachAgentRuntime, args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("player", ""))
    player_id, player_name = _resolve_player(runtime, query)
    if player_id is None:
        return {"error": f"Jugador no identificat: {query!r}"}
    last_n = max(1, min(int(args.get("last_n", 10)), 30))
    frame = get_player_match_history(runtime.db_path, runtime.team_id, player_id).head(last_n)
    return {"player": player_name, "rows": _records(frame), "limit": last_n, "note": "raw observed player-match stats; no new performance score calculated"}


def tool_list_recent_matches(runtime: CoachAgentRuntime, args: dict[str, Any]) -> dict[str, Any]:
    last_n = max(1, min(int(args.get("last_n", 10)), 20))
    frame = get_team_matches(runtime.db_path, runtime.team_id).head(last_n)
    return {"matches": _records(frame)}


def tool_get_match_detail(runtime: CoachAgentRuntime, args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("match", ""))
    match_id, match_row = _resolve_match(runtime, query)
    if match_id is None:
        return {"error": f"Partit no identificat: {query!r}. Usa list_recent_matches si cal."}
    ratings = get_match_ratings(runtime.db_path, runtime.team_id, match_id)
    observations = get_match_observations(runtime.db_path, runtime.team_id, match_id)
    return {
        "match": match_row,
        "ratings": _records(ratings),
        "observations": observations,
        "note": "observations are deterministic; ratings are already materialized analytics",
    }


def tool_get_data_quality(runtime: CoachAgentRuntime, args: dict[str, Any]) -> dict[str, Any]:
    try:
        summary = get_attention_summary(runtime.db_path, runtime.team_id)
        flags = get_team_attention_flags(runtime.db_path, runtime.team_id)
    except Exception as exc:
        summary = pd.DataFrame()
        flags = pd.DataFrame()
        attention_error = f"{type(exc).__name__}: {exc}"
    else:
        attention_error = None
    try:
        gps = get_gps_summary_status(runtime.db_path)
    except Exception as exc:
        gps = {"error": f"{type(exc).__name__}: {exc}"}
    return {
        "attention_summary": _records(summary),
        "recent_flags": _records(flags.head(30)),
        "attention_error": attention_error,
        "gps_status": gps,
        "policy": "data-quality/context flags only; no fatigue, injury-risk or good/bad performance threshold is validated",
    }


def tool_get_player_gps(runtime: CoachAgentRuntime, args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("player", ""))
    player_id, player_name = _resolve_player(runtime, query)
    if player_id is None:
        return {"error": f"Jugador no identificat: {query!r}"}
    try:
        frame = get_player_gps_history(runtime.db_path, runtime.team_id, player_id)
    except Exception as exc:
        return {"player": player_name, "error": f"GPS unavailable: {type(exc).__name__}: {exc}"}
    return {
        "player": player_name,
        "gps_history": _records(frame.tail(12)),
        "interpretation": "descriptive normalized GPS only; no validated fatigue/readiness/injury-risk model",
    }


def tool_compare_players(runtime: CoachAgentRuntime, args: dict[str, Any]) -> dict[str, Any]:
    requested = args.get("players") or []
    if isinstance(requested, str):
        requested = [requested]
    requested = [str(x) for x in requested][:6]
    snapshot = get_team_player_rating_snapshot(runtime.db_path, runtime.team_id)
    rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for query in requested:
        player_id, player_name = _resolve_player(runtime, query)
        if player_id is None:
            unresolved.append(query)
            continue
        selected = snapshot.loc[snapshot["player_id"].astype(str) == player_id]
        if selected.empty:
            rows.append({"player": player_name, "error": "No Match Rating snapshot available"})
        else:
            rows.append(_records(selected, 1)[0])
    return {
        "players": rows,
        "unresolved": unresolved,
        "comparison_policy": "descriptive only; avg_last5/trend_delta_5v5 are materialized fields; preserve position and sample-size limitations",
    }


TOOL_FUNCTIONS = {
    "get_team_snapshot": tool_get_team_snapshot,
    "get_player_profile": tool_get_player_profile,
    "get_player_match_stats": tool_get_player_match_stats,
    "list_recent_matches": tool_list_recent_matches,
    "get_match_detail": tool_get_match_detail,
    "get_data_quality": tool_get_data_quality,
    "get_player_gps": tool_get_player_gps,
    "compare_players": tool_compare_players,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_team_snapshot",
            "description": "Team overview, recent team Match Rating history and per-player recent descriptive form/trend fields.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_player_profile",
            "description": "One player's participation, recent Match Ratings, current Performance Index and expert gate.",
            "parameters": {
                "type": "object",
                "properties": {"player": {"type": "string", "description": "Player name or unique fragment."}},
                "required": ["player"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_player_match_stats",
            "description": "Recent raw observed player-match stats. Use when the question asks what changed in underlying actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "player": {"type": "string"},
                    "last_n": {"type": "integer", "minimum": 1, "maximum": 30},
                },
                "required": ["player"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_recent_matches",
            "description": "Recent matches and opponents. Use to resolve references such as 'last match' or an opponent.",
            "parameters": {
                "type": "object",
                "properties": {"last_n": {"type": "integer", "minimum": 1, "maximum": 20}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_match_detail",
            "description": "One match's materialized player ratings and deterministic post-match observations.",
            "parameters": {
                "type": "object",
                "properties": {"match": {"type": "string", "description": "Match ID, opponent name or unique opponent fragment."}},
                "required": ["match"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_quality",
            "description": "Auditable context/data-evidence limitations and GPS availability.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_player_gps",
            "description": "Normalized descriptive GPS history for a player. Never infer fatigue/readiness/injury risk.",
            "parameters": {
                "type": "object",
                "properties": {"player": {"type": "string"}},
                "required": ["player"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_players",
            "description": "Descriptively compare up to six players using already materialized Match Rating snapshot/form fields.",
            "parameters": {
                "type": "object",
                "properties": {
                    "players": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 6}
                },
                "required": ["players"],
            },
        },
    },
]


def _request_json(url: str, *, payload: dict[str, Any] | None = None, timeout: int = 180) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"No es pot connectar amb Ollama a {url}: {exc}") from exc


def ollama_status(base_url: str | None = None) -> dict[str, Any]:
    base = (base_url or DEFAULT_OLLAMA_URL).rstrip("/")
    try:
        payload = _request_json(f"{base}/api/tags", timeout=5)
    except Exception as exc:
        return {"available": False, "url": base, "models": [], "error": str(exc)}
    models = []
    for item in payload.get("models", []) or []:
        name = item.get("name") or item.get("model")
        if name:
            models.append(str(name))
    return {"available": True, "url": base, "models": models, "error": None}


def _chat(messages: list[dict[str, Any]], *, model: str, base_url: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "tools": TOOLS,
        "stream": False,
        "options": {"temperature": 0.1},
    }
    return _request_json(f"{base_url.rstrip('/')}/api/chat", payload=payload, timeout=300)


def _normalize_tool_args(arguments: Any) -> dict[str, Any]:
    if arguments is None:
        return {}
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            value = json.loads(arguments)
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


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
    """Run one open-ended local agent turn with an auditable multi-tool loop."""
    selected_model = model or DEFAULT_MODEL
    selected_url = (base_url or DEFAULT_OLLAMA_URL).rstrip("/")
    runtime = CoachAgentRuntime(Path(db_path).expanduser().resolve(), str(team_id))

    status = ollama_status(selected_url)
    if not status["available"]:
        return CoachAgentResult(
            text="Ollama no està disponible localment. Inicia Ollama i torna-ho a provar.",
            model=selected_model,
            tool_rounds=0,
            tools_used=(),
            error=status["error"],
        )
    installed = status.get("models") or []
    if selected_model not in installed and not any(name.split(":")[0] == selected_model for name in installed):
        return CoachAgentResult(
            text=f"El model local `{selected_model}` no està instal·lat. Executa: ollama pull {selected_model}",
            model=selected_model,
            tool_rounds=0,
            tools_used=(),
            error="MODEL_NOT_INSTALLED",
        )

    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in (history or [])[-12:]:
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question.strip()})

    tools_used: list[str] = []
    limit = max(1, min(int(max_tool_rounds or MAX_TOOL_ROUNDS), 12))

    for round_index in range(limit + 1):
        response = _chat(messages, model=selected_model, base_url=selected_url)
        message = response.get("message") or {}
        tool_calls = message.get("tool_calls") or []
        content = str(message.get("content") or "").strip()

        if not tool_calls:
            if not content:
                content = "No he pogut generar una resposta amb l'evidència disponible."
            return CoachAgentResult(
                text=content,
                model=selected_model,
                tool_rounds=round_index,
                tools_used=tuple(tools_used),
            )

        messages.append(message)
        for call in tool_calls:
            function = call.get("function") or {}
            name = str(function.get("name") or "")
            args = _normalize_tool_args(function.get("arguments"))
            tools_used.append(name or "UNKNOWN_TOOL")
            fn = TOOL_FUNCTIONS.get(name)
            if fn is None:
                result = {"error": f"Unknown tool: {name}"}
            else:
                try:
                    result = fn(runtime, args)
                except Exception as exc:
                    result = {"error": f"{type(exc).__name__}: {exc}"}
            messages.append({"role": "tool", "tool_name": name, "content": _json(result)})

    return CoachAgentResult(
        text="He arribat al límit de consultes internes abans de poder donar una resposta fiable.",
        model=selected_model,
        tool_rounds=limit,
        tools_used=tuple(tools_used),
        error="MAX_TOOL_ROUNDS",
    )


def run_coach_agent(
    question: str,
    *,
    db_path: Path,
    team_id: str,
    history: list[dict[str, str]] | None = None,
    model: str | None = None,
) -> str:
    """Compatibility wrapper returning only final text."""
    return run_coach_agent_turn(
        question,
        db_path=db_path,
        team_id=team_id,
        history=history,
        model=model,
    ).text


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ask an open question to the local Ollama Coach Copilot.")
    parser.add_argument("question")
    parser.add_argument("--db", default=os.environ.get("FPS_DB_PATH"))
    parser.add_argument("--team-id", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    if not args.db:
        raise SystemExit("Set FPS_DB_PATH or pass --db.")
    result = run_coach_agent_turn(
        args.question,
        db_path=Path(args.db),
        team_id=args.team_id,
        model=args.model,
    )
    print(result.text)
    print(f"\nmodel={result.model} tool_rounds={result.tool_rounds} tools={','.join(result.tools_used) or 'none'}")
    if result.error:
        print(f"error={result.error}")
