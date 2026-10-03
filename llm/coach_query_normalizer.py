"""Conservative normalization for natural Coach Copilot questions.

The LLM remains the primary semantic router. This module only canonicalizes a
small set of high-confidence supported intents when spelling, accents or terse
coach phrasing would otherwise make routing brittle. It never calculates data
or selects unsupported football conclusions.
"""
from __future__ import annotations

import re
import unicodedata


def _norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text.casefold())
    return " ".join(text.split())


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _player_alias(text: str) -> str | None:
    match = re.search(r"\bjugador\s*0*(\d{1,3})\b", text)
    if not match:
        return None
    return f"Jugador {int(match.group(1)):02d}"


def _rival_alias(text: str) -> str | None:
    match = re.search(r"\brival\s*0*(\d{1,3})\b", text)
    if not match:
        return None
    return f"Rival {int(match.group(1)):02d}"


def canonicalize_question(question: str) -> str:
    """Return a canonical supported phrasing only for high-confidence intents.

    Unknown or ambiguous questions are returned unchanged so Granite remains the
    primary interpreter and unsupported questions still fail closed.
    """
    original = str(question or "").strip()
    q = _norm(original)
    if not q:
        return original

    # Policy-sensitive questions must reach the existing guardrails unchanged.
    if _contains_any(
        q,
        (
            "fatiga", "fatigad", "cansancio", "cansad", "agotad", "readiness",
            "lesion", "once ideal", "alineacion ideal", "deberia jugar",
            "deberia ser titular", "tactica recomiendas", "sistema recomiendas",
        ),
    ):
        return original

    ranking_hint = _contains_any(q, ("maximo", "maxima", "mas ", "mayor", "lider", "top", "mejor"))

    if _contains_any(q, ("goleador", "goleadora", "goles", "ha marcado", "marca mas", "mas gol")) and ranking_hint:
        return "¿Quién es el máximo goleador?"

    if _contains_any(q, ("asistencia", "asistencias", "asistente")) and ranking_hint:
        return "¿Quién lleva más asistencias?"

    if _contains_any(q, ("remate", "remates", "disparo", "disparos", "tira mas")) and ranking_hint:
        return "¿Quién acumula más remates?"

    if _contains_any(q, ("minutos", "minuto", "ha jugado", "juega mas")) and ranking_hint:
        return "¿Quién acumula más minutos?"

    if _contains_any(q, ("apariciones", "partidos jugados", "ha jugado mas partidos")) and ranking_hint:
        return "¿Quién acumula más apariciones?"

    player = _player_alias(q)
    if player and _contains_any(q, ("gps", "fisico", "fisica", "distancia", "velocidad")):
        return f"Enséñame los datos GPS de {player}."

    if player and _contains_any(q, ("evolucion", "evolucionado", "mejorado", "empeorado", "forma", "rendimiento")):
        return f"¿Cómo ha evolucionado {player} últimamente?"

    rival = _rival_alias(q)
    if rival and _contains_any(q, ("contra", "vs", "versus", "partido", "paso", "resultado", "rival")):
        return f"¿Qué pasó contra {rival}?"

    if _contains_any(q, ("calidad de datos", "limitaciones de datos", "datos incompletos", "cobertura de datos")):
        return "¿Qué limitaciones de datos tenemos?"

    if _contains_any(q, ("estado del equipo", "estado equipo", "forma del equipo", "como esta el equipo", "como va el equipo")):
        return "Resume el estado reciente del equipo."

    return original
