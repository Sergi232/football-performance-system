"""Generic-query runtime for the local Coach Copilot.

This layer keeps the validated Granite v2 tools and adds one generic ranking
contract plus deterministic conversational follow-ups. Football calculations stay
in Python/DuckDB; the LLM only maps language to a query and verbalizes evidence.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

from app.access_control import assert_team_access
from app.data_access import connect_read_only
from app.gps_physical_access import PHYSICAL_SUMMARY_VERSION
from app.match_rating_access import get_team_player_rating_snapshot
from llm import coach_agent as _core
from llm import coach_agent_granite as _base
from llm import coach_agent_granite_v2 as _legacy

DEFAULT_MODEL = _legacy.DEFAULT_MODEL
DEFAULT_OLLAMA_URL = _legacy.DEFAULT_OLLAMA_URL
CoachAgentResult = _legacy.CoachAgentResult
ollama_status = _legacy.ollama_status

METRICS: dict[str, dict[str, str]] = {
    "goals": {"source": "raw", "column": "goals", "agg": "sum", "label": "goles", "unit": ""},
    "assists": {"source": "raw", "column": "assists", "agg": "sum", "label": "asistencias", "unit": ""},
    "shots": {"source": "raw", "column": "shots_total", "agg": "sum", "label": "remates", "unit": ""},
    "passes_total": {"source": "raw", "column": "passes_total", "agg": "sum", "label": "pases", "unit": ""},
    "passes_completed": {"source": "raw", "column": "passes_completed", "agg": "sum", "label": "pases completados", "unit": ""},
    "tackles_total": {"source": "raw", "column": "tackles_total", "agg": "sum", "label": "entradas", "unit": ""},
    "tackles_won": {"source": "raw", "column": "tackles_won", "agg": "sum", "label": "entradas ganadas", "unit": ""},
    "interceptions": {"source": "raw", "column": "interceptions", "agg": "sum", "label": "intercepciones", "unit": ""},
    "turnovers": {"source": "raw", "column": "turnovers", "agg": "sum", "label": "pérdidas", "unit": ""},
    "dispossessed": {"source": "raw", "column": "dispossessed", "agg": "sum", "label": "desposesiones", "unit": ""},
    "minutes": {"source": "raw", "column": "minutes", "agg": "sum", "label": "minutos", "unit": "min"},
    "appearances": {"source": "raw", "column": "appearances", "agg": "sum", "label": "apariciones", "unit": ""},
    "total_distance_m": {"source": "gps", "column": "total_distance_m", "agg": "mean", "label": "distancia", "unit": "m"},
    "peak_speed_m_s": {"source": "gps", "column": "peak_speed_m_s", "agg": "max", "label": "velocidad máxima", "unit": "m/s"},
    "max_acceleration_m_s2": {"source": "gps", "column": "max_acceleration_m_s2", "agg": "max", "label": "aceleración máxima", "unit": "m/s²"},
    "min_acceleration_m_s2": {"source": "gps", "column": "min_acceleration_m_s2", "agg": "min", "label": "aceleración mínima", "unit": "m/s²"},
    "latest_match_rating": {"source": "rating", "column": "latest_match_rating", "agg": "latest", "label": "Match Rating más reciente", "unit": "/10"},
    "avg_last5": {"source": "rating", "column": "avg_last5", "agg": "latest", "label": "Match Rating medio últimos 5", "unit": "/10"},
    "trend_delta_5v5": {"source": "rating", "column": "trend_delta_5v5", "agg": "latest", "label": "tendencia 5 vs 5", "unit": ""},
}

ALIASES = {
    "gol": "goals", "goles": "goals", "goals": "goals",
    "asistencia": "assists", "asistencias": "assists", "assists": "assists",
    "remate": "shots", "remates": "shots", "disparo": "shots", "disparos": "shots", "shots": "shots",
    "pases": "passes_total", "passes_total": "passes_total",
    "pases completados": "passes_completed", "passes_completed": "passes_completed",
    "entradas": "tackles_total", "tackles_total": "tackles_total",
    "entradas ganadas": "tackles_won", "tackles_won": "tackles_won",
    "intercepciones": "interceptions", "interceptions": "interceptions",
    "perdidas": "turnovers", "turnovers": "turnovers",
    "desposesiones": "dispossessed", "dispossessed": "dispossessed",
    "minutos": "minutes", "minutes": "minutes",
    "apariciones": "appearances", "appearances": "appearances",
    "distancia": "total_distance_m", "metros": "total_distance_m", "distance": "total_distance_m", "total_distance_m": "total_distance_m",
    "velocidad": "peak_speed_m_s", "velocidad maxima": "peak_speed_m_s", "peak_speed_m_s": "peak_speed_m_s",
    "aceleracion maxima": "max_acceleration_m_s2", "max_acceleration_m_s2": "max_acceleration_m_s2",
    "aceleracion minima": "min_acceleration_m_s2", "min_acceleration_m_s2": "min_acceleration_m_s2",
    "match rating": "latest_match_rating", "rating": "latest_match_rating", "latest_match_rating": "latest_match_rating",
    "avg_last5": "avg_last5", "tendencia": "trend_delta_5v5", "trend_delta_5v5": "trend_delta_5v5",
}

ROUTER_PROMPT = """Devuelve SOLO JSON válido para consultar un sistema de análisis de fútbol.
Formato: {"calls":[{"tool":"NOMBRE","args":{...}}]}.

Herramienta genérica principal:
rank_players(metric, aggregation, last_n_matches, role, min_minutes, order, limit)
metric puede ser:
goals, assists, shots, passes_total, passes_completed, tackles_total, tackles_won,
interceptions, turnovers, dispossessed, minutes, appearances, total_distance_m,
peak_speed_m_s, max_acceleration_m_s2, min_acceleration_m_s2,
latest_match_rating, avg_last5, trend_delta_5v5.
aggregation: sum|mean|max|min|latest. "por partido/promedio/media" => mean;
"total/acumulado" => sum; "máximo/pico" => max; "mínimo" => min.
"últimos N partidos" => last_n_matches=N. Para quién tiene más/menos usa rank_players.

También disponibles:
get_team_snapshot args={}
get_player_profile args={"player":"texto"}
get_player_match_stats args={"player":"texto","last_n":N}
get_player_gps args={"player":"texto"}
get_match_detail args={"match":"texto"}
get_data_quality args={}
compare_players args={"players":["a","b"]}

No inventes nombres, métricas ni datos. Si no hay una herramienta válida, {"calls":[]}.
"""

ALLOWED = {
    "rank_players", "get_team_snapshot", "get_player_profile", "get_player_match_stats",
    "get_player_gps", "get_match_detail", "get_data_quality", "compare_players",
}


def _metric(value: object) -> str | None:
    raw = _base._norm(value)
    return raw if raw in METRICS else ALIASES.get(raw)


def _request_plan(model: str, question: str, history: list[dict[str, Any]] | None, base_url: str) -> dict[str, Any]:
    context = []
    for item in (history or [])[-6:]:
        role = str(item.get("role") or "")
        text = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and text:
            context.append(f"{role}: {text[:300]}")
    user = question[:600]
    if context:
        user = "CONTEXTO:\n" + "\n".join(context) + "\n\nPREGUNTA:\n" + user
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": ROUTER_PROMPT}, {"role": "user", "content": user}],
        "stream": False, "think": False, "format": "json", "keep_alive": "10m",
        "options": {"temperature": 0, "num_ctx": int(os.environ.get("FPS_AGENT_NUM_CTX", "1536")), "num_predict": 150},
    }
    response = _core._request_json(
        f"{base_url.rstrip('/')}/api/chat",
        payload=payload,
        timeout=int(os.environ.get("FPS_AGENT_TIMEOUT", "45")),
    )
    text = str((response.get("message") or {}).get("content") or "").strip()
    try:
        parsed = json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return {"calls": []}
        try:
            parsed = json.loads(m.group(0))
        except Exception:
            return {"calls": []}
    return parsed if isinstance(parsed, dict) else {"calls": []}


def _validated(plan: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out = []
    seen = set()
    for item in (plan.get("calls") or [])[:3]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("tool") or "")
        if name not in ALLOWED or name in seen:
            continue
        raw = item.get("args") if isinstance(item.get("args"), dict) else {}
        args = dict(raw)
        if name == "rank_players":
            metric = _metric(args.get("metric"))
            if metric is None:
                continue
            aggregation = _base._norm(args.get("aggregation"))
            if aggregation not in {"sum", "mean", "max", "min", "latest"}:
                aggregation = METRICS[metric]["agg"]
            if METRICS[metric]["source"] == "rating":
                aggregation = "latest"
            clean: dict[str, Any] = {
                "metric": metric,
                "aggregation": aggregation,
                "order": "asc" if _base._norm(args.get("order")) in {"asc", "ascending", "menor"} else "desc",
                "limit": 5,
            }
            try:
                clean["limit"] = max(1, min(int(args.get("limit", 5)), 10))
            except Exception:
                pass
            try:
                if args.get("last_n_matches") is not None:
                    clean["last_n_matches"] = max(1, min(int(args["last_n_matches"]), 50))
            except Exception:
                pass
            role = str(args.get("role") or "").strip()
            if role:
                clean["role"] = role
            try:
                if args.get("min_minutes") is not None:
                    clean["min_minutes"] = max(0.0, float(args["min_minutes"]))
            except Exception:
                pass
            args = clean
        elif name in {"get_player_profile", "get_player_gps", "get_player_match_stats"}:
            player = str(args.get("player") or "").strip()
            if not player:
                continue
            clean = {"player": player}
            if name == "get_player_match_stats":
                try:
                    clean["last_n"] = max(1, min(int(args.get("last_n", 10)), 30))
                except Exception:
                    clean["last_n"] = 10
            args = clean
        elif name == "get_match_detail":
            match = str(args.get("match") or "").strip()
            if not match:
                continue
            args = {"match": match}
        elif name == "compare_players":
            players = [str(x).strip() for x in (args.get("players") or []) if str(x).strip()][:6]
            if len(players) < 2:
                continue
            args = {"players": players}
        else:
            args = {}
        seen.add(name)
        out.append((name, args))
    return out


def _last_user(history: list[dict[str, Any]] | None) -> str | None:
    for item in reversed(history or []):
        if str(item.get("role") or "") == "user" and str(item.get("content") or "").strip():
            return str(item["content"]).strip()
    return None


def _is_evidence(q: str) -> bool:
    q = _base._norm(q)
    return any(x in q for x in ("evidencia", "evidencias", "en que te basas", "de donde sale", "que datos usaste", "por que dices eso", "como sabes eso"))


def _ordinal(q: str) -> int | None:
    q = _base._norm(q)
    for word, idx in {"primero": 0, "segundo": 1, "tercero": 2, "cuarto": 3, "quinto": 4}.items():
        if re.search(rf"\b{word}\b", q):
            return idx
    return None


def _window(q: str) -> int | None:
    q = _base._norm(q)
    for p in (r"ultim\w*\s+(\d{1,2})\s+partid", r"(\d{1,2})\s+ultim\w*\s+partid"):
        m = re.search(p, q)
        if m:
            return max(1, min(int(m.group(1)), 50))
    return None


def _metric_in_text(q: str) -> str | None:
    q = _base._norm(q)
    for alias in sorted(ALIASES, key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", q):
            return ALIASES[alias]
    return None


def _followup(q: str) -> bool:
    n = _base._norm(q)
    return _is_evidence(q) or _ordinal(q) is not None or _window(q) is not None or (len(n.split()) <= 8 and n.startswith(("y ", "i ")))


def _modify(calls: list[tuple[str, dict[str, Any]]], q: str) -> list[tuple[str, dict[str, Any]]]:
    metric = _metric_in_text(q)
    window = _window(q)
    n = _base._norm(q)
    out = []
    for name, args in calls:
        args = dict(args)
        if name == "rank_players":
            if metric:
                args["metric"] = metric
                args["aggregation"] = METRICS[metric]["agg"]
            if window:
                args["last_n_matches"] = window
            if any(x in n for x in ("por partido", "promedio", "media ")):
                args["aggregation"] = "mean"
            elif any(x in n for x in ("total", "acumulad")):
                args["aggregation"] = "sum"
        out.append((name, args))
    return out


def _agg(expr: str, aggregation: str) -> str:
    return {
        "sum": f"SUM({expr})", "mean": f"AVG({expr})", "max": f"MAX({expr})",
        "min": f"MIN({expr})", "latest": f"arg_max({expr}, match_date)",
    }[aggregation]


def _rank_sql(runtime: _core.CoachAgentRuntime, args: dict[str, Any], gps: bool) -> pd.DataFrame:
    spec = METRICS[args["metric"]]
    last_n = int(args.get("last_n_matches") or 100000)
    role = args.get("role")
    min_minutes = float(args.get("min_minutes") or 0)
    direction = "ASC" if args.get("order") == "asc" else "DESC"
    limit = int(args["limit"])
    if gps:
        metric_expr = f"g.{spec['column']}"
        source_from = """
            player_match_gps_summary g
            JOIN players p ON p.player_id=g.player_id
            JOIN player_match pm ON pm.match_id=g.match_id AND pm.player_id=g.player_id AND pm.team_id=g.team_id
            JOIN matches m ON m.match_id=g.match_id
        """
        source_where = "g.summary_version=? AND g.import_rank=1 AND g.team_id=?"
        params = [runtime.team_id, last_n, PHYSICAL_SUMMARY_VERSION, runtime.team_id, role, role, min_minutes, limit]
    else:
        metric_expr = "1" if args["metric"] == "appearances" else ("pm.minutes_played" if args["metric"] == "minutes" else f"rs.{spec['column']}")
        source_from = """
            player_match pm
            JOIN players p ON p.player_id=pm.player_id
            JOIN matches m ON m.match_id=pm.match_id
            LEFT JOIN player_match_raw_stats rs ON rs.match_id=pm.match_id AND rs.player_id=pm.player_id AND rs.team_id=pm.team_id
        """
        source_where = "pm.team_id=?"
        params = [runtime.team_id, last_n, runtime.team_id, role, role, min_minutes, limit]
    aggregation = _agg("metric_value", args["aggregation"])
    with connect_read_only(runtime.db_path) as con:
        return con.execute(
            f"""
            WITH recent AS (
                SELECT tm.match_id FROM team_match tm JOIN matches m ON m.match_id=tm.match_id
                WHERE tm.team_id=? ORDER BY m.match_date DESC, m.match_id DESC LIMIT ?
            ), base AS (
                SELECT p.player_id, p.display_name AS player, pm.match_id, m.match_date,
                       pm.minutes_played AS minutes, pm.primary_role, {metric_expr} AS metric_value
                FROM {source_from}
                WHERE {source_where}
                  AND pm.match_id IN (SELECT match_id FROM recent)
                  AND pm.minutes_played > 0
                  AND (? IS NULL OR LOWER(COALESCE(pm.primary_role,'')) LIKE '%' || LOWER(?) || '%')
            ), ranked AS (
                SELECT player_id, player, COUNT(DISTINCT match_id) AS sample_matches,
                       SUM(minutes) AS minutes,
                       string_agg(DISTINCT primary_role, ', ' ORDER BY primary_role)
                         FILTER (WHERE primary_role IS NOT NULL) AS observed_roles,
                       {aggregation} AS value
                FROM base GROUP BY player_id, player
            )
            SELECT * FROM ranked
            WHERE value IS NOT NULL AND minutes >= ?
            ORDER BY value {direction} NULLS LAST, minutes DESC, player
            LIMIT ?
            """, params
        ).df()


def _rank(runtime: _core.CoachAgentRuntime, args: dict[str, Any]) -> dict[str, Any]:
    assert_team_access(runtime.team_id)
    spec = METRICS[args["metric"]]
    try:
        if spec["source"] == "rating":
            frame = get_team_player_rating_snapshot(runtime.db_path, runtime.team_id).copy()
            col = spec["column"]
            if frame.empty or col not in frame.columns:
                rows = []
            else:
                frame[col] = pd.to_numeric(frame[col], errors="coerce")
                role = str(args.get("role") or "")
                if role and "latest_position_group" in frame.columns:
                    frame = frame.loc[frame["latest_position_group"].astype(str).str.contains(role, case=False, na=False)]
                frame = frame.loc[frame[col].notna()].sort_values(col, ascending=args.get("order") == "asc").head(args["limit"])
                rows = [{
                    "player": r.get("player"), "value": r.get(col),
                    "sample_matches": r.get("rated_matches") or r.get("n_last5"),
                    "observed_roles": r.get("latest_position_group"),
                } for r in frame.to_dict("records")]
            source = "materialized Match Rating analytics"
        else:
            frame = _rank_sql(runtime, args, gps=spec["source"] == "gps")
            rows = [{k: _core._clean(v) for k, v in r.items()} for r in frame.to_dict("records")]
            source = "player_match_gps_summary" if spec["source"] == "gps" else "player_match + player_match_raw_stats"
        return {
            "metric": args["metric"], "metric_label": spec["label"], "unit": spec["unit"],
            "aggregation": args["aggregation"], "last_n_matches": args.get("last_n_matches"),
            "source": source, "rows": rows,
            "definition": "Ranking descriptivo calculado por Python/DuckDB; el LLM no calcula el resultado.",
        }
    except Exception as exc:
        return {"metric": args["metric"], "aggregation": args["aggregation"], "rows": [], "error": f"{type(exc).__name__}: {exc}"}


def _compact_rank(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric": payload.get("metric"), "metric_label": payload.get("metric_label"),
        "unit": payload.get("unit"), "aggregation": payload.get("aggregation"),
        "last_n_matches": payload.get("last_n_matches"), "source": payload.get("source"),
        "definition": payload.get("definition"), "rows": (payload.get("rows") or [])[:10],
        "error": payload.get("error"),
    }


def _execute(runtime: _core.CoachAgentRuntime, name: str, args: dict[str, Any]) -> dict[str, Any]:
    return _rank(runtime, args) if name == "rank_players" else _base._execute_tool(runtime, name, args)


def _value(v: Any, unit: str | None) -> str:
    try:
        s = f"{float(v):.2f}".rstrip("0").rstrip(".")
    except Exception:
        s = str(v)
    return f"{s} {unit}".strip() if unit else s


def _evidence_answer(evidence: dict[str, Any]) -> str:
    block = evidence.get("rank_players")
    if block:
        rows = block.get("rows") or []
        sample = rows[0].get("sample_matches") if rows else None
        suffix = f"; el primer registro tiene {sample} partidos con dato" if sample is not None else ""
        return (
            f"La respuesta se basa en `{block.get('source')}`, métrica {block.get('metric_label')}, "
            f"agregación `{block.get('aggregation')}`{suffix}. El ranking lo calcula Python/DuckDB; Granite solo interpreta y redacta."
        )
    return "La respuesta se basa en estas consultas estructuradas: " + ", ".join(evidence.keys()) + "."


def _ordinal_answer(evidence: dict[str, Any], idx: int) -> str | None:
    block = evidence.get("rank_players")
    if not block:
        return None
    rows = block.get("rows") or []
    if idx >= len(rows):
        return "No hay suficientes registros válidos para ese puesto."
    row = rows[idx]
    sample = row.get("sample_matches")
    suffix = f" ({sample} partidos con dato)" if sample is not None else ""
    return f"{idx + 1}. {row.get('player')}: {_value(row.get('value'), block.get('unit'))} en {block.get('metric_label')}{suffix}."


def _fallback(evidence: dict[str, Any]) -> str:
    block = evidence.get("rank_players")
    if block and (block.get("rows") or []):
        row = block["rows"][0]
        return f"{row.get('player')} lidera {block.get('metric_label')} con {_value(row.get('value'), block.get('unit'))}."
    return _base._fallback(evidence)


def run_coach_agent_turn(
    question: str, *, db_path: Path, team_id: str, history: list[dict[str, Any]] | None = None,
    model: str | None = None, base_url: str | None = None, max_tool_rounds: int | None = None,
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

    previous = _last_user(history)
    is_follow = bool(previous and _followup(question))
    try:
        plan = _request_plan(selected_model, previous if is_follow else question, None if is_follow else history, selected_url)
        calls = _validated(plan)
        if is_follow:
            calls = _modify(calls, question)
        if not calls and is_follow and not _is_evidence(question):
            plan = _request_plan(selected_model, f"Consulta anterior: {previous}\nSeguimiento: {question}", history, selected_url)
            calls = _validated(plan)
    except Exception as exc:
        return CoachAgentResult(_base.UNSUPPORTED_MESSAGE, selected_model, 0, (), f"INTENT_SELECTION:{type(exc).__name__}: {exc}")
    if not calls:
        return CoachAgentResult(_base.UNSUPPORTED_MESSAGE, selected_model, 0, (), None)

    evidence: dict[str, Any] = {}
    tools = []
    for name, args in calls:
        payload = _execute(runtime, name, args)
        evidence[name] = _compact_rank(payload) if name == "rank_players" else _legacy._compact_evidence(name, payload)
        tools.append(name)

    if _is_evidence(question):
        return CoachAgentResult(_evidence_answer(evidence), selected_model, 1, tuple(tools), None)
    idx = _ordinal(question) if is_follow else None
    if idx is not None:
        answer = _ordinal_answer(evidence, idx)
        if answer:
            return CoachAgentResult(answer, selected_model, 1, tuple(tools), None)

    try:
        raw = _legacy._synthesize(selected_model, question, evidence, base_url=selected_url)
        text = _base._numeric_guard(raw, evidence) or _fallback(evidence)
        return CoachAgentResult(text, selected_model, 1, tuple(tools), None)
    except Exception as exc:
        return CoachAgentResult(_fallback(evidence), selected_model, 1, tuple(tools), f"SYNTHESIS_FALLBACK:{type(exc).__name__}: {exc}")


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    return run_coach_agent_turn(*args, **kwargs).text
