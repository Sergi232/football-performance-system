"""Evidence-led professional PDF reports for football technical staff.

Design principles are inspired by professional reporting workflows (Opta/ProVision,
Wyscout, StatsBomb and UEFA technical reports) without copying proprietary layouts or
metrics. The renderer only consumes the structured report payload. No critical model
is recalculated here and no tactical recommendation is invented.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from reports.pdf_engine_pro import (
    AMBER,
    BORDER,
    GREEN,
    GRID,
    LIGHT,
    MUTED,
    NAVY,
    NAVY_2,
    RED,
    TEAL,
    TEXT,
    WHITE,
    _bar_chart,
    _count,
    _cover,
    _data_table,
    _date,
    _expert_status,
    _fmt,
    _footer,
    _insight_grid,
    _kpi_row,
    _num,
    _position,
    _rating_context,
    _roles,
    _safe,
    _scatter_chart,
    _section,
    _styles,
    _trend_chart,
)


def _rating_name(version: Any) -> str:
    text = str(version or "")
    return "Match Rating V5" if "0.5" in text else (text or "Match Rating")


def _fmt_profile_value(row: dict[str, Any], key: str) -> str:
    value = _num(row.get(key))
    if value is None:
        return "-"
    decimals = int(row.get("decimals") or 1)
    suffix = str(row.get("suffix") or "")
    sign = "+" if key.startswith("delta") and value > 0 else ""
    return f"{sign}{value:.{decimals}f}{suffix}"


def _profile_table(profile: list[dict[str, Any]], width: float, styles, mode: str) -> Table:
    if mode == "match":
        rows = [["Indicador", "Partido", "Media 5 prev.", "Δ"]]
        for item in profile:
            rows.append([
                item.get("label"),
                _fmt_profile_value(item, "current"),
                _fmt_profile_value(item, "prior5"),
                _fmt_profile_value(item, "delta_vs_prior5"),
            ])
        widths = [72 * mm, 31 * mm, 39 * mm, 29 * mm]
    else:
        rows = [["Indicador", "Último", "Últimos 5", "5 anteriores", "Δ 5v5"]]
        for item in profile:
            rows.append([
                item.get("label"),
                _fmt_profile_value(item, "current"),
                _fmt_profile_value(item, "last5"),
                _fmt_profile_value(item, "previous5"),
                _fmt_profile_value(item, "delta_5v5"),
            ])
        widths = [61 * mm, 27 * mm, 30 * mm, 30 * mm, 25 * mm]
    return _data_table(rows, widths, styles)


def _phase_cards(profile: list[dict[str, Any]], width: float, styles, mode: str) -> Table:
    by_key = {str(x.get("key")): x for x in profile}

    def value(key: str, field: str) -> str:
        row = by_key.get(key)
        return "-" if row is None else _fmt_profile_value(row, field)

    if mode == "match":
        current_field, ref_field = "current", "prior5"
        ref_label = "Media 5 partidos previos"
    else:
        current_field, ref_field = "last5", "previous5"
        ref_label = "5 partidos anteriores"

    items = [
        (
            "Con balón",
            f"Pase {value('pass_completion_pct', current_field)}",
            f"Referencia: {value('pass_completion_pct', ref_field)} · {ref_label}",
            TEAL,
        ),
        (
            "Finalización",
            f"Remates {value('shots_total', current_field)} · Goles {value('goals', current_field)}",
            f"Referencia: {value('shots_total', ref_field)} remates · {value('goals', ref_field)} goles",
            NAVY_2,
        ),
        (
            "Recuperación defensiva",
            f"Entradas ganadas {value('tackles_won', current_field)} · Interc. {value('interceptions', current_field)}",
            f"Referencia: {value('tackles_won', ref_field)} · {value('interceptions', ref_field)}",
            AMBER,
        ),
        (
            "Pérdidas",
            f"Pérdidas {value('turnovers', current_field)} · Desposesiones {value('dispossessed', current_field)}",
            f"Referencia: {value('turnovers', ref_field)} · {value('dispossessed', ref_field)}",
            RED,
        ),
    ]
    return _insight_grid(items, width, styles)


def _evidence_strip(items: list[tuple[str, str]], width: float, styles) -> Table:
    cols = []
    for label, value in items:
        cell = Table(
            [[Paragraph(label.upper(), styles["kpi_label"])], [Paragraph(value, styles["body_bold"])]],
            colWidths=[width / max(len(items), 1) - 2 * mm],
        )
        cell.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        cols.append(cell)
    table = Table([cols], colWidths=[width / len(cols)] * len(cols))
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1),
    ]))
    return table


def _player_metric_selection(profile: list[dict[str, Any]], position_group: str) -> list[dict[str, Any]]:
    by_key = {str(x.get("key")): x for x in profile}
    if position_group == "GK":
        keys = ["pass_completion_pct", "passes_completed_per90", "turnovers_per90", "dispossessed_per90"]
    elif position_group in {"CB", "FB", "WB", "FB_WB"}:
        keys = ["pass_completion_pct", "passes_completed_per90", "tackles_won_per90", "interceptions_per90", "turnovers_per90", "shots_per90"]
    elif position_group in {"DM", "CM", "DM_CM", "AM"}:
        keys = ["pass_completion_pct", "passes_completed_per90", "assists_per90", "interceptions_per90", "turnovers_per90", "dispossessed_per90"]
    else:
        keys = ["pass_completion_pct", "shots_per90", "goals_per90", "assists_per90", "turnovers_per90", "dispossessed_per90"]
    return [by_key[k] for k in keys if k in by_key and any(_num(by_key[k].get(f)) is not None for f in ("current", "last5", "previous5"))]


def _team_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    team = _safe((payload.get("team") or {}).get("display_name"), "Equipo")
    overview = payload.get("overview") or {}
    matches = sorted(list(payload.get("matches") or []), key=lambda r: _date(r.get("match_date")), reverse=True)
    snapshot = list(payload.get("rating_snapshot") or [])
    history = sorted(list(payload.get("rating_history") or []), key=lambda r: _date(r.get("match_date")))
    squad = list(payload.get("squad") or [])
    technical = list(payload.get("technical_profile") or [])
    latest = matches[0] if matches else {}
    latest_hist = history[-1] if history else {}
    period = "Sin periodo disponible"
    if matches:
        period = f"{_date(matches[-1].get('match_date'))} - {_date(matches[0].get('match_date'))}"
    story: list[Any] = [
        _cover("Informe de rendimiento · Equipo", team, f"Periodo {period} · {_rating_name(payload.get('match_rating_version'))}", width, styles),
        Spacer(1, 4 * mm),
    ]
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

    comparable = [r for r in snapshot if _num(r.get("trend_delta_5v5")) is not None]
    rise = max(comparable, key=lambda r: _num(r.get("trend_delta_5v5")) or -999) if comparable else None
    fall = min(comparable, key=lambda r: _num(r.get("trend_delta_5v5")) or 999) if comparable else None
    venue = "Local" if latest.get("venue") == "H" else "Visitante" if latest.get("venue") == "A" else "Contexto no disponible"
    story += _section("01 · Resumen ejecutivo", "Qué ha pasado, qué ha cambiado y dónde conviene revisar.", width, styles)
    story.append(_insight_grid([
        ("Último registro", f"{team} {score} {_safe(latest.get('opponent'))}", f"{_date(latest.get('match_date'))} · {venue}", TEAL),
        ("Forma reciente", " · ".join(form) if form else "-", "Secuencia descriptiva; no predicción", NAVY_2),
        ("Mayor subida reciente", f"{_safe(rise.get('player'))} ({_fmt(rise.get('trend_delta_5v5'), 2)})" if rise else "Sin muestra comparable", "Últimos 5 vs 5 anteriores", GREEN),
        ("Mayor bajada reciente", f"{_safe(fall.get('player'))} ({_fmt(fall.get('trend_delta_5v5'), 2)})" if fall else "Sin muestra comparable", "Últimos 5 vs 5 anteriores", RED),
    ], width, styles))

    story += _section("02 · Evolución del rendimiento", "Mediana del Match Rating de los jugadores utilizados por partido.", width, styles)
    vals = [v for v in [_num(r.get("median_match_rating")) for r in history] if v is not None]
    labs = [_date(r.get("match_date")) for r in history if _num(r.get("median_match_rating")) is not None]
    story.append(_trend_chart(vals, labs, width, 52 * mm, 3, 10))

    story.append(PageBreak())
    story += _section("03 · Pulso técnico", "Datos observados del equipo. Se priorizan métricas simples y comparables; no se aplican umbrales bueno/malo.", width, styles)
    if technical:
        story.append(_phase_cards(technical, width, styles, "team"))
        story.append(Spacer(1, 2 * mm))
        story.append(_profile_table(technical, width, styles, "team"))
    else:
        story.append(Paragraph("No hay datos técnicos agregados disponibles.", styles["body"]))

    story += _section("04 · Plantilla: nivel reciente y cambio", "Media de los últimos 5 partidos frente al cambio respecto a los 5 anteriores. No es un ranking de calidad.", width, styles)
    points = []
    for row in snapshot:
        x, y = _num(row.get("avg_last5")), _num(row.get("trend_delta_5v5"))
        if x is not None and y is not None:
            points.append((_safe(row.get("player")), x, y))
    if points:
        story.append(_scatter_chart(points, width, 47 * mm))

    story.append(PageBreak())
    story += _section("05 · Seguimiento de plantilla", "Ordenado por minutos acumulados. La tabla aporta detalle; el gráfico anterior aporta contexto.", width, styles)
    snap_by_player = {str(r.get("player")): r for r in snapshot}
    rows = [["Jugador", "Perfil", "Min", "Último", "Media L5", "Δ 5v5", "Conf. %"]]
    for row in sorted(squad, key=lambda r: _num(r.get("minutes")) or 0, reverse=True):
        if (_num(row.get("minutes")) or 0) <= 0:
            continue
        s = snap_by_player.get(str(row.get("player")), {})
        rows.append([
            row.get("player"), _position(s.get("latest_position_group")), _count(row.get("minutes")),
            _fmt(s.get("latest_match_rating"), 2), _fmt(s.get("avg_last5"), 2),
            _fmt(s.get("trend_delta_5v5"), 2), _fmt(s.get("latest_confidence"), 0),
        ])
    story.append(_data_table(rows[:25], [35*mm, 31*mm, 19*mm, 22*mm, 24*mm, 22*mm, 20*mm], styles))

    story += _section("06 · Partidos recientes", "Resultado y contexto básico de los últimos registros.", width, styles)
    rows = [["Fecha", "L/V", "Rival", "Marcador", "Formación"]]
    for row in matches[:10]:
        a, b = _num(row.get("score_for")), _num(row.get("score_against"))
        result = f"{int(a)}-{int(b)}" if a is not None and b is not None else "-"
        rows.append([_date(row.get("match_date")), "L" if row.get("venue") == "H" else "V", row.get("opponent"), result, _safe(row.get("starting_formation"))])
    story.append(_data_table(rows, [28*mm, 14*mm, 64*mm, 25*mm, 35*mm], styles))
    story.append(Spacer(1, 3 * mm))
    story.append(_evidence_strip([
        ("Base", f"{_count(overview.get('matches'))} partidos · {_count(overview.get('players'))} jugadores"),
        ("GPS", "Opcional · no condiciona Team Mode"),
        ("Interpretación", "Descriptiva y auditable"),
        ("Decisiones", "Sin recomendación automática"),
    ], width, styles))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("El informe combina resultados ya materializados con agregados descriptivos transparentes de las acciones registradas. No calcula xG, posesión, presión, tracking ni otras métricas que no existan en la fuente.", styles["note"]))
    return story


def _player_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    team = _safe((payload.get("team") or {}).get("display_name"), "Equipo")
    summary = payload.get("summary") or {}
    snapshot = payload.get("player_snapshot") or {}
    ratings = sorted(list(payload.get("match_ratings") or []), key=lambda r: _date(r.get("match_date")), reverse=True)
    history = list(payload.get("match_history") or [])
    technical = list(payload.get("technical_profile") or [])
    latest = ratings[0] if ratings else {}
    gate = payload.get("latest_role_fit_gate") or {}
    perf = payload.get("performance_index") or {}
    player = _safe(summary.get("player"), "Jugador")
    group = str(latest.get("position_group") or snapshot.get("latest_position_group") or "")
    profile = _position(group)
    story: list[Any] = [
        _cover("Informe individual · Jugador", player, f"{team} · {profile} · {_rating_name(payload.get('match_rating_version'))}", width, styles),
        Spacer(1, 4 * mm),
    ]
    story.append(_kpi_row([
        ("Último Match Rating", _fmt(latest.get("match_rating_10"), 2, "/10"), _safe(latest.get("opponent"))),
        ("Media últimos 5", _fmt(snapshot.get("avg_last5"), 2, "/10"), "Forma reciente"),
        ("Cambio 5 vs 5", _fmt(snapshot.get("trend_delta_5v5"), 2), "Últimos 5 vs anteriores"),
        ("Confianza", _fmt(latest.get("match_rating_confidence"), 0, "%"), "Último partido"),
    ], width, styles))
    sf, sa = _num(latest.get("score_for")), _num(latest.get("score_against"))
    score = f"{int(sf)}-{int(sa)}" if sf is not None and sa is not None else "-"
    story += _section("01 · Resumen para el staff", "Contexto, forma y disponibilidad de evidencia.", width, styles)
    story.append(_insight_grid([
        ("Último partido", f"{_safe(latest.get('opponent'))} · {score}", f"{_date(latest.get('match_date'))} · {_count(latest.get('minutes_played'))} min", TEAL),
        ("Perfil observado", profile, f"{_count(summary.get('appearances'))} apariciones · {_count(summary.get('minutes'))} min", NAVY_2),
        ("Performance Index", _fmt(perf.get("performance_score"), 1, "/100"), "Capa histórica/posicional complementaria", AMBER),
        ("Motor experto", _expert_status(gate.get("final_status")), f"Cobertura: {_fmt((_num(gate.get('evidence_coverage')) or 0) * 100 if 0 <= (_num(gate.get('evidence_coverage')) or 0) <= 1 else gate.get('evidence_coverage'), 0, '%')}", RED if "Sin recomendación" in _expert_status(gate.get("final_status")) else TEAL),
    ], width, styles))

    story += _section("02 · Trayectoria", "Evolución del Match Rating partido a partido; escala fija 3-10.", width, styles)
    chronological = sorted(ratings, key=lambda r: _date(r.get("match_date")))
    vals = [v for v in [_num(r.get("match_rating_10")) for r in chronological] if v is not None]
    labs = [_date(r.get("match_date")) for r in chronological if _num(r.get("match_rating_10")) is not None]
    story.append(_trend_chart(vals, labs, width, 52 * mm, 3, 10))

    dims = []
    if group == "GK":
        for label, key in [("Shot-stopping", "defensive_contribution"), ("Distribución", "creation_progression"), ("Disciplina", "discipline")]:
            v = _num(latest.get(key))
            if v is not None:
                dims.append((label, v))
    else:
        for label, key in [("Amenaza ofensiva", "attacking_threat"), ("Creación / progresión", "creation_progression"), ("Contribución defensiva", "defensive_contribution"), ("Finalización", "finishing"), ("Disciplina", "discipline")]:
            v = _num(latest.get(key))
            if v is not None:
                dims.append((label, v))
    if dims:
        block = _section("03 · Dimensiones del último partido", "Scores materializados que explican la nota; no son un scouting independiente.", width, styles)
        block.append(_bar_chart(dims, width, 35 * mm, 0, 100))
        story.append(KeepTogether(block))

    story.append(PageBreak())
    story += _section("04 · Perfil técnico reciente", "Métricas simples por rol de uso. Últimos 5 frente a 5 anteriores; sin etiquetar el cambio como bueno o malo.", width, styles)
    selected_metrics = _player_metric_selection(technical, group)
    if selected_metrics:
        story.append(_profile_table(selected_metrics, width, styles, "player"))
    else:
        story.append(Paragraph("No hay muestra técnica suficiente para construir el perfil reciente.", styles["body"]))

    story += _section("05 · Producción reciente", "Acciones registradas en los últimos partidos. Los conteos se mantienen junto al contexto de minutos.", width, styles)
    rows = [["Fecha", "Rival", "Min", "Pases", "Remates", "Goles", "Entradas", "Interc."]]
    for row in sorted(history, key=lambda r: _date(r.get("match_date")), reverse=True)[:7]:
        pc, pt = _num(row.get("passes_completed")), _num(row.get("passes_total"))
        passes = f"{int(pc)}/{int(pt)}" if pc is not None and pt is not None else "-"
        rows.append([_date(row.get("match_date")), row.get("opponent"), _count(row.get("minutes")), passes, _count(row.get("shots_total")), _count(row.get("goals")), _count(row.get("tackles_won")), _count(row.get("interceptions"))])
    story.append(_data_table(rows, [27*mm, 44*mm, 14*mm, 25*mm, 18*mm, 15*mm, 20*mm, 18*mm], styles))

    story += _section("06 · Trazabilidad", "Qué sabe el sistema y qué no debe inferirse.", width, styles)
    story.append(_evidence_strip([
        ("Rol observado", _roles(gate.get("observed_role"))),
        ("Historial mismo rol", _count(gate.get("same_role_history"))),
        ("Cobertura", _fmt((_num(gate.get('evidence_coverage')) or 0) * 100 if 0 <= (_num(gate.get('evidence_coverage')) or 0) <= 1 else gate.get('evidence_coverage'), 0, '%')),
        ("Estado", _expert_status(gate.get("final_status"))),
    ], width, styles))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("El informe prioriza evolución, contexto y métricas observables. No infiere causa táctica, fatiga, riesgo de lesión, titularidad ni potencial futuro a partir de estos datos.", styles["note"]))
    return story


def _match_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    team = _safe((payload.get("team") or {}).get("display_name"), "Equipo")
    match = payload.get("match") or {}
    summary = payload.get("match_summary") or {}
    ratings = list(payload.get("ratings") or [])
    obs = payload.get("observations") or {}
    technical = list(payload.get("technical_profile") or [])
    opponent = _safe(match.get("opponent"), "Rival")
    sf, sa = _num(match.get("score_for")), _num(match.get("score_against"))
    score = f"{int(sf)}-{int(sa)}" if sf is not None and sa is not None else "-"
    venue = "Local" if match.get("venue") == "H" else "Visitante" if match.get("venue") == "A" else "-"
    story: list[Any] = [
        _cover("Informe postpartido", f"{team} {score} {opponent}", f"{_date(match.get('match_date'))} · {venue} · {_rating_name(payload.get('match_rating_version'))}", width, styles),
        Spacer(1, 4 * mm),
    ]
    fallback = sum(1 for r in ratings if "ROLE_UNAVAILABLE" in str(r.get("rating_path") or ""))
    story.append(_kpi_row([
        ("Marcador", score, f"{team} vs {opponent}"),
        ("Rating mediano", _fmt(summary.get("median_match_rating"), 2, "/10"), "Valor materializado"),
        ("Confianza mediana", _fmt(summary.get("median_confidence"), 0, "%"), "Valor materializado"),
        ("Rol no disponible", str(fallback), "Fallback explícito"),
    ], width, styles))

    scorers = obs.get("goal_scorers") or []
    assists = obs.get("assist_providers") or []
    leaders = obs.get("leaders") or {}
    goals_text = ", ".join(f"{x.get('player')} ({x.get('goals')})" for x in scorers) if scorers else "Sin goles registrados"
    assists_text = ", ".join(f"{x.get('player')} ({x.get('assists')})" for x in assists) if assists else "Sin asistencias registradas"
    def leader_text(key: str) -> str:
        item = leaders.get(key) or {}
        players = item.get("players") or []
        value = item.get("value")
        return f"{', '.join(map(str, players))} · {_fmt(value, 0)}" if players else "Sin dato"

    story += _section("01 · Lectura rápida", "Hechos deterministas del partido; sirven para priorizar la revisión de vídeo.", width, styles)
    story.append(_insight_grid([
        ("Goles", goals_text, "Contribución directa", TEAL),
        ("Asistencias", assists_text, "Contribución directa", NAVY_2),
        ("Remates", leader_text("shots_total"), "Máximo individual observado", AMBER),
        ("Pases completados", leader_text("passes_completed"), "Máximo individual observado", TEAL),
    ], width, styles))

    story += _section("02 · Huella técnica del equipo", "El partido se compara únicamente con los cinco partidos anteriores disponibles. No se utilizan partidos futuros.", width, styles)
    if technical:
        story.append(_phase_cards(technical, width, styles, "match"))
        story.append(Spacer(1, 2 * mm))
        story.append(_profile_table(technical, width, styles, "match"))

    story += _section("03 · Distribución del Match Rating", "Ordenación descriptiva; no es una recomendación de selección.", width, styles)
    bars = sorted([(_safe(r.get("player")), _num(r.get("match_rating_10"))) for r in ratings if _num(r.get("match_rating_10")) is not None], key=lambda x: x[1], reverse=True)
    story.append(_bar_chart([(name, float(value)) for name, value in bars[:15]], width, 62 * mm, 3, 10))

    story.append(PageBreak())
    story += _section("04 · Ficha de jugadores", "Minutos, perfil, Match Rating, confianza y método materializado.", width, styles)
    rows = [["Jugador", "Perfil", "Min", "Rating", "Conf. %", "Método"]]
    for row in sorted(ratings, key=lambda r: _num(r.get("match_rating_10")) or -999, reverse=True):
        rows.append([row.get("player"), _position(row.get("position_group")), _count(row.get("minutes_played")), _fmt(row.get("match_rating_10"), 2), _fmt(row.get("match_rating_confidence"), 0), _rating_context(row.get("match_rating_context") or row.get("rating_path"))])
    story.append(_data_table(rows, [34*mm, 29*mm, 13*mm, 18*mm, 18*mm, 55*mm], styles))

    outfield = [r for r in ratings if "OUTFIELD_PERF18" in str(r.get("rating_path") or "")]
    if outfield:
        story += _section("05 · Dimensiones explicativas", "Valores que explican el Match Rating de los jugadores de campo con contexto posicional fiable.", width, styles)
        rows = [["Jugador", "Amenaza", "Creación", "Defensa", "Finalización", "Disciplina"]]
        for row in outfield[:10]:
            rows.append([row.get("player"), _fmt(row.get("attacking_threat"), 1), _fmt(row.get("creation_progression"), 1), _fmt(row.get("defensive_contribution"), 1), _fmt(row.get("finishing"), 1), _fmt(row.get("discipline"), 1)])
        story.append(_data_table(rows, [42*mm, 24*mm, 24*mm, 24*mm, 27*mm, 24*mm], styles))

    conf = [_num(r.get("match_rating_confidence")) for r in ratings]
    conf = [x for x in conf if x is not None]
    story += _section("06 · Calidad de evidencia", "Límites antes de convertir los datos en una decisión técnica.", width, styles)
    story.append(_evidence_strip([
        ("Jugadores utilizados", str(len(ratings))),
        ("Fallback de rol", str(fallback)),
        ("Confianza mínima", _fmt(min(conf) if conf else None, 0, "%")),
        ("Uso", "Revisión descriptiva"),
    ], width, styles))
    story.append(Spacer(1, 3 * mm))
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
    if report_type == "team":
        story = _team_story(payload, styles, width)
    elif report_type == "player":
        story = _player_story(payload, styles, width)
    else:
        story = _match_story(payload, styles, width)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
