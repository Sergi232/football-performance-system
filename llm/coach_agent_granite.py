"""Tool-driven local Coach Copilot runtime for the Spanish MVP.

The LLM interprets natural-language questions and selects bounded read-only tools.
All football metrics remain calculated outside the LLM. The final answer is checked
for numeric grounding but is not replaced by a deterministic template unless local
synthesis fails.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from app.access_control import assert_team_access
from app.data_access import connect_read_only, get_squad_summary, get_team_matches
from llm import coach_agent as _core

DEFAULT_MODEL = os.environ.get("FPS_LOCAL_LLM_MODEL", "granite4.2:3b")
DEFAULT_OLLAMA_URL = _core.DEFAULT_OLLAMA_URL
CoachAgentResult = _core.CoachAgentResult
ollama_status = _core.ollama_status

_NUM_RE = re.compile(r"(?<![\w])[-+]?\d+(?:[\.,]\d+)?%?")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")

SYSTEM_PROMPT = """Eres el Asistente IA local de un cuerpo técnico de fútbol.
Tu trabajo es entender preguntas naturales en castellano y consultar SOLO las herramientas de datos disponibles.
No tienes acceso directo a DuckDB. No calcules ni inventes Match Rating, Performance Index, métricas, umbrales ni recomendaciones.
Si una pregunta necesita datos, usa la herramienta adecuada. Puedes solicitar varias herramientas si son necesarias.
Si ninguna herramienta permite responder, no improvises conocimiento general.
No infieras fatiga, readiness, riesgo de lesión, XI ideal ni recomendaciones tácticas no validadas.
Mantén la respuesta breve, clara y en castellano.
"""

SYNTHESIS_PROMPT = """Redacta una respuesta breve para un entrenador usando EXCLUSIVAMENTE la EVIDENCIA JSON suministrada.
No inventes números, causas, etiquetas, umbrales ni recomendaciones. No recalcules métricas.
Si falta evidencia para una parte de la pregunta, dilo explícitamente.
No hables de ti mismo como IA. Responde en castellano y en un máximo de 5 frases.
"""

UNSUPPORTED_MESSAGE = (
    "No tengo una consulta validada para responder esa pregunta con los datos disponibles. "
    "Puedo responder sobre equipo, jugadores, partidos, estadísticas observadas, evolución, GPS descriptivo y calidad de datos."
)


def _norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().strip().split())


def _guardrail(question: str) -> str | None:
    q = _norm(question)
    fatigue = ("fatiga", "fatigado", "fatigada", "cansancio", "cansado", "cansada", "agotado", "agotada", "readiness")
    injury = ("riesgo de lesion", "riesgo lesion", "riesgo de lesión", "lesionarse", "lesion")
    lineup = ("quien deberia ser titular", "quien debería ser titular", "once ideal", "alineacion ideal", "alineación ideal", "quien deberia jugar", "quien debería jugar")
    tactical = ("que tactica recomiendas", "qué táctica recomiendas", "que sistema recomiendas", "qué sistema recomiendas")
    if any(_norm(t) in q for t in fatigue):
        return "No puedo determinar fatiga o cansancio porque el sistema no tiene un modelo validado para hacerlo. Puedo mostrar los datos GPS descriptivos disponibles sin convertirlos en una inferencia de fatiga."
    if any(_norm(t) in q for t in injury):
        return "No puedo estimar riesgo de lesión porque el sistema no tiene un modelo validado para hacerlo."
    if any(_norm(t) in q for t in lineup):
        return "No puedo recomendar quién debe ser titular ni un once ideal porque esa política no está validada. Puedo describir rendimiento, evolución y evidencia disponible."
    if any(_norm(t) in q for t in tactical):
        return "No puedo emitir una recomendación táctica automática porque esa política no está validada. Puedo describir el contexto y los datos disponibles."
    return None


def _canonical_player(db_path: Path, team_id: str, query: object) -> str:
    raw = str(query or "").strip()
    if not raw:
        return raw
    squad = get_squad_summary(db_path, team_id)
    if squad.empty:
        return raw
    target = _norm(raw)
    names = squad["player"].dropna().astype(str).tolist()
    exact = [name for name in names if _norm(name) == target]
    if len(exact) == 1:
        return exact[0]
    contains = [name for name in names if target and (target in _norm(name) or _norm(name) in target)]
    if len(contains) == 1:
        return contains[0]
    digits = re.findall(r"\d+", raw)
    if digits:
        wanted = str(int(digits[-1]))
        numeric_matches: list[str] = []
        for name in names:
            nd = re.findall(r"\d+", name)
            if nd and str(int(nd[-1])) == wanted:
                numeric_matches.append(name)
        if len(numeric_matches) == 1:
            return numeric_matches[0]
    return raw


def _canonical_match(db_path: Path, team_id: str, query: object) -> str:
    raw = str(query or "").strip()
    if not raw:
        return raw
    matches = get_team_matches(db_path, team_id)
    if matches.empty:
        return raw
    ids = matches["match_id"].astype(str).tolist()
    if raw in ids:
        return raw
    target = _norm(raw)
    for row in matches.itertuples(index=False):
        opponent = str(getattr(row, "opponent", "") or "")
        if opponent and (_norm(opponent) == target or target in _norm(opponent) or _norm(opponent) in target):
            return str(getattr(row, "match_id"))
    digits = re.findall(r"\d+", raw)
    if digits:
        wanted = str(int(digits[-1]))
        candidates: list[str] = []
        for row in matches.itertuples(index=False):
            opponent = str(getattr(row, "opponent", "") or "")
            nd = re.findall(r"\d+", opponent)
            if nd and str(int(nd[-1])) == wanted:
                candidates.append(str(getattr(row, "match_id")))
        if candidates:
            return candidates[0]
    return raw


def _query_team_stats(runtime: _core.CoachAgentRuntime, args: dict[str, Any]) -> dict[str, Any]:
    assert_team_access(runtime.team_id)
    metric = str(args.get("metric") or "").strip().casefold()
    metric_map = {
        "goals": "goals",
        "assists": "assists",
        "shots": "shots",
        "minutes": "minutes",
        "appearances": "appearances",
    }
    if metric not in metric_map:
        return {"error": f"Métrica no soportada: {metric}"}
    limit = max(1, min(int(args.get("limit", 5) or 5), 10))
    with connect_read_only(runtime.db_path) as con:
        frame = con.execute(
            """
            SELECT
                p.player_id,
                p.display_name AS player,
                COUNT(*) FILTER (WHERE pm.minutes_played > 0) AS appearances,
                SUM(pm.minutes_played) AS minutes,
                SUM(COALESCE(rs.goals, 0)) AS goals,
                SUM(COALESCE(rs.assists, 0)) AS assists,
                SUM(COALESCE(rs.shots_total, 0)) AS shots
            FROM player_match pm
            JOIN players p ON p.player_id = pm.player_id
            LEFT JOIN player_match_raw_stats rs
              ON rs.match_id = pm.match_id
             AND rs.player_id = pm.player_id
             AND rs.team_id = pm.team_id
            WHERE pm.team_id = ?
            GROUP BY p.player_id, p.display_name
            """,
            [runtime.team_id],
        ).df()
    if frame.empty:
        return {"metric": metric, "rows": []}
    for col in ("appearances", "minutes", "goals", "assists", "shots"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0)
    frame = frame.sort_values([metric_map[metric], "minutes", "player"], ascending=[False, False, True]).head(limit)
    return {
        "metric": metric,
        "definition": "Ranking descriptivo a partir de estadísticas observadas acumuladas del equipo.",
        "rows": frame.to_dict(orient="records"),
    }


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_team_stats",
            "description": "Ordena jugadores del equipo por una estadística observada acumulada: goles, asistencias, remates, minutos o apariciones.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": ["goals", "assists", "shots", "minutes", "appearances"]},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_snapshot",
            "description": "Estado reciente del equipo, Match Rating y tendencias descriptivas de jugadores.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_player_profile",
            "description": "Perfil de un jugador: participación, Match Ratings recientes, Performance Index y estado del motor experto.",
            "parameters": {"type": "object", "properties": {"player": {"type": "string"}}, "required": ["player"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_player_gps",
            "description": "Datos GPS descriptivos de un jugador. No infiere fatiga ni riesgo de lesión.",
            "parameters": {"type": "object", "properties": {"player": {"type": "string"}}, "required": ["player"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_match_detail",
            "description": "Datos observados y Match Ratings de un partido concreto o rival.",
            "parameters": {"type": "object", "properties": {"match": {"type": "string"}}, "required": ["match"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_quality",
            "description": "Cobertura, limitaciones, flags de calidad y estado de datos GPS.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_players",
            "description": "Comparación descriptiva de dos o más jugadores, respetando rol y tamaño de muestra.",
            "parameters": {
                "type": "object",
                "properties": {"players": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 6}},
                "required": ["players"],
            },
        },
    },
]


def _chat(model: str, messages: list[dict[str, Any]], *, base_url: str, tools: list[dict[str, Any]] | None = None, num_predict: int = 128) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0,
            "num_ctx": int(os.environ.get("FPS_AGENT_NUM_CTX", "1536")),
            "num_predict": num_predict,
        },
    }
    if tools:
        payload["tools"] = tools
    timeout = int(os.environ.get("FPS_AGENT_TIMEOUT", "75"))
    return _core._request_json(f"{base_url.rstrip('/')}/api/chat", payload=payload, timeout=timeout)


def _tool_calls(response: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    msg = response.get("message") or {}
    out: list[tuple[str, dict[str, Any]]] = []
    for call in (msg.get("tool_calls") or [])[:3]:
        fn = call.get("function") or {}
        name = str(fn.get("name") or "").strip()
        args = fn.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        if name and isinstance(args, dict):
            out.append((name, args))
    return out


def _execute_tool(runtime: _core.CoachAgentRuntime, name: str, args: dict[str, Any]) -> dict[str, Any]:
    clean = dict(args)
    if name in {"get_player_profile", "get_player_gps"}:
        clean["player"] = _canonical_player(runtime.db_path, runtime.team_id, clean.get("player"))
    elif name == "compare_players":
        clean["players"] = [_canonical_player(runtime.db_path, runtime.team_id, p) for p in (clean.get("players") or [])]
    elif name == "get_match_detail":
        clean["match"] = _canonical_match(runtime.db_path, runtime.team_id, clean.get("match"))

    if name == "query_team_stats":
        return _query_team_stats(runtime, clean)
    fn = _core.TOOL_FUNCTIONS.get(name)
    if fn is None:
        return {"error": f"Herramienta no disponible: {name}"}
    try:
        return fn(runtime, clean)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _compact(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if name == "query_team_stats":
        return {"metric": payload.get("metric"), "definition": payload.get("definition"), "rows": (payload.get("rows") or [])[:8], "error": payload.get("error")}
    if name == "get_team_snapshot":
        return {
            "overview": payload.get("overview"),
            "recent_team_rating_history": (payload.get("recent_team_rating_history") or [])[-4:],
            "player_recent_form": (payload.get("player_recent_form") or [])[:6],
            "definition": payload.get("definition"),
        }
    if name == "get_player_profile":
        return {
            "player": payload.get("player"),
            "summary": payload.get("summary"),
            "recent_match_ratings": (payload.get("recent_match_ratings") or [])[-5:],
            "latest_performance_index": payload.get("latest_performance_index"),
            "latest_expert_gate": payload.get("latest_expert_gate"),
            "error": payload.get("error"),
        }
    if name == "get_player_gps":
        return {"player": payload.get("player"), "gps_history": (payload.get("gps_history") or [])[-5:], "interpretation": payload.get("interpretation"), "error": payload.get("error")}
    if name == "get_match_detail":
        return {"match": payload.get("match"), "ratings": (payload.get("ratings") or [])[:15], "observations": payload.get("observations"), "note": payload.get("note"), "error": payload.get("error")}
    if name == "get_data_quality":
        return {"attention_summary": (payload.get("attention_summary") or [])[:8], "recent_flags": (payload.get("recent_flags") or [])[:5], "gps_status": payload.get("gps_status"), "policy": payload.get("policy"), "attention_error": payload.get("attention_error")}
    if name == "compare_players":
        return {"players": (payload.get("players") or [])[:6], "unresolved": payload.get("unresolved"), "comparison_policy": payload.get("comparison_policy")}
    return payload


def _canon_number(token: str) -> str:
    raw = token.strip().replace(",", ".")
    pct = raw.endswith("%")
    if pct:
        raw = raw[:-1]
    try:
        core = f"{float(raw):.12g}"
    except ValueError:
        core = raw
    return core + ("%" if pct else "")


def _numeric_guard(answer: str, evidence: dict[str, Any]) -> str:
    evidence_blob = json.dumps(evidence, ensure_ascii=False, default=str)
    allowed = {_canon_number(m.group(0)) for m in _NUM_RE.finditer(evidence_blob)}
    chunks = [c.strip() for c in _SENTENCE_SPLIT_RE.split(answer) if c.strip()]
    kept: list[str] = []
    for chunk in chunks:
        nums = {_canon_number(m.group(0)) for m in _NUM_RE.finditer(chunk)}
        if nums and not nums.issubset(allowed):
            continue
        kept.append(chunk)
    return " ".join(kept[:5]).strip()


def _fallback(evidence: dict[str, Any]) -> str:
    ranking = evidence.get("query_team_stats")
    if isinstance(ranking, dict):
        rows = ranking.get("rows") or []
        if rows:
            row = rows[0]
            metric = str(ranking.get("metric") or "dato")
            value = row.get(metric)
            return f"Según los datos registrados, {row.get('player')} lidera el equipo en {metric} con {value}."
    profile = evidence.get("get_player_profile")
    if isinstance(profile, dict) and profile.get("player"):
        summary = profile.get("summary") or {}
        return f"{profile.get('player')}: {summary.get('appearances', 'sin dato')} apariciones y {summary.get('minutes', 'sin dato')} minutos registrados."
    match = evidence.get("get_match_detail")
    if isinstance(match, dict) and isinstance(match.get("match"), dict):
        meta = match["match"]
        if meta.get("score_for") is not None and meta.get("score_against") is not None:
            return f"Partido contra {meta.get('opponent')}: {meta.get('score_for')}-{meta.get('score_against')}."
    return "Hay evidencia estructurada disponible, pero no puedo formular una respuesta fiable con ella."


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

    blocked = _guardrail(question)
    if blocked:
        return CoachAgentResult(blocked, selected_model, 0, (), None)

    status = ollama_status(selected_url)
    if not status.get("available"):
        return CoachAgentResult("Ollama no está disponible localmente.", selected_model, 0, (), status.get("error"))
    if selected_model not in (status.get("models") or []):
        return CoachAgentResult(f"El modelo local `{selected_model}` no está instalado.", selected_model, 0, (), "MODEL_NOT_INSTALLED")

    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in (history or [])[-4:]:
        if item.get("role") in {"user", "assistant"} and item.get("content"):
            messages.append({"role": str(item["role"]), "content": str(item["content"])[:700]})
    messages.append({"role": "user", "content": str(question)[:500]})

    try:
        planned = _chat(selected_model, messages, base_url=selected_url, tools=TOOLS, num_predict=96)
    except Exception as exc:
        return CoachAgentResult(UNSUPPORTED_MESSAGE, selected_model, 0, (), f"TOOL_SELECTION:{type(exc).__name__}: {exc}")

    calls = _tool_calls(planned)
    if not calls:
        return CoachAgentResult(UNSUPPORTED_MESSAGE, selected_model, 0, (), None)

    evidence: dict[str, Any] = {}
    tools_used: list[str] = []
    for name, args in calls:
        if name in evidence:
            continue
        payload = _execute_tool(runtime, name, args)
        evidence[name] = _compact(name, payload)
        tools_used.append(name)

    evidence_text = json.dumps(evidence, ensure_ascii=False, default=str)
    evidence_text = evidence_text[:6000]
    synthesis_messages = [
        {"role": "system", "content": SYNTHESIS_PROMPT},
        {"role": "user", "content": f"PREGUNTA:\n{question[:500]}\n\nEVIDENCIA JSON:\n{evidence_text}"},
    ]
    try:
        final_response = _chat(selected_model, synthesis_messages, base_url=selected_url, num_predict=180)
        text = str((final_response.get("message") or {}).get("content") or "").strip()
        text = _numeric_guard(text, evidence)
        if not text:
            text = _fallback(evidence)
        return CoachAgentResult(text, selected_model, 1, tuple(tools_used), None)
    except Exception as exc:
        return CoachAgentResult(_fallback(evidence), selected_model, 1, tuple(tools_used), f"SYNTHESIS_FALLBACK:{type(exc).__name__}: {exc}")


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    return run_coach_agent_turn(*args, **kwargs).text
