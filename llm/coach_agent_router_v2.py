"""Router v2 for the local Coach Copilot.

Fixes ambiguous quality/GPS questions (for example asking whether current data are
sufficient to discuss fatigue) so they inspect data quality instead of being blocked
as if they were unsupported medical/performance recommendations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from llm import coach_agent_hybrid as _hybrid

_ORIGINAL_PLAN = _hybrid._plan_tools

QUALITY_TERMS = (
    "limitacions", "limitaciones", "qualitat", "calidad", "qualitat de dades",
    "calidad de datos", "dades falten", "datos faltan", "datos disponibles",
    "dades disponibles", "evidencia", "evidència", "cobertura", "missing",
    "tenim prou dades", "tenemos suficientes datos", "tenemos datos suficientes",
    "podem parlar", "podemos hablar", "es pot parlar", "se puede hablar",
)

GPS_TERMS = (
    "gps", "fisic", "físic", "fisico", "físico", "distancia", "distància",
    "velocitat", "velocidad", "carrega", "càrrega", "carga", "fatiga",
    "readiness", "disponibilitat física", "disponibilidad fisica",
)

RECOMMENDATION_TERMS = (
    "qui està fatigat", "quien esta fatigado", "quién está fatigado",
    "qui té fatiga", "quien tiene fatiga", "quién tiene fatiga",
    "risc de lesio", "risc de lesió", "riesgo de lesion", "riesgo de lesión",
    "qui hauria de ser titular", "quien deberia ser titular", "quién debería ser titular",
    "alineacio ideal", "alineació ideal", "alineacion ideal", "alineación ideal",
    "onze ideal", "once ideal", "millor onze", "mejor once",
)


def _norm(text: object) -> str:
    return _hybrid._norm(text)


def plan_tools_v2(
    question: str,
    *,
    db_path: Path,
    team_id: str,
    history: list[dict[str, str]] | None,
) -> tuple[list[tuple[str, dict[str, Any]]], str | None]:
    q = _norm(question)

    # Explicit unsupported decisions remain blocked.
    if any(_norm(term) in q for term in RECOMMENDATION_TERMS):
        return [], (
            "No puc donar aquesta recomanació perquè el sistema no té una política validada "
            "per convertir aquestes dades en una decisió d'alineació, fatiga o risc de lesió. "
            "Puc descriure l'evidència disponible sense convertir-la en una recomanació no validada."
        )

    # Questions about whether evidence is sufficient are quality questions, even if
    # they mention fatigue/readiness as something the current data may not support.
    if any(_norm(term) in q for term in QUALITY_TERMS):
        plan: list[tuple[str, dict[str, Any]]] = [("get_data_quality", {})]
        if any(_norm(term) in q for term in ("equip", "equipo", "forma", "tendencia", "tendència")):
            plan.append(("get_team_snapshot", {}))
        return plan[:3], None

    # Generic GPS/physical availability question without a named player -> quality.
    if any(_norm(term) in q for term in GPS_TERMS):
        players = _hybrid._find_players(db_path, team_id, question)
        if not players:
            return [("get_data_quality", {})], None

    return _ORIGINAL_PLAN(question, db_path=db_path, team_id=team_id, history=history)


def install() -> None:
    _hybrid._plan_tools = plan_tools_v2


install()
