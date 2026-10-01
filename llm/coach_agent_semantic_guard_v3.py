"""Semantic-guard refinements for player rating/component questions.

Extends the V5 evidence adapter with the materialized Match Rating dimensions,
Performance Index fields and expert-gate state so the safe renderer can answer
'why this rating?' and 'separate Match Rating / Performance Index / expert engine'
without free-form invention.
"""
from __future__ import annotations

from typing import Any

from llm import coach_agent_hybrid as _hybrid
from llm import coach_agent_semantic_guard as _guard
from llm import coach_agent_semantic_guard_v2 as _v2

_BASE_PLAYER_ANSWER = _guard._player_answer


def _alias(mapping: Any, aliases: dict[str, tuple[str, ...]]) -> dict[str, Any]:
    if not isinstance(mapping, dict):
        return {}
    out: dict[str, Any] = {}
    for target, sources in aliases.items():
        for source in sources:
            value = mapping.get(source)
            if value is not None and value != "":
                out[target] = value
                break
    return out


def compact_payload_v6(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if name != "get_player_profile":
        return _v2.compact_payload_v5(name, payload)

    summary = _alias(payload.get("summary"), {
        "player_id": ("player_id",),
        "player": ("player",),
        "appearances": ("appearances",),
        "starts": ("starts",),
        "minutes": ("minutes",),
        "goals": ("goals",),
        "assists": ("assists",),
        "role": ("observed_roles", "primary_role", "role", "position"),
    })

    ratings: list[dict[str, Any]] = []
    for row in (payload.get("recent_match_ratings") or [])[-5:]:
        ratings.append(_alias(row, {
            "match_date": ("match_date",),
            "opponent": ("opponent",),
            "minutes": ("minutes_played", "minutes"),
            "role": ("primary_role", "role"),
            "position": ("position_group", "position"),
            "match_rating": ("match_rating_10", "match_rating", "rating"),
            "confidence": ("match_rating_confidence", "confidence"),
            "route": ("rating_path", "route", "rating_route"),
            "attacking_threat": ("attacking_threat",),
            "creation_progression": ("creation_progression",),
            "defensive_contribution": ("defensive_contribution",),
            "finishing": ("finishing",),
            "discipline": ("discipline",),
        }))

    pi = _alias(payload.get("latest_performance_index"), {
        "match_date": ("match_date",),
        "role": ("primary_role",),
        "position": ("position_group",),
        "dimension_coverage_count": ("dimension_coverage_count",),
        "attacking_threat": ("attacking_threat",),
        "creation_progression": ("creation_progression",),
        "defensive_contribution": ("defensive_contribution",),
        "finishing": ("finishing",),
        "discipline": ("discipline",),
        "performance_score": ("performance_score",),
        "confidence": ("score_evidence_confidence",),
        "status": ("score_status",),
    })

    gate = _alias(payload.get("latest_expert_gate"), {
        "match_date": ("match_date",),
        "observed_role": ("observed_role",),
        "same_role_history": ("same_role_history",),
        "evaluable_signals": ("evaluable_signals",),
        "evidence_coverage": ("evidence_coverage",),
        "evidence_availability": ("evidence_availability",),
        "recommendation_gate": ("recommendation_gate",),
        "policy_status": ("policy_status",),
        "final_status": ("final_status",),
    })

    return {
        "player": payload.get("player"),
        "summary": summary,
        "recent_match_ratings": ratings,
        "latest_performance_index": pi,
        "latest_expert_gate": gate,
    }


def _latest_rating(profile: dict[str, Any]) -> dict[str, Any]:
    rows = [r for r in (profile.get("recent_match_ratings") or []) if isinstance(r, dict)]
    return rows[-1] if rows else {}


def player_answer_v3(profile: dict[str, Any], lang: str, question: str) -> str:
    q = _hybrid._norm(question)
    player = str(profile.get("player") or "Jugador")
    latest = _latest_rating(profile)
    components_question = (
        "performance index" in q
        or "motor expert" in q
        or "motor experto" in q
        or ("separa" in q and "match rating" in q)
    )
    rating_question = any(token in q for token in ("per que", "por que", "nota recent", "nota reciente", "match rating", "aquesta nota", "esta nota"))

    if components_question:
        mr = latest.get("match_rating")
        pi = profile.get("latest_performance_index") or {}
        gate = profile.get("latest_expert_gate") or {}
        pi_score = pi.get("performance_score")
        gate_status = gate.get("final_status") or gate.get("recommendation_gate") or gate.get("policy_status")
        lines: list[str] = []
        if lang == "ca":
            lines.append(f"{player}: són tres capes diferents.")
            lines.append(f"Match Rating: {_guard._fmt(mr) if mr is not None else 'no disponible en l’evidència actual'}.")
            lines.append(f"Performance Index: {_guard._fmt(pi_score) if pi_score is not None else 'no disponible en l’evidència actual'}.")
            lines.append(f"Motor expert: {gate_status if gate_status is not None else 'estat no disponible en l’evidència actual'}.")
        else:
            lines.append(f"{player}: son tres capas distintas.")
            lines.append(f"Match Rating: {_guard._fmt(mr) if mr is not None else 'no disponible en la evidencia actual'}.")
            lines.append(f"Performance Index: {_guard._fmt(pi_score) if pi_score is not None else 'no disponible en la evidencia actual'}.")
            lines.append(f"Motor experto: {gate_status if gate_status is not None else 'estado no disponible en la evidencia actual'}.")
        return " ".join(lines)

    if rating_question and latest:
        rating = latest.get("match_rating")
        opponent = latest.get("opponent")
        role = latest.get("role") or latest.get("position")
        dims = []
        labels = {
            "attacking_threat": ("amenaça ofensiva", "amenaza ofensiva"),
            "creation_progression": ("creació/progressió", "creación/progresión"),
            "defensive_contribution": ("contribució defensiva", "contribución defensiva"),
            "finishing": ("finalització", "finalización"),
            "discipline": ("disciplina", "disciplina"),
        }
        for key, translated in labels.items():
            value = latest.get(key)
            if value is not None:
                dims.append(f"{translated[0 if lang == 'ca' else 1]} {_guard._fmt(value)}")
        if lang == "ca":
            first = f"{player}: l’últim Match Rating materialitzat és {_guard._fmt(rating) if rating is not None else 'no disponible'}"
            if opponent:
                first += f" contra {opponent}"
            if role:
                first += f" amb rol/posició {role}"
            first += "."
            second = "Dimensions materialitzades: " + ", ".join(dims) + "." if dims else "No hi ha dimensions addicionals disponibles en aquesta evidència."
            third = "Això descriu els components registrats; no atribueix causes que les dades no validen."
        else:
            first = f"{player}: el último Match Rating materializado es {_guard._fmt(rating) if rating is not None else 'no disponible'}"
            if opponent:
                first += f" contra {opponent}"
            if role:
                first += f" con rol/posición {role}"
            first += "."
            second = "Dimensiones materializadas: " + ", ".join(dims) + "." if dims else "No hay dimensiones adicionales disponibles en esta evidencia."
            third = "Esto describe los componentes registrados; no atribuye causas que los datos no validan."
        return " ".join((first, second, third))

    return _BASE_PLAYER_ANSWER(profile, lang, question)


def install() -> None:
    _hybrid._compact_payload = compact_payload_v6
    _guard._player_answer = player_answer_v3
    _hybrid._postprocess_grounded = _guard.postprocess_grounded_safe


install()
