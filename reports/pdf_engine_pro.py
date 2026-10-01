"""Professional coaching-staff PDF renderer for TEAM / PLAYER / MATCH reports.

This renderer is intentionally report-specific: it is neither a screenshot of the web
app nor a raw table dump. It consumes only structured/materialized analytics, adds no
new critical metrics or tactical recommendations, and uses deterministic descriptive
summaries plus vector charts suitable for technical staff review.
"""
from __future__ import annotations

from html import escape
from io import BytesIO
from math import isnan
from typing import Any, Iterable

from reportlab.graphics.shapes import Circle, Drawing, Line, Path, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#0B1F33")
NAVY_2 = colors.HexColor("#14344F")
TEAL = colors.HexColor("#13A37F")
TEAL_DARK = colors.HexColor("#14765F")
GREEN = colors.HexColor("#198754")
RED = colors.HexColor("#C84630")
AMBER = colors.HexColor("#B7791F")
TEXT = colors.HexColor("#172B3A")
MUTED = colors.HexColor("#6B7C8F")
GRID = colors.HexColor("#E7EDF2")
BORDER = colors.HexColor("#DDE5EB")
LIGHT = colors.HexColor("#F5F7FA")
LIGHT_TEAL = colors.HexColor("#EAF7F3")
WHITE = colors.white

POSITION_LABELS = {
    "CB": "Central",
    "FB": "Lateral",
    "WB": "Carrilero",
    "FB_WB": "Lateral / Carrilero",
    "DM": "Mediocentro defensivo",
    "CM": "Mediocentro",
    "DM_CM": "Mediocentro / Interior",
    "AM": "Mediapunta",
    "W": "Extremo",
    "AM_W": "Mediapunta / Extremo",
    "ST": "Delantero",
    "GK": "Portero",
    "OTHER_OUTFIELD": "Rol no observable",
}

ROLE_REPLACEMENTS = (
    ("Defensive Midfielder", "Mediocentro defensivo"),
    ("Attacking Midfielder", "Mediapunta"),
    ("Wing Back", "Carrilero"),
    ("Goalkeeper", "Portero"),
    ("Midfielder", "Centrocampista"),
    ("Defender", "Defensa"),
    ("Striker", "Delantero"),
    ("Substitute", "Suplente"),
    ("Centre", "Centro"),
    ("Right", "Derecha"),
    ("Left", "Izquierda"),
)


def _safe(value: Any, fallback: str = "-") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text and text.lower() != "nan" else fallback


def _num(value: Any) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
        if isnan(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def _fmt(value: Any, decimals: int = 1, suffix: str = "") -> str:
    number = _num(value)
    return "-" if number is None else f"{number:.{decimals}f}{suffix}"


def _count(value: Any) -> str:
    number = _num(value)
    return "-" if number is None else str(int(round(number)))


def _date(value: Any) -> str:
    text = _safe(value)
    return text[:10] if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-" else text


def _position(value: Any) -> str:
    return POSITION_LABELS.get(str(value), _safe(value)) if value is not None else "-"


def _roles(value: Any) -> str:
    text = _safe(value)
    if text == "-":
        return text
    for source, target in ROLE_REPLACEMENTS:
        text = text.replace(source, target)
    return text


def _coverage(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "-"
    if 0 <= number <= 1:
        number *= 100
    return f"{number:.0f}%"


def _expert_status(value: Any) -> str:
    raw = _safe(value, "")
    labels = {
        "RECOMMENDATION_NOT_ISSUED_POLICY_UNVALIDATED": "Sin recomendación: política no validada",
        "RECOMMENDATION_NOT_ISSUED_INSUFFICIENT_EVIDENCE": "Sin recomendación: evidencia insuficiente",
        "RECOMMENDATION_NOT_ISSUED_ROLE_UNAVAILABLE": "Sin recomendación: rol no disponible",
    }
    if raw in labels:
        return labels[raw]
    if raw.startswith("RECOMMENDATION_NOT_ISSUED_"):
        return "Sin recomendación automática"
    return raw.replace("_", " ").title() if raw else "-"


def _rating_context(value: Any) -> str:
    raw = _safe(value, "").upper()
    if "GOALKEEPER" in raw:
        return "Modelo específico de portero"
    if "ROLE_UNAVAILABLE" in raw or "FALLBACK" in raw:
        return "Rol no disponible - fallback"
    if "POSITION_PRO" in raw or "OUTFIELD" in raw:
        return "Jugador de campo - contexto posicional"
    return "Materializado"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("pro_title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=22, leading=25, textColor=WHITE, alignment=TA_LEFT),
        "cover_sub": ParagraphStyle("pro_cover_sub", parent=base["Normal"], fontName="Helvetica", fontSize=9.2, leading=12, textColor=colors.HexColor("#BFD0DC")),
        "kicker": ParagraphStyle("pro_kicker", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.2, leading=9, textColor=TEAL, spaceAfter=2),
        "h1": ParagraphStyle("pro_h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=NAVY, spaceAfter=4),
        "h2": ParagraphStyle("pro_h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=NAVY, spaceBefore=6, spaceAfter=5),
        "body": ParagraphStyle("pro_body", parent=base["BodyText"], fontName="Helvetica", fontSize=8.4, leading=11.2, textColor=TEXT),
        "body_bold": ParagraphStyle("pro_body_bold", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8.4, leading=11.2, textColor=TEXT),
        "small": ParagraphStyle("pro_small", parent=base["BodyText"], fontName="Helvetica", fontSize=7.2, leading=9.2, textColor=MUTED),
        "small_bold": ParagraphStyle("pro_small_bold", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.2, leading=9.2, textColor=TEXT),
        "note": ParagraphStyle("pro_note", parent=base["BodyText"], fontName="Helvetica-Oblique", fontSize=7.1, leading=9, textColor=MUTED),
        "kpi_label": ParagraphStyle("pro_kpi_label", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=6.3, leading=7.5, textColor=MUTED, alignment=TA_CENTER),
        "kpi_value": ParagraphStyle("pro_kpi_value", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=17, textColor=NAVY, alignment=TA_CENTER),
        "kpi_sub": ParagraphStyle("pro_kpi_sub", parent=base["Normal"], fontName="Helvetica", fontSize=5.9, leading=7.2, textColor=MUTED, alignment=TA_CENTER),
        "th": ParagraphStyle("pro_th", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=6.3, leading=7.5, textColor=WHITE, alignment=TA_CENTER),
        "td": ParagraphStyle("pro_td", parent=base["Normal"], fontName="Helvetica", fontSize=6.3, leading=7.8, textColor=TEXT),
    }


def _p(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_safe(value)), style)


def _cover(title: str, subtitle: str, meta: str, width: float, styles: dict[str, ParagraphStyle]) -> Table:
    inner = Table([
        [Paragraph("FOOTBALL PERFORMANCE SYSTEM", ParagraphStyle("brand", parent=styles["kicker"], textColor=colors.HexColor("#7FE0C5")))],
        [Paragraph(escape(title), styles["title"])],
        [Paragraph(escape(subtitle), styles["cover_sub"])],
        [Spacer(1, 3 * mm)],
        [Paragraph(escape(meta), styles["cover_sub"])],
    ], colWidths=[width - 18 * mm])
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 9 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9 * mm),
        ("TOPPADDING", (0, 0), (-1, 0), 8 * mm),
        ("TOPPADDING", (0, 1), (-1, -1), 1.5 * mm),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8 * mm),
    ]))
    return inner


def _section(title: str, subtitle: str, width: float, styles: dict[str, ParagraphStyle]) -> list[Any]:
    return [
        Spacer(1, 3 * mm),
        Paragraph(escape(title), styles["h2"]),
        Paragraph(escape(subtitle), styles["small"]) if subtitle else Spacer(1, 0),
        Spacer(1, 1.5 * mm),
        Table([[""]], colWidths=[width], rowHeights=[1.2], style=[("BACKGROUND", (0, 0), (-1, -1), TEAL)]),
        Spacer(1, 2 * mm),
    ]


def _kpi_card(label: str, value: str, sub: str, width: float, styles: dict[str, ParagraphStyle]) -> Table:
    t = Table([
        [Paragraph(escape(label.upper()), styles["kpi_label"])],
        [Paragraph(escape(value), styles["kpi_value"])],
        [Paragraph(escape(sub), styles["kpi_sub"])],
    ], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _kpi_row(items: list[tuple[str, str, str]], width: float, styles: dict[str, ParagraphStyle]) -> Table:
    gap = 2.5 * mm
    card_w = (width - gap * (len(items) - 1)) / len(items)
    cells: list[Any] = []
    widths: list[float] = []
    for i, item in enumerate(items):
        cells.append(_kpi_card(*item, card_w, styles))
        widths.append(card_w)
        if i < len(items) - 1:
            cells.append("")
            widths.append(gap)
    t = Table([cells], colWidths=widths)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return t


def _insight(title: str, body: str, meta: str, width: float, styles: dict[str, ParagraphStyle], accent=TEAL) -> Table:
    t = Table([
        [Paragraph(escape(title), styles["small_bold"])],
        [Paragraph(escape(body), styles["body_bold"])],
        [Paragraph(escape(meta), styles["small"])],
    ], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("LINEBEFORE", (0, 0), (0, -1), 3, accent),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _insight_grid(items: list[tuple[str, str, str, colors.Color]], width: float, styles: dict[str, ParagraphStyle]) -> Table:
    gap = 3 * mm
    card_w = (width - gap) / 2
    rows = []
    for i in range(0, len(items), 2):
        left = _insight(*items[i][:3], card_w, styles, items[i][3])
        right = _insight(*items[i + 1][:3], card_w, styles, items[i + 1][3]) if i + 1 < len(items) else ""
        rows.append([left, "", right])
    t = Table(rows, colWidths=[card_w, gap, card_w])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return t


def _data_table(rows: list[list[Any]], widths: list[float], styles: dict[str, ParagraphStyle], header=True) -> Table:
    cooked = []
    for r_idx, row in enumerate(rows):
        style = styles["th"] if header and r_idx == 0 else styles["td"]
        cooked.append([_p(cell, style) for cell in row])
    t = Table(cooked, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, BORDER),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    for i in range(1 if header else 0, len(cooked)):
        if i % 2 == 0:
            commands.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    t.setStyle(TableStyle(commands))
    return t


def _trend_chart(values: list[float], labels: list[str], width: float, height: float, y_min: float, y_max: float) -> Drawing:
    d = Drawing(width, height)
    left, right, bottom, top = 30, 10, 18, 10
    pw, ph = width - left - right, height - bottom - top
    for i in range(4):
        y = bottom + ph * i / 3
        d.add(Line(left, y, left + pw, y, strokeColor=GRID, strokeWidth=0.8))
        val = y_min + (y_max - y_min) * i / 3
        d.add(String(2, y - 3, f"{val:.1f}", fontName="Helvetica", fontSize=6, fillColor=MUTED))
    if values:
        n = len(values)
        path = Path()
        for i, value in enumerate(values):
            x = left + (pw * i / max(n - 1, 1))
            y = bottom + ph * (value - y_min) / max(y_max - y_min, 0.001)
            y = max(bottom, min(bottom + ph, y))
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
            d.add(Circle(x, y, 2.6, fillColor=TEAL, strokeColor=WHITE, strokeWidth=0.8))
        path.strokeColor = TEAL
        path.strokeWidth = 2.2
        path.fillColor = None
        d.add(path)
        picks = sorted(set([0, n // 2, n - 1]))
        for idx in picks:
            x = left + (pw * idx / max(n - 1, 1))
            d.add(String(x, 2, labels[idx][:10], textAnchor="middle", fontName="Helvetica", fontSize=5.8, fillColor=MUTED))
    return d


def _bar_chart(items: list[tuple[str, float]], width: float, height: float, x_min: float, x_max: float) -> Drawing:
    d = Drawing(width, height)
    left, right, top, bottom = 86, 24, 8, 8
    pw = width - left - right
    row_h = (height - top - bottom) / max(len(items), 1)
    for i, (label, value) in enumerate(items):
        y = height - top - row_h * (i + 1) + row_h * 0.22
        d.add(String(left - 5, y + 2, label[:23], textAnchor="end", fontName="Helvetica", fontSize=6.2, fillColor=TEXT))
        d.add(Rect(left, y, pw, row_h * 0.52, fillColor=LIGHT, strokeColor=None))
        ratio = max(0, min(1, (value - x_min) / max(x_max - x_min, 0.001)))
        d.add(Rect(left, y, pw * ratio, row_h * 0.52, fillColor=TEAL, strokeColor=None))
        d.add(String(left + pw + 4, y + 2, f"{value:.1f}", fontName="Helvetica-Bold", fontSize=6.2, fillColor=TEXT))
    return d


def _scatter_chart(points: list[tuple[str, float, float]], width: float, height: float) -> Drawing:
    d = Drawing(width, height)
    left, right, bottom, top = 34, 14, 23, 10
    pw, ph = width - left - right, height - bottom - top
    y_abs = max([abs(p[2]) for p in points] + [0.5]) * 1.15
    x_min, x_max = 3.0, 10.0
    for i in range(4):
        y = bottom + ph * i / 3
        d.add(Line(left, y, left + pw, y, strokeColor=GRID, strokeWidth=0.7))
    zero_y = bottom + ph * (y_abs) / (2 * y_abs)
    z = Line(left, zero_y, left + pw, zero_y, strokeColor=MUTED, strokeWidth=0.8)
    z.strokeDashArray = [3, 3]
    d.add(z)
    label_names = {p[0] for p in sorted(points, key=lambda x: abs(x[2]), reverse=True)[:6]}
    for name, x_val, y_val in points:
        x = left + pw * (x_val - x_min) / (x_max - x_min)
        y = bottom + ph * (y_val + y_abs) / (2 * y_abs)
        d.add(Circle(x, y, 3.2, fillColor=TEAL, strokeColor=WHITE, strokeWidth=0.8))
        if name in label_names:
            d.add(String(x + 4, y + 2, name, fontName="Helvetica", fontSize=5.5, fillColor=TEXT))
    d.add(String(left + pw / 2, 2, "Media Match Rating - últimos 5", textAnchor="middle", fontName="Helvetica", fontSize=6.2, fillColor=MUTED))
    d.add(String(2, height / 2, "Cambio 5 vs 5", fontName="Helvetica", fontSize=6.2, fillColor=MUTED))
    return d


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.line(16 * mm, 13 * mm, A4[0] - 16 * mm, 13 * mm)
    canvas.setFont("Helvetica", 6.8)
    canvas.setFillColor(MUTED)
    canvas.drawString(16 * mm, 8.5 * mm, "Football Performance System - informe técnico")
    canvas.drawRightString(A4[0] - 16 * mm, 8.5 * mm, f"Página {doc.page}")
    canvas.restoreState()


def _recent_form(matches: list[dict[str, Any]], n: int = 5) -> str:
    labels = []
    for row in matches[:n]:
        sf, sa = _num(row.get("score_for")), _num(row.get("score_against"))
        if sf is None or sa is None:
            continue
        labels.append("G" if sf > sa else "P" if sf < sa else "E")
    return " · ".join(labels) if labels else "-"


def _team_story(payload: dict[str, Any], styles: dict[str, ParagraphStyle], width: float) -> list[Any]:
    team = _safe((payload.get("team") or {}).get("display_name"), "Equipo")
    matches = list(payload.get("matches") or [])
    snapshot = list(payload.get("rating_snapshot") or [])
    history = list(payload.get("rating_history") or [])
    squad = list(payload.get("squad") or [])
    overview = payload.get("overview") or {}
    matches = sorted(matches, key=lambda r: _date(r.get("match_date")), reverse=True)
    history = sorted(history, key=lambda r: _date(r.get("match_date")))
    latest = matches[0] if matches else {}
    latest_hist = history[-1] if history else {}

    title = "Informe técnico de equipo"
    subtitle = team
    period = "Sin periodo disponible"
    if matches:
        period = f"{_date(matches[-1].get('match_date'))} - {_date(matches[0].get('match_date'))}"
    meta = f"Periodo: {period} | Match Rating {payload.get('match_rating_version')}"
    story: list[Any] = [_cover(title, subtitle, meta, width, styles), Spacer(1, 5 * mm)]

    latest_score = "-"
    if latest:
        sf, sa = _num(latest.get("score_for")), _num(latest.get("score_against"))
        latest_score = f"{int(sf)}-{int(sa)}" if sf is not None and sa is not None else "-"
    story.append(_kpi_row([
        ("Último partido", latest_score, _safe(latest.get("opponent"))),
        ("Match Rating mediano", _fmt(latest_hist.get("median_match_rating"), 2, "/10"), "Último partido"),
        ("Forma L5", _recent_form(matches), "Más reciente primero"),
        ("Cobertura", f"{_count(overview.get('matches'))} partidos", f"{_count(overview.get('players'))} jugadores"),
    ], width, styles))

    comparable = [r for r in snapshot if _num(r.get("trend_delta_5v5")) is not None]
    rise = max(comparable, key=lambda r: _num(r.get("trend_delta_5v5")) or -999) if comparable else None
    fall = min(comparable, key=lambda r: _num(r.get("trend_delta_5v5")) or 999) if comparable else None
    venue = "Local" if latest.get("venue") == "H" else "Visitante" if latest.get("venue") == "A" else "Contexto no disponible"
    insights = [
        ("Último registro", f"{team} {latest_score} {_safe(latest.get('opponent'))}", f"{_date(latest.get('match_date'))} · {venue}", TEAL),
        ("Forma reciente", _recent_form(matches), "Secuencia descriptiva de los últimos cinco partidos", NAVY_2),
    ]
    if rise:
        insights.append(("Mayor subida reciente", f"{_safe(rise.get('player'))} ({_fmt(rise.get('trend_delta_5v5'), 2)})", "Cambio entre últimos 5 y 5 anteriores", GREEN))
    if fall:
        insights.append(("Mayor bajada reciente", f"{_safe(fall.get('player'))} ({_fmt(fall.get('trend_delta_5v5'), 2)})", "Cambio entre últimos 5 y 5 anteriores", RED))
    story += _section("Lectura rápida", "Hechos descriptivos para orientar la revisión del staff.", width, styles)
    story.append(_insight_grid(insights, width, styles))

    story += _section("Evolución del rendimiento", "Mediana del Match Rating de los jugadores utilizados por partido.", width, styles)
    vals = [v for v in [_num(r.get("median_match_rating")) for r in history] if v is not None]
    labs = [_date(r.get("match_date")) for r in history if _num(r.get("median_match_rating")) is not None]
    story.append(_trend_chart(vals, labs, width, 58 * mm, 3, 10))

    story.append(PageBreak())
    story += _section("Plantilla: nivel reciente y cambio", "El eje horizontal muestra la media de los últimos 5 partidos; el vertical, el cambio frente a los 5 anteriores. No es un ranking de calidad.", width, styles)
    points = []
    for r in snapshot:
        x, y = _num(r.get("avg_last5")), _num(r.get("trend_delta_5v5"))
        if x is not None and y is not None:
            points.append((_safe(r.get("player")), x, y))
    story.append(_scatter_chart(points, width, 66 * mm))

    story += _section("Seguimiento de plantilla", "Ordenado por minutos acumulados para evitar interpretar la tabla como una clasificación de calidad.", width, styles)
    minutes = {str(r.get("player")): _num(r.get("minutes")) or 0 for r in squad}
    current = sorted(snapshot, key=lambda r: minutes.get(str(r.get("player")), 0), reverse=True)
    rows = [["Jugador", "Perfil", "Min", "Último", "Media L5", "Delta 5v5", "Conf. %"]]
    for r in current[:24]:
        rows.append([
            r.get("player"), _position(r.get("latest_position_group")), _count(minutes.get(str(r.get("player")))),
            _fmt(r.get("latest_match_rating"), 2), _fmt(r.get("avg_last5"), 2), _fmt(r.get("trend_delta_5v5"), 2), _fmt(r.get("latest_confidence"), 0),
        ])
    story.append(_data_table(rows, [37*mm, 31*mm, 15*mm, 19*mm, 20*mm, 22*mm, 18*mm], styles))

    story.append(PageBreak())
    story += _section("Partidos recientes", "Resultado, condición y formación registrada.", width, styles)
    rows = [["Fecha", "L/V", "Rival", "Marcador", "Formación"]]
    for r in matches[:12]:
        sf, sa = _num(r.get("score_for")), _num(r.get("score_against"))
        score = f"{int(sf)}-{int(sa)}" if sf is not None and sa is not None else "-"
        venue_code = "L" if r.get("venue") == "H" else "V" if r.get("venue") == "A" else "-"
        rows.append([_date(r.get("match_date")), venue_code, r.get("opponent"), score, r.get("starting_formation") or "-"])
    story.append(_data_table(rows, [27*mm, 12*mm, 62*mm, 25*mm, 38*mm], styles))

    story += _section("Cobertura y límites", "Qué puede y qué no puede concluirse de este informe.", width, styles)
    story.append(_insight_grid([
        ("Base analizada", f"{_count(overview.get('matches'))} partidos · {_count(overview.get('players'))} jugadores", "Datos materializados disponibles en el sistema", TEAL),
        ("GPS", "Capa opcional", "La ausencia de GPS no invalida el Team Mode", NAVY_2),
        ("Interpretación", "Descriptiva y auditable", "No se crean umbrales bueno/malo en esta capa", AMBER),
        ("Recomendaciones", "No automáticas", "El Match Rating no activa decisiones tácticas por sí solo", RED),
    ], width, styles))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("El informe consume resultados ya materializados. No recalcula el Match Rating ni el Performance Index y no sustituye la revisión del cuerpo técnico.", styles["note"]))
    return story


def _player_story(payload: dict[str, Any], styles: dict[str, ParagraphStyle], width: float) -> list[Any]:
    team = _safe((payload.get("team") or {}).get("display_name"), "Equipo")
    summary = payload.get("summary") or {}
    snapshot = payload.get("player_snapshot") or {}
    ratings = sorted(list(payload.get("match_ratings") or []), key=lambda r: _date(r.get("match_date")), reverse=True)
    latest = ratings[0] if ratings else {}
    perf = payload.get("performance_index") or {}
    gate = payload.get("latest_role_fit_gate") or {}
    history = list(payload.get("match_history") or [])
    index_history = sorted(list(payload.get("performance_index_history") or []), key=lambda r: _date(r.get("match_date")))
    player = _safe(summary.get("player"), "Jugador")
    profile = _position(latest.get("position_group") or snapshot.get("latest_position_group"))
    meta = f"{team} | {profile} | Match Rating {payload.get('match_rating_version')}"
    story: list[Any] = [_cover("Informe técnico de jugador", player, meta, width, styles), Spacer(1, 5 * mm)]

    story.append(_kpi_row([
        ("Último Match Rating", _fmt(latest.get("match_rating_10"), 2, "/10"), _safe(latest.get("opponent"))),
        ("Media últimos 5", _fmt(snapshot.get("avg_last5"), 2, "/10"), "Forma reciente"),
        ("Cambio 5 vs 5", _fmt(snapshot.get("trend_delta_5v5"), 2), "Últimos 5 vs 5 anteriores"),
        ("Confianza", _fmt(latest.get("match_rating_confidence"), 0, "%"), "Último partido"),
    ], width, styles))

    sf, sa = _num(latest.get("score_for")), _num(latest.get("score_against"))
    score = f"{int(sf)}-{int(sa)}" if sf is not None and sa is not None else "-"
    story += _section("Lectura rápida", "Contexto de uso para el staff.", width, styles)
    story.append(_insight_grid([
        ("Último partido", f"{_safe(latest.get('opponent'))} · {score}", f"{_date(latest.get('match_date'))} · {_count(latest.get('minutes_played'))} minutos", TEAL),
        ("Perfil observado", profile, f"{_count(summary.get('appearances'))} apariciones · {_count(summary.get('minutes'))} minutos", NAVY_2),
        ("Performance Index", _fmt(perf.get("performance_score"), 1, "/100"), "Capa histórica/posicional complementaria", AMBER),
        ("Motor experto", _expert_status(gate.get("final_status")), f"Cobertura: {_coverage(gate.get('evidence_coverage'))}", RED if "Sin recomendación" in _expert_status(gate.get("final_status")) else TEAL),
    ], width, styles))

    story += _section("Trayectoria de Match Rating", "Evolución partido a partido en escala fija 3-10.", width, styles)
    chronological = sorted(ratings, key=lambda r: _date(r.get("match_date")))
    vals = [v for v in [_num(r.get("match_rating_10")) for r in chronological] if v is not None]
    labs = [_date(r.get("match_date")) for r in chronological if _num(r.get("match_rating_10")) is not None]
    story.append(_trend_chart(vals, labs, width, 56 * mm, 3, 10))

    dims: list[tuple[str, float]] = []
    if latest.get("position_group") == "GK":
        for label, key in [("Shot-stopping", "defensive_contribution"), ("Distribución", "creation_progression"), ("Disciplina", "discipline")]:
            value = _num(latest.get(key))
            if value is not None:
                dims.append((label, value))
    else:
        for label, key in [("Amenaza ofensiva", "attacking_threat"), ("Creación / progresión", "creation_progression"), ("Contribución defensiva", "defensive_contribution"), ("Finalización", "finishing"), ("Disciplina", "discipline")]:
            value = _num(latest.get(key))
            if value is not None:
                dims.append((label, value))
    if dims:
        story += _section("Dimensiones del último partido", "Scores materializados que explican la nota; no son métricas independientes de scouting.", width, styles)
        story.append(_bar_chart(dims, width, 48 * mm, 0, 100))

    story.append(PageBreak())
    story += _section("Producción técnica reciente", "Acciones registradas en los últimos partidos disponibles.", width, styles)
    rows = [["Fecha", "Rival", "Min", "Pases", "Remates", "Goles", "Entradas", "Interc."]]
    for r in sorted(history, key=lambda x: _date(x.get("match_date")), reverse=True)[:10]:
        passes = "-"
        pc, pt = _num(r.get("passes_completed")), _num(r.get("passes_total"))
        if pc is not None and pt is not None:
            passes = f"{int(pc)}/{int(pt)}"
        rows.append([
            _date(r.get("match_date")), r.get("opponent"), _count(r.get("minutes")), passes,
            _count(r.get("shots_total")), _count(r.get("goals")), _count(r.get("tackles_won")), _count(r.get("interceptions")),
        ])
    story.append(_data_table(rows, [25*mm, 45*mm, 13*mm, 24*mm, 17*mm, 14*mm, 18*mm, 18*mm], styles))

    if index_history:
        story += _section("Performance Index", "Evolución de la capa histórica/posicional. No sustituye el Match Rating del partido.", width, styles)
        vals = [v for v in [_num(r.get("performance_score")) for r in index_history] if v is not None]
        labs = [_date(r.get("match_date")) for r in index_history if _num(r.get("performance_score")) is not None]
        story.append(_trend_chart(vals, labs, width, 48 * mm, 0, 100))

    story += _section("Motor experto y trazabilidad", "Estado materializado del sistema jerárquico.", width, styles)
    story.append(_insight_grid([
        ("Rol observado", _roles(gate.get("observed_role")), "Rol utilizado por el motor", TEAL),
        ("Historial mismo rol", _count(gate.get("same_role_history")), "Observaciones comparables", NAVY_2),
        ("Cobertura", _coverage(gate.get("evidence_coverage")), "Evidencia disponible", AMBER),
        ("Estado final", _expert_status(gate.get("final_status")), "No es texto generado por LLM", RED if "Sin recomendación" in _expert_status(gate.get("final_status")) else TEAL),
    ], width, styles))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Las conclusiones del informe son descriptivas. No se infieren causas tácticas, fatiga, riesgo de lesión ni titularidad a partir de estas métricas.", styles["note"]))
    return story


def _match_story(payload: dict[str, Any], styles: dict[str, ParagraphStyle], width: float) -> list[Any]:
    team = _safe((payload.get("team") or {}).get("display_name"), "Equipo")
    match = payload.get("match") or {}
    ratings = list(payload.get("ratings") or [])
    obs = payload.get("observations") or {}
    opponent = _safe(match.get("opponent"), "Rival")
    sf, sa = _num(match.get("score_for")), _num(match.get("score_against"))
    score = f"{int(sf)}-{int(sa)}" if sf is not None and sa is not None else "-"
    venue = "Local" if match.get("venue") == "H" else "Visitante" if match.get("venue") == "A" else "-"
    meta = f"{_date(match.get('match_date'))} | {venue} | Match Rating {payload.get('match_rating_version')}"
    story: list[Any] = [_cover("Informe técnico de partido", f"{team} {score} {opponent}", meta, width, styles), Spacer(1, 5 * mm)]

    rating_vals = [v for v in [_num(r.get("match_rating_10")) for r in ratings] if v is not None]
    conf_vals = [v for v in [_num(r.get("match_rating_confidence")) for r in ratings] if v is not None]
    rating_vals_sorted = sorted(rating_vals)
    conf_vals_sorted = sorted(conf_vals)
    median_rating = rating_vals_sorted[len(rating_vals_sorted)//2] if rating_vals_sorted else None
    median_conf = conf_vals_sorted[len(conf_vals_sorted)//2] if conf_vals_sorted else None
    fallback = sum(1 for r in ratings if "ROLE_UNAVAILABLE" in str(r.get("rating_path") or ""))
    story.append(_kpi_row([
        ("Marcador", score, f"{team} vs {opponent}"),
        ("Rating mediano", _fmt(median_rating, 2, "/10"), "Jugadores utilizados"),
        ("Confianza mediana", _fmt(median_conf, 0, "%"), "Cobertura de evidencia"),
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
    bars = sorted([(_safe(r.get("player")), _num(r.get("match_rating_10"))) for r in ratings if _num(r.get("match_rating_10")) is not None], key=lambda x: x[1], reverse=True)
    story.append(_bar_chart([(n, float(v)) for n, v in bars[:15]], width, 78 * mm, 3, 10))

    story.append(PageBreak())
    story += _section("Ficha de jugadores", "Minutos, perfil, Match Rating, confianza y método de cálculo materializado.", width, styles)
    rows = [["Jugador", "Perfil", "Min", "Rating", "Conf. %", "Método"]]
    ordered = sorted(ratings, key=lambda r: _num(r.get("match_rating_10")) or -999, reverse=True)
    for r in ordered:
        rows.append([
            r.get("player"), _position(r.get("position_group")), _count(r.get("minutes_played")), _fmt(r.get("match_rating_10"), 2),
            _fmt(r.get("match_rating_confidence"), 0), _rating_context(r.get("match_rating_context") or r.get("rating_path")),
        ])
    story.append(_data_table(rows, [34*mm, 29*mm, 13*mm, 18*mm, 18*mm, 55*mm], styles))

    outfield = [r for r in ratings if "OUTFIELD_PERF18" in str(r.get("rating_path") or "")]
    if outfield:
        story += _section("Dimensiones materializadas", "Valores explicativos del Match Rating para jugadores de campo con contexto posicional fiable.", width, styles)
        rows = [["Jugador", "Amenaza", "Creación", "Defensa", "Finalización", "Disciplina"]]
        for r in outfield[:12]:
            rows.append([
                r.get("player"), _fmt(r.get("attacking_threat"), 1), _fmt(r.get("creation_progression"), 1),
                _fmt(r.get("defensive_contribution"), 1), _fmt(r.get("finishing"), 1), _fmt(r.get("discipline"), 1),
            ])
        story.append(_data_table(rows, [42*mm, 24*mm, 24*mm, 24*mm, 27*mm, 24*mm], styles))

    story += _section("Calidad de evidencia", "Limitaciones que deben considerarse antes de interpretar el partido.", width, styles)
    story.append(_insight_grid([
        ("Jugadores utilizados", str(len(ratings)), "Apariciones con minutos", TEAL),
        ("Fallback de rol", str(fallback), "Casos sin rol táctico fiable", AMBER if fallback else GREEN),
        ("Confianza mínima", _fmt(min(conf_vals) if conf_vals else None, 0, "%"), "Valor mínimo del partido", NAVY_2),
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
        story = _team_story(payload, styles, width)
    elif report_type == "player":
        story = _player_story(payload, styles, width)
    else:
        story = _match_story(payload, styles, width)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
