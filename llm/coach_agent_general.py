"""Hybrid local Coach Copilot runtime for the Spanish MVP.

High-confidence query families are routed deterministically to generic read-only
analytics tools. Ambiguous language falls back to Qwen3.5 4B as a semantic router.
Football calculations and final factual values stay in Python/DuckDB; the LLM never
calculates metrics or recommendations.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

from app.access_control import assert_team_access
from app.data_access import connect_read_only, get_squad_summary, get_team_matches
from app.gps_physical_access import PHYSICAL_SUMMARY_VERSION
from app.match_rating_access import get_team_player_rating_snapshot
from llm import coach_agent as _core
from llm import coach_agent_granite as _base
from llm import coach_agent_granite_v2 as _legacy

DEFAULT_MODEL = os.environ.get("FPS_LOCAL_LLM_MODEL", "qwen3.5:4b")
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
    "gol": "goals", "goles": "goals", "goleador": "goals", "goals": "goals",
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
    "apariciones": "appearances", "partidos jugados": "appearances", "appearances": "appearances",
    "distancia": "total_distance_m", "metros": "total_distance_m", "kilometros": "total_distance_m", "distance": "total_distance_m", "total_distance_m": "total_distance_m",
    "velocidad": "peak_speed_m_s", "velocidad maxima": "peak_speed_m_s", "peak_speed_m_s": "peak_speed_m_s",
    "aceleracion maxima": "max_acceleration_m_s2", "max_acceleration_m_s2": "max_acceleration_m_s2",
    "aceleracion minima": "min_acceleration_m_s2", "maxima desaceleracion": "min_acceleration_m_s2", "min_acceleration_m_s2": "min_acceleration_m_s2",
    "match rating": "latest_match_rating", "rating": "latest_match_rating", "nota": "latest_match_rating", "latest_match_rating": "latest_match_rating",
    "rating medio": "avg_last5", "media rating": "avg_last5", "avg_last5": "avg_last5",
    "tendencia": "trend_delta_5v5", "mejora": "trend_delta_5v5", "trend_delta_5v5": "trend_delta_5v5",
}

ROUTER_PROMPT = """Eres el router semántico de un asistente de análisis de fútbol. Devuelve SOLO JSON válido.
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

No respondas la pregunta. No inventes nombres, métricas ni datos. Si no hay una herramienta válida, {"calls":[]}.
"""

ALLOWED = {
    "rank_players", "get_team_snapshot", "get_player_profile", "get_player_match_stats",
    "get_player_gps", "get_match_detail", "get_data_quality", "compare_players",
}


def _norm(value: object) -> str:
    return _base._norm(value)


def _metric(value: object) -> str | None:
    raw = _norm(value)
    return raw if raw in METRICS else ALIASES.get(raw)


def _request_plan(model: str, question: str, history: list[dict[str, Any]] | None, base_url: str) -> dict[str, Any]:
    context = []
    for item in (history or [])[-6:]:
        role = str(item.get("role") or "")
        text = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and text:
            context.append(f"{role}: {text[:260]}")
    user = question[:600]
    if context:
        user = "CONTEXTO:\n" + "\n".join(context) + "\n\nPREGUNTA:\n" + user
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": ROUTER_PROMPT}, {"role": "user", "content": user}],
        "stream": False,
        "think": False,
        "format": "json",
        "keep_alive": "30m",
        "options": {
            "temperature": 0,
            "num_ctx": int(os.environ.get("FPS_AGENT_ROUTER_CTX", "1024")),
            "num_predict": 100,
        },
    }
    response = _core._request_json(
        f"{base_url.rstrip('/')}/api/chat",
        payload=payload,
        timeout=int(os.environ.get("FPS_AGENT_TIMEOUT", "75")),
    )
    text = str((response.get("message") or {}).get("content") or "").strip()
    try:
        parsed = json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {"calls": []}
        try:
            parsed = json.loads(match.group(0))
        except Exception:
            return {"calls": []}
    return parsed if isinstance(parsed, dict) else {"calls": []}


def _validated(plan: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for item in (plan.get("calls") or [])[:3]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("tool") or "").strip()
        if name not in ALLOWED or name in seen:
            continue
        raw = item.get("args") if isinstance(item.get("args"), dict) else {}
        args = dict(raw)
        if name == "rank_players":
            metric = _metric(args.get("metric"))
            if metric is None:
                continue
            aggregation = _norm(args.get("aggregation"))
            if aggregation not in {"sum", "mean", "max", "min", "latest"}:
                aggregation = METRICS[metric]["agg"]
            if METRICS[metric]["source"] == "rating":
                aggregation = "latest"
            clean: dict[str, Any] = {
                "metric": metric,
                "aggregation": aggregation,
                "order": "asc" if _norm(args.get("order")) in {"asc", "ascending", "menor"} else "desc",
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


def _is_evidence(question: str) -> bool:
    q = _norm(question)
    return any(x in q for x in (
        "evidencia", "evidencias", "en que te basas", "de donde sale",
        "que datos usaste", "por que dices eso", "como sabes eso", "fuente",
    ))


def _ordinal(question: str) -> int | None:
    q = _norm(question)
    ordinals = {
        "primero": 0, "primera": 0, "segundo": 1, "segunda": 1,
        "tercero": 2, "tercera": 2, "cuarto": 3, "cuarta": 3,
        "quinto": 4, "quinta": 4,
    }
    for word, idx in ordinals.items():
        if re.search(rf"\b{word}\b", q):
            return idx
    return None


def _window(question: str) -> int | None:
    q = _norm(question)
    for pattern in (r"ultim\w*\s+(\d{1,2})\s+partid", r"(\d{1,2})\s+ultim\w*\s+partid"):
        match = re.search(pattern, q)
        if match:
            return max(1, min(int(match.group(1)), 50))
    return None


def _metric_in_text(question: str) -> str | None:
    q = _norm(question)
    for alias in sorted(ALIASES, key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", q):
            return ALIASES[alias]
    return None


def _followup(question: str) -> bool:
    q = _norm(question)
    return _is_evidence(question) or _ordinal(question) is not None or _window(question) is not None or (len(q.split()) <= 8 and q.startswith(("y ", "i ")))


def _rank_aggregation(metric: str, question: str) -> str:
    if METRICS[metric]["source"] == "rating":
        return "latest"
    q = _norm(question)
    if "por partido" in q or "promedio" in q or re.search(r"\bmedia\b", q):
        return "mean"
    if "acumulad" in q or re.search(r"\btotal\b", q):
        return "sum"
    if "pico" in q:
        return "max"
    return METRICS[metric]["agg"]


def _rank_order(question: str) -> str:
    q = _norm(question)
    return "asc" if any(x in q for x in ("menos", "menor", "minimo", "peor")) else "desc"


def _rank_limit(question: str) -> int:
    q = _norm(question)
    match = re.search(r"\btop\s*(\d{1,2})\b", q)
    if match:
        return max(1, min(int(match.group(1)), 10))
    return 5


def _deterministic_rank_calls(question: str) -> list[tuple[str, dict[str, Any]]]:
    metric = _metric_in_text(question)
    if metric is None:
        return []
    q = _norm(question)
    rank_signal = any(x in q for x in (
        " mas ", " menos ", " mayor", " menor", "maximo", "minimo", "mejor", "peor",
        "lider", "ranking", "top ", "quien ", "quienes ",
    ))
    if not rank_signal:
        return []
    args: dict[str, Any] = {
        "metric": metric,
        "aggregation": _rank_aggregation(metric, question),
        "order": _rank_order(question),
        "limit": _rank_limit(question),
    }
    window = _window(question)
    if window:
        args["last_n_matches"] = window
    return [("rank_players", args)]


def _player_mentions(runtime: _core.CoachAgentRuntime, question: str) -> list[str]:
    squad = get_squad_summary(runtime.db_path, runtime.team_id)
    if squad.empty:
        return []
    q = _norm(question)
    found: list[str] = []
    for name in squad["player"].dropna().astype(str).tolist():
        token = _norm(name)
        if token and re.search(rf"(?<!\w){re.escape(token)}(?!\w)", q):
            found.append(name)
    return found


def _match_mention(runtime: _core.CoachAgentRuntime, question: str) -> str | None:
    matches = get_team_matches(runtime.db_path, runtime.team_id)
    if matches.empty:
        return None
    q = _norm(question)
    for row in matches.itertuples(index=False):
        opponent = str(getattr(row, "opponent", "") or "")
        token = _norm(opponent)
        if token and re.search(rf"(?<!\w){re.escape(token)}(?!\w)", q):
            return opponent
    return None


def _deterministic_route(runtime: _core.CoachAgentRuntime, question: str) -> list[tuple[str, dict[str, Any]]]:
    rank = _deterministic_rank_calls(question)
    if rank:
        return rank

    q = _norm(question)
    players = _player_mentions(runtime, question)
    if len(players) >= 2 and any(x in q for x in ("compara", "comparar", "comparacion", " versus ", " vs ")):
        return [("compare_players", {"players": players[:6]})]

    if len(players) == 1:
        player = players[0]
        if any(x in q for x in ("gps", "fisic", "distancia", "velocidad", "aceleracion", "desaceleracion")):
            return [("get_player_gps", {"player": player})]
        if any(x in q for x in ("evolucion", "evolucionado", "rendimiento", "forma", "perfil", "rating", "performance index")):
            return [("get_player_profile", {"player": player})]
        if any(x in q for x in ("ultimos partidos", "estadisticas", "acciones", "que hizo", "partido a partido")):
            return [("get_player_match_stats", {"player": player, "last_n": _window(question) or 10})]

    opponent = _match_mention(runtime, question)
    if opponent and any(x in q for x in ("contra", "partido", "resultado", "paso", "rival")):
        return [("get_match_detail", {"match": opponent})]

    if "datos" in q and any(x in q for x in ("calidad", "limitacion", "cobertura", "faltan", "incomplet")):
        return [("get_data_quality", {})]

    if "equipo" in q and any(x in q for x in ("estado", "forma", "tendencia", "como esta", "como va", "evolucion", "reciente")):
        return [("get_team_snapshot", {})]

    return []


def _modify(calls: list[tuple[str, dict[str, Any]]], question: str) -> list[tuple[str, dict[str, Any]]]:
    metric = _metric_in_text(question)
    window = _window(question)
    q = _norm(question)
    out = []
    for name, args in calls:
        args = dict(args)
        if name == "rank_players":
            if metric:
                args["metric"] = metric
                args["aggregation"] = _rank_aggregation(metric, question)
            if window:
                args["last_n_matches"] = window
            if "por partido" in q or "promedio" in q or re.search(r"\bmedia\b", q):
                args["aggregation"] = "mean"
            elif "total" in q or "acumulad" in q:
                args["aggregation"] = "sum"
        out.append((name, args))
    return out


def _agg(expr: str, aggregation: str) -> str:
    return {
        "sum": f"SUM({expr})",
        "mean": f"AVG({expr})",
        "max": f"MAX({expr})",
        "min": f"MIN({expr})",
        "latest": f"arg_max({expr}, match_date)",
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
            """,
            params,
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
                    "player": row.get("player"),
                    "value": row.get(col),
                    "sample_matches": row.get("rated_matches") or row.get("n_last5"),
                    "observed_roles": row.get("latest_position_group"),
                } for row in frame.to_dict("records")]
            source = "materialized Match Rating analytics"
        else:
            frame = _rank_sql(runtime, args, gps=spec["source"] == "gps")
            rows = [{k: _core._clean(v) for k, v in row.items()} for row in frame.to_dict("records")]
            source = "player_match_gps_summary" if spec["source"] == "gps" else "player_match + player_match_raw_stats"
        return {
            "metric": args["metric"],
            "metric_label": spec["label"],
            "unit": spec["unit"],
            "aggregation": args["aggregation"],
            "last_n_matches": args.get("last_n_matches"),
            "source": source,
            "rows": rows,
            "definition": "Ranking descriptivo calculado por Python/DuckDB; el LLM no calcula el resultado.",
        }
    except Exception as exc:
        return {
            "metric": args["metric"],
            "aggregation": args["aggregation"],
            "rows": [],
            "error": f"{type(exc).__name__}: {exc}",
        }


def _compact_rank(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric": payload.get("metric"),
        "metric_label": payload.get("metric_label"),
        "unit": payload.get("unit"),
        "aggregation": payload.get("aggregation"),
        "last_n_matches": payload.get("last_n_matches"),
        "source": payload.get("source"),
        "definition": payload.get("definition"),
        "rows": (payload.get("rows") or [])[:10],
        "error": payload.get("error"),
    }


def _execute(runtime: _core.CoachAgentRuntime, name: str, args: dict[str, Any]) -> dict[str, Any]:
    return _rank(runtime, args) if name == "rank_players" else _base._execute_tool(runtime, name, args)


def _value(value: Any, unit: str | None) -> str:
    try:
        text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    except Exception:
        text = str(value)
    return f"{text} {unit}".strip() if unit else text


def _aggregation_label(value: str | None) -> str:
    return {
        "sum": "total",
        "mean": "media",
        "max": "máximo",
        "min": "mínimo",
        "latest": "último valor",
    }.get(str(value), str(value or "valor"))


def _evidence_answer(evidence: dict[str, Any]) -> str:
    block = evidence.get("rank_players")
    if block:
        rows = block.get("rows") or []
        sample = rows[0].get("sample_matches") if rows else None
        suffix = f"; el primer registro tiene {sample} partidos con dato" if sample is not None else ""
        return (
            f"La respuesta usa `{block.get('source')}`, la métrica {block.get('metric_label')} y agregación "
            f"`{block.get('aggregation')}`{suffix}. El ranking lo calcula Python/DuckDB; el modelo local solo interpreta la consulta cuando hace falta."
        )
    labels = {
        "get_team_snapshot": "resumen estructurado del equipo",
        "get_player_profile": "perfil y analítica materializada del jugador",
        "get_player_match_stats": "estadísticas observadas jugador-partido",
        "get_player_gps": "resumen GPS normalizado",
        "get_match_detail": "datos observados y ratings materializados del partido",
        "get_data_quality": "capa de calidad y cobertura de datos",
        "compare_players": "snapshot descriptivo materializado de jugadores",
    }
    used = [labels.get(name, name) for name in evidence]
    return "La respuesta se basa en: " + ", ".join(used) + ". No se han inventado métricas ni datos fuera de esas consultas."


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


def _rank_answer(question: str, evidence: dict[str, Any]) -> str:
    block = evidence.get("rank_players") or {}
    rows = block.get("rows") or []
    if not rows:
        if block.get("error"):
            return "No he podido obtener un ranking válido con los datos disponibles."
        return "No hay registros suficientes para construir ese ranking."
    q = _norm(question)
    show_list = any(x in q for x in ("ranking", "top ", "quienes", "lista"))
    count = min(len(rows), 5 if show_list else 1)
    agg = _aggregation_label(block.get("aggregation"))
    lines = []
    for idx, row in enumerate(rows[:count], start=1):
        sample = row.get("sample_matches")
        sample_text = f", {sample} partidos con dato" if sample is not None else ""
        lines.append(f"{idx}. {row.get('player')}: {_value(row.get('value'), block.get('unit'))} ({agg}{sample_text})")
    if count == 1:
        return f"{rows[0].get('player')} lidera {block.get('metric_label')}: {_value(rows[0].get('value'), block.get('unit'))} ({agg})."
    return f"Ranking de {block.get('metric_label')}: " + "; ".join(lines) + "."


def _answer_from_evidence(question: str, evidence: dict[str, Any]) -> str:
    if "rank_players" in evidence:
        return _rank_answer(question, evidence)

    profile = evidence.get("get_player_profile")
    if profile:
        if profile.get("error"):
            return str(profile["error"])
        summary = profile.get("summary") or {}
        player = profile.get("player") or summary.get("player") or "El jugador"
        parts = []
        if summary.get("appearances") is not None:
            parts.append(f"{summary.get('appearances')} apariciones")
        if summary.get("minutes") is not None:
            parts.append(f"{_value(summary.get('minutes'), 'min')}")
        if summary.get("goals") is not None:
            parts.append(f"{summary.get('goals')} goles")
        if summary.get("assists") is not None:
            parts.append(f"{summary.get('assists')} asistencias")
        ratings = profile.get("recent_match_ratings") or []
        latest = ratings[-1] if ratings else {}
        rating = latest.get("match_rating_10")
        rating_text = f" Último Match Rating disponible: {_value(rating, '/10')}." if rating is not None else ""
        return f"{player}: " + (", ".join(parts) if parts else "perfil disponible") + "." + rating_text

    gps = evidence.get("get_player_gps")
    if gps:
        if gps.get("error"):
            return str(gps["error"])
        rows = gps.get("gps_history") or []
        player = gps.get("player") or "El jugador"
        if not rows:
            return f"No hay datos GPS descriptivos disponibles para {player}."
        row = rows[-1]
        bits = []
        if row.get("total_distance_m") is not None:
            bits.append(f"distancia {_value(row.get('total_distance_m'), 'm')}")
        if row.get("peak_speed_m_s") is not None:
            bits.append(f"velocidad máxima {_value(row.get('peak_speed_m_s'), 'm/s')}")
        if row.get("max_acceleration_m_s2") is not None:
            bits.append(f"aceleración máxima {_value(row.get('max_acceleration_m_s2'), 'm/s²')}")
        opponent = row.get("opponent")
        context = f" contra {opponent}" if opponent else ""
        return f"Último GPS disponible de {player}{context}: " + ", ".join(bits) + "."

    match = evidence.get("get_match_detail")
    if match:
        if match.get("error"):
            return str(match["error"])
        info = match.get("match") or {}
        opponent = info.get("opponent") or "rival"
        score_for = info.get("score_for")
        score_against = info.get("score_against")
        score = f" {score_for}-{score_against}" if score_for is not None and score_against is not None else ""
        top = match.get("top_ratings") or []
        top_text = ""
        if top and top[0].get("player") is not None and top[0].get("match_rating_10") is not None:
            top_text = f" Mejor Match Rating: {top[0]['player']} ({_value(top[0]['match_rating_10'], '/10')})."
        return f"Partido contra {opponent}:{score}." + top_text

    team = evidence.get("get_team_snapshot")
    if team:
        overview = team.get("overview") or {}
        parts = []
        if overview.get("matches") is not None:
            parts.append(f"{overview.get('matches')} partidos")
        if overview.get("goals") is not None:
            parts.append(f"{overview.get('goals')} goles")
        if overview.get("assists") is not None:
            parts.append(f"{overview.get('assists')} asistencias")
        form = team.get("player_recent_form") or []
        trend_text = ""
        if form and form[0].get("player") is not None and form[0].get("trend_delta_5v5") is not None:
            trend_text = f" Mayor tendencia descriptiva 5v5 disponible: {form[0]['player']} ({_value(form[0]['trend_delta_5v5'], None)})."
        return "Resumen del equipo: " + (", ".join(parts) if parts else "datos disponibles") + "." + trend_text

    quality = evidence.get("get_data_quality")
    if quality:
        gps_status = quality.get("gps_status") or {}
        if gps_status.get("table_available"):
            return (
                "Calidad/cobertura: GPS disponible con "
                f"{gps_status.get('rows', 0)} registros, {gps_status.get('matches', 0)} partidos y "
                f"{gps_status.get('players', 0)} jugadores. No se infieren fatiga, readiness ni riesgo de lesión."
            )
        return "La capa de calidad está disponible, pero no hay tabla GPS utilizable. No se infieren fatiga, readiness ni riesgo de lesión."

    comparison = evidence.get("compare_players")
    if comparison:
        rows = comparison.get("players") or []
        if not rows:
            return "No hay suficiente evidencia materializada para comparar esos jugadores."
        parts = []
        for row in rows[:6]:
            player = row.get("player") or "Jugador"
            rating = row.get("latest_match_rating")
            avg = row.get("avg_last5")
            detail = []
            if rating is not None:
                detail.append(f"último rating {_value(rating, '/10')}")
            if avg is not None:
                detail.append(f"media últimos 5 {_value(avg, '/10')}")
            parts.append(player + (": " + ", ".join(detail) if detail else ""))
        return "Comparación descriptiva: " + "; ".join(parts) + "."

    stats = evidence.get("get_player_match_stats")
    if stats:
        rows = stats.get("rows") or []
        player = stats.get("player") or "El jugador"
        if not rows:
            return f"No hay historial jugador-partido disponible para {player}."
        return f"Hay {len(rows)} partidos recientes observados disponibles para {player}; abre la evidencia para revisar las acciones registradas."

    return _base._fallback(evidence)


def _model_ready(model: str, base_url: str) -> tuple[bool, str | None]:
    status = ollama_status(base_url)
    if not status.get("available"):
        return False, status.get("error") or "OLLAMA_UNAVAILABLE"
    if model not in (status.get("models") or []):
        return False, "MODEL_NOT_INSTALLED"
    return True, None


def run_coach_agent_turn(
    question: str,
    *,
    db_path: Path,
    team_id: str,
    history: list[dict[str, Any]] | None = None,
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

    previous = _last_user(history)
    is_follow = bool(previous and _followup(question))
    route_question = previous if is_follow else question

    calls = _deterministic_route(runtime, route_question)
    router_used = False
    if not calls:
        ready, model_error = _model_ready(selected_model, selected_url)
        if not ready:
            text = (
                "Ollama no está disponible localmente."
                if model_error != "MODEL_NOT_INSTALLED"
                else f"El modelo local `{selected_model}` no está instalado."
            )
            return CoachAgentResult(text, selected_model, 0, (), model_error)
        try:
            plan = _request_plan(selected_model, route_question, None if is_follow else history, selected_url)
            calls = _validated(plan)
            router_used = True
        except Exception as exc:
            return CoachAgentResult(_base.UNSUPPORTED_MESSAGE, selected_model, 0, (), f"INTENT_SELECTION:{type(exc).__name__}: {exc}")

    if is_follow:
        calls = _modify(calls, question)
        if not calls and not _is_evidence(question):
            ready, model_error = _model_ready(selected_model, selected_url)
            if not ready:
                return CoachAgentResult(_base.UNSUPPORTED_MESSAGE, selected_model, 0, (), model_error)
            try:
                plan = _request_plan(selected_model, f"Consulta anterior: {previous}\nSeguimiento: {question}", history, selected_url)
                calls = _validated(plan)
                router_used = True
            except Exception as exc:
                return CoachAgentResult(_base.UNSUPPORTED_MESSAGE, selected_model, 0, (), f"FOLLOWUP_SELECTION:{type(exc).__name__}: {exc}")

    if not calls:
        return CoachAgentResult(_base.UNSUPPORTED_MESSAGE, selected_model, 0, (), None)

    evidence: dict[str, Any] = {}
    tools: list[str] = []
    for name, args in calls:
        payload = _execute(runtime, name, args)
        evidence[name] = _compact_rank(payload) if name == "rank_players" else _legacy._compact_evidence(name, payload)
        tools.append(name)

    if _is_evidence(question):
        return CoachAgentResult(_evidence_answer(evidence), selected_model, 1 if router_used else 0, tuple(tools), None)

    idx = _ordinal(question) if is_follow else None
    if idx is not None:
        answer = _ordinal_answer(evidence, idx)
        if answer:
            return CoachAgentResult(answer, selected_model, 1 if router_used else 0, tuple(tools), None)

    text = _answer_from_evidence(question, evidence)
    return CoachAgentResult(text, selected_model, 1 if router_used else 0, tuple(tools), None)


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    return run_coach_agent_turn(*args, **kwargs).text
