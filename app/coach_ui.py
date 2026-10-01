"""Presentation and descriptive insight helpers for the coaching dashboard.

This module never recalculates critical ratings. It only renders already materialized
analytics and simple descriptive summaries (recent averages, deltas and ordering).
"""
from __future__ import annotations

import html
from typing import Iterable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ACCENT = "#13A37F"
NAVY = "#0B1F33"
TEXT = "#172B3A"
MUTED = "#6B7C8F"
GRID = "#E7EDF2"
POSITIVE = "#198754"
NEGATIVE = "#C84630"
AMBER = "#B7791F"


def safe_number(value: object, digits: int = 1, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{digits}f}{suffix}"


def safe_int(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{int(value):,}".replace(",", ".")


def safe_text(value: object, fallback: str = "—") -> str:
    if value is None or pd.isna(value):
        return fallback
    text = str(value).strip()
    return text if text else fallback


def result_code(score_for: object, score_against: object) -> tuple[str, str]:
    if score_for is None or score_against is None or pd.isna(score_for) or pd.isna(score_against):
        return "—", "neutral"
    sf, sa = int(score_for), int(score_against)
    if sf > sa:
        return f"G {sf}-{sa}", "positive"
    if sf < sa:
        return f"P {sf}-{sa}", "negative"
    return f"E {sf}-{sa}", "neutral"


def recent_record(matches: pd.DataFrame, n: int = 5) -> str:
    if matches.empty:
        return "—"
    recent = matches.copy().head(n)
    labels: list[str] = []
    for row in recent.itertuples(index=False):
        if pd.isna(row.score_for) or pd.isna(row.score_against):
            continue
        labels.append("G" if row.score_for > row.score_against else "P" if row.score_for < row.score_against else "E")
    return " · ".join(labels) if labels else "—"


def page_header(kicker: str, title: str, subtitle: str, badge: str | None = None) -> None:
    badge_html = "" if not badge else f"<span class='coach-badge'>{html.escape(badge)}</span>"
    st.markdown(
        f"""
        <div class="coach-page-header">
          <div>
            <div class="coach-kicker">{html.escape(kicker)}</div>
            <div class="coach-title">{html.escape(title)}</div>
            <div class="coach-subtitle">{html.escape(subtitle)}</div>
          </div>
          {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, sub: str = "", delta: str | None = None, tone: str = "neutral") -> None:
    delta_html = "" if not delta else f"<div class='coach-delta coach-{tone}'>{html.escape(delta)}</div>"
    st.markdown(
        f"""
        <div class="coach-metric-card">
          <div class="coach-metric-label">{html.escape(label)}</div>
          <div class="coach-metric-value">{html.escape(value)}</div>
          {delta_html}
          <div class="coach-metric-sub">{html.escape(sub)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight_card(title: str, body: str, meta: str = "", tone: str = "neutral") -> None:
    st.markdown(
        f"""
        <div class="coach-insight coach-insight-{tone}">
          <div class="coach-insight-title">{html.escape(title)}</div>
          <div class="coach-insight-body">{html.escape(body)}</div>
          <div class="coach-insight-meta">{html.escape(meta)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def scoreboard_card(team: str, opponent: str, score_for: object, score_against: object, date_text: str, venue: str, formation: str) -> None:
    result, tone = result_code(score_for, score_against)
    st.markdown(
        f"""
        <div class="coach-scoreboard">
          <div class="coach-score-meta">{html.escape(date_text)} · {html.escape(venue)}</div>
          <div class="coach-score-row">
            <div class="coach-score-team">{html.escape(team)}</div>
            <div class="coach-score coach-{tone}">{html.escape(result)}</div>
            <div class="coach-score-team coach-score-team-right">{html.escape(opponent)}</div>
          </div>
          <div class="coach-score-foot">Formación inicial: {html.escape(formation)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="coach-section-head">
          <div class="coach-section-title">{html.escape(title)}</div>
          <div class="coach-section-sub">{html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _base_layout(height: int = 330) -> dict:
    return dict(
        height=height,
        margin=dict(l=8, r=8, t=18, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, Arial, sans-serif", color=TEXT, size=12),
        hoverlabel=dict(bgcolor="#FFFFFF", font_color=TEXT),
        showlegend=False,
    )


def rating_trend_chart(history: pd.DataFrame, y_col: str = "median_match_rating", title: str | None = None, y_range: tuple[float, float] = (3, 10)) -> go.Figure:
    frame = history.dropna(subset=[y_col]).copy()
    frame["match_date"] = pd.to_datetime(frame["match_date"])
    frame = frame.sort_values("match_date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=frame["match_date"], y=frame[y_col], mode="lines+markers",
        line=dict(color=ACCENT, width=3), marker=dict(size=7),
        hovertemplate="%{x|%d/%m/%Y}<br>%{y:.2f}<extra></extra>",
    ))
    if len(frame) >= 5:
        rolling = pd.to_numeric(frame[y_col], errors="coerce").rolling(5, min_periods=3).mean()
        fig.add_trace(go.Scatter(
            x=frame["match_date"], y=rolling, mode="lines",
            line=dict(color=NAVY, width=2, dash="dot"),
            hovertemplate="Media móvil 5: %{y:.2f}<extra></extra>",
        ))
        fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.08, x=0))
        fig.data[0].name = "Partido"
        fig.data[1].name = "Media móvil 5"
    fig.update_layout(**_base_layout())
    fig.update_yaxes(range=list(y_range), gridcolor=GRID, zeroline=False, title="")
    fig.update_xaxes(gridcolor="rgba(0,0,0,0)", title="")
    if title:
        fig.update_layout(title=dict(text=title, x=0, font=dict(size=15)))
    return fig


def player_rating_chart(ratings: pd.DataFrame, max_players: int | None = None) -> go.Figure:
    frame = ratings.dropna(subset=["match_rating_10"]).copy()
    frame["match_rating_10"] = pd.to_numeric(frame["match_rating_10"], errors="coerce")
    frame = frame.sort_values("match_rating_10", ascending=True)
    if max_players is not None and len(frame) > max_players:
        frame = frame.tail(max_players)
    hover = []
    for row in frame.itertuples(index=False):
        confidence = getattr(row, "match_rating_confidence", None)
        profile = getattr(row, "position_group", None)
        hover.append(f"{safe_text(profile)} · confianza {safe_number(confidence, 0, '%')}")
    fig = go.Figure(go.Bar(
        x=frame["match_rating_10"], y=frame["player"], orientation="h",
        marker=dict(color=ACCENT), text=frame["match_rating_10"].round(1), textposition="outside",
        customdata=hover,
        hovertemplate="<b>%{y}</b><br>Rating %{x:.2f}<br>%{customdata}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(max(320, 32 * max(8, len(frame)))))
    fig.update_xaxes(range=[3, 10], gridcolor=GRID, title="Match Rating")
    fig.update_yaxes(title="", automargin=True)
    return fig


def squad_matrix_chart(snapshot: pd.DataFrame) -> go.Figure:
    frame = snapshot.copy()
    frame["avg_last5"] = pd.to_numeric(frame["avg_last5"], errors="coerce")
    frame["trend_delta_5v5"] = pd.to_numeric(frame["trend_delta_5v5"], errors="coerce")
    frame = frame.dropna(subset=["avg_last5", "trend_delta_5v5"])
    fig = go.Figure()
    if frame.empty:
        fig.update_layout(**_base_layout())
        return fig
    fig.add_trace(go.Scatter(
        x=frame["avg_last5"], y=frame["trend_delta_5v5"], mode="markers",
        marker=dict(size=12, color=ACCENT, opacity=.82, line=dict(width=1, color="#FFFFFF")),
        text=frame["player"],
        customdata=frame[["latest_match_rating", "latest_confidence"]].to_numpy(),
        hovertemplate="<b>%{text}</b><br>Media últimos 5: %{x:.2f}<br>Delta 5 vs 5: %{y:+.2f}<br>Último rating: %{customdata[0]:.2f}<br>Confianza: %{customdata[1]:.0f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="#9AA7B4")
    fig.update_layout(**_base_layout(360))
    fig.update_xaxes(range=[3, 10], gridcolor=GRID, title="Media Match Rating · últimos 5")
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title="Cambio vs 5 anteriores")
    return fig


def player_trend_chart(history: pd.DataFrame, y_col: str, y_range: tuple[float, float], hover_col: str | None = "opponent") -> go.Figure:
    frame = history.dropna(subset=[y_col]).copy()
    frame["match_date"] = pd.to_datetime(frame["match_date"])
    frame = frame.sort_values("match_date")
    custom = frame[hover_col] if hover_col and hover_col in frame.columns else None
    fig = go.Figure(go.Scatter(
        x=frame["match_date"], y=frame[y_col], mode="lines+markers",
        line=dict(color=ACCENT, width=3), marker=dict(size=7),
        customdata=custom,
        hovertemplate=("%{x|%d/%m/%Y}<br>%{customdata}<br>%{y:.2f}<extra></extra>" if custom is not None else "%{x|%d/%m/%Y}<br>%{y:.2f}<extra></extra>"),
    ))
    fig.update_layout(**_base_layout(330))
    fig.update_xaxes(gridcolor="rgba(0,0,0,0)", title="")
    fig.update_yaxes(range=list(y_range), gridcolor=GRID, zeroline=False, title="")
    return fig


def dimension_chart(values: dict[str, object]) -> go.Figure:
    labels = list(values.keys())
    numeric = [pd.to_numeric(pd.Series([values[label]]), errors="coerce").iloc[0] for label in labels]
    frame = pd.DataFrame({"label": labels, "value": numeric}).dropna().sort_values("value", ascending=True)
    fig = go.Figure(go.Bar(
        x=frame["value"], y=frame["label"], orientation="h",
        marker=dict(color=ACCENT), text=frame["value"].round(1), textposition="outside",
        hovertemplate="%{y}: %{x:.1f}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(280))
    fig.update_xaxes(range=[0, 100], gridcolor=GRID, title="")
    fig.update_yaxes(title="", automargin=True)
    return fig


def describe_trend(snapshot: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = snapshot.copy()
    frame["trend_delta_5v5"] = pd.to_numeric(frame.get("trend_delta_5v5"), errors="coerce")
    frame = frame.dropna(subset=["trend_delta_5v5"])
    rising = frame.sort_values("trend_delta_5v5", ascending=False).head(3)
    falling = frame.sort_values("trend_delta_5v5", ascending=True).head(3)
    return rising, falling


def names_with_delta(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "Sin historial comparable"
    bits = []
    for row in frame.itertuples(index=False):
        bits.append(f"{row.player} ({float(row.trend_delta_5v5):+.2f})")
    return " · ".join(bits)


def style_rating_table(frame: pd.DataFrame) -> pd.io.formats.style.Styler:
    return frame.style.background_gradient(subset=[c for c in ["Rating", "Media últimos 5", "Match Rating"] if c in frame.columns], cmap="Greens", vmin=3, vmax=10)
