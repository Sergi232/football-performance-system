"""Shared presentation helpers for the Streamlit coaching dashboard."""
from __future__ import annotations

import html

import streamlit as st

POSITION_LABELS = {
    "CB": "Central",
    "FB_WB": "Lateral / Carriler",
    "DM_CM": "Migcentre / Interior",
    "AM_W": "Mitjapunta / Extrem",
    "ST": "Davanter",
    "GK": "Porter",
    "OTHER_OUTFIELD": "Rol no observable",
}


def apply_professional_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #f4f7f9;
        }
        [data-testid="stSidebar"] {
            background: #0d1b2a;
        }
        [data-testid="stSidebar"] * {
            color: #f7fafc;
        }
        .block-container {
            max-width: 1500px;
            padding-top: 1.6rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3 {
            letter-spacing: -0.02em;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #dde5eb;
            border-radius: 14px;
            padding: 0.85rem 1rem;
            box-shadow: 0 2px 10px rgba(13, 27, 42, 0.05);
        }
        [data-testid="stMetricLabel"] {
            color: #5f6f7d;
        }
        [data-testid="stMetricValue"] {
            color: #102a43;
            font-weight: 750;
        }
        div[data-baseweb="tab-list"] {
            gap: 0.4rem;
            border-bottom: 1px solid #dbe4ea;
        }
        button[data-baseweb="tab"] {
            padding: 0.7rem 1rem;
            border-radius: 10px 10px 0 0;
        }
        .fps-hero {
            background: linear-gradient(120deg, #102a43 0%, #183b56 62%, #1f5f55 100%);
            color: #ffffff;
            border-radius: 18px;
            padding: 1.4rem 1.6rem;
            margin-bottom: 1rem;
            box-shadow: 0 8px 24px rgba(13, 27, 42, 0.15);
        }
        .fps-kicker {
            color: #b7d5ce;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }
        .fps-player-name {
            font-size: 2rem;
            line-height: 1.1;
            font-weight: 800;
            margin: 0;
        }
        .fps-player-meta {
            margin-top: 0.55rem;
            color: #d7e3ea;
            font-size: 0.96rem;
        }
        .fps-score-card {
            background: #ffffff;
            border: 1px solid #dde5eb;
            border-radius: 16px;
            padding: 1rem 1.15rem;
            min-height: 138px;
            box-shadow: 0 3px 14px rgba(13, 27, 42, 0.06);
        }
        .fps-score-label {
            color: #6b7c88;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            font-weight: 700;
        }
        .fps-score-value {
            color: #102a43;
            font-size: 2.45rem;
            font-weight: 850;
            line-height: 1.05;
            margin-top: 0.3rem;
        }
        .fps-score-sub {
            color: #617382;
            margin-top: 0.35rem;
            font-size: 0.88rem;
        }
        .fps-section-note {
            color: #627585;
            font-size: 0.88rem;
            margin-top: -0.35rem;
            margin-bottom: 0.9rem;
        }
        .fps-dim-row {
            margin-bottom: 0.8rem;
        }
        .fps-dim-head {
            display: flex;
            justify-content: space-between;
            font-size: 0.9rem;
            margin-bottom: 0.28rem;
            color: #263746;
        }
        .fps-dim-track {
            height: 8px;
            background: #e8eef2;
            border-radius: 999px;
            overflow: hidden;
        }
        .fps-dim-fill {
            height: 100%;
            background: linear-gradient(90deg, #1f7a6d 0%, #2c9c88 100%);
            border-radius: 999px;
        }
        .fps-muted-card {
            background: #ffffff;
            border: 1px solid #dde5eb;
            border-radius: 14px;
            padding: 1rem 1.1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def position_label(value: object) -> str:
    if value is None:
        return "—"
    raw = str(value)
    return POSITION_LABELS.get(raw, raw)


def hero(player_name: str, team_name: str, role: str, meta: str = "") -> None:
    role_text = html.escape(role or "Rol no disponible")
    meta_text = html.escape(meta)
    st.markdown(
        f"""
        <div class="fps-hero">
            <div class="fps-kicker">{html.escape(team_name)}</div>
            <div class="fps-player-name">{html.escape(player_name)}</div>
            <div class="fps-player-meta">{role_text}{' · ' + meta_text if meta_text else ''}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def score_card(label: str, value: str, sub: str) -> None:
    st.markdown(
        f"""
        <div class="fps-score-card">
            <div class="fps-score-label">{html.escape(label)}</div>
            <div class="fps-score-value">{html.escape(value)}</div>
            <div class="fps-score-sub">{html.escape(sub)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def dimension_bar(label: str, value: object) -> None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float("nan")
    if numeric != numeric:
        st.markdown(
            f"<div class='fps-dim-row'><div class='fps-dim-head'><span>{html.escape(label)}</span><span>—</span></div><div class='fps-dim-track'></div></div>",
            unsafe_allow_html=True,
        )
        return
    clamped = max(0.0, min(100.0, numeric))
    st.markdown(
        f"""
        <div class="fps-dim-row">
            <div class="fps-dim-head"><span>{html.escape(label)}</span><strong>{numeric:.1f}</strong></div>
            <div class="fps-dim-track"><div class="fps-dim-fill" style="width:{clamped:.1f}%"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
