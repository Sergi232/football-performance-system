"""Deterministic semantic guard for Coach Copilot.

The local LLM may propose wording, but the MVP answer returned to the coach is built
from the structured evidence for the validated tool families. This prevents fluent
but unsupported paraphrases (wrong roles, invented qualitative claims, mistranslated
football actions) from reaching the product.

No rating, feature or expert output is recalculated here. The renderer only selects,
orders and formats fields already returned by validated read-only tools.
"""
from __future__ import annotations

import re
from typing import Any

from llm import coach_agent_hybrid as _hybrid

_ORIGINAL_POSTPROCESS = _hybrid._postprocess_grounded


def _lang(question: str) -> str:
    q = _hybrid._norm(question)
    ca = (
        "resumeix", "equip", "partit", "dades", "rendiment", "ultim partit",
        "que ha canviat", "qui presenta", "hauria", "explica'm", "com ha evolucionat",
        "quines", "jugadors", "informacio gps", "sense inferir",
    )
    es = (
        "resume el", "equipo", "partido", "datos", "rendimiento", "ultimo partido",
        "que ha cambiado", "quien presenta", "deberia", "explicame", "como ha evolucionado",
        "que limitaciones", "jugadores", "informacion gps", "sin inferir",
    )
    ca_score = sum(int(x in q) for x in ca)
    es_score = sum(int(x in q) for x in es)
    return "ca" if ca_score > es_score else "es"


def _value(mapping: Any, *keys: str) -> Any:
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "":
            return value
    return None


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _score(row: dict[str, Any]) -> Any:
    return _value(row, "match_rating", "rating", "latest_match_rating", "avg_last5")


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _recent_rating_sequence(profile: dict[str, Any], lang: str) -> str | None:
    rows = [r for r in (profile.get("recent_match_ratings") or []) if isinstance(r, dict)]
    items: list[str] = []
    for row in rows[-4:]:
        rating = _score(row)
        if rating is None:
            continue
        opponent = _value(row, "opponent")
        date = _value(row, "match_date")
        label = str(opponent or date or "partit" if lang == "ca" else opponent or date or "partido")
        items.append(f"{label}: {_fmt(rating)}")
    if not items:
        return None
    prefix = "Últims Match Ratings" if lang == "ca" else "Últimos Match Ratings"
    return f"{prefix}: " + "; ".join(items) + "."


def _team_answer(payload: dict[str, Any], lang: str) -> str:
    overview = payload.get("overview") or {}
    history = [r for r in (payload.get("recent_team_rating_history") or []) if isinstance(r, dict)]
    form = [r for r in (payload.get("player_recent_form") or []) if isinstance(r, dict)]
    parts: list[str] = []

    if history:
        row = history[-1]
        opponent = _value(row, "opponent")
        sf = _value(row, "score_for")
        sa = _value(row, "score_against")
        result = _value(row, "result")
        team_rating = _value(row, "team_avg_rating", "avg_match_rating")
        if lang == "ca":
            sentence = f"Últim registre de l'equip"
            if opponent:
                sentence += f" contra {opponent}"
            if sf is not None and sa is not None:
                sentence += f": {_fmt(sf)}-{_fmt(sa)}"
            elif result:
                sentence += f": {result}"
            if team_rating is not None:
                sentence += f", Match Rating mitjà {_fmt(team_rating)}"
        else:
            sentence = "Último registro del equipo"
            if opponent:
                sentence += f" contra {opponent}"
            if sf is not None and sa is not None:
                sentence += f": {_fmt(sf)}-{_fmt(sa)}"
            elif result:
                sentence += f": {result}"
            if team_rating is not None:
                sentence += f", Match Rating medio {_fmt(team_rating)}"
        parts.append(sentence + ".")

    if form:
        row = form[0]
        player = _value(row, "player")
        delta = _value(row, "trend_delta_5v5")
        n1 = _value(row, "n_last5")
        n0 = _value(row, "n_previous5")
        if player and delta is not None:
            if lang == "ca":
                sentence = f"El canvi 5-vs-5 més positiu disponible és {player}: {_fmt(delta)}"
                if n1 is not None and n0 is not None:
                    sentence += f" (mostres {_fmt(n1)} i {_fmt(n0)})"
            else:
                sentence = f"El cambio 5-vs-5 más positivo disponible es {player}: {_fmt(delta)}"
                if n1 is not None and n0 is not None:
                    sentence += f" (muestras {_fmt(n1)} y {_fmt(n0)})"
            parts.append(sentence + ".")

    if not parts:
        matches = _value(overview, "matches", "match_count")
        players = _value(overview, "players", "player_count")
        if lang == "ca":
            parts.append(
                f"La base disponible conté {_fmt(matches) if matches is not None else 'dades de'} partits"
                + (f" i {_fmt(players)} jugadors" if players is not None else "") + "."
            )
        else:
            parts.append(
                f"La base disponible contiene {_fmt(matches) if matches is not None else 'datos de'} partidos"
                + (f" y {_fmt(players)} jugadores" if players is not None else "") + "."
            )
    return " ".join(parts[:3])


def _player_answer(profile: dict[str, Any], lang: str, question: str) -> str:
    player = str(profile.get("player") or ("El jugador" if lang == "es" else "El jugador"))
    summary = profile.get("summary") or {}
    appearances = _value(summary, "appearances", "apps", "matches")
    starts = _value(summary, "starts", "started")
    minutes = _value(summary, "minutes", "mins")
    goals = _value(summary, "goals")
    assists = _value(summary, "assists")
    role = _value(summary, "primary_role", "role", "position", "primary_position")
    parts: list[str] = []

    if lang == "ca":
        base = f"{player}"
        details: list[str] = []
        if appearances is not None:
            details.append(f"{_fmt(appearances)} aparicions")
        if starts is not None:
            details.append(f"{_fmt(starts)} titularitats")
        if minutes is not None:
            details.append(f"{_fmt(minutes)} minuts")
        if details:
            base += ": " + ", ".join(details)
        if role:
            base += f"; rol/posició registrada: {role}"
        parts.append(base + ".")
        ga: list[str] = []
        if goals is not None:
            ga.append(f"{_fmt(goals)} gols")
        if assists is not None:
            ga.append(f"{_fmt(assists)} assistències")
        if ga:
            parts.append("Producció registrada: " + ", ".join(ga) + ".")
    else:
        base = f"{player}"
        details = []
        if appearances is not None:
            details.append(f"{_fmt(appearances)} apariciones")
        if starts is not None:
            details.append(f"{_fmt(starts)} titularidades")
        if minutes is not None:
            details.append(f"{_fmt(minutes)} minutos")
        if details:
            base += ": " + ", ".join(details)
        if role:
            base += f"; rol/posición registrada: {role}"
        parts.append(base + ".")
        ga = []
        if goals is not None:
            ga.append(f"{_fmt(goals)} goles")
        if assists is not None:
            ga.append(f"{_fmt(assists)} asistencias")
        if ga:
            parts.append("Producción registrada: " + ", ".join(ga) + ".")

    seq = _recent_rating_sequence(profile, lang)
    q = _hybrid._norm(question)
    if seq and any(t in q for t in ("evoluc", "ultimos", "ultims", "recent", "rendiment", "rendimiento")):
        parts.append(seq)
    return " ".join(parts[:4])


def _compare_answer(payload: dict[str, Any], lang: str) -> str:
    rows = [r for r in (payload.get("players") or []) if isinstance(r, dict) and r.get("player")]
    if len(rows) < 2:
        return "No hi ha dos perfils comparables disponibles." if lang == "ca" else "No hay dos perfiles comparables disponibles."
    a, b = rows[0], rows[1]
    lines: list[str] = []
    for row in (a, b):
        name = str(row.get("player"))
        role = _value(row, "position", "role")
        avg5 = _value(row, "avg_last5")
        delta = _value(row, "trend_delta_5v5")
        n5 = _value(row, "n_last5")
        pieces: list[str] = []
        if role:
            pieces.append(f"rol/posició {role}" if lang == "ca" else f"rol/posición {role}")
        if avg5 is not None:
            pieces.append(f"mitjana últims 5 {_fmt(avg5)}" if lang == "ca" else f"media últimos 5 {_fmt(avg5)}")
        if delta is not None:
            pieces.append(f"canvi 5-vs-5 {_fmt(delta)}" if lang == "ca" else f"cambio 5-vs-5 {_fmt(delta)}")
        if n5 is not None:
            pieces.append(f"mostra {_fmt(n5)}" if lang == "ca" else f"muestra {_fmt(n5)}")
        lines.append(f"{name}: " + ", ".join(pieces) + ".")

    av = _num(_value(a, "avg_last5"))
    bv = _num(_value(b, "avg_last5"))
    if av is not None and bv is not None:
        if av > bv:
            leader = str(a.get("player"))
        elif bv > av:
            leader = str(b.get("player"))
        else:
            leader = ""
        if leader:
            lines.append(
                (f"En la mitjana materialitzada dels últims cinc, {leader} té el valor més alt." if lang == "ca" else
                 f"En la media materializada de los últimos cinco, {leader} tiene el valor más alto.")
            )
    lines.append(
        "La comparació és descriptiva i s'ha d'interpretar respectant rol i mida de mostra."
        if lang == "ca" else
        "La comparación es descriptiva y debe interpretarse respetando rol y tamaño de muestra."
    )
    return " ".join(lines[:4])


def _match_answer(payload: dict[str, Any], lang: str) -> str:
    match = payload.get("match") or {}
    opponent = _value(match, "opponent")
    date = _value(match, "match_date", "date")
    sf = _value(match, "score_for")
    sa = _value(match, "score_against")
    result = _value(match, "result")
    parts: list[str] = []
    if lang == "ca":
        sentence = "Partit"
        if opponent:
            sentence += f" contra {opponent}"
        if date:
            sentence += f" ({date})"
        if sf is not None and sa is not None:
            sentence += f": {_fmt(sf)}-{_fmt(sa)}"
        elif result:
            sentence += f": {result}"
    else:
        sentence = "Partido"
        if opponent:
            sentence += f" contra {opponent}"
        if date:
            sentence += f" ({date})"
        if sf is not None and sa is not None:
            sentence += f": {_fmt(sf)}-{_fmt(sa)}"
        elif result:
            sentence += f": {result}"
    parts.append(sentence + ".")

    ratings = [r for r in (payload.get("ratings") or []) if isinstance(r, dict) and r.get("player")]
    scored = [(r, _num(_score(r))) for r in ratings]
    scored = [(r, s) for r, s in scored if s is not None]
    scored.sort(key=lambda x: x[1], reverse=True)
    if scored:
        top = scored[:3]
        items = ", ".join(f"{r.get('player')} {_fmt(s)}" for r, s in top)
        parts.append(("Match Ratings més alts: " if lang == "ca" else "Match Ratings más altos: ") + items + ".")
    return " ".join(parts[:3])


def _quality_answer(payload: dict[str, Any], lang: str) -> str:
    gps = payload.get("gps_status") or {}
    err = payload.get("attention_error")
    rows = _value(gps, "rows")
    matches = _value(gps, "matches")
    players = _value(gps, "players")
    imports = _value(gps, "imports")
    parts: list[str] = []
    if err:
        parts.append((f"Hi ha un error de qualitat/context: {err}." if lang == "ca" else f"Hay un error de calidad/contexto: {err}."))
    if rows == 0 or (rows is None and not payload.get("recent_flags")):
        parts.append(
            "No hi ha registres GPS disponibles a la base actual."
            if lang == "ca" else
            "No hay registros GPS disponibles en la base actual."
        )
    elif rows is not None:
        details = [f"rows={_fmt(rows)}"]
        if matches is not None:
            details.append(f"matches={_fmt(matches)}")
        if players is not None:
            details.append(f"players={_fmt(players)}")
        if imports is not None:
            details.append(f"imports={_fmt(imports)}")
        parts.append(("Estat GPS: " if lang == "ca" else "Estado GPS: ") + ", ".join(details) + ".")
    parts.append(
        "Aquesta capa només valida qualitat/context; no valida fatiga, risc de lesió ni llindars de rendiment."
        if lang == "ca" else
        "Esta capa solo valida calidad/contexto; no valida fatiga, riesgo de lesión ni umbrales de rendimiento."
    )
    return " ".join(parts[:3])


def _gps_answer(payload: dict[str, Any], lang: str) -> str:
    player = str(payload.get("player") or ("jugador" if lang == "ca" else "jugador"))
    history = [r for r in (payload.get("gps_history") or []) if isinstance(r, dict)]
    if not history:
        return (
            f"No hi ha registres GPS disponibles de {player}. La capa GPS és descriptiva i no permet inferir fatiga, readiness o risc de lesió."
            if lang == "ca" else
            f"No hay registros GPS disponibles de {player}. La capa GPS es descriptiva y no permite inferir fatiga, readiness o riesgo de lesión."
        )
    latest = history[-1]
    fields = [(k, v) for k, v in latest.items() if v is not None][:4]
    body = ", ".join(f"{k}={_fmt(v)}" for k, v in fields)
    return (
        f"Últim registre GPS de {player}: {body}. És una lectura descriptiva; no permet inferir fatiga, readiness o risc de lesió."
        if lang == "ca" else
        f"Último registro GPS de {player}: {body}. Es una lectura descriptiva; no permite inferir fatiga, readiness o riesgo de lesión."
    )


def deterministic_answer(question: str, evidence: dict[str, Any]) -> str:
    lang = _lang(question)
    if "compare_players" in evidence:
        return _compare_answer(evidence["compare_players"], lang)
    if "get_match_detail" in evidence:
        return _match_answer(evidence["get_match_detail"], lang)
    if "get_player_gps" in evidence:
        return _gps_answer(evidence["get_player_gps"], lang)
    if "get_data_quality" in evidence and len(evidence) == 1:
        return _quality_answer(evidence["get_data_quality"], lang)
    if "get_player_profile" in evidence:
        return _player_answer(evidence["get_player_profile"], lang, question)
    if "get_team_snapshot" in evidence:
        return _team_answer(evidence["get_team_snapshot"], lang)
    if "get_data_quality" in evidence:
        return _quality_answer(evidence["get_data_quality"], lang)
    return (
        "No hi ha prou evidència estructurada per respondre aquesta pregunta."
        if lang == "ca" else
        "No hay suficiente evidencia estructurada para responder esta pregunta."
    )


def postprocess_grounded_safe(question: str, text: str, evidence: dict[str, Any]) -> str:
    """Return the evidence-derived deterministic answer for validated MVP tools.

    The LLM candidate is still generated upstream, but cannot override structured
    facts in the final MVP response. This is intentionally conservative after human
    review found fluent semantic hallucinations that numeric-only checks could not
    detect.
    """
    baseline = deterministic_answer(question, evidence).strip()
    if baseline:
        return baseline
    return _ORIGINAL_POSTPROCESS(question, text, evidence)


def install() -> None:
    _hybrid._postprocess_grounded = postprocess_grounded_safe


install()
