"""Elite technical PDF renderer v4.

Small staff-facing refinement over v3: the Team evolution chart labels the two
highest and two lowest Match Rating medians with date, opponent and value, so the
staff can identify which matches produced the visible peaks without cluttering every
point. All analytics and REPORTS-03 guardrails remain unchanged.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.graphics.shapes import Circle, Drawing, Line, Path, String
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate

from reports import pdf_engine_elite_v2 as base_v2
from reports import pdf_engine_elite_v3 as base


def _short_date(value: Any) -> str:
    text = base_v2._date(value)
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return f"{text[8:10]}/{text[5:7]}"
    return text[:10]


def _team_trend_chart(payload: dict[str, Any], width: float, height: float, y_min: float = 3, y_max: float = 10) -> Drawing:
    history = sorted(
        [row for row in list(payload.get("rating_history") or []) if base_v2._num(row.get("median_match_rating")) is not None],
        key=lambda row: base_v2._date(row.get("match_date")),
    )
    matches = list(payload.get("matches") or [])
    opponent_by_date = {base_v2._date(row.get("match_date")): base_v2._safe(row.get("opponent"), "Rival") for row in matches}

    drawing = Drawing(width, height)
    left, right, bottom, top = 30, 10, 18, 18
    plot_w, plot_h = width - left - right, height - bottom - top

    for i in range(4):
        y = bottom + plot_h * i / 3
        drawing.add(Line(left, y, left + plot_w, y, strokeColor=base_v2.GRID, strokeWidth=0.8))
        value = y_min + (y_max - y_min) * i / 3
        drawing.add(String(2, y - 3, f"{value:.1f}", fontName="Helvetica", fontSize=6, fillColor=base_v2.MUTED))

    if not history:
        return drawing

    values = [float(row.get("median_match_rating")) for row in history]
    n = len(values)
    coords: list[tuple[float, float]] = []
    path = Path()
    for i, value in enumerate(values):
        x = left + plot_w * i / max(n - 1, 1)
        y = bottom + plot_h * (value - y_min) / max(y_max - y_min, 0.001)
        y = max(bottom, min(bottom + plot_h, y))
        coords.append((x, y))
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
        drawing.add(Circle(x, y, 2.6, fillColor=base_v2.TEAL, strokeColor=base_v2.WHITE, strokeWidth=0.8))

    path.strokeColor = base_v2.TEAL
    path.strokeWidth = 2.2
    path.fillColor = None
    drawing.add(path)

    # Preserve sparse date anchors on the x-axis.
    for idx in sorted(set([0, n // 2, n - 1])):
        x, _ = coords[idx]
        drawing.add(String(x, 2, base_v2._date(history[idx].get("match_date"))[:10], textAnchor="middle", fontName="Helvetica", fontSize=5.8, fillColor=base_v2.MUTED))

    # Two highest + two lowest observations, deduplicated.
    high_idx = sorted(range(n), key=lambda i: values[i], reverse=True)[:2]
    low_idx = sorted(range(n), key=lambda i: values[i])[:2]
    selected = []
    for idx in high_idx + low_idx:
        if idx not in selected:
            selected.append(idx)

    high_set = set(high_idx)
    for idx in selected:
        x, y = coords[idx]
        row = history[idx]
        date_key = base_v2._date(row.get("match_date"))
        opponent = opponent_by_date.get(date_key, "Rival")
        label = f"{_short_date(date_key)} · {opponent} · {values[idx]:.2f}"

        is_high = idx in high_set
        label_y = y + 9 if is_high else y - 12
        label_y = max(5, min(height - 7, label_y))
        on_right = x > left + plot_w * 0.58
        text_x = x - 5 if on_right else x + 5
        anchor = "end" if on_right else "start"

        drawing.add(Line(x, y + (3 if is_high else -3), x, label_y + (-2 if is_high else 7), strokeColor=base_v2.MUTED, strokeWidth=0.45))
        drawing.add(String(text_x, label_y, label, textAnchor=anchor, fontName="Helvetica-Bold", fontSize=5.2, fillColor=base_v2.TEXT))

    return drawing


def _team_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    story = base._team_story(payload, styles, width)

    # In the Team story, the first Drawing is the temporal Match Rating chart.
    replacement = _team_trend_chart(payload, width, 52 * mm, 3, 10)
    for idx, item in enumerate(story):
        if isinstance(item, Drawing):
            story[idx] = replacement
            break
    return story


def _player_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
    return base._player_story(payload, styles, width)


def _match_story(payload: dict[str, Any], styles, width: float) -> list[Any]:
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
