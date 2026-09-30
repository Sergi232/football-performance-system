"""Router v2 for the local Coach Copilot.

Bilingual deterministic router for Spanish/Catalan open questions. It keeps the
LLM away from free SQL, routes only to approved read-only tools, resolves player
follow-ups from short conversation history, and distinguishes questions about data
sufficiency from unsupported recommendations about fatigue/injury/line-ups.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm import coach_agent_hybrid as _hybrid

# Only explicit data-quality/sufficiency language belongs here. Generic phrases such
# as "según los datos disponibles", "amb les dades disponibles" or "evidencia
# disponible" are deliberately excluded because they are grounding qualifiers, not
# requests for a second data-quality tool. Over-routing those phrases inflated the
# synthesis prompt and caused avoidable CPU timeouts in ordinary team/player queries.
QUALITY_TERMS = (
    "limitacions", "limitaciones", "qualitat", "calidad", "qualitat de dades",
    "calidad de datos", "dades falten", "datos faltan", "quines dades falten",
    "que datos faltan", "qué datos faltan", "cobertura", "missing",
    "tenim prou dades", "tenemos suficientes datos", "tenemos datos suficientes",
    "podem parlar", "podemos hablar", "es pot parlar", "se puede hablar",
    "manca de dades", "falta de datos", "dades insuficients", "datos insuficientes",
)

GPS_TERMS = (
    "gps", "fisic", "físic", "fisico", "físico", "distancia", "distància",
    "velocitat", "velocidad", "carrega", "càrrega", "carga", "fatiga",
    "readiness", "disponibilitat física", "disponibilidad fisica",
    "informacio fisica", "información física", "informacion fisica",
)

RECOMMENDATION_TERMS = (
    "qui està fatigat", "quien esta fatigado", "quién está fatigado",
    "qui té fatiga", "quien tiene fatiga", "quién tiene fatiga",
    "hauria de descansar", "deberia descansar", "debería descansar",
    "risc de lesio", "risc de lesió", "riesgo de lesion", "riesgo de lesión",
    "qui hauria de ser titular", "quien deberia ser titular", "quién debería ser titular",
    "alineacio ideal", "alineació ideal", "alineacion ideal", "alineación ideal",
    "onze ideal", "once ideal", "millor onze", "mejor once",
    "qui hauria de jugar", "quien deberia jugar", "quién debería jugar",
)

SPANISH_RECOMMENDATION_HINTS = (
    "quien esta fatigado", "quién está fatigado", "quien tiene fatiga", "quién tiene fatiga",
    "deberia descansar", "debería descansar", "riesgo de lesion", "riesgo de lesión",
    "quien deberia ser titular", "quién debería ser titular", "alineacion ideal",
    "alineación ideal", "once ideal", "mejor once", "quien deberia jugar",
    "quién debería jugar",
)

COMPARE_TERMS = (
    "compara", "comparar", "comparacio", "comparació", "comparacion", "comparación",
    "diferencies", "diferències", "diferencias", "versus", " vs ",
)

MATCH_TERMS = (
    "partit", "partido", "match", "contra", "rival", "ultim", "últim", "ultimo",
    "último", "darrer", "anterior encuentro", "último encuentro", "ultim encontre",
)

PLAYER_DETAIL_TERMS = (
    "per que", "per què", "por que", "por qué", "evoluc", "canvi", "cambio",
    "accions", "acciones", "estad", "rendiment recent", "rendimiento reciente",
    "ultims partits", "últimos partidos", "ultimos partidos", "mostra", "muestra",
    "nota", "rating", "match rating", "performance index", "motor expert",
    "motor experto",
)

TEAM_TERMS = (
    "equip", "equipo", "forma", "millorant", "mejorando", "empitjorant", "empeorando",
    "canvi recent", "cambio reciente", "tendencia", "tendència", "estat recent",
    "estado reciente", "qui presenta", "quien presenta", "quién presenta",
)

FOLLOWUP_TERMS = (
    "i com", "y como", "y cómo", "i que", "i què", "y que", "y qué", "la seva",
    "su ", "aquesta", "esta ", "esa ", "ell", "ella", "él", "ella",
)


def _norm(text: object) -> str:
    return _hybrid._norm(text)


def _history_text(history: list[dict[str, str]] | None) -> str:
    parts: list[str] = []
    for item in (history or [])[-4:]:
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            parts.append(content[:700])
    return " ".join(parts)


def _dedupe(plan: list[tuple[str, dict[str, Any]]]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for name, args in plan:
        key = name + json.dumps(args, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append((name, args))
    return out[:4]


def _recommendation_guardrail(question: str) -> str:
    q = _norm(question)
    if any(_norm(term) in q for term in SPANISH_RECOMMENDATION_HINTS):
        return (
            "No puedo dar esa recomendación porque el sistema no tiene una política validada "
            "para convertir estos datos en una decisión de alineación, fatiga o riesgo de lesión. "
            "Puedo describir la evidencia disponible sin convertirla en una recomendación no validada."
        )
    return (
        "No puc donar aquesta recomanació perquè el sistema no té una política validada "
        "per convertir aquestes dades en una decisió d'alineació, fatiga o risc de lesió. "
        "Puc descriure l'evidència disponible sense convertir-la en una recomanació no validada."
    )


def plan_tools_v2(
    question: str,
    *,
    db_path: Path,
    team_id: str,
    history: list[dict[str, str]] | None,
) -> tuple[list[tuple[str, dict[str, Any]]], str | None]:
    q = _norm(question)
    combined_raw = f"{_history_text(history)} {question}".strip()
    combined = _norm(combined_raw)

    # Resolve entities first so mixed intents (for example "explain X and state the
    # data limitations") can use both the domain tool and data-quality tool.
    players = _hybrid._find_players(db_path, team_id, combined_raw)

    # Explicit unsupported decisions remain blocked. The patterns are deliberately
    # specific, so an evidence-sufficiency question such as "do we have enough data
    # to discuss fatigue?" is not blocked.
    if any(_norm(term) in q for term in RECOMMENDATION_TERMS):
        return [], _recommendation_guardrail(question)

    plan: list[tuple[str, dict[str, Any]]] = []

    # Data-quality is compositional only when the user explicitly asks about quality,
    # missingness, coverage or sufficiency. Generic grounding qualifiers do not add it.
    quality_question = any(_norm(term) in q for term in QUALITY_TERMS)
    if quality_question:
        plan.append(("get_data_quality", {}))

    # Comparisons need both resolved players and one bounded comparison tool.
    if len(players) >= 2 and any(_norm(term) in q for term in COMPARE_TERMS):
        plan.append(("compare_players", {"players": players[:6]}))
        return _dedupe(plan), None

    # Physical/GPS questions about a named player use that player's GPS view.
    if any(_norm(term) in q for term in GPS_TERMS):
        if players:
            plan.append(("get_player_gps", {"player": players[0]}))
        else:
            plan.append(("get_data_quality", {}))

    # Match resolution works from the current question plus short history.
    match_query = _hybrid._resolve_match_query(db_path, team_id, combined_raw)
    if match_query and any(_norm(term) in q for term in MATCH_TERMS):
        plan.append(("get_match_detail", {"match": match_query}))

    # Named-player questions get a profile. Evolution/why/action questions also inspect
    # recent player-match evidence. This also handles pronoun follow-ups via history.
    if players and not any(name == "compare_players" for name, _ in plan):
        plan.append(("get_player_profile", {"player": players[0]}))
        needs_detail = any(_norm(term) in q for term in PLAYER_DETAIL_TERMS)
        if history and any(_norm(term) in q for term in FOLLOWUP_TERMS):
            needs_detail = True
        if needs_detail:
            plan.append(("get_player_match_stats", {"player": players[0], "last_n": 5}))

    # Team-level open questions without a named player get the team snapshot.
    if any(_norm(term) in q for term in TEAM_TERMS) and not players:
        plan.append(("get_team_snapshot", {}))

    # Generic match wording such as "último partido" may resolve after earlier branches.
    if not any(name == "get_match_detail" for name, _ in plan):
        if match_query and any(_norm(term) in combined for term in MATCH_TERMS):
            plan.append(("get_match_detail", {"match": match_query}))

    if not plan:
        # Open-question fallback remains descriptive and auditable.
        plan.append(("get_team_snapshot", {}))

    return _dedupe(plan), None


def install() -> None:
    _hybrid._plan_tools = plan_tools_v2


install()
