"""Shared ReportLab renderer for TEAM / PLAYER / MATCH static PDF exports."""
from __future__ import annotations

from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _safe(value: Any) -> str:
    if value is None:
        return "—"
    return str(value)


def _p(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_safe(value)), style)


def _table(rows: list[list[Any]], widths: list[float], styles: dict[str, ParagraphStyle]) -> Table:
    cooked: list[list[Any]] = []
    for ridx, row in enumerate(rows):
        style = styles["table_header"] if ridx == 0 else styles["table_cell"]
        cooked.append([_p(cell, style) for cell in row])
    table = Table(cooked, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECEFF1")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B0BEC5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("FPS_Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=19, leading=22, spaceAfter=8),
        "subtitle": ParagraphStyle("FPS_Subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#455A64"), spaceAfter=10),
        "h2": ParagraphStyle("FPS_H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, spaceBefore=8, spaceAfter=5),
        "body": ParagraphStyle("FPS_Body", parent=base["BodyText"], fontName="Helvetica", fontSize=9, leading=12, spaceAfter=5),
        "note": ParagraphStyle("FPS_Note", parent=base["BodyText"], fontName="Helvetica-Oblique", fontSize=8, leading=10, textColor=colors.HexColor("#455A64"), spaceAfter=5),
        "table_header": ParagraphStyle("FPS_TableHeader", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=9, alignment=TA_CENTER),
        "table_cell": ParagraphStyle("FPS_TableCell", parent=base["Normal"], fontName="Helvetica", fontSize=7, leading=9),
    }


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#607D8B"))
    canvas.drawString(18 * mm, 10 * mm, "Football Performance System · exportació estructurada")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Pàgina {doc.page}")
    canvas.restoreState()


def _header(story: list[Any], payload: dict[str, Any], title: str, styles: dict[str, ParagraphStyle]) -> None:
    team = payload.get("team") or {}
    story.append(Paragraph(escape(title), styles["title"]))
    story.append(
        Paragraph(
            escape(
                f"{_safe(team.get('display_name'))} · motor {_safe(payload.get('engine_version'))} · "
                f"features {_safe(payload.get('feature_version'))}"
            ),
            styles["subtitle"],
        )
    )


def _guardrail_note(story: list[Any], styles: dict[str, ParagraphStyle]) -> None:
    story.append(
        Paragraph(
            "Aquest informe és una exportació estàtica de dades i resultats ja calculats. "
            "No crea mètriques, rankings, scores ni recomanacions tàctiques noves.",
            styles["note"],
        )
    )


def _team_story(payload: dict[str, Any], styles: dict[str, ParagraphStyle], width: float) -> list[Any]:
    story: list[Any] = []
    _header(story, payload, "Informe d'equip", styles)
    overview = payload.get("overview") or {}
    story.append(Paragraph("Resum", styles["h2"]))
    summary = [
        ["Partits", "Jugadors", "Minuts-jugador", "Gols", "Assistències"],
        [overview.get("matches"), overview.get("players"), overview.get("player_minutes"), overview.get("goals"), overview.get("assists")],
    ]
    story.append(_table(summary, [width / 5] * 5, styles))
    _guardrail_note(story, styles)

    matches = payload.get("matches") or []
    story.append(Paragraph("Partits", styles["h2"]))
    rows = [["Data", "L/V", "Rival", "Marcador", "Formació"]]
    for row in matches:
        score = "—" if row.get("score_for") is None or row.get("score_against") is None else f"{row.get('score_for')}-{row.get('score_against')}"
        rows.append([row.get("match_date"), row.get("venue"), row.get("opponent"), score, row.get("starting_formation")])
    story.append(_table(rows, [32 * mm, 12 * mm, 58 * mm, 24 * mm, 34 * mm], styles))

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
    _header(story, payload, f"Informe de jugador · {_safe(summary.get('player'))}", styles)

    rows = [
        ["Aparicions", "Titularitats", "Minuts", "Gols", "Assistències", "Rols observats"],
        [summary.get("appearances"), summary.get("starts"), summary.get("minutes"), summary.get("goals"), summary.get("assists"), summary.get("observed_roles")],
    ]
    story.append(_table(rows, [22 * mm, 22 * mm, 22 * mm, 18 * mm, 20 * mm, 62 * mm], styles))

    story.append(Paragraph("Evidència de rol i gate final", styles["h2"]))
    gate = payload.get("latest_role_fit_gate")
    if gate:
        gate_rows = [
            ["Rol", "Historial mateix rol", "Senyals avaluables", "Cobertura", "Estat final"],
            [gate.get("observed_role"), gate.get("same_role_history"), gate.get("evaluable_signals"), gate.get("evidence_coverage"), gate.get("final_status")],
        ]
        story.append(_table(gate_rows, [28 * mm, 32 * mm, 28 * mm, 24 * mm, 55 * mm], styles))
    else:
        story.append(Paragraph("No hi ha estat N12000/N13000 disponible per al darrer partit jugat.", styles["body"]))
    _guardrail_note(story, styles)

    feature_history = payload.get("feature_history") or {}
    if feature_history:
        story.append(Paragraph("Últimes observacions de features seleccionades", styles["h2"]))
        feature_rows = [["Feature", "Data", "Rival", "Rol", "Valor"]]
        for feature_name, observations in feature_history.items():
            for obs in observations:
                feature_rows.append([feature_name, obs.get("match_date"), obs.get("opponent"), obs.get("primary_role"), obs.get("feature_value")])
        story.append(_table(feature_rows, [42 * mm, 30 * mm, 42 * mm, 28 * mm, 24 * mm], styles))

    story.append(PageBreak())
    story.append(Paragraph("Historial recent de partits", styles["h2"]))
    match_rows = [["Data", "Rival", "Min.", "Rol", "Pases", "Comp.", "Remats", "Gols", "Tackles", "Interc."]]
    for row in payload.get("match_history") or []:
        match_rows.append([
            row.get("match_date"), row.get("opponent"), row.get("minutes"), row.get("primary_role"),
            row.get("passes_total"), row.get("passes_completed"), row.get("shots_total"), row.get("goals"),
            row.get("tackles_total"), row.get("interceptions"),
        ])
    story.append(_table(match_rows, [27 * mm, 36 * mm, 13 * mm, 24 * mm, 13 * mm, 13 * mm, 13 * mm, 11 * mm, 13 * mm, 13 * mm], styles))
    return story


def _match_story(payload: dict[str, Any], styles: dict[str, ParagraphStyle], width: float) -> list[Any]:
    story: list[Any] = []
    match = payload.get("match") or {}
    title = f"Informe de partit · {_safe(match.get('opponent'))}"
    _header(story, payload, title, styles)

    score = "—" if match.get("score_for") is None or match.get("score_against") is None else f"{match.get('score_for')}-{match.get('score_against')}"
    info = [
        ["Data", "L/V", "Rival", "Marcador", "Formació"],
        [match.get("match_date"), match.get("venue"), match.get("opponent"), score, match.get("starting_formation")],
    ]
    story.append(_table(info, [32 * mm, 15 * mm, 55 * mm, 25 * mm, 40 * mm], styles))
    _guardrail_note(story, styles)

    story.append(Paragraph("Jugadors i estadístiques observades", styles["h2"]))
    rows = [["Jugador", "#", "Tit.", "Min.", "Rol", "Pases", "Comp.", "Assist.", "Remats", "Gols", "Tackles", "Interc."]]
    for row in payload.get("lineup") or []:
        rows.append([
            row.get("player"), row.get("shirt_number"), row.get("started"), row.get("minutes"), row.get("primary_role"),
            row.get("passes_total"), row.get("passes_completed"), row.get("assists"), row.get("shots_total"), row.get("goals"),
            row.get("tackles_total"), row.get("interceptions"),
        ])
    story.append(_table(rows, [36 * mm, 9 * mm, 11 * mm, 12 * mm, 24 * mm, 12 * mm, 12 * mm, 12 * mm, 12 * mm, 10 * mm, 12 * mm, 12 * mm], styles))
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
        topMargin=18 * mm,
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
