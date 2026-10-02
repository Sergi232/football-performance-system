"""Elite technical PDF renderer v3.

Final staff-facing refinement over v2:
- adds deterministic review prompts instead of more raw tables;
- normalizes goalkeeper role presentation;
- preserves all REPORTS-03 guardrails and analytics contracts;
- keeps Team=3 pages, Player=2 pages, Match=2 pages as design targets.

No critical metric is recalculated here and no tactical cause is asserted.
"""
from __future__ import annotations

from copy import deepcopy
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from reports import pdf_engine_elite_v2 as base


def _row(profile: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    for item in profile:
        if str(item.get("key")) == key:
            return item
    return None


def _delta_text(item: dict[str, Any] | None, field: str) -> str:
    if not item:
        return "-"
    value = base._num(item.get(field))
    if value is None:
        return "-"
    sign = "+" if value > 0 else ""
    if str(item.get("key")) == "pass_completion_pct":
        return f"{sign}{value:.1f} pp"
    decimals = int(item.get("decimals") or 1)
    return f"{sign}{value:.{decimals}f}"


def _value_text(item: dict[str, Any] | None, field: str) -> str:
    if not item:
        return "-"
    value = base._num(item.get(field))
    if value is None:
        return "-"
    decimals = int(item.get("decimals") or 1)
    suffix = str(item.get("suffix") or "")
    return f"{value:.{decimals}f}{suffix}"


def _review_box(title: str, lines: list[str], width: float, styles) -> Table:
    body = [Paragraph(escape(title), styles["body_bold"])]
    for line in lines:
        body.append(Spacer(1, 1.2 * mm))
        body.append(Paragraph(f"- {escape(line)}", styles["body"]))
    body.append(Spacer(1, 0.8 * mm))
    body.append(Paragraph(
        "Estas señales sirven para seleccionar clips y preguntas de revisión; no demuestran por sí solas una causa táctica.",
        styles["note"],
    ))
    table = Table([[body]], colWidths=[width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2F8F6")),
        ("BOX", (0, 0), (-1, -1), 0.7, base.TEAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def _team_review_lines(payload: dict[str, Any]) -> list[str]:
    profile = list(payload.get("technical_profile") or [])
    pase = _row(profile, "pass_completion_pct")
    shots = _row(profile, "shots_total")
    goals = _row(profile, "goals")
    tackles = _row(profile, "tackles_won")
    inter = _row(profile, "interceptions")
    losses = _row(profile, "turnovers")
    disposs = _row(profile, "dispossessed")
    return [
        f"Con balón: precisión {_value_text(pase, 'last5')} vs {_value_text(pase, 'previous5')} ({_delta_text(pase, 'delta_5v5')}). Revisar secuencias de pase del bloque reciente.",
        f"Finalización: remates {_value_text(shots, 'last5')} vs {_value_text(shots, 'previous5')} ({_delta_text(shots, 'delta_5v5')}); goles {_value_text(goals, 'last5')} vs {_value_text(goals, 'previous5')} ({_delta_text(goals, 'delta_5v5')}).",
        f"Sin balón y pérdidas: entradas {_delta_text(tackles, 'delta_5v5')}, intercepciones {_delta_text(inter, 'delta_5v5')}, pérdidas {_delta_text(losses, 'delta_5v5')} y desposesiones {_delta_text(disposs, 'delta_5v5')} frente al bloque anterior.",
    ]


def _player_review_lines(payload: dict[str, Any]) -> list[str]:
    profile = list(payload.get("technical_profile") or [])
    ratings = sorted(list(payload.get("match_ratings") or []), key=lambda r: str(r.get("match_date") or ""), reverse=True)
    latest = ratings[0] if ratings else {}
    group = str(latest.get("position_group") or (payload.get("player_snapshot") or {}).get("latest_position_group") or "")
    if group == "GK":
        pase = _row(profile, "pass_completion_pct")
        completados = _row(profile, "passes_completed_per90")
        return [
            f"Distribución reciente: precisión {_value_text(pase, 'last5')} vs {_value_text(pase, 'previous5')} ({_delta_text(pase, 'delta_5v5')}).",
            f"Pases completados / 90: {_value_text(completados, 'last5')} vs {_value_text(completados, 'previous5')} ({_delta_text(completados, 'delta_5v5')}).",
            "El conjunto de datos no distingue longitud, riesgo ni objetivo del pase; usar vídeo antes de interpretar la calidad de la distribución.",
        ]
    selected = base._player_metric_selection(profile, group)
    lines = []
    for item in selected[:3]:
        lines.append(
            f"{item.get('label')}: {_value_text(item, 'last5')} vs {_value_text(item, 'previous5')} ({_delta_text(item, 'delta_5v5')})."
        )
    return lines or ["No hay muestra técnica suficiente para añadir una prioridad específica de revisión."]


def _normalize_player_payload(payload: dict[str, Any]) -> dict[str, Any]:
    safe = deepcopy(payload)
    ratings = sorted(list(safe.get("match_ratings") or []), key=lambda r: str(r.get("match_date") or ""), reverse=True)
    latest = ratings[0] if ratings else {}
    group = str(latest.get("position_group") or (safe.get("player_snapshot") or {}).get("latest_position_group") or "")
    if group == "GK":
        gate = dict(safe.get("latest_role_fit_gate") or {})
        if gate:
            gate["observed_role"] = "Portero"
            safe["latest_role_fit_gate"] = gate
    return safe


def _insert_before_nth_break(story: list[Any], nth: int, elements: list[Any]) -> list[Any]:
    indices = [i for i, item in enumerate(story) if isinstance(item, PageBreak)]
    if len(indices) < nth:
        return story + elements
    idx = indices[nth - 1]
    return story[:idx] + elements + story[idx:]


def _team_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    story = base._team_story(payload, styles, width)
    box = [Spacer(1, 3 * mm), _review_box("Claves para la revisión técnica", _team_review_lines(payload), width, styles)]
    return _insert_before_nth_break(story, 2, box)


def _player_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    safe = _normalize_player_payload(payload)
    story = base._player_story(safe, styles, width)
    box = [Spacer(1, 3 * mm), _review_box("Claves para revisar al jugador", _player_review_lines(safe), width, styles)]
    return _insert_before_nth_break(story, 1, box)


def _match_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    # V2 already uses the first page as the deterministic post-match summary and
    # the second page for player review. Adding another narrative block here would
    # duplicate the technical footprint and risk a third page, so the structure is frozen.
    return base._match_story(payload, styles, width)


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
    styles = base._styles()
    width = A4[0] - 32 * mm

    if report_type == "team":
        story = _team_story(payload, styles, width)
    elif report_type == "player":
        story = _player_story(payload, styles, width)
    else:
        story = _match_story(payload, styles, width)

    doc.build(story, onFirstPage=base._footer, onLaterPages=base._footer)
    return buffer.getvalue()
