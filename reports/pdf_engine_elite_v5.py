"""Elite technical PDF renderer v5.

Team Pulse refinement over v4:
- Team technical cards/table use Último / Últimos 10 / Todos;
- the descriptive delta is Últimos 10 minus all available matches in the report period;
- legacy 5v5 remains unchanged for squad trend/change because it answers a different question;
- Player and Match reports remain unchanged from v4.

No critical metric is recalculated here and no tactical cause is asserted.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from reports import pdf_engine_elite_v2 as base_v2
from reports import pdf_engine_elite_v3 as base_v3
from reports import pdf_engine_elite_v4 as base_v4


def _team_value(item: dict[str, Any] | None, field: str) -> str:
    if not item:
        return "-"
    value = base_v2._num(item.get(field))
    if value is None:
        return "-"
    decimals = int(item.get("decimals") or 1)
    suffix = str(item.get("suffix") or "")
    if field.startswith("delta"):
        sign = "+" if value > 0 else ""
        if str(item.get("key")) == "pass_completion_pct":
            return f"{sign}{value:.{decimals}f} pp"
        return f"{sign}{value:.{decimals}f}"
    return f"{value:.{decimals}f}{suffix}"


def _team_phase_cards(profile: list[dict[str, Any]], width: float, styles) -> Any:
    by_key = {str(item.get("key")): item for item in profile}

    def val(key: str, field: str) -> str:
        return _team_value(by_key.get(key), field)

    return base_v2._insight_grid([
        (
            "Con balón",
            f"Últimos 10 · Pase {val('pass_completion_pct', 'last10')}",
            f"Todos · Pase {val('pass_completion_pct', 'all')}",
            base_v2.TEAL,
        ),
        (
            "Finalización",
            f"Últimos 10 · Remates {val('shots_total', 'last10')} · Goles {val('goals', 'last10')}",
            f"Todos · {val('shots_total', 'all')} remates · {val('goals', 'all')} goles",
            base_v2.NAVY_2,
        ),
        (
            "Recuperación defensiva",
            f"Últimos 10 · Entradas {val('tackles_won', 'last10')} · Interc. {val('interceptions', 'last10')}",
            f"Todos · {val('tackles_won', 'all')} entradas · {val('interceptions', 'all')} interc.",
            base_v2.AMBER,
        ),
        (
            "Pérdidas",
            f"Últimos 10 · Pérdidas {val('turnovers', 'last10')} · Desposesiones {val('dispossessed', 'last10')}",
            f"Todos · {val('turnovers', 'all')} pérdidas · {val('dispossessed', 'all')} desposesiones",
            base_v2.RED,
        ),
    ], width, styles)


def _team_profile_table(profile: list[dict[str, Any]], styles) -> Any:
    rows = [["Indicador", "Último", "Últimos 10", "Todos", "Δ 10 vs todos"]]
    for item in profile:
        rows.append([
            item.get("label"),
            _team_value(item, "current"),
            _team_value(item, "last10"),
            _team_value(item, "all"),
            _team_value(item, "delta_10_all"),
        ])
    return base_v2._compact_table(rows, [57 * mm, 26 * mm, 30 * mm, 28 * mm, 32 * mm], styles)


def _team_review_lines(payload: dict[str, Any]) -> list[str]:
    profile = list(payload.get("technical_profile") or [])
    by_key = {str(item.get("key")): item for item in profile}

    def value(key: str, field: str) -> str:
        return _team_value(by_key.get(key), field)

    return [
        f"Con balón: últimos 10 {value('pass_completion_pct', 'last10')} vs todos {value('pass_completion_pct', 'all')} ({value('pass_completion_pct', 'delta_10_all')}). Revisar secuencias de pase recientes.",
        f"Finalización: últimos 10 {value('shots_total', 'last10')} remates y {value('goals', 'last10')} goles vs todos {value('shots_total', 'all')} y {value('goals', 'all')}.",
        f"Sin balón y pérdidas: diferencia últimos 10 vs todos — entradas {value('tackles_won', 'delta_10_all')}, intercepciones {value('interceptions', 'delta_10_all')}, pérdidas {value('turnovers', 'delta_10_all')} y desposesiones {value('dispossessed', 'delta_10_all')}.",
    ]


def _team_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    team = base_v2._safe((payload.get("team") or {}).get("display_name"), "Equipo")
    overview = payload.get("overview") or {}
    matches = sorted(list(payload.get("matches") or []), key=lambda row: base_v2._date(row.get("match_date")), reverse=True)
    snapshot = list(payload.get("rating_snapshot") or [])
    history = sorted(list(payload.get("rating_history") or []), key=lambda row: base_v2._date(row.get("match_date")))
    squad = list(payload.get("squad") or [])
    technical = list(payload.get("technical_profile") or [])
    latest = matches[0] if matches else {}
    latest_hist = history[-1] if history else {}
    period = f"{base_v2._date(matches[-1].get('match_date'))} - {base_v2._date(matches[0].get('match_date'))}" if matches else "Sin periodo disponible"

    story: list[Any] = [
        base_v2._cover(
            "Informe de rendimiento · Equipo",
            team,
            f"Periodo {period} · {base_v2._rating_name(payload.get('match_rating_version'))}",
            width,
            styles,
        ),
        Spacer(1, 4 * mm),
    ]

    sf, sa = base_v2._num(latest.get("score_for")), base_v2._num(latest.get("score_against"))
    score = f"{int(sf)}-{int(sa)}" if sf is not None and sa is not None else "-"
    form = []
    for row in matches[:5]:
        a, b = base_v2._num(row.get("score_for")), base_v2._num(row.get("score_against"))
        if a is not None and b is not None:
            form.append("G" if a > b else "P" if a < b else "E")

    story.append(base_v2._kpi_row([
        ("Último partido", score, base_v2._safe(latest.get("opponent"))),
        ("Match Rating mediano", base_v2._fmt(latest_hist.get("median_match_rating"), 2, "/10"), "Último partido"),
        ("Forma L5", " · ".join(form) if form else "-", "Más reciente primero"),
        ("Cobertura", f"{base_v2._count(overview.get('matches'))} partidos", f"{base_v2._count(overview.get('players'))} jugadores"),
    ], width, styles))

    comparable = [row for row in snapshot if base_v2._num(row.get("trend_delta_5v5")) is not None]
    rise = max(comparable, key=lambda row: base_v2._num(row.get("trend_delta_5v5")) or -999) if comparable else None
    fall = min(comparable, key=lambda row: base_v2._num(row.get("trend_delta_5v5")) or 999) if comparable else None
    venue = "Local" if latest.get("venue") == "H" else "Visitante" if latest.get("venue") == "A" else "Contexto no disponible"

    story += base_v2._section("01 · Resumen ejecutivo", "Qué ha pasado, qué ha cambiado y dónde conviene revisar.", width, styles)
    story.append(base_v2._insight_grid([
        ("Último registro", f"{team} {score} {base_v2._safe(latest.get('opponent'))}", f"{base_v2._date(latest.get('match_date'))} · {venue}", base_v2.TEAL),
        ("Forma reciente", " · ".join(form) if form else "-", "Secuencia descriptiva; no predicción", base_v2.NAVY_2),
        ("Mayor subida reciente", f"{base_v2._safe(rise.get('player'))} ({base_v2._fmt(rise.get('trend_delta_5v5'), 2)})" if rise else "Sin muestra comparable", "Últimos 5 vs 5 anteriores", base_v2.GREEN),
        ("Mayor bajada reciente", f"{base_v2._safe(fall.get('player'))} ({base_v2._fmt(fall.get('trend_delta_5v5'), 2)})" if fall else "Sin muestra comparable", "Últimos 5 vs 5 anteriores", base_v2.RED),
    ], width, styles))

    story += base_v2._section("02 · Evolución del rendimiento", "Mediana del Match Rating de los jugadores utilizados por partido.", width, styles)
    story.append(base_v4._team_trend_chart(payload, width, 52 * mm, 3, 10))

    story.append(PageBreak())
    story += base_v2._section(
        "03 · Pulso técnico",
        "Último partido, últimos 10 y todos los partidos disponibles del periodo. Comparación descriptiva; no se aplican umbrales bueno/malo.",
        width,
        styles,
    )
    if technical:
        story.append(_team_phase_cards(technical, width, styles))
        story.append(Spacer(1, 2 * mm))
        story.append(_team_profile_table(technical, styles))

    story += base_v2._section("04 · Plantilla: nivel reciente y cambio", "Media de los últimos 5 partidos frente al cambio respecto a los 5 anteriores. No es un ranking de calidad.", width, styles)
    points = []
    for row in snapshot:
        x_value, y_value = base_v2._num(row.get("avg_last5")), base_v2._num(row.get("trend_delta_5v5"))
        if x_value is not None and y_value is not None:
            points.append((base_v2._safe(row.get("player")), x_value, y_value))
    if points:
        story.append(base_v2._scatter_chart_focus(points, width, 43 * mm))

    story.append(Spacer(1, 3 * mm))
    story.append(base_v3._review_box("Claves para la revisión técnica", _team_review_lines(payload), width, styles))

    story.append(PageBreak())
    story += base_v2._section("05 · Seguimiento de plantilla", "Ordenado por minutos acumulados. El detalle sirve para decidir qué revisar, no para clasificar calidad.", width, styles)
    snap_by_player = {str(row.get("player")): row for row in snapshot}
    rows = [["Jugador", "Perfil", "Min", "Último", "Media L5", "Δ 5v5", "Conf. %"]]
    for row in sorted(squad, key=lambda item: base_v2._num(item.get("minutes")) or 0, reverse=True):
        if (base_v2._num(row.get("minutes")) or 0) <= 0:
            continue
        state = snap_by_player.get(str(row.get("player")), {})
        rows.append([
            row.get("player"),
            base_v2._position(state.get("latest_position_group")),
            base_v2._count(row.get("minutes")),
            base_v2._fmt(state.get("latest_match_rating"), 2),
            base_v2._fmt(state.get("avg_last5"), 2),
            base_v2._fmt(state.get("trend_delta_5v5"), 2),
            base_v2._fmt(state.get("latest_confidence"), 0),
        ])
    story.append(base_v2._compact_table(rows[:25], [35*mm, 31*mm, 19*mm, 22*mm, 24*mm, 22*mm, 20*mm], styles))

    story += base_v2._section("06 · Partidos recientes", "Resultado y contexto básico de los últimos registros.", width, styles)
    recent = [["Fecha", "L/V", "Rival", "Marcador", "Formación"]]
    for row in matches[:8]:
        a, b = base_v2._num(row.get("score_for")), base_v2._num(row.get("score_against"))
        result = f"{int(a)}-{int(b)}" if a is not None and b is not None else "-"
        recent.append([
            base_v2._date(row.get("match_date")),
            "L" if row.get("venue") == "H" else "V",
            row.get("opponent"),
            result,
            base_v2._safe(row.get("starting_formation")),
        ])
    story.append(base_v2._compact_table(recent, [28*mm, 14*mm, 64*mm, 25*mm, 35*mm], styles))
    story.append(Spacer(1, 2 * mm))
    story.append(base_v2._evidence_strip([
        ("Base", f"{base_v2._count(overview.get('matches'))} partidos · {base_v2._count(overview.get('players'))} jugadores"),
        ("GPS", "Opcional · no condiciona Team Mode"),
        ("Interpretación", "Descriptiva y auditable"),
        ("Decisiones", "Sin recomendación automática"),
    ], width, styles))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "El informe combina resultados materializados con agregados descriptivos transparentes. No calcula xG, posesión, presión o tracking si la fuente no los contiene.",
        styles["note"],
    ))
    return story


def _player_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    return base_v4._player_story(payload, styles, width)


def _match_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    return base_v4._match_story(payload, styles, width)


def render_pdf_bytes(payload: dict[str, Any]) -> bytes:
    report_type = str(payload.get("report_type") or "").lower()
    if report_type not in {"team", "player", "match"}:
        raise ValueError(f"Unsupported report_type: {report_type}")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
        title="Football Performance System - Informe técnico",
        author="Football Performance System",
    )
    styles = base_v2._styles()
    width = A4[0] - 32 * mm

    if report_type == "team":
        story = _team_story(payload, styles, width)
    elif report_type == "player":
        story = _player_story(payload, styles, width)
    else:
        story = _match_story(payload, styles, width)

    doc.build(story, onFirstPage=base_v2._footer, onLaterPages=base_v2._footer)
    return buffer.getvalue()
