"""Spanish-only ReportLab renderer for TEAM / PLAYER / MATCH PDF exports.

Consumes structured report payloads only. It does not calculate critical metrics or
issue tactical recommendations. Demo identity masking is handled upstream by the
report data builder.
"""
from __future__ import annotations

from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#102A43")
TEAL = colors.HexColor("#1F7A6D")
LIGHT = colors.HexColor("#F4F7F9")
BORDER = colors.HexColor("#DDE5EB")
TEXT = colors.HexColor("#263746")
MUTED = colors.HexColor("#607D8B")
WHITE = colors.white

POSITION_LABELS = {
    "CB": "Central",
    "FB_WB": "Lateral / Carrilero",
    "DM_CM": "Mediocentro / Interior",
    "AM_W": "Mediapunta / Extremo",
    "ST": "Delantero",
    "GK": "Portero",
    "OTHER_OUTFIELD": "Rol no observable",
}


def _safe(value: Any) -> str:
    return "—" if value is None else str(value)


def _fmt(value: Any, decimals: int = 1) -> str:
    try:
        if value is None:
            return "—"
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return _safe(value)


def _position(value: Any) -> str:
    return "—" if value is None else POSITION_LABELS.get(str(value), str(value))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "kicker": ParagraphStyle("fps_kicker", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=TEAL, tracking=1.0),
        "title": ParagraphStyle("fps_title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20, leading=23, textColor=NAVY, alignment=TA_LEFT, spaceAfter=3),
        "subtitle": ParagraphStyle("fps_subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=8.2, leading=10.5, textColor=MUTED, spaceAfter=7),
        "h2": ParagraphStyle("fps_h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=NAVY, spaceBefore=9, spaceAfter=5),
        "body": ParagraphStyle("fps_body", parent=base["BodyText"], fontName="Helvetica", fontSize=8.2, leading=11, textColor=TEXT, spaceAfter=4),
        "note": ParagraphStyle("fps_note", parent=base["BodyText"], fontName="Helvetica-Oblique", fontSize=7.3, leading=9.2, textColor=MUTED, spaceBefore=4, spaceAfter=5),
        "table_header": ParagraphStyle("fps_th", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=6.6, leading=8.2, textColor=WHITE, alignment=TA_CENTER),
        "table_cell": ParagraphStyle("fps_td", parent=base["Normal"], fontName="Helvetica", fontSize=6.6, leading=8.2, textColor=TEXT),
        "kpi_label": ParagraphStyle("fps_kl", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=6.2, leading=7.4, textColor=MUTED, alignment=TA_CENTER),
        "kpi_value": ParagraphStyle("fps_kv", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=14, leading=16, textColor=NAVY, alignment=TA_CENTER),
        "kpi_sub": ParagraphStyle("fps_ks", parent=base["Normal"], fontName="Helvetica", fontSize=5.8, leading=7.2, textColor=MUTED, alignment=TA_CENTER),
    }


def _p(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_safe(value)), style)


def _table(rows: list[list[Any]], widths: list[float], styles: dict[str, ParagraphStyle]) -> Table:
    cooked: list[list[Any]] = []
    for i, row in enumerate(rows):
        style = styles["table_header"] if i == 0 else styles["table_cell"]
        cooked.append([_p(cell, style) for cell in row])
    table = Table(cooked, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, BORDER),
    ]
    for i in range(1, len(cooked)):
        if i % 2 == 0:
            commands.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    table.setStyle(TableStyle(commands))
    return table


def _kpis(items: list[tuple[str, Any, str]], width: float, styles: dict[str, ParagraphStyle]) -> Table:
    gap = 2.5 * mm
    card_width = (width - gap * (len(items) - 1)) / max(len(items), 1)
    cells: list[Any] = []
    widths: list[float] = []
    for idx, (label, value, sub) in enumerate(items):
        card = Table([
            [Paragraph(escape(label), styles["kpi_label"])],
            [Paragraph(escape(_safe(value)), styles["kpi_value"])],
            [Paragraph(escape(sub), styles["kpi_sub"])],
        ], colWidths=[card_width])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        cells.append(card)
        widths.append(card_width)
        if idx < len(items) - 1:
            cells.append("")
            widths.append(gap)
    outer = Table([cells], colWidths=widths, hAlign="LEFT")
    outer.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return outer


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "Football Performance System · exportación estructurada")
    canvas.drawRightString(A4[0] - 18 * mm, 9 * mm, f"Página {doc.page}")
    canvas.restoreState()


def _header(story: list[Any], payload: dict[str, Any], title: str, styles: dict[str, ParagraphStyle]) -> None:
    team = payload.get("team") or {}
    story.append(Paragraph("FOOTBALL PERFORMANCE SYSTEM", styles["kicker"]))
    story.append(Paragraph(escape(title), styles["title"]))
    meta = f"{_safe(team.get('display_name'))} · Match Rating {_safe(payload.get('match_rating_version'))} · Analytics {_safe(payload.get('engine_version'))}"
    story.append(Paragraph(escape(meta), styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceBefore=0, spaceAfter=8))


def _method_note(story: list[Any], styles: dict[str, ParagraphStyle]) -> None:
    story.append(Paragraph(
        "Nota metodológica: este informe muestra datos y resultados ya materializados. No recalcula ratings, no crea umbrales nuevos y no emite recomendaciones tácticas no validadas.",
        styles["note"],
    ))


def _team_story(payload: dict[str, Any], styles: dict[str, ParagraphStyle], width: float) -> list[Any]:
    story: list[Any] = []
    _header(story, payload, "Informe de equipo", styles)
    overview = payload.get("overview") or {}
    story.append(_kpis([
        ("PARTIDOS", overview.get("matches"), "Historial disponible"),
        ("JUGADORES", overview.get("players"), "Plantilla registrada"),
        ("GOLES", overview.get("goals"), "Datos observados"),
        ("ASISTENCIAS", overview.get("assists"), "Datos observados"),
    ], width, styles))

    story.append(Paragraph("Estado actual de la plantilla", styles["h2"]))
    snapshot = payload.get("rating_snapshot") or []
    if snapshot:
        rows = [["Jugador", "Perfil", "Último rating", "Conf. %", "Media L5", "Delta 5v5"]]
        for row in snapshot:
            rows.append([row.get("player"), _position(row.get("latest_position_group")), _fmt(row.get("latest_match_rating")), _fmt(row.get("latest_confidence"), 0), _fmt(row.get("avg_last5")), _fmt(row.get("trend_delta_5v5"))])
        story.append(_table(rows, [42 * mm, 34 * mm, 23 * mm, 19 * mm, 22 * mm, 22 * mm], styles))
    else:
        story.append(Paragraph("No hay Match Ratings materializados para la plantilla.", styles["body"]))

    story.append(Paragraph("Partidos recientes", styles["h2"]))
    rows = [["Fecha", "L/V", "Rival", "Marcador", "Formación"]]
    for row in (payload.get("matches") or [])[:12]:
        score = "—" if row.get("score_for") is None or row.get("score_against") is None else f"{row.get('score_for')}-{row.get('score_against')}"
        rows.append([row.get("match_date"), row.get("venue"), row.get("opponent"), score, row.get("starting_formation")])
    story.append(_table(rows, [31 * mm, 12 * mm, 58 * mm, 24 * mm, 35 * mm], styles))
    _method_note(story, styles)

    story.append(PageBreak())
    story.append(Paragraph("Plantilla", styles["h2"]))
    rows = [["Jugador", "Apar.", "Tit.", "Minutos", "Goles", "Asist.", "Roles"]]
    for row in payload.get("squad") or []:
        rows.append([row.get("player"), row.get("appearances"), row.get("starts"), row.get("minutes"), row.get("goals"), row.get("assists"), row.get("observed_roles")])
    story.append(_table(rows, [44 * mm, 14 * mm, 14 * mm, 19 * mm, 14 * mm, 16 * mm, 45 * mm], styles))
    return story


def _player_story(payload: dict[str, Any], styles: dict[str, ParagraphStyle], width: float) -> list[Any]:
    story: list[Any] = []
    summary = payload.get("summary") or {}
    ratings = payload.get("match_ratings") or []
    latest = ratings[0] if ratings else {}
    perf = payload.get("performance_index") or {}
    _header(story, payload, f"Informe de jugador · {_safe(summary.get('player'))}", styles)

    story.append(_kpis([
        ("MATCH RATING", "—" if not latest else f"{_fmt(latest.get('match_rating_10'))}/10", "Último partido"),
        ("CONFIANZA", "—" if not latest else f"{_fmt(latest.get('match_rating_confidence'), 0)}%", "Evidencia del partido"),
        ("PERFORMANCE INDEX", "—" if not perf else f"{_fmt(perf.get('performance_score'))}/100", "Histórico / posicional"),
        ("APARICIONES", summary.get("appearances"), "Temporada"),
        ("MINUTOS", summary.get("minutes"), "Acumulados"),
    ], width, styles))

    story.append(Paragraph("Perfil y producción", styles["h2"]))
    story.append(_table([
        ["Titularidades", "Goles", "Asistencias", "Roles observados"],
        [summary.get("starts"), summary.get("goals"), summary.get("assists"), summary.get("observed_roles")],
    ], [30 * mm, 24 * mm, 26 * mm, 80 * mm], styles))

    story.append(Paragraph("Historial reciente", styles["h2"]))
    rows = [["Fecha", "Rival", "Min", "Perfil", "Rating", "Conf. %"]]
    for row in ratings[:12]:
        rows.append([row.get("match_date"), row.get("opponent"), _fmt(row.get("minutes_played"), 0), _position(row.get("position_group")), _fmt(row.get("match_rating_10")), _fmt(row.get("match_rating_confidence"), 0)])
    story.append(_table(rows, [31 * mm, 48 * mm, 16 * mm, 31 * mm, 18 * mm, 18 * mm], styles))

    gate = payload.get("latest_role_fit_gate") or {}
    if gate:
        story.append(Paragraph("Motor experto", styles["h2"]))
        story.append(_table([
            ["Rol observado", "Historial mismo rol", "Cobertura", "Estado final"],
            [gate.get("observed_role"), gate.get("same_role_history"), gate.get("evidence_coverage"), gate.get("final_status")],
        ], [35 * mm, 35 * mm, 25 * mm, 65 * mm], styles))
    _method_note(story, styles)
    return story


def _match_story(payload: dict[str, Any], styles: dict[str, ParagraphStyle], width: float) -> list[Any]:
    story: list[Any] = []
    match = payload.get("match") or {}
    team = payload.get("team") or {}
    opponent = match.get("opponent") or "Rival"
    score = "—" if match.get("score_for") is None or match.get("score_against") is None else f"{match.get('score_for')}-{match.get('score_against')}"
    _header(story, payload, f"Informe de partido · {_safe(team.get('display_name'))} vs {_safe(opponent)}", styles)
    story.append(_kpis([
        ("MARCADOR", score, "Resultado"),
        ("SEDE", "Local" if match.get("venue") == "H" else "Visitante", "Contexto"),
        ("FORMACIÓN", match.get("starting_formation") or "—", "Registro de origen"),
        ("FECHA", match.get("match_date") or "—", "Partido"),
    ], width, styles))

    ratings = payload.get("ratings") or []
    story.append(Paragraph("Match Rating por jugador", styles["h2"]))
    if ratings:
        rows = [["Jugador", "Perfil", "Min", "Rating", "Conf. %", "Contexto"]]
        for row in ratings:
            rows.append([row.get("player"), _position(row.get("position_group")), _fmt(row.get("minutes_played"), 0), _fmt(row.get("match_rating_10")), _fmt(row.get("match_rating_confidence"), 0), row.get("match_rating_context") or row.get("rating_path")])
        story.append(_table(rows, [41 * mm, 31 * mm, 14 * mm, 18 * mm, 18 * mm, 40 * mm], styles))
    else:
        story.append(Paragraph("No hay ratings materializados para este partido.", styles["body"]))

    obs = payload.get("observations") or {}
    story.append(Paragraph("Observaciones deterministas", styles["h2"]))
    scorers = obs.get("goal_scorers") or []
    assists = obs.get("assist_providers") or []
    text_parts: list[str] = []
    if scorers:
        text_parts.append("Goles: " + ", ".join(f"{x.get('player')} ({x.get('goals')})" for x in scorers))
    if assists:
        text_parts.append("Asistencias: " + ", ".join(f"{x.get('player')} ({x.get('assists')})" for x in assists))
    if not text_parts:
        text_parts.append("Sin contribuciones directas adicionales registradas en esta capa.")
    for text in text_parts:
        story.append(Paragraph(escape(text), styles["body"]))
    _method_note(story, styles)
    return story


def render_pdf_bytes(payload: dict[str, Any]) -> bytes:
    """Render one Spanish static PDF from a validated structured payload."""
    report_type = str(payload.get("report_type") or "").lower()
    if report_type not in {"team", "player", "match"}:
        raise ValueError(f"Unsupported report_type: {report_type}")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm, title="Football Performance System")
    styles = _styles()
    width = A4[0] - 36 * mm
    if report_type == "team":
        story = _team_story(payload, styles, width)
    elif report_type == "player":
        story = _player_story(payload, styles, width)
    else:
        story = _match_story(payload, styles, width)
    story.append(Spacer(1, 4 * mm))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
