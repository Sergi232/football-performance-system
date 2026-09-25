"""Deterministic assistant facade and safety guardrails.

This module remains the safety baseline even when a generative provider is enabled.
It answers only from structured context and blocks requests that would require an
unvalidated ranking or tactical recommendation policy.
"""
from __future__ import annotations

from typing import Any


BLOCKED_TERMS = (
    "millor jugador",
    "pitjor jugador",
    "qui està millorant més",
    "qui esta millorant mes",
    "qui rendeix millor",
    "qui rendeix pitjor",
    "millor com a",
    "pitjor com a",
    "recomana",
    "recomanació",
    "recomanacio",
    "qui hauria",
    "hauria de jugar",
    "hauria de ser titular",
    "alineació ideal",
    "alineacio ideal",
    "onze ideal",
    "best player",
    "worst player",
    "who is best",
    "who is worst",
    "who should start",
    "recommend",
)


def is_blocked_question(question: str) -> bool:
    """Return True when answering would require unvalidated evaluative policy."""
    q = (question or "").strip().lower()
    return any(term in q for term in BLOCKED_TERMS)


def _fmt(value: Any) -> str:
    if value is None:
        return "no disponible"
    return str(value)


def answer_from_context(question: str, context: dict[str, Any]) -> str:
    q = (question or "").strip().lower()
    if not q:
        return "Escriu una pregunta sobre les dades disponibles."

    if is_blocked_question(question):
        return (
            "Aquesta pregunta requereix un ranking o una política de recomanació que encara no està validada. "
            "El sistema pot mostrar evidència descriptiva, però no convertir-la en una recomanació tàctica."
        )

    scope = context.get("scope")

    if scope == "team":
        overview = context.get("overview") or {}
        return (
            f"Equip: {_fmt(overview.get('matches'))} partits, {_fmt(overview.get('players'))} jugadors, "
            f"{_fmt(overview.get('player_minutes'))} minuts-jugador, {_fmt(overview.get('goals'))} gols i "
            f"{_fmt(overview.get('assists'))} assistències. "
            "Això és un resum descriptiu de les dades registrades; no és una valoració de rendiment."
        )

    if scope == "player":
        summary = context.get("summary") or {}
        gate = context.get("latest_role_fit_gate") or {}

        if any(term in q for term in ("rol", "encaix", "fit", "evidència", "evidencia")):
            return (
                f"Rol observat més recent: {_fmt(gate.get('observed_role'))}. "
                f"Historial del mateix rol: {_fmt(gate.get('same_role_history'))}. "
                f"Senyals avaluables: {_fmt(gate.get('evaluable_signals'))}. "
                f"Cobertura d'evidència: {_fmt(gate.get('evidence_coverage'))}. "
                f"Estat final: {_fmt(gate.get('final_status'))}. "
                "N12000/N13000 exposen evidència, però no emeten una recomanació mentre la política final no estigui validada."
            )

        if any(term in q for term in ("evolució", "evolucio", "tendència", "tendencia", "mètrica", "metrica")):
            feature_name = context.get("feature_name")
            rows = [r for r in (context.get("feature_history") or []) if r.get("feature_value") is not None]
            if not feature_name:
                return "Selecciona una feature concreta per descriure la seva evolució."
            if not rows:
                return f"No hi ha valors disponibles per a {feature_name}."
            first = rows[0]
            last = rows[-1]
            return (
                f"{feature_name}: primer valor disponible {_fmt(first.get('feature_value'))} "
                f"({_fmt(first.get('match_date'))}) i últim valor {_fmt(last.get('feature_value'))} "
                f"({_fmt(last.get('match_date'))}). "
                "La diferència es mostra de forma descriptiva; no s'etiqueta com a millora o empitjorament."
            )

        return (
            f"Jugador: {_fmt(summary.get('player'))}. Aparicions: {_fmt(summary.get('appearances'))}; "
            f"titularitats: {_fmt(summary.get('starts'))}; minuts: {_fmt(summary.get('minutes'))}; "
            f"gols: {_fmt(summary.get('goals'))}; assistències: {_fmt(summary.get('assists'))}; "
            f"rols observats: {_fmt(summary.get('observed_roles'))}."
        )

    if scope == "match":
        match = context.get("match") or {}
        return (
            f"Partit {_fmt(match.get('match_date'))}, {_fmt(match.get('venue'))} contra {_fmt(match.get('opponent'))}: "
            f"{_fmt(match.get('score_for'))}-{_fmt(match.get('score_against'))}. "
            f"Formació registrada: {_fmt(match.get('starting_formation'))}. "
            "Les estadístiques de jugador mostrades al context són dades player-match observades/brutes."
        )

    return "No hi ha un context estructurat compatible amb aquesta pregunta."
