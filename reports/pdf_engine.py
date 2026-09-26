"""Shared ReportLab renderer for TEAM / PLAYER / MATCH static PDF exports."""
from __future__ import annotations

from html import escape
from io import BytesIO
from statistics import median
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#102A43")
TEAL = colors.HexColor("#1F7A6D")
TEAL_LIGHT = colors.HexColor("#E7F3F0")
LIGHT = colors.HexColor("#F4F7F9")
BORDER = colors.HexColor("#DDE5EB")
TEXT = colors.HexColor("#263746")
MUTED = colors.HexColor("#607D8B")
WHITE = colors.white

POSITION_LABELS = {
    "CB": "Central",
    "FB_WB": "Lateral / Carriler",
    "DM_CM": "Migcentre / Interior",
    "AM_W": "Mitjapunta / Extrem",
    "ST": "Davanter",
    "GK": "Porter",
    "OTHER_OUTFIELD": "Rol no observable",
}

EVIDENCE_LABELS = {
    "DIRECT_SIGNED": "Evidència directa",
    "CONTRIBUTION_FALLBACK": "Contribució observada de suport",
    "MISSING": "Sense evidència",
}


def _safe(value: Any) -> str:
    return "—" if value is None else str(value)


def _fmt1(value: Any) -> str:
    try:
        if value is None:
            return "—"
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return _safe(value)


def _fmt0(value: Any) -> str:
    try:
        if value is None:
            return "—"
        return f"{float(value):.0f}"
    except (TypeError, ValueError):
        return _safe(value)


def _position(value: Any) -> str:
    if value is None:
        return "—"
    return POSITION_LABELS.get(str(value), str(value))


def _p(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_safe(value)), style)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "kicker": ParagraphStyle(
            "FPS_Kicker", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.5,
            leading=9, textColor=TEAL, spaceAfter=3, tracking=1.2,
        ),
        "title": ParagraphStyle(
            "FPS_Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=21,
            leading=24, textColor=NAVY, alignment=TA_LEFT, spaceAfter=3,
        ),
        "subtitle": ParagraphStyle(
            "FPS_Subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=8.5,
            leading=11, textColor=MUTED, spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "FPS_H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12,
            leading=15, textColor=NAVY, spaceBefore=10, spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "FPS_H3", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=9.5,
            leading=12, textColor=TEXT, spaceBefore=6, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "FPS_Body", parent=base["BodyText"], fontName="Helvetica", fontSize=8.5,
            leading=11.5, textColor=TEXT, spaceAfter=4,
        ),
        "note": ParagraphStyle(
            "FPS_Note", parent=base["BodyText"], fontName="Helvetica-Oblique", fontSize=7.5,
            leading=9.5, textColor=MUTED, spaceBefore=4, spaceAfter=5,
        ),
        "table_header": ParagraphStyle(
            "FPS_TableHeader", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=6.8,
            leading=8.5, textColor=WHITE, alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "FPS_TableCell", parent=base["Normal"], fontName="Helvetica", fontSize=6.8,
            leading=8.5, textColor=TEXT,
        ),
        "kpi_label": ParagraphStyle(
            "FPS_KpiLabel", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=6.5,
            leading=8, textColor=MUTED, alignment=TA_CENTER,
        ),
        "kpi_value": ParagraphStyle(
            "FPS_KpiValue", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=15,
            leading=17, textColor=NAVY, alignment=TA_CENTER,
        ),
        "kpi_sub": ParagraphStyle(
            "FPS_KpiSub", parent=base["Normal"], fontName="Helvetica", fontSize=6,
            leading=7.5, textColor=MUTED, alignment=TA_CENTER,
        ),
    }


def _table(rows: list[list[Any]], widths: list[float], styles: dict[str, ParagraphStyle]) -> Table:
    cooked: list[list[Any]] = []
    for ridx, row in enumerate(rows):
        style = styles["table_header"] if ridx == 0 else styles["table_cell"]
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
    for ridx in range(1, len(cooked)):
        if ridx % 2 == 0:
            commands.append(("BACKGROUND", (0, ridx), (-1, ridx), LIGHT))
    table.setStyle(TableStyle(commands))
    return table


def _kpi_strip(items: list[tuple[str, Any, str]], width: float, styles: dict[str, ParagraphStyle]) -> Table:
    count = max(len(items), 1)
    gap = 3 * mm
    card_width = (width - gap * (count - 1)) / count
    cards: list[Any] = []
    widths: list[float] = []

    for idx, (label, value, sub) in enumerate(items):
        card = Table(
            [
                [Paragraph(escape(label), styles["kpi_label"])],
                [Paragraph(escape(_safe(value)), styles["kpi_value"])],
                [Paragraph(escape(sub), styles["kpi_sub"])],
            ],
            colWidths=[card_width],
        )
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        cards.append(card)
        widths.append(card_width)
        if idx < count - 1:
            cards.append("")
            widths.append(gap)

    outer = Table([cards], colWidths=widths, hAlign="LEFT")
    outer.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return outer


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "Football Performance System - exportació estructurada")
    canvas.drawRightString(A4[0] - 18 * mm, 9 * mm, f"Pàgina {doc.page}")
    canvas.restoreState()


def _header(story: list[Any], payload: dict[str, Any], title: str, styles: dict[str, ParagraphStyle]) -> None:
    team = payload.get("team") or {}
    story.append(Paragraph("FOOTBALL PERFORMANCE SYSTEM", styles["kicker"]))
    story.append(Paragraph(escape(title), styles["title"]))
    meta = (
        f"{_safe(team.get('display_name'))} · Match Rating {_safe(payload.get('match_rating_version'))} · "
        f"Analytics {_safe(payload.get('engine_version'))}"
    )
    story.append(Paragraph(escape(meta), styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceBefore=0, spaceAfter=8))


def _guardrail_note(story: list[Any], styles: dict[str, ParagraphStyle]) -> None:
    story.append(Paragraph(
        "Nota metodològica: aquest informe mostra dades i resultats ja materialitzats. No recalcula ratings, no crea llindars nous i no emet recomanacions tàctiques no validades.",
        styles["note"],
    ))


def _team_story(payload: dict[str, Any], styles: dict[str, ParagraphStyle], width: float) -> list[Any]:
    story: list[Any] = []
    _header(story, payload, "Informe d'equip", styles)

    overview = payload.get("overview") or {}
    snapshot = payload.get("rating_snapshot") or []
    latest_ratings = [row.get("latest_match_rating") for row in snapshot if row.get("latest_match_rating") is not None]
    latest_conf = [row.get("latest_confidence") for row in snapshot if row.get("latest_confidence") is not None]

    story.append(_kpi_strip([
        ("PARTITS", overview.get("matches"), "Historial disponible"),
        ("JUGADORS", overview.get("players"), "Plantilla registrada"),
        ("GOLS", overview.get("goals"), "Dades observades"),
        ("RATING MEDIÀ", "—" if not latest_ratings else f"{median(latest_ratings):.1f}/10", "Últim rating per jugador"),
        ("CONFIANÇA", "—" if not latest_conf else f"{median(latest_conf):.0f}%", "Mediana descriptiva"),
    ], width, styles))

    story.append(Paragraph("Estat actual de la plantilla", styles["h2"]))
    if snapshot:
        rows = [["Jugador", "Perfil", "Últim rating", "Conf.", "Mitj. L5", "Delta 5v5"]]
        for row in snapshot:
            rows.append([
                row.get("player"),
                _position(row.get("latest_position_group")),
                _fmt1(row.get("latest_match_rating")),
                _fmt0(row.get("latest_confidence")),
                _fmt1(row.get("avg_last5")),
                _fmt1(row.get("trend_delta_5v5")),
            ])
        story.append(_table(rows, [43 * mm, 33 * mm, 22 * mm, 18 * mm, 22 * mm, 22 * mm], styles))
    else:
        story.append(Paragraph("No hi ha Match Ratings materialitzats per a la plantilla.", styles["body"]))

    story.append(Paragraph("Partits", styles["h2"]))
    rows = [["Data", "L/V", "Rival", "Marcador", "Formació"]]
    for row in (payload.get("matches") or [])[:12]:
        score = "—" if row.get("score_for") is None or row.get("score_against") is None else f"{row.get('score_for')}-{row.get('score_against')}"
        rows.append([row.get("match_date"), row.get("venue"), row.get("opponent"), score, row.get("starting_formation")])
    story.append(_table(rows, [32 * mm, 12 * mm, 58 * mm, 24 * mm, 34 * mm], styles))
    _guardrail_note(story, styles)

    story.append(PageBreak())
    story.append(Paragraph("Plantilla", styles["h2"]))
    squad_rows = [["Jugador", "Apar.", "Tit.", "Minuts", "Gols", "Assist.", "Rols"]]
    for row in payload.get("squad") or []:
        squad_rows.append([
            row.get("player"), row.get("appearances"), row.get("starts"), row.get("minutes"),
            row.get("goals"), row.get("assists"), row.get("observed_roles"),
        ])
    story.append(_table(squad_rows, [45 * mm, 14 * mm, 14 * mm, 18 * mm, 14 * mm, 16 * mm, 45 * mm], styles))
    return story


def _player_story(payload: dict[str, Any], styles: dict[str, ParagraphStyle], width: float) -> list[Any]:
    story: list[Any] = []
    summary = payload.get("summary") or {}
    ratings = payload.get("match_ratings") or []
    latest_rating = ratings[0] if ratings else {}
    perf = payload.get("performance_index") or {}

    _header(story, payload, f"Informe de jugador · {_safe(summary.get('player'))}", styles)

    story.append(_kpi_strip([
        ("MATCH RATING", "—" if not latest_rating else f"{_fmt1(latest_rating.get('match_rating_10'))}/10", "Últim partit"),
        ("CONFIANÇA", "—" if not latest_rating else f"{_fmt0(latest_rating.get('match_rating_confidence'))}%", "Evidència del partit"),
        ("PERFORMANCE INDEX", "—" if not perf else f"{_fmt1(perf.get('performance_score'))}/100", "Històric/posicional"),
        ("APARICIONS", summary.get("appearances"), "Temporada"),
        ("MINUTS", summary.get("minutes"), "Acumulats"),
    ], width, styles))

    story.append(Paragraph("Perfil i producció", styles["h2"]))
    profile_rows = [["Titularitats", "Gols", "Assistències", "Rols observats"], [
        summary.get("starts"), summary.get("goals"), summary.get("assists"), summary.get("observed_roles"),
    ]]
    story.append(_table(profile_rows, [28 * mm, 20 * mm, 24 * mm, 94 * mm], styles))

    story.append(Paragraph("Performance Index", styles["h2"]))
    if perf:
        index_rows = [["Perfil", "Índex", "Conf.", "Amenaça", "Creació", "Defensa", "Finalització", "Disciplina"]]
        index_rows.append([
            _position(perf.get("position_group")),
            _fmt1(perf.get("performance_score")),
            _fmt0(perf.get("score_evidence_confidence")),
            _fmt1(perf.get("attacking_threat")),
            _fmt1(perf.get("creation_progression")),
            _fmt1(perf.get("defensive_contribution")),
            _fmt1(perf.get("finishing")),
            _fmt1(perf.get("discipline")),
        ])
        story.append(_table(index_rows, [30 * mm, 18 * mm, 16 * mm, 20 * mm, 20 * mm, 20 * mm, 22 * mm, 20 * mm], styles))

        evidence_rows = [["Dimensió", "Procedència"]]
        for key, label in [
            ("attacking_threat", "Amenaça ofensiva"),
            ("creation_progression", "Creació / progressió"),
            ("defensive_contribution", "Contribució defensiva"),
            ("finishing", "Finalització"),
            ("discipline", "Disciplina"),
        ]:
            evidence_rows.append([label, EVIDENCE_LABELS.get(str(perf.get(f"{key}_evidence")), _safe(perf.get(f"{key}_evidence")))])
        story.append(Spacer(1, 4))
        story.append(_table(evidence_rows, [66 * mm, 100 * mm], styles))
    else:
        story.append(Paragraph("No hi ha Performance Index posicional elegible per aquest jugador.", styles["body"]))

    story.append(Paragraph("Match Rating recent", styles["h2"]))
    if ratings:
        rating_rows = [["Data", "Rival", "Min.", "Rol", "Rating", "Conf."]]
        for row in ratings[:10]:
            rating_rows.append([
                row.get("match_date"), row.get("opponent"), row.get("minutes_played"), row.get("primary_role"),
                _fmt1(row.get("match_rating_10")), _fmt0(row.get("match_rating_confidence")),
            ])
        story.append(_table(rating_rows, [30 * mm, 45 * mm, 15 * mm, 36 * mm, 20 * mm, 20 * mm], styles))
    else:
        story.append(Paragraph("No hi ha Match Rating materialitzat.", styles["body"]))

    story.append(Paragraph("Evidència de rol i motor expert", styles["h2"]))
    gate = payload.get("latest_role_fit_gate")
    if gate:
        gate_rows = [["Rol", "Historial mateix rol", "Senyals", "Cobertura", "Estat final"], [
            gate.get("observed_role"), gate.get("same_role_history"), gate.get("evaluable_signals"),
            gate.get("evidence_coverage"), gate.get("final_status"),
        ]]
        story.append(_table(gate_rows, [28 * mm, 32 * mm, 22 * mm, 24 * mm, 60 * mm], styles))
    else:
        story.append(Paragraph("No hi ha estat N12000/N13000 disponible per al darrer partit jugat.", styles["body"]))
    _guardrail_note(story, styles)

    story.append(PageBreak())
    story.append(Paragraph("Historial recent de partits", styles["h2"]))
    match_rows = [["Data", "Rival", "Min.", "Rol", "Passes", "Comp.", "Remats", "Gols", "Entrades", "Interc."]]
    for row in payload.get("match_history") or []:
        match_rows.append([
            row.get("match_date"), row.get("opponent"), row.get("minutes"), row.get("primary_role"),
            row.get("passes_total"), row.get("passes_completed"), row.get("shots_total"), row.get("goals"),
            row.get("tackles_total"), row.get("interceptions"),
        ])
    story.append(_table(match_rows, [27 * mm, 36 * mm, 13 * mm, 24 * mm, 13 * mm, 13 * mm, 13 * mm, 11 * mm, 13 * mm, 13 * mm], styles))
    return story


def _leader_text(item: dict[str, Any] | None) -> str:
    if not item:
        return "—"
    players = item.get("players") or []
    value = item.get("value")
    if not players:
        return "—"
    suffix = "" if value is None else f" · {_fmt1(value)}"
    return ", ".join(str(p) for p in players) + suffix


def _match_story(payload: dict[str, Any], styles: dict[str, ParagraphStyle], width: float) -> list[Any]:
    story: list[Any] = []
    match = payload.get("match") or {}
    lineup = payload.get("lineup") or []
    observations = payload.get("observations") or {}

    _header(story, payload, f"Informe de partit · {_safe(match.get('opponent'))}", styles)

    score = "—" if match.get("score_for") is None or match.get("score_against") is None else f"{match.get('score_for')}-{match.get('score_against')}"
    rating_values = [row.get("match_rating_10") for row in lineup if row.get("match_rating_10") is not None]
    confidence_values = [row.get("match_rating_confidence") for row in lineup if row.get("match_rating_confidence") is not None]

    story.append(_kpi_strip([
        ("RESULTAT", score, f"{_safe(match.get('venue'))} · {_safe(match.get('match_date'))}"),
        ("FORMACIÓ", match.get("starting_formation"), "Sistema inicial"),
        ("JUGADORS", len(lineup), "Participants amb registre"),
        ("RATING MEDIÀ", "—" if not rating_values else f"{median(rating_values):.1f}/10", "Mediana player-match"),
        ("CONFIANÇA", "—" if not confidence_values else f"{median(confidence_values):.0f}%", "Mediana d'evidència"),
    ], width, styles))

    story.append(Paragraph("Observacions postpartit", styles["h2"]))
    goal_scorers = observations.get("goal_scorers") or []
    assist_providers = observations.get("assist_providers") or []
    leaders = observations.get("leaders") or {}

    observations_rows = [["Àrea", "Observació"]]
    observations_rows.append([
        "Gols",
        ", ".join(f"{item.get('player')} ({item.get('goals')})" for item in goal_scorers) if goal_scorers else "Sense golejadors registrats",
    ])
    observations_rows.append([
        "Assistències",
        ", ".join(f"{item.get('player')} ({item.get('assists')})" for item in assist_providers) if assist_providers else "Sense assistències registrades",
    ])
    observations_rows.extend([
        ["Més rematades", _leader_text(leaders.get("shots_total"))],
        ["Més passades completades", _leader_text(leaders.get("passes_completed"))],
        ["Més entrades guanyades", _leader_text(leaders.get("tackles_won"))],
        ["Més intercepcions", _leader_text(leaders.get("interceptions"))],
    ])
    story.append(_table(observations_rows, [52 * mm, 114 * mm], styles))

    story.append(Paragraph("Jugadors · Match Rating i estadístiques", styles["h2"]))
    rows = [["Jugador", "Tit.", "Min.", "Rol", "Rating", "Conf.", "Passes", "Comp.", "Remats", "Gols", "Entrades", "Interc."]]
    for row in lineup:
        rows.append([
            row.get("player"), row.get("started"), row.get("minutes"), row.get("primary_role"),
            _fmt1(row.get("match_rating_10")), _fmt0(row.get("match_rating_confidence")),
            row.get("passes_total"), row.get("passes_completed"), row.get("shots_total"), row.get("goals"),
            row.get("tackles_total"), row.get("interceptions"),
        ])
    story.append(_table(rows, [33 * mm, 10 * mm, 11 * mm, 23 * mm, 14 * mm, 14 * mm, 11 * mm, 11 * mm, 11 * mm, 9 * mm, 11 * mm, 11 * mm], styles))
    _guardrail_note(story, styles)
    return story


def render_pdf_bytes(payload: dict[str, Any]) -> bytes:
    report_type = payload.get("report_type")
    if report_type not in {"team", "player", "match"}:
        raise ValueError(f"Unsupported report_type: {report_type}")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"Football Performance System - {report_type}",
        author="Football Performance System",
    )
    styles = _styles()

    if report_type == "team":
        story = _team_story(payload, styles, doc.width)
    elif report_type == "player":
        story = _player_story(payload, styles, doc.width)
    else:
        story = _match_story(payload, styles, doc.width)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
