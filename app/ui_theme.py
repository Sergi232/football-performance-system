"""Shared presentation helpers for the Streamlit coaching dashboard."""
from __future__ import annotations

import html

import streamlit as st

POSITION_LABELS = {
    "CB": "Central",
    "FB": "Lateral",
    "FB_WB": "Lateral / Carrilero",
    "DM": "Pivote",
    "CM": "Mediocentro / Interior",
    "DM_CM": "Mediocentro / Interior",
    "AM": "Mediapunta",
    "W": "Extremo",
    "AM_W": "Mediapunta / Extremo",
    "ST": "Delantero",
    "GK": "Portero",
    "OTHER_OUTFIELD": "Rol no observable",
}


def apply_professional_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --fps-navy: #0B1F33;
            --fps-navy-2: #122B43;
            --fps-accent: #13A37F;
            --fps-bg: #F5F7FA;
            --fps-card: #FFFFFF;
            --fps-border: #E1E8EE;
            --fps-text: #172B3A;
            --fps-muted: #6B7C8F;
            --fps-good: #198754;
            --fps-bad: #C84630;
            --fps-warn: #B7791F;
        }
        html, body, [class*="css"] {
            font-family: "Segoe UI", Inter, -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .stApp { background: var(--fps-bg); color: var(--fps-text); }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stToolbar"] { opacity: .55; }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #081827 0%, #0B1F33 100%);
            border-right: 1px solid rgba(255,255,255,.05);
        }
        [data-testid="stSidebarNav"] { display: none; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span { color: #EAF1F6; }
        [data-testid="stSidebar"] a {
            border-radius: 9px;
            margin-bottom: 3px;
            text-decoration: none;
        }
        [data-testid="stSidebar"] a:hover { background: rgba(255,255,255,.08); }
        .block-container {
            max-width: 1480px;
            padding-top: 1.25rem;
            padding-bottom: 3.5rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        h1, h2, h3 { color: var(--fps-text); letter-spacing: -0.025em; }
        h2 { font-size: 1.35rem; }
        h3 { font-size: 1.08rem; }
        .coach-brand {
            padding: .75rem .35rem 1.25rem .35rem;
            border-bottom: 1px solid rgba(255,255,255,.08);
            margin-bottom: .8rem;
        }
        .coach-brand-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 34px; height: 34px;
            border-radius: 9px;
            background: #13A37F;
            color: #fff;
            font-size: .84rem;
            font-weight: 900;
            letter-spacing: -.02em;
            margin-bottom: .7rem;
        }
        .coach-brand-title { color:#fff; font-size:1rem; font-weight:800; line-height:1.15; }
        .coach-brand-sub { color:#91A5B5; font-size:.75rem; margin-top:.25rem; }
        .coach-nav-label {
            color:#6F879A;
            font-size:.68rem;
            font-weight:800;
            letter-spacing:.09em;
            text-transform:uppercase;
            margin:.85rem 0 .35rem .35rem;
        }
        .coach-page-header {
            display:flex;
            align-items:flex-start;
            justify-content:space-between;
            gap:1rem;
            margin: .1rem 0 1rem 0;
            padding-bottom: .8rem;
            border-bottom: 1px solid var(--fps-border);
        }
        .coach-kicker, .fps-kicker {
            color: var(--fps-accent);
            font-size: .72rem;
            font-weight: 850;
            text-transform: uppercase;
            letter-spacing: .11em;
            margin-bottom: .28rem;
        }
        .coach-title { color:var(--fps-text); font-size:1.9rem; line-height:1.1; font-weight:850; letter-spacing:-.03em; }
        .coach-subtitle { color:var(--fps-muted); font-size:.89rem; line-height:1.45; margin-top:.32rem; max-width:760px; }
        .coach-badge {
            display:inline-flex;
            border:1px solid #CDE5DE;
            background:#EAF7F3;
            color:#14765F;
            font-size:.74rem;
            font-weight:800;
            padding:.38rem .65rem;
            border-radius:999px;
            white-space:nowrap;
        }
        .coach-section-head { margin: 1rem 0 .5rem 0; }
        .coach-section-title { font-size:1.05rem; font-weight:800; color:var(--fps-text); letter-spacing:-.015em; }
        .coach-section-sub { font-size:.78rem; color:var(--fps-muted); line-height:1.35; margin-top:.14rem; }
        .coach-metric-card, .fps-score-card {
            background: var(--fps-card);
            border: 1px solid var(--fps-border);
            border-radius: 9px;
            padding: .78rem .9rem;
            min-height: 104px;
            box-shadow: none;
        }
        .coach-metric-label, .fps-score-label {
            color: var(--fps-muted);
            font-size: .68rem;
            text-transform: uppercase;
            letter-spacing: .08em;
            font-weight: 800;
            line-height: 1.2;
        }
        .coach-metric-value, .fps-score-value {
            color: var(--fps-text);
            font-size: 1.3rem;
            font-weight: 850;
            line-height: 1.1;
            letter-spacing: -.025em;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
            margin-top: .32rem;
        }
        .coach-metric-sub, .fps-score-sub { color: var(--fps-muted); margin-top:.28rem; font-size:.75rem; line-height:1.32; }
        .coach-delta { margin-top:.25rem; font-size:.77rem; font-weight:800; }
        .coach-positive { color:var(--fps-good); }
        .coach-negative { color:var(--fps-bad); }
        .coach-neutral { color:var(--fps-muted); }
        .coach-warning { color:var(--fps-warn); }
        .coach-scoreboard {
            background: linear-gradient(135deg, #0B1F33 0%, #14344F 100%);
            color:#fff;
            border-radius:11px;
            padding:1.05rem 1.2rem;
            box-shadow:none;
            min-height:158px;
        }
        .coach-score-meta { color:#9CB0C0; font-size:.76rem; font-weight:750; text-transform:uppercase; letter-spacing:.06em; }
        .coach-score-row { display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:1rem; margin-top:1.1rem; }
        .coach-score-team { font-size:1.12rem; font-weight:800; line-height:1.2; }
        .coach-score-team-right { text-align:right; }
        .coach-score { color:#fff; background:rgba(255,255,255,.1); padding:.5rem .8rem; border-radius:10px; font-weight:900; font-size:1.45rem; }
        .coach-score-foot { margin-top:1rem; color:#B6C5D0; font-size:.78rem; }
        .coach-insight {
            background:#fff;
            border:1px solid var(--fps-border);
            border-left:4px solid #9AA8B4;
            border-radius:8px;
            padding:.72rem .85rem;
            margin-bottom:.5rem;
            min-height:0;
        }
        .coach-insight-positive { border-left-color:var(--fps-good); }
        .coach-insight-negative { border-left-color:var(--fps-bad); }
        .coach-insight-warning { border-left-color:var(--fps-warn); }
        .coach-insight-neutral { border-left-color:#8A9AA8; }
        .coach-insight-title { color:var(--fps-text); font-size:.82rem; font-weight:850; }
        .coach-insight-body { color:#2B3F4F; font-size:.9rem; font-weight:650; margin-top:.2rem; line-height:1.35; }
        .coach-insight-meta { color:var(--fps-muted); font-size:.72rem; margin-top:.32rem; line-height:1.3; }
        .fps-hero {
            background: #0B1F33;
            color:#fff;
            border-radius:15px;
            padding:1.15rem 1.3rem;
            margin-bottom:1rem;
        }
        .fps-player-name { font-size:1.8rem; line-height:1.1; font-weight:850; margin:0; }
        .fps-player-meta { margin-top:.45rem; color:#B7C6D2; font-size:.9rem; }
        .fps-muted-card { background:#fff; border:1px solid var(--fps-border); border-radius:12px; padding:1rem; }
        .fps-dim-row { margin-bottom:.75rem; }
        .fps-dim-head { display:flex; justify-content:space-between; font-size:.84rem; margin-bottom:.25rem; color:#304454; }
        .fps-dim-track { height:7px; background:#E8EDF1; border-radius:999px; overflow:hidden; }
        .fps-dim-fill { height:100%; background:var(--fps-accent); border-radius:999px; }
        [data-testid="stMetric"] {
            background:#fff;
            border:1px solid var(--fps-border);
            border-radius:12px;
            padding:.75rem .9rem;
            box-shadow:none;
        }
        [data-testid="stMetricLabel"] { color:var(--fps-muted); }
        [data-testid="stMetricValue"] { color:var(--fps-text); font-weight:800; }
        [data-testid="stDataFrame"] { border:1px solid var(--fps-border); border-radius:11px; overflow:hidden; }
        div[data-baseweb="select"] > div { border-radius:9px; border-color:#D8E1E8; background:#fff; }
        div[data-baseweb="tab-list"] { gap:.2rem; border-bottom:1px solid var(--fps-border); }
        button[data-baseweb="tab"] { padding:.62rem .85rem; border-radius:8px 8px 0 0; font-size:.86rem; }
        button[kind="secondary"], button[kind="primary"] { border-radius:9px; }
        hr { border-color:var(--fps-border); }
        @media (max-width: 900px) {
            .block-container { padding-left:1rem; padding-right:1rem; }
            .coach-page-header { flex-direction:column; }
            .coach-title { font-size:1.7rem; }
            .coach-score-row { grid-template-columns:1fr; text-align:left; }
            .coach-score-team-right { text-align:left; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_navigation() -> None:
    st.sidebar.markdown(
        """
        <div class="coach-brand">
          <div class="coach-brand-mark">FPS</div>
          <div class="coach-brand-title">Football Performance</div>
          <div class="coach-brand-sub">Sistema de inteligencia para el staff técnico</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<div class='coach-nav-label'>Operativa</div>", unsafe_allow_html=True)
    st.sidebar.page_link("streamlit_app.py", label="Centro de mando", icon="🏠")
    st.sidebar.page_link("pages/3_Equip.py", label="Equipo", icon="🏟️")
    st.sidebar.page_link("pages/4_Partit.py", label="Partido", icon="⚽")
    st.sidebar.page_link("pages/2_Jugador.py", label="Jugador", icon="👤")
    st.sidebar.markdown("<div class='coach-nav-label'>Análisis</div>", unsafe_allow_html=True)
    st.sidebar.page_link("pages/1_Performance_Index.py", label="Performance Index", icon="📈")
    st.sidebar.page_link("pages/6_Fisic_GPS.py", label="Físico / GPS", icon="📡")
    st.sidebar.page_link("pages/7_Alertes.py", label="Calidad y alertas", icon="🚩")
    st.sidebar.markdown("<div class='coach-nav-label'>Asistente</div>", unsafe_allow_html=True)
    st.sidebar.page_link("pages/5_Assistent_IA.py", label="Asistente IA", icon="💬")
    st.sidebar.caption("Match Rating V5 · uso local")


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
