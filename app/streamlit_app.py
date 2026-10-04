"""Coach Command Center — professional operational dashboard for technical staff."""
from __future__ import annotations

import os
import sys
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.attention_access import get_attention_summary, get_team_attention_flags
from app.coach_ui import (
    describe_trend,
    insight_card,
    metric_card,
    names_with_delta,
    page_header,
    player_rating_chart,
    rating_trend_chart,
    recent_record,
    safe_int,
    safe_number,
    safe_text,
    scoreboard_card,
    section_header,
    squad_matrix_chart,
)
from app.dashboard_config import DASHBOARD_CONFIG
from app.data_access import get_squad_summary, get_team_matches, get_team_overview, list_teams
from app.gps_physical_access import get_gps_summary_status
from app.match_rating_access import (
    get_latest_team_match_ratings,
    get_team_match_rating_history,
    get_team_player_rating_snapshot,
)
from app.presentation import (
    anonymize_frame,
    build_opponent_aliases,
    build_player_aliases,
    build_player_name_aliases,
    demo_mode,
    display_opponent,
    display_team_name,
    replace_known_names,
)
from app.ui_theme import apply_professional_theme, position_label, sidebar_navigation

DEFAULT_DB = ROOT / "data" / "football_performance_synthetic_demo.duckdb"
CFG = DASHBOARD_CONFIG

st.set_page_config(
    page_title="Centro de mando · FPS",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_professional_theme()
sidebar_navigation()

st.markdown(
    """
    <style>
    .fps-command-strip {display:flex;gap:.55rem;flex-wrap:wrap;margin:.1rem 0 1rem 0;}
    .fps-command-pill {background:#FFFFFF;border:1px solid #DDE5EB;border-radius:999px;padding:.38rem .72rem;font-size:.76rem;font-weight:750;color:#486173;}
    .fps-command-pill strong { color:#0B1F33; }
    .fps-status-panel {background:#FFFFFF;border:1px solid #DDE5EB;border-radius:14px;padding:1rem 1.05rem;min-height:100%;}
    .fps-status-label {font-size:.68rem;font-weight:850;letter-spacing:.075em;color:#718493;text-transform:uppercase;margin-bottom:.25rem;}
    .fps-status-value {color:#102A43;font-size:1.05rem;font-weight:850;line-height:1.2;}
    .fps-status-sub {color:#607D8B;font-size:.77rem;line-height:1.35;margin-top:.25rem;}
    [data-testid="stPageLink"] a {border:1px solid #DDE5EB;border-radius:10px;padding:.55rem .75rem;background:#FFFFFF;text-decoration:none;font-weight:750;}
    [data-testid="stPageLink"] a:hover {border-color:#AFC5D2;background:#F8FAFB;}
    [data-testid="stSidebar"] [data-testid="stPageLink"] a {border:0;border-radius:8px;padding:.45rem .5rem;background:transparent;}
    [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {border-color:transparent;background:rgba(255,255,255,.08);}
    @media (max-width: 900px) {.fps-command-strip { gap:.35rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def _cols_ratio(name: str, fallback: list[float]) -> list[float]:
    raw = CFG.get(name, fallback)
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        return fallback
    try:
        return [float(raw[0]), float(raw[1])]
    except (TypeError, ValueError):
        return fallback


def _render_quick_nav() -> None:
    if not CFG.get("show_quick_nav", True):
        return
    st.caption("Acceso rápido")
    n1, n2, n3, n4 = st.columns(4)
    with n1:
        st.page_link("pages/3_Equip.py", label="Equipo")
    with n2:
        st.page_link("pages/4_Partit.py", label="Partido")
    with n3:
        st.page_link("pages/2_Jugador.py", label="Jugador")
    with n4:
        st.page_link("pages/5_Assistent_IA.py", label="Asistente IA")


path = db_path()
if not path.exists():
    st.error(f"No se ha encontrado la base de datos: {path}")
    st.stop()

teams = list_teams(path)
if teams.empty:
    st.info("No hay equipos disponibles.")
    st.stop()

raw_team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
team_ids = list(raw_team_labels)
display_team_labels = {
    tid: display_team_name(raw_team_labels[tid], team_ids.index(tid) + 1)
    for tid in team_ids
}
control_team, control_nav = st.columns([1.0, 2.8], gap="large")
with control_team:
    team_id = st.selectbox("Equipo", options=team_ids, format_func=lambda x: display_team_labels[x])
with control_nav:
    _render_quick_nav()

raw_team_name = raw_team_labels[team_id]
team_name = display_team_labels[team_id]
overview = get_team_overview(path, team_id)
matches = get_team_matches(path, team_id).copy()
squad = get_squad_summary(path, team_id)
ratings = get_latest_team_match_ratings(path, team_id)
rating_history = get_team_match_rating_history(path, team_id)
rating_snapshot = get_team_player_rating_snapshot(path, team_id)

player_aliases = build_player_aliases(squad)
player_name_aliases = build_player_name_aliases(squad)
opponent_aliases = build_opponent_aliases(matches.get("opponent", pd.Series(dtype=str)).tolist())
ratings = anonymize_frame(ratings, player_aliases_by_id=player_aliases, player_name_aliases=player_name_aliases, opponent_aliases=opponent_aliases)
rating_snapshot = anonymize_frame(rating_snapshot, player_aliases_by_id=player_aliases, player_name_aliases=player_name_aliases, opponent_aliases=opponent_aliases)

try:
    attention = get_team_attention_flags(path, team_id)
    attention_summary = get_attention_summary(path, team_id)
    attention = anonymize_frame(attention, player_aliases_by_id=player_aliases, player_name_aliases=player_name_aliases, opponent_aliases=opponent_aliases)
    if demo_mode() and not attention.empty and "message" in attention.columns:
        attention["message"] = attention["message"].map(
            lambda x: replace_known_names(
                x,
                player_name_aliases=player_name_aliases,
                opponent_aliases=opponent_aliases,
                team_name=raw_team_name,
                team_alias=team_name,
            )
        )
except Exception:
    attention = pd.DataFrame()
    attention_summary = pd.DataFrame()

try:
    gps_status = get_gps_summary_status(path)
except Exception:
    gps_status = {"rows": 0, "matches": 0, "players": 0, "imports": 0}

if not matches.empty:
    matches["match_date"] = pd.to_datetime(matches["match_date"])
    matches = matches.sort_values(["match_date", "match_id"], ascending=[False, False])
    latest_match = matches.iloc[0]
else:
    latest_match = None

page_header(
    "TEAM MODE · CENTRO DE MANDO",
    team_name,
    "Visión ejecutiva del último partido, evolución reciente, plantilla y calidad de la evidencia.",
    "Match Rating V5",
)

if latest_match is None:
    st.info("No hay partidos disponibles.")
    st.stop()

median_rating = pd.to_numeric(ratings.get("match_rating_10"), errors="coerce").median() if not ratings.empty else None
median_conf = pd.to_numeric(ratings.get("match_rating_confidence"), errors="coerce").median() if not ratings.empty else None
role_flags = 0
if not attention_summary.empty:
    rows = attention_summary.loc[attention_summary["attention_code"] == "ROLE_CONTEXT_UNAVAILABLE", "rows"]
    if not rows.empty:
        role_flags = int(rows.iloc[0])

rising, falling = describe_trend(rating_snapshot) if not rating_snapshot.empty else (pd.DataFrame(), pd.DataFrame())
ranked = ratings.dropna(subset=["match_rating_10"]).sort_values("match_rating_10", ascending=False) if not ratings.empty else pd.DataFrame()
top_three = ranked.head(3)
gps_rows = int(gps_status.get("rows", 0))
last_date = str(pd.to_datetime(latest_match["match_date"]).date())
venue_value = latest_match.get("venue")
venue_text = "Local" if venue_value in {"H", "Home", "Local"} else "Visitante"
latest_opponent = display_opponent(latest_match.get("opponent"), opponent_aliases)

if CFG.get("show_command_strip", True):
    st.markdown(
        f"""
        <div class="fps-command-strip">
          <div class="fps-command-pill">Último partido · <strong>{escape(last_date)}</strong></div>
          <div class="fps-command-pill">Forma L5 · <strong>{escape(recent_record(matches, 5))}</strong></div>
          <div class="fps-command-pill">Plantilla · <strong>{safe_int(overview.get("players"))}</strong></div>
          <div class="fps-command-pill">Partidos · <strong>{safe_int(overview.get("matches"))}</strong></div>
          <div class="fps-command-pill">GPS · <strong>{"Disponible" if gps_rows else "Sin datos"}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    left, right = st.columns(_cols_ratio("hero_ratio", [1.45, 1.0]), gap="large")
    with left:
        scoreboard_card(
            team_name,
            latest_opponent,
            latest_match.get("score_for"),
            latest_match.get("score_against"),
            last_date,
            venue_text,
            safe_text(latest_match.get("starting_formation"), "No disponible"),
        )
    with right:
        section_header("Estado del equipo", "Lectura inmediata del último partido")
        r1, r2 = st.columns(2)
        with r1:
            metric_card("Match Rating", safe_number(median_rating, 2, "/10"), "Mediana del último partido")
        with r2:
            metric_card("Confianza", safe_number(median_conf, 0, "%"), "Mediana de evidencia")
        r3, r4 = st.columns(2)
        with r3:
            metric_card("Forma L5", recent_record(matches, 5), "Últimos cinco partidos")
        with r4:
            metric_card("Contexto de rol", str(role_flags), "Apariciones con rol no fiable")


def render_coach_brief() -> None:
    section_header("Coach Brief", "Qué ha pasado y qué conviene revisar primero")
    if not top_three.empty:
        top_names = " · ".join(f"{r.player} {float(r.match_rating_10):.1f}" for r in top_three.itertuples(index=False))
    else:
        top_names = "Sin datos"
    quality_text = f"{role_flags} registros con contexto de rol limitado"
    if gps_rows == 0:
        quality_text += " · GPS no disponible"
    cards = [
        ("Destacados · último partido", top_names, "Match Rating V5", "positive"),
        ("Mejora reciente", names_with_delta(rising), "Media L5 vs 5 anteriores", "positive"),
        ("Descenso reciente", names_with_delta(falling), "Señal descriptiva, no diagnóstica", "negative"),
        ("Calidad de datos", quality_text, "Limitaciones visibles antes de interpretar", "warning" if role_flags or gps_rows == 0 else "neutral"),
    ]
    if int(CFG.get("brief_columns", 4)) == 2:
        for start in (0, 2):
            c1, c2 = st.columns(2, gap="medium")
            for col, item in zip((c1, c2), cards[start:start + 2]):
                with col:
                    insight_card(*item)
    else:
        cols = st.columns(4, gap="medium")
        for col, item in zip(cols, cards):
            with col:
                insight_card(*item)


def render_trend() -> None:
    section_header("Evolución del rendimiento", "Match Rating agregado por partido y contexto temporal")
    trend_col, context_col = st.columns(_cols_ratio("trend_ratio", [1.65, 0.75]), gap="large")
    with trend_col:
        if rating_history.empty:
            st.info("Todavía no hay historial de Match Rating.")
        else:
            st.plotly_chart(rating_trend_chart(rating_history), width="stretch", config={"displayModeBar": False})
    with context_col:
        st.markdown(
            f"""
            <div class="fps-status-panel">
              <div class="fps-status-label">Temporada disponible</div>
              <div class="fps-status-value">{safe_int(overview.get("matches"))} partidos</div>
              <div class="fps-status-sub">Historial utilizado por el dashboard.</div>
              <br>
              <div class="fps-status-label">Plantilla registrada</div>
              <div class="fps-status-value">{safe_int(overview.get("players"))} jugadores</div>
              <div class="fps-status-sub">Perfiles con datos dentro del sistema.</div>
              <br>
              <div class="fps-status-label">GPS</div>
              <div class="fps-status-value">{"Disponible" if gps_rows else "No disponible"}</div>
              <div class="fps-status-sub">Fuente complementaria; no condiciona el Team Mode.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_squad_map() -> None:
    if rating_snapshot.empty:
        st.info("No hay snapshot de plantilla disponible.")
    else:
        st.plotly_chart(squad_matrix_chart(rating_snapshot), width="stretch", config={"displayModeBar": False})
        st.caption("Cada punto representa a un jugador. El eje vertical muestra cambio reciente y no una clasificación absoluta.")


def _render_last_match_ratings() -> None:
    if ratings.empty:
        st.info("No hay ratings disponibles.")
    else:
        chart_ratings = ratings.copy()
        chart_ratings["position_group"] = chart_ratings["position_group"].map(position_label)
        st.plotly_chart(player_rating_chart(chart_ratings), width="stretch", config={"displayModeBar": False})


def render_squad() -> None:
    section_header("Plantilla", "Nivel reciente, evolución individual y último partido")
    if CFG.get("squad_mode", "tabs") == "split":
        left, right = st.columns([1.15, 1.0], gap="large")
        with left:
            st.caption("Mapa de plantilla")
            _render_squad_map()
        with right:
            st.caption("Ratings · último partido")
            _render_last_match_ratings()
    else:
        tab_map, tab_match = st.tabs(["Mapa de plantilla", "Ratings · último partido"])
        with tab_map:
            _render_squad_map()
        with tab_match:
            _render_last_match_ratings()


def render_quality() -> None:
    section_header("Calidad y revisión", "Incidencias de contexto o cobertura que pueden afectar la lectura")
    if CFG.get("quality_mode", "cards") == "compact":
        st.markdown(
            f"""
            <div class="fps-status-panel">
              <div class="fps-status-label">Contexto de rol</div>
              <div class="fps-status-value">{role_flags}</div>
              <div class="fps-status-sub">Apariciones con fallback explícito.</div>
              <br>
              <div class="fps-status-label">GPS</div>
              <div class="fps-status-value">{safe_int(gps_rows)}</div>
              <div class="fps-status-sub">Muestras normalizadas.</div>
              <br>
              <div class="fps-status-label">Cobertura</div>
              <div class="fps-status-value">{safe_int(overview.get("players"))} jugadores</div>
              <div class="fps-status-sub">{safe_int(overview.get('matches'))} partidos.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        q1, q2, q3 = st.columns(3)
        with q1:
            metric_card("Contexto de rol", str(role_flags), "Apariciones con fallback explícito")
        with q2:
            metric_card("GPS", safe_int(gps_rows), "Muestras normalizadas")
        with q3:
            metric_card("Cobertura", safe_int(overview.get("players")), f"{safe_int(overview.get('matches'))} partidos")
    if not attention.empty:
        with st.expander("Ver incidencias de calidad y contexto", expanded=False):
            detail = attention[["match_date", "player", "attention_code", "message"]].copy()
            detail["match_date"] = pd.to_datetime(detail["match_date"], errors="coerce").dt.date
            detail.columns = ["Fecha", "Jugador", "Código", "Contexto"]
            st.dataframe(detail, hide_index=True, width="stretch", height=320)


render_hero()

renderers = {"coach_brief": render_coach_brief, "trend": render_trend, "squad": render_squad, "quality": render_quality}
seen = set()
for key in CFG.get("section_order", ["coach_brief", "trend", "squad", "quality"]):
    if key in renderers and key not in seen:
        renderers[key]()
        seen.add(key)
for key in ("coach_brief", "trend", "squad", "quality"):
    if key not in seen:
        renderers[key]()

with st.expander("Metodología y límites del dashboard", expanded=False):
    st.markdown(
        """
        - El **Match Rating** es una nota jugador-partido materializada por el motor analítico.
        - Las tendencias son descriptivas y no constituyen diagnósticos.
        - Las limitaciones de rol y cobertura se muestran explícitamente.
        - El GPS es opcional.
        - El dashboard **no recalcula** ratings.
        - El LLM no genera conclusiones críticas ni modifica métricas.
        """
    )
