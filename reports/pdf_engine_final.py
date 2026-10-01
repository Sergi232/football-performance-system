"""Final professional PDF entry point.

TEAM and PLAYER reuse the professional report layouts from pdf_engine_pro with a
small final presentation pass. MATCH uses the same visual language but reads the
materialized match summary supplied by the analytics layer instead of recomputing
aggregate rating/confidence in the report.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any

import reports.pdf_engine_pro as pro
from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer

from reports.pdf_engine_pro import (
    AMBER,
    GREEN,
    NAVY_2,
    RED,
    TEAL,
    _bar_chart,
    _count,
    _cover,
    _data_table,
    _date,
    _fmt,
    _footer,
    _insight_grid,
    _num,
    _player_story,
    _position,
    _rating_context,
    _safe,
    _section,
    _styles,
    _team_story,
    _kpi_row,
)


def _scatter_chart_final(points: list[tuple[str, float, float]], width: float, height: float) -> Drawing:
    """Team scatter with fewer labels to improve readability in the PDF."""
    d = Drawing(width, height)
    left, right, bottom, top = 34, 14, 23, 10
    pw, ph = width - left - right, height - bottom - top
    y_abs = max([abs(p[2]) for p in points] + [0.5]) * 1.15
    x_min, x_max = 3.0, 10.0
    for i in range(4):
        y = bottom + ph * i / 3
        d.add(Line(left, y, left + pw, y, strokeColor=pro.GRID, strokeWidth=0.7))
    zero_y = bottom + ph * (y_abs) / (2 * y_abs)
    z = Line(left, zero_y, left + pw, zero_y, strokeColor=pro.MUTED, strokeWidth=0.8)
    z.strokeDashArray = [3, 3]
    d.add(z)

    # Only the four strongest recent changes are labelled. All points remain visible.
    label_names = {p[0] for p in sorted(points, key=lambda x: abs(x[2]), reverse=True)[:4]}
    for name, x_val, y_val in points:
        x = left + pw * (x_val - x_min) / (x_max - x_min)
        y = bottom + ph * (y_val + y_abs) / (2 * y_abs)
        d.add(Circle(x, y, 3.2, fillColor=TEAL, strokeColor=pro.WHITE, strokeWidth=0.8))
        if name in label_names:
            d.add(String(x + 4, y + 2, name, fontName="Helvetica", fontSize=5.2, fillColor=pro.TEXT))
    d.add(String(left + pw / 2, 2, "Media Match Rating - últimos 5", textAnchor="middle", fontName="Helvetica", fontSize=6.2, fillColor=pro.MUTED))
    d.add(String(2, height / 2, "Cambio 5 vs 5", fontName="Helvetica", fontSize=6.2, fillColor=pro.MUTED))
    return d


def _team_story_final(payload: dict[str, Any], styles, width: float) -> list[Any]:
    original_scatter = pro._scatter_chart
    pro._scatter_chart = _scatter_chart_final
    try:
        return _team_story(payload, styles, width)
    finally:
        pro._scatter_chart = original_scatter


def _player_story_final(payload: dict[str, Any], styles, width: float) -> list[Any]:
    """Compact the player report without changing its analytical content.

    - keep the dimensions heading and chart together;
    - cap the dimensions chart height;
    - remove the forced break before recent production;
    - show eight recent matches in the table to keep the report near two pages.
    """
    compact_payload = dict(payload)
    compact_payload["match_history"] = list(payload.get("match_history") or [])[:8]

    original_bar = pro._bar_chart

    def compact_bar(items, chart_width, chart_height, x_min, x_max):
        return original_bar(items, chart_width, min(chart_height, 34 * mm), x_min, x_max)

    pro._bar_chart = compact_bar
    try:
        story = _player_story(compact_payload, styles, width)
    finally:
        pro._bar_chart = original_bar

    # The original layout deliberately started recent production on a new page.
    # Let ReportLab paginate naturally instead so the second page is used efficiently.
    story = [item for item in story if not isinstance(item, PageBreak)]

    # Prevent an orphaned "Dimensiones" heading at the bottom of a page.
    for i, item in enumerate(story):
        if isinstance(item, Paragraph) and item.getPlainText() == "Dimensiones del último partido":
            chart_index = None
            for j in range(i + 1, min(i + 8, len(story))):
                if isinstance(story[j], Drawing):
                    chart_index = j
                    break
            if chart_index is not None:
                grouped = KeepTogether(story[i : chart_index + 1])
                story = story[:i] + [grouped] + story[chart_index + 1 :]
            break
    return story


def _match_story_final(payload: dict[str, Any], styles, width: float) -> list[Any]:
    team = _safe((payload.get("team") or {}).get("display_name"), "Equipo")
    match = payload.get("match") or {}
    summary = payload.get("match_summary") or {}
    ratings = list(payload.get("ratings") or [])
    obs = payload.get("observations") or {}
    opponent = _safe(match.get("opponent"), "Rival")
    sf, sa = _num(match.get("score_for")), _num(match.get("score_against"))
    score = f"{int(sf)}-{int(sa)}" if sf is not None and sa is not None else "-"
    venue = "Local" if match.get("venue") == "H" else "Visitante" if match.get("venue") == "A" else "-"
    meta = f"{_date(match.get('match_date'))} | {venue} | Match Rating {payload.get('match_rating_version')}"
    story: list[Any] = [_cover("Informe técnico de partido", f"{team} {score} {opponent}", meta, width, styles), Spacer(1, 5 * mm)]

    median_rating = summary.get("median_match_rating")
    median_conf = summary.get("median_confidence")
    fallback = sum(1 for r in ratings if "ROLE_UNAVAILABLE" in str(r.get("rating_path") or ""))
    story.append(_kpi_row([
        ("Marcador", score, f"{team} vs {opponent}"),
        ("Rating mediano", _fmt(median_rating, 2, "/10"), "Valor materializado"),
        ("Confianza mediana", _fmt(median_conf, 0, "%"), "Valor materializado"),
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

    story += _section("Lectura rápida", "Hechos del partido derivados directamente de los datos registrados.", width, styles)
    story.append(_insight_grid([
        ("Goles", goals_text, "Contribución directa", TEAL),
        ("Asistencias", assists_text, "Contribución directa", NAVY_2),
        ("Remates", leader_text("shots_total"), "Máximo observado", AMBER),
        ("Pases completados", leader_text("passes_completed"), "Máximo observado", TEAL),
    ], width, styles))

    story += _section("Distribución del Match Rating", "Ordenación descriptiva de la nota del partido. No es una recomendación de selección.", width, styles)
    bars = sorted(
        [(_safe(r.get("player")), _num(r.get("match_rating_10"))) for r in ratings if _num(r.get("match_rating_10")) is not None],
        key=lambda x: x[1],
        reverse=True,
    )
    story.append(_bar_chart([(name, float(value)) for name, value in bars[:15]], width, 78 * mm, 3, 10))

    story.append(PageBreak())
    story += _section("Ficha de jugadores", "Minutos, perfil, Match Rating, confianza y método de cálculo materializado.", width, styles)
    rows = [["Jugador", "Perfil", "Min", "Rating", "Conf. %", "Método"]]
    ordered = sorted(ratings, key=lambda r: _num(r.get("match_rating_10")) or -999, reverse=True)
    for r in ordered:
        rows.append([
            r.get("player"),
            _position(r.get("position_group")),
            _count(r.get("minutes_played")),
            _fmt(r.get("match_rating_10"), 2),
            _fmt(r.get("match_rating_confidence"), 0),
            _rating_context(r.get("match_rating_context") or r.get("rating_path")),
        ])
    story.append(_data_table(rows, [34*mm, 29*mm, 13*mm, 18*mm, 18*mm, 55*mm], styles))

    outfield = [r for r in ratings if "OUTFIELD_PERF18" in str(r.get("rating_path") or "")]
    if outfield:
        story += _section("Dimensiones materializadas", "Valores explicativos del Match Rating para jugadores de campo con contexto posicional fiable.", width, styles)
        rows = [["Jugador", "Amenaza", "Creación", "Defensa", "Finalización", "Disciplina"]]
        for r in outfield[:12]:
            rows.append([
                r.get("player"),
                _fmt(r.get("attacking_threat"), 1),
                _fmt(r.get("creation_progression"), 1),
                _fmt(r.get("defensive_contribution"), 1),
                _fmt(r.get("finishing"), 1),
                _fmt(r.get("discipline"), 1),
            ])
        story.append(_data_table(rows, [42*mm, 24*mm, 24*mm, 24*mm, 27*mm, 24*mm], styles))

    conf_vals = [v for v in [_num(r.get("match_rating_confidence")) for r in ratings] if v is not None]
    story += _section("Calidad de evidencia", "Limitaciones que deben considerarse antes de interpretar el partido.", width, styles)
    story.append(_insight_grid([
        ("Jugadores utilizados", str(len(ratings)), "Apariciones con minutos", TEAL),
        ("Fallback de rol", str(fallback), "Casos sin rol táctico fiable", AMBER if fallback else GREEN),
        ("Confianza mínima", _fmt(min(conf_vals) if conf_vals else None, 0, "%"), "Valor mínimo observado", NAVY_2),
        ("Uso del informe", "Revisión descriptiva", "No determina alineación ni causa táctica", RED),
    ], width, styles))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Las observaciones y ratings son deterministas y ya estaban materializados antes de generar el PDF. El informe no usa un LLM para recalcularlos.", styles["note"]))
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
        story = _team_story_final(payload, styles, width)
    elif report_type == "player":
        story = _player_story_final(payload, styles, width)
    else:
        story = _match_story_final(payload, styles, width)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
