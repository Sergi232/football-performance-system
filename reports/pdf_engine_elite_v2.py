"""Elite technical PDF renderer v2.

This revision keeps the REPORTS-03 analytical contract intact while tightening the
staff-facing document: Team=3 pages, Player=2 pages and Match=2 pages by design.
It removes dead space, keeps related sections together, uses compact audit tables and
never recalculates Match Rating, Performance Index or expert decisions.
"""
from __future__ import annotations

from html import escape
from io import BytesIO
from typing import Any

from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from reports.pdf_engine_elite import _evidence_strip, _rating_name
from reports.pdf_engine_pro import (
    AMBER,
    BORDER,
    GREEN,
    GRID,
    LIGHT,
    MUTED,
    NAVY_2,
    RED,
    TEAL,
    TEXT,
    WHITE,
    _bar_chart,
    _count,
    _cover,
    _date,
    _expert_status,
    _fmt,
    _footer,
    _insight_grid,
    _kpi_row,
    _num,
    _position,
    _roles,
    _safe,
    _section,
    _styles,
    _trend_chart,
)


def _fmt_profile_value(row: dict[str, Any], field: str) -> str:
    value = _num(row.get(field))
    if value is None:
        return "-"
    decimals = int(row.get("decimals") or 1)
    suffix = str(row.get("suffix") or "")
    sign = "+" if field.startswith("delta") and value > 0 else ""
    if str(row.get("key")) == "pass_completion_pct" and field.startswith("delta"):
        return f"{sign}{value:.{decimals}f} pp"
    return f"{sign}{value:.{decimals}f}{suffix}"


def _compact_table(rows: list[list[Any]], widths: list[float], styles, header: bool = True) -> Table:
    cooked = []
    for r_idx, row in enumerate(rows):
        style = styles["th"] if header and r_idx == 0 else styles["td"]
        cooked.append([Paragraph(escape(_safe(cell)), style) for cell in row])
    table = Table(cooked, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -1), 0.2, BORDER),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F33")))
    for i in range(1 if header else 0, len(cooked)):
        if i % 2 == 0:
            commands.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    table.setStyle(TableStyle(commands))
    return table


def _profile_table(profile: list[dict[str, Any]], styles, mode: str) -> Table:
    if mode == "match":
        rows = [["Indicador", "Partido", "Media 5 prev.", "Cambio"]]
        for item in profile:
            rows.append([
                item.get("label"),
                _fmt_profile_value(item, "current"),
                _fmt_profile_value(item, "prior5"),
                _fmt_profile_value(item, "delta_vs_prior5"),
            ])
        widths = [72 * mm, 31 * mm, 39 * mm, 29 * mm]
    else:
        rows = [["Indicador", "Último", "Últimos 5", "5 anteriores", "Cambio 5v5"]]
        for item in profile:
            rows.append([
                item.get("label"),
                _fmt_profile_value(item, "current"),
                _fmt_profile_value(item, "last5"),
                _fmt_profile_value(item, "previous5"),
                _fmt_profile_value(item, "delta_5v5"),
            ])
        widths = [61 * mm, 27 * mm, 30 * mm, 30 * mm, 25 * mm]
    return _compact_table(rows, widths, styles)


def _phase_cards(profile: list[dict[str, Any]], width: float, styles, mode: str) -> Table:
    by_key = {str(item.get("key")): item for item in profile}

    def value(key: str, field: str) -> str:
        row = by_key.get(key)
        return "-" if row is None else _fmt_profile_value(row, field)

    if mode == "match":
        current_field, ref_field = "current", "prior5"
        ref_label = "media 5 partidos previos"
    else:
        current_field, ref_field = "last5", "previous5"
        ref_label = "5 partidos anteriores"

    return _insight_grid([
        ("Con balón", f"Pase {value('pass_completion_pct', current_field)}", f"Referencia: {value('pass_completion_pct', ref_field)} · {ref_label}", TEAL),
        ("Finalización", f"Remates {value('shots_total', current_field)} · Goles {value('goals', current_field)}", f"Referencia: {value('shots_total', ref_field)} remates · {value('goals', ref_field)} goles", NAVY_2),
        ("Recuperación defensiva", f"Entradas ganadas {value('tackles_won', current_field)} · Interc. {value('interceptions', current_field)}", f"Referencia: {value('tackles_won', ref_field)} · {value('interceptions', ref_field)}", AMBER),
        ("Pérdidas", f"Pérdidas {value('turnovers', current_field)} · Desposesiones {value('dispossessed', current_field)}", f"Referencia: {value('turnovers', ref_field)} · {value('dispossessed', ref_field)}", RED),
    ], width, styles)


def _metric_has_information(row: dict[str, Any]) -> bool:
    values = [_num(row.get(field)) for field in ("current", "last5", "previous5")]
    values = [value for value in values if value is not None]
    if not values:
        return False
    return any(abs(value) > 1e-9 for value in values) or str(row.get("key")) == "pass_completion_pct"


def _player_metric_selection(profile: list[dict[str, Any]], position_group: str) -> list[dict[str, Any]]:
    by_key = {str(item.get("key")): item for item in profile}
    if position_group == "GK":
        keys = ["pass_completion_pct", "passes_completed_per90", "turnovers_per90", "dispossessed_per90"]
    elif position_group in {"CB", "FB", "WB", "FB_WB"}:
        keys = ["pass_completion_pct", "passes_completed_per90", "tackles_won_per90", "interceptions_per90", "turnovers_per90", "shots_per90"]
    elif position_group in {"DM", "CM", "DM_CM", "AM"}:
        keys = ["pass_completion_pct", "passes_completed_per90", "assists_per90", "interceptions_per90", "turnovers_per90", "dispossessed_per90"]
    else:
        keys = ["pass_completion_pct", "shots_per90", "goals_per90", "assists_per90", "turnovers_per90", "dispossessed_per90"]
    return [by_key[key] for key in keys if key in by_key and _metric_has_information(by_key[key])]


def _scatter_chart_focus(points: list[tuple[str, float, float]], width: float, height: float) -> Drawing:
    drawing = Drawing(width, height)
    left, right, bottom, top = 34, 14, 23, 10
    plot_w, plot_h = width - left - right, height - bottom - top
    y_abs = max([abs(point[2]) for point in points] + [0.5]) * 1.15
    x_min, x_max = 3.0, 10.0
    for i in range(4):
        y = bottom + plot_h * i / 3
        drawing.add(Line(left, y, left + plot_w, y, strokeColor=GRID, strokeWidth=0.7))
    zero_y = bottom + plot_h * 0.5
    zero = Line(left, zero_y, left + plot_w, zero_y, strokeColor=MUTED, strokeWidth=0.8)
    zero.strokeDashArray = [3, 3]
    drawing.add(zero)
    label_names = {point[0] for point in sorted(points, key=lambda x: abs(x[2]), reverse=True)[:4]}
    for name, x_value, y_value in points:
        x = left + plot_w * (x_value - x_min) / (x_max - x_min)
        y = bottom + plot_h * (y_value + y_abs) / (2 * y_abs)
        drawing.add(Circle(x, y, 3.0, fillColor=TEAL, strokeColor=WHITE, strokeWidth=0.8))
        if name in label_names:
            drawing.add(String(x + 4, y + 2, name, fontName="Helvetica", fontSize=5.2, fillColor=TEXT))
    drawing.add(String(left + plot_w / 2, 2, "Media Match Rating · últimos 5", textAnchor="middle", fontName="Helvetica", fontSize=6.2, fillColor=MUTED))
    drawing.add(String(2, height / 2, "Cambio 5 vs 5", fontName="Helvetica", fontSize=6.2, fillColor=MUTED))
    return drawing


def _team_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    team = _safe((payload.get("team") or {}).get("display_name"), "Equipo")
    overview = payload.get("overview") or {}
    matches = sorted(list(payload.get("matches") or []), key=lambda row: _date(row.get("match_date")), reverse=True)
    snapshot = list(payload.get("rating_snapshot") or [])
    history = sorted(list(payload.get("rating_history") or []), key=lambda row: _date(row.get("match_date")))
    squad = list(payload.get("squad") or [])
    technical = list(payload.get("technical_profile") or [])
    latest = matches[0] if matches else {}
    latest_hist = history[-1] if history else {}
    period = f"{_date(matches[-1].get('match_date'))} - {_date(matches[0].get('match_date'))}" if matches else "Sin periodo disponible"
    story: list[Any] = [_cover("Informe de rendimiento · Equipo", team, f"Periodo {period} · {_rating_name(payload.get('match_rating_version'))}", width, styles), Spacer(1, 4 * mm)]

    sf, sa = _num(latest.get("score_for")), _num(latest.get("score_against"))
    score = f"{int(sf)}-{int(sa)}" if sf is not None and sa is not None else "-"
    form = []
    for row in matches[:5]:
        a, b = _num(row.get("score_for")), _num(row.get("score_against"))
        if a is not None and b is not None:
            form.append("G" if a > b else "P" if a < b else "E")
    story.append(_kpi_row([
        ("Último partido", score, _safe(latest.get("opponent"))),
        ("Match Rating mediano", _fmt(latest_hist.get("median_match_rating"), 2, "/10"), "Último partido"),
        ("Forma L5", " · ".join(form) if form else "-", "Más reciente primero"),
        ("Cobertura", f"{_count(overview.get('matches'))} partidos", f"{_count(overview.get('players'))} jugadores"),
    ], width, styles))

    comparable = [row for row in snapshot if _num(row.get("trend_delta_5v5")) is not None]
    rise = max(comparable, key=lambda row: _num(row.get("trend_delta_5v5")) or -999) if comparable else None
    fall = min(comparable, key=lambda row: _num(row.get("trend_delta_5v5")) or 999) if comparable else None
    venue = "Local" if latest.get("venue") == "H" else "Visitante" if latest.get("venue") == "A" else "Contexto no disponible"
    story += _section("01 · Resumen ejecutivo", "Qué ha pasado, qué ha cambiado y dónde conviene revisar.", width, styles)
    story.append(_insight_grid([
        ("Último registro", f"{team} {score} {_safe(latest.get('opponent'))}", f"{_date(latest.get('match_date'))} · {venue}", TEAL),
        ("Forma reciente", " · ".join(form) if form else "-", "Secuencia descriptiva; no predicción", NAVY_2),
        ("Mayor subida reciente", f"{_safe(rise.get('player'))} ({_fmt(rise.get('trend_delta_5v5'), 2)})" if rise else "Sin muestra comparable", "Últimos 5 vs 5 anteriores", GREEN),
        ("Mayor bajada reciente", f"{_safe(fall.get('player'))} ({_fmt(fall.get('trend_delta_5v5'), 2)})" if fall else "Sin muestra comparable", "Últimos 5 vs 5 anteriores", RED),
    ], width, styles))
    story += _section("02 · Evolución del rendimiento", "Mediana del Match Rating de los jugadores utilizados por partido.", width, styles)
    vals = [value for value in [_num(row.get("median_match_rating")) for row in history] if value is not None]
    labels = [_date(row.get("match_date")) for row in history if _num(row.get("median_match_rating")) is not None]
    story.append(_trend_chart(vals, labels, width, 48 * mm, 3, 10))

    story.append(PageBreak())
    story += _section("03 · Pulso técnico", "Datos observados del equipo. Se priorizan métricas simples y comparables; no se aplican umbrales bueno/malo.", width, styles)
    if technical:
        story.append(_phase_cards(technical, width, styles, "team"))
        story.append(Spacer(1, 2 * mm))
        story.append(_profile_table(technical, styles, "team"))
    story += _section("04 · Plantilla: nivel reciente y cambio", "Media de los últimos 5 partidos frente al cambio respecto a los 5 anteriores. No es un ranking de calidad.", width, styles)
    points = []
    for row in snapshot:
        x_value, y_value = _num(row.get("avg_last5")), _num(row.get("trend_delta_5v5"))
        if x_value is not None and y_value is not None:
            points.append((_safe(row.get("player")), x_value, y_value))
    if points:
        story.append(_scatter_chart_focus(points, width, 43 * mm))

    story.append(PageBreak())
    story += _section("05 · Seguimiento de plantilla", "Ordenado por minutos acumulados. El detalle sirve para decidir qué revisar, no para clasificar calidad.", width, styles)
    snap_by_player = {str(row.get("player")): row for row in snapshot}
    rows = [["Jugador", "Perfil", "Min", "Último", "Media L5", "Cambio 5v5", "Conf. %"]]
    for row in sorted(squad, key=lambda item: _num(item.get("minutes")) or 0, reverse=True):
        if (_num(row.get("minutes")) or 0) <= 0:
            continue
        state = snap_by_player.get(str(row.get("player")), {})
        rows.append([row.get("player"), _position(state.get("latest_position_group")), _count(row.get("minutes")), _fmt(state.get("latest_match_rating"), 2), _fmt(state.get("avg_last5"), 2), _fmt(state.get("trend_delta_5v5"), 2), _fmt(state.get("latest_confidence"), 0)])
    story.append(_compact_table(rows[:25], [35*mm, 31*mm, 19*mm, 22*mm, 24*mm, 22*mm, 20*mm], styles))

    story += _section("06 · Partidos recientes", "Resultado y contexto básico de los últimos registros.", width, styles)
    recent = [["Fecha", "L/V", "Rival", "Marcador", "Formación"]]
    for row in matches[:8]:
        a, b = _num(row.get("score_for")), _num(row.get("score_against"))
        result = f"{int(a)}-{int(b)}" if a is not None and b is not None else "-"
        recent.append([_date(row.get("match_date")), "L" if row.get("venue") == "H" else "V", row.get("opponent"), result, _safe(row.get("starting_formation"))])
    story.append(_compact_table(recent, [28*mm, 14*mm, 64*mm, 25*mm, 35*mm], styles))
    story.append(Spacer(1, 2 * mm))
    story.append(_evidence_strip([
        ("Base", f"{_count(overview.get('matches'))} partidos · {_count(overview.get('players'))} jugadores"),
        ("GPS", "Opcional · no condiciona el modo equipo"),
        ("Interpretación", "Descriptiva y auditable"),
        ("Decisiones", "Sin recomendación automática"),
    ], width, styles))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("El informe combina resultados materializados con agregados descriptivos transparentes. No calcula xG, posesión, presión o seguimiento posicional si la fuente no los contiene.", styles["note"]))
    return story


def _player_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    team = _safe((payload.get("team") or {}).get("display_name"), "Equipo")
    summary = payload.get("summary") or {}
    snapshot = payload.get("player_snapshot") or {}
    ratings = sorted(list(payload.get("match_ratings") or []), key=lambda row: _date(row.get("match_date")), reverse=True)
    history = list(payload.get("match_history") or [])
    technical = list(payload.get("technical_profile") or [])
    latest = ratings[0] if ratings else {}
    gate = payload.get("latest_role_fit_gate") or {}
    perf = payload.get("performance_index") or {}
    player = _safe(summary.get("player"), "Jugador")
    group = str(latest.get("position_group") or snapshot.get("latest_position_group") or "")
    profile = _position(group)
    story: list[Any] = [_cover("Informe individual · Jugador", player, f"{team} · {profile} · {_rating_name(payload.get('match_rating_version'))}", width, styles), Spacer(1, 4 * mm)]
    story.append(_kpi_row([
        ("Último Match Rating", _fmt(latest.get("match_rating_10"), 2, "/10"), _safe(latest.get("opponent"))),
        ("Media últimos 5", _fmt(snapshot.get("avg_last5"), 2, "/10"), "Forma reciente"),
        ("Cambio 5 vs 5", _fmt(snapshot.get("trend_delta_5v5"), 2), "Últimos 5 vs anteriores"),
        ("Confianza", _fmt(latest.get("match_rating_confidence"), 0, "%"), "Último partido"),
    ], width, styles))
    sf, sa = _num(latest.get("score_for")), _num(latest.get("score_against"))
    score = f"{int(sf)}-{int(sa)}" if sf is not None and sa is not None else "-"
    performance_text = _fmt(perf.get("performance_score"), 1, "/100") if _num(perf.get("performance_score")) is not None else "No disponible"
    coverage_value = _num(gate.get("evidence_coverage"))
    coverage_pct = coverage_value * 100 if coverage_value is not None and 0 <= coverage_value <= 1 else coverage_value
    story += _section("01 · Resumen para el cuerpo técnico", "Contexto, forma y disponibilidad de evidencia.", width, styles)
    story.append(_insight_grid([
        ("Último partido", f"{_safe(latest.get('opponent'))} · {score}", f"{_date(latest.get('match_date'))} · {_count(latest.get('minutes_played'))} min", TEAL),
        ("Perfil observado", profile, f"{_count(summary.get('appearances'))} apariciones · {_count(summary.get('minutes'))} min", NAVY_2),
        ("Performance Index", performance_text, "Capa histórica experimental v0.2", AMBER),
        ("Motor experto", _expert_status(gate.get("final_status")), f"Cobertura: {_fmt(coverage_pct, 0, '%')}", RED if "Sin recomendación" in _expert_status(gate.get("final_status")) else TEAL),
    ], width, styles))
    story += _section("02 · Trayectoria", "Evolución del Match Rating partido a partido; escala fija 3-10.", width, styles)
    chronological = sorted(ratings, key=lambda row: _date(row.get("match_date")))
    values = [value for value in [_num(row.get("match_rating_10")) for row in chronological] if value is not None]
    labels = [_date(row.get("match_date")) for row in chronological if _num(row.get("match_rating_10")) is not None]
    story.append(_trend_chart(values, labels, width, 46 * mm, 3, 10))

    story.append(PageBreak())
    dims = []
    dim_defs = [("Paradas", "defensive_contribution"), ("Distribución", "creation_progression"), ("Disciplina", "discipline")] if group == "GK" else [("Amenaza ofensiva", "attacking_threat"), ("Creación / progresión", "creation_progression"), ("Contribución defensiva", "defensive_contribution"), ("Finalización", "finishing"), ("Disciplina", "discipline")]
    for label, key in dim_defs:
        value = _num(latest.get(key))
        if value is not None:
            dims.append((label, value))
    if dims:
        block = _section("03 · Dimensiones del último partido", "Puntuaciones materializadas que explican la nota; no constituyen una evaluación independiente del jugador.", width, styles)
        block.append(_bar_chart(dims, width, 29 * mm, 0, 100))
        story.append(KeepTogether(block))

    story += _section("04 · Perfil técnico reciente", "Métricas de uso por posición. Últimos 5 frente a 5 anteriores; los cambios no se etiquetan como buenos o malos.", width, styles)
    selected_metrics = _player_metric_selection(technical, group)
    if selected_metrics:
        story.append(_profile_table(selected_metrics, styles, "player"))
    else:
        story.append(Paragraph("No hay muestra técnica suficiente para construir un perfil reciente útil.", styles["body"]))

    story += _section("05 · Producción reciente", "Acciones registradas con contexto de minutos; se evita sobreinterpretar volúmenes sin exposición.", width, styles)
    rating_by_match = {str(row.get("match_id")): row for row in ratings}
    if group == "GK":
        rows = [["Fecha", "Rival", "Min", "Pases", "Precisión", "Nota", "Conf. %"]]
        for row in sorted(history, key=lambda item: _date(item.get("match_date")), reverse=True)[:5]:
            completed, total = _num(row.get("passes_completed")), _num(row.get("passes_total"))
            passes = f"{int(completed)}/{int(total)}" if completed is not None and total is not None else "-"
            precision = "-" if total is None or total <= 0 or completed is None else f"{completed / total * 100:.0f}%"
            rating = rating_by_match.get(str(row.get("match_id")), {})
            rows.append([_date(row.get("match_date")), row.get("opponent"), _count(row.get("minutes")), passes, precision, _fmt(rating.get("match_rating_10"), 2), _fmt(rating.get("match_rating_confidence"), 0)])
        story.append(_compact_table(rows, [27*mm, 47*mm, 14*mm, 25*mm, 22*mm, 20*mm, 20*mm], styles))
    else:
        rows = [["Fecha", "Rival", "Min", "Pases", "Remates", "Goles", "Entradas", "Interc."]]
        for row in sorted(history, key=lambda item: _date(item.get("match_date")), reverse=True)[:5]:
            completed, total = _num(row.get("passes_completed")), _num(row.get("passes_total"))
            passes = f"{int(completed)}/{int(total)}" if completed is not None and total is not None else "-"
            rows.append([_date(row.get("match_date")), row.get("opponent"), _count(row.get("minutes")), passes, _count(row.get("shots_total")), _count(row.get("goals")), _count(row.get("tackles_won")), _count(row.get("interceptions"))])
        story.append(_compact_table(rows, [27*mm, 44*mm, 14*mm, 25*mm, 18*mm, 15*mm, 20*mm, 18*mm], styles))

    story += _section("06 · Trazabilidad", "Qué sabe el sistema y qué no debe inferirse.", width, styles)
    story.append(_evidence_strip([
        ("Rol observado", _roles(gate.get("observed_role"))),
        ("Historial mismo rol", _count(gate.get("same_role_history"))),
        ("Cobertura", _fmt(coverage_pct, 0, "%")),
        ("Estado", _expert_status(gate.get("final_status"))),
    ], width, styles))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("El informe prioriza evolución, contexto y métricas observables. No infiere causa táctica, fatiga, riesgo de lesión, titularidad ni potencial futuro.", styles["note"]))
    return story


def _short_context(row: dict[str, Any]) -> str:
    path = str(row.get("rating_path") or row.get("match_rating_context") or "").upper()
    if "GOALKEEPER" in path:
        return "Portero"
    if "ROLE_UNAVAILABLE" in path or "FALLBACK" in path:
        return "Rol no disponible"
    return "Posicional"


def _match_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    team = _safe((payload.get("team") or {}).get("display_name"), "Equipo")
    match = payload.get("match") or {}
    summary = payload.get("match_summary") or {}
    ratings = list(payload.get("ratings") or [])
    observations = payload.get("observations") or {}
    technical = list(payload.get("technical_profile") or [])
    opponent = _safe(match.get("opponent"), "Rival")
    sf, sa = _num(match.get("score_for")), _num(match.get("score_against"))
    score = f"{int(sf)}-{int(sa)}" if sf is not None and sa is not None else "-"
    venue = "Local" if match.get("venue") == "H" else "Visitante" if match.get("venue") == "A" else "-"
    story: list[Any] = [_cover("Informe postpartido", f"{team} {score} {opponent}", f"{_date(match.get('match_date'))} · {venue} · {_rating_name(payload.get('match_rating_version'))}", width, styles), Spacer(1, 4 * mm)]
    fallback = sum(1 for row in ratings if "ROLE_UNAVAILABLE" in str(row.get("rating_path") or ""))
    story.append(_kpi_row([
        ("Marcador", score, f"{team} vs {opponent}"),
        ("Rating mediano", _fmt(summary.get("median_match_rating"), 2, "/10"), "Valor materializado"),
        ("Confianza mediana", _fmt(summary.get("median_confidence"), 0, "%"), "Valor materializado"),
        ("Rol analítico no disponible", str(fallback), "Ruta alternativa explícita"),
    ], width, styles))

    scorers = observations.get("goal_scorers") or []
    assists = observations.get("assist_providers") or []
    leaders = observations.get("leaders") or {}
    goals_text = ", ".join(f"{item.get('player')} ({item.get('goals')})" for item in scorers) if scorers else "Sin goles registrados"
    assists_text = ", ".join(f"{item.get('player')} ({item.get('assists')})" for item in assists) if assists else "Sin asistencias registradas"
    def leader_text(key: str) -> str:
        item = leaders.get(key) or {}
        players = item.get("players") or []
        return f"{', '.join(map(str, players))} · {_fmt(item.get('value'), 0)}" if players else "Sin dato"

    story += _section("01 · Lectura rápida", "Hechos deterministas del partido; sirven para priorizar la revisión de vídeo.", width, styles)
    story.append(_insight_grid([
        ("Goles", goals_text, "Contribución directa", TEAL),
        ("Asistencias", assists_text, "Contribución directa", NAVY_2),
        ("Remates", leader_text("shots_total"), "Máximo individual observado", AMBER),
        ("Pases completados", leader_text("passes_completed"), "Máximo individual observado", TEAL),
    ], width, styles))
    story += _section("02 · Huella técnica del equipo", "Partido frente a los cinco partidos anteriores disponibles; no se usan partidos futuros.", width, styles)
    if technical:
        story.append(_phase_cards(technical, width, styles, "match"))
        story.append(Spacer(1, 2 * mm))
        story.append(_profile_table(technical, styles, "match"))

    story.append(PageBreak())
    story += _section("03 · Distribución del Match Rating", "Ordenación descriptiva para orientar la revisión; no es una recomendación de selección.", width, styles)
    bars = sorted([(_safe(row.get("player")), _num(row.get("match_rating_10"))) for row in ratings if _num(row.get("match_rating_10")) is not None], key=lambda item: item[1], reverse=True)
    story.append(_bar_chart([(name, float(value)) for name, value in bars[:15]], width, 43 * mm, 3, 10))

    story += _section("04 · Ficha de jugadores", "Minutos, perfil, Match Rating, confianza y contexto del cálculo.", width, styles)
    rows = [["Jugador", "Perfil", "Min", "Nota", "Conf. %", "Contexto"]]
    for row in sorted(ratings, key=lambda item: _num(item.get("match_rating_10")) or -999, reverse=True):
        rows.append([row.get("player"), _position(row.get("position_group")), _count(row.get("minutes_played")), _fmt(row.get("match_rating_10"), 2), _fmt(row.get("match_rating_confidence"), 0), _short_context(row)])
    story.append(_compact_table(rows, [37*mm, 31*mm, 14*mm, 19*mm, 20*mm, 46*mm], styles))

    outfield = [row for row in ratings if "OUTFIELD_PERF18" in str(row.get("rating_path") or "")]
    if outfield:
        story += _section("05 · Dimensiones explicativas", "Matriz compacta de las dimensiones ya materializadas para los jugadores con contexto posicional fiable.", width, styles)
        rows = [["Jugador", "Amenaza", "Creación", "Defensa", "Finalización", "Disciplina"]]
        for row in outfield[:10]:
            rows.append([row.get("player"), _fmt(row.get("attacking_threat"), 1), _fmt(row.get("creation_progression"), 1), _fmt(row.get("defensive_contribution"), 1), _fmt(row.get("finishing"), 1), _fmt(row.get("discipline"), 1)])
        story.append(_compact_table(rows, [42*mm, 24*mm, 24*mm, 24*mm, 27*mm, 24*mm], styles))

    confidence = [value for value in [_num(row.get("match_rating_confidence")) for row in ratings] if value is not None]
    story += _section(f"{6 if outfield else 5:02} · Calidad de evidencia", "Límites antes de convertir los datos en una decisión técnica.", width, styles)
    story.append(_evidence_strip([
        ("Jugadores utilizados", str(len(ratings))),
        ("Rol analítico no disponible", str(fallback)),
        ("Confianza mínima", _fmt(min(confidence) if confidence else None, 0, "%")),
        ("Uso", "Revisión descriptiva"),
    ], width, styles))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("El informe usa resultados materializados y agregados descriptivos transparentes. No recalcula Match Rating, no crea xG/posesión/presión y no determina alineación ni causa táctica.", styles["note"]))
    return story


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
    styles = _styles()
    width = A4[0] - 32 * mm
    story = _team_story(payload, styles, width) if report_type == "team" else _player_story(payload, styles, width) if report_type == "player" else _match_story(payload, styles, width)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
