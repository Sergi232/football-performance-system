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
    q = (question or "").strip().lower()
    return any(term in q for term in BLOCKED_TERMS)


def _fmt(value: Any) -> str:
    if value is None:
        return "no disponible"
    return str(value)


def _rating_explanation(rating: dict[str, Any]) -> str:
    if not rating:
        return "No hi ha Match Rating materialitzat disponible."
    labels = {
        "attacking_threat": "amenaça ofensiva",
        "creation_progression": "creació/progressió",
        "defensive_contribution": "contribució defensiva",
        "finishing": "finalització",
        "discipline": "disciplina",
    }
    parts = []
    for key, label in labels.items():
        value = rating.get(key)
        if value is not None:
            try:
                parts.append(f"{label} {float(value):.1f}")
            except (TypeError, ValueError):
                parts.append(f"{label} {_fmt(value)}")
    dimensions = ", ".join(parts) if parts else "sense dimensions de camp disponibles"
    try:
        rating_value = f"{float(rating.get('match_rating_10')):.1f}/10"
    except (TypeError, ValueError):
        rating_value = _fmt(rating.get("match_rating_10"))
    try:
        confidence = f"{float(rating.get('match_rating_confidence')):.0f}%"
    except (TypeError, ValueError):
        confidence = _fmt(rating.get("match_rating_confidence"))
    return (
        f"Match Rating: {rating_value}. Confiança d'evidència: {confidence}. "
        f"Context: {_fmt(rating.get('match_rating_context'))}. Evidència del partit: {dimensions}. "
        "La nota ja ve calculada pel motor analític; l'assistent només l'explica."
    )


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
        if any(term in q for term in ("rating", "nota", "forma", "evolució", "evolucio")):
            snapshot = context.get("match_rating_snapshot") or []
            return (
                f"Hi ha Match Rating materialitzat per {len(snapshot)} jugadors de la plantilla amb aparicions registrades. "
                "La vista d'equip permet consultar l'última nota, la mitjana dels últims 5 partits i el delta 5 vs 5. "
                "Aquestes dades són descriptives i no s'utilitzen aquí per generar un rànquing entre jugadors."
            )
        return (
            f"Equip: {_fmt(overview.get('matches'))} partits, {_fmt(overview.get('players'))} jugadors, "
            f"{_fmt(overview.get('player_minutes'))} minuts-jugador, {_fmt(overview.get('goals'))} gols i "
            f"{_fmt(overview.get('assists'))} assistències. "
            "Això és un resum descriptiu de les dades registrades; no és una valoració de rendiment."
        )

    if scope == "player":
        summary = context.get("summary") or {}
        gate = context.get("latest_role_fit_gate") or {}
        latest_rating = context.get("latest_match_rating") or {}
        latest_index = context.get("latest_performance_index") or {}

        if any(term in q for term in ("rating", "nota", "últim partit", "ultim partit", "per què", "perque", "per què té", "perque te")):
            text = _rating_explanation(latest_rating)
            if latest_index:
                try:
                    index_text = f"{float(latest_index.get('performance_score')):.1f}/100"
                except (TypeError, ValueError):
                    index_text = _fmt(latest_index.get("performance_score"))
                text += f" Performance Index complementari actual: {index_text}."
            return text

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
                rating_rows = context.get("match_ratings") or []
                if rating_rows:
                    return (
                        f"Hi ha {len(rating_rows)} Match Ratings disponibles per aquest jugador. "
                        "L'evolució es consulta sobre les notes player-match ja materialitzades; selecciona una mètrica concreta si vols descriure també una feature."
                    )
                return "No hi ha historial de Match Rating disponible."
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
        observations = context.get("observations") or {}
        ratings = context.get("match_ratings") or []
        base = (
            f"Partit {_fmt(match.get('match_date'))}, {_fmt(match.get('venue'))} contra {_fmt(match.get('opponent'))}: "
            f"{_fmt(match.get('score_for'))}-{_fmt(match.get('score_against'))}. "
            f"Formació registrada: {_fmt(match.get('starting_formation'))}. "
        )
        if any(term in q for term in ("rating", "nota", "valoració", "valoracio")):
            return base + (
                f"Hi ha {len(ratings)} Match Ratings materialitzats per als jugadors amb minuts. "
                "L'assistent pot explicar una nota concreta, però no recalcula ni substitueix el motor analític."
            )
        if any(term in q for term in ("què ha passat", "que ha passat", "resum", "observacions")):
            goals = observations.get("goal_scorers") or []
            assists = observations.get("assist_providers") or []
            goal_text = ", ".join(f"{x['player']} ({x['goals']})" for x in goals) or "cap golejador registrat"
            assist_text = ", ".join(f"{x['player']} ({x['assists']})" for x in assists) or "cap assistència registrada"
            return base + f"Gols registrats: {goal_text}. Assistències registrades: {assist_text}."
        return base + "Les estadístiques de jugador i els Match Ratings del context ja provenen de capes analítiques materialitzades."

    return "No hi ha un context estructurat compatible amb aquesta pregunta."
