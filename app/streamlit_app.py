"""Coach Command Center — operational home for technical staff."""
from __future__ import annotations

import os
import sys
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
from app.data_access import get_team_matches, get_team_overview, list_teams
from app.gps_physical_access import get_gps_summary_status
from app.match_rating_access import (
    get_latest_team_match_ratings,
    get_team_match_rating_history,
    get_team_player_rating_snapshot,
)
from app.ui_theme import apply_professional_theme, position_label, sidebar_navigation

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(page_title="Coach Command Center · FPS", page_icon="⚽", layout="wide")
apply_professional_theme()
sidebar_navigation()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


path = db_path()
if not path.exists():
    st.error(f"No s'ha trobat la base de dades: {path}")
    st.stop()

teams = list_teams(path)
if teams.empty:
    st.info("No hi ha equips disponibles.")
    st.stop()

team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
selector, _ = st.columns([1.0, 2.3])
with selector:
    team_id = st.selectbox("Equip", options=list(team_labels), format_func=lambda x: team_labels[x])
team_name = team_labels[team_id]

overview = get_team_overview(path, team_id)
matches = get_team_matches(path, team_id).copy()
ratings = get_latest_team_match_ratings(path, team_id)
rating_history = get_team_match_rating_history(path, team_id)
rating_snapshot = get_team_player_rating_snapshot(path, team_id)
try:
    attention = get_team_attention_flags(path, team_id)
    attention_summary = get_attention_summary(path, team_id)
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
    "TEAM MODE · COACH COMMAND CENTER",
    team_name,
    "Una sola vista per entendre l'últim partit, la forma recent, els canvis de la plantilla i la qualitat de l'evidència.",
    "Match Rating V5",
)

if latest_match is None:
    st.info("No hi ha partits disponibles.")
    st.stop()

median_rating = pd.to_numeric(ratings.get("match_rating_10"), errors="coerce").median() if not ratings.empty else None
median_conf = pd.to_numeric(ratings.get("match_rating_confidence"), errors="coerce").median() if not ratings.empty else None
role_flags = 0
if not attention_summary.empty:
    row = attention_summary.loc[attention_summary["attention_code"] == "ROLE_CONTEXT_UNAVAILABLE", "rows"]
    role_flags = int(row.iloc[0]) if not row.empty else 0

# --- Immediate staff brief ---------------------------------------------------
left, right = st.columns([1.55, 1.0], gap="large")
with left:
    scoreboard_card(
        team_name,
        safe_text(latest_match.get("opponent"), "Rival no disponible"),
        latest_match.get("score_for"),
        latest_match.get("score_against"),
        str(pd.to_datetime(latest_match["match_date"]).date()),
        "Local" if latest_match.get("venue") == "H" else "Visitant",
        safe_text(latest_match.get("starting_formation"), "No disponible"),
    )
    m1, m2, m3 = st.columns(3)
    with m1:
        metric_card("Rating equip · mediana", safe_number(median_rating, 2, "/10"), "Jugadors utilitzats a l'últim partit")
    with m2:
        metric_card("Confiança · mediana", safe_number(median_conf, 0, "%"), "Cobertura de l'evidència del rating")
    with m3:
        metric_card("Forma recent", recent_record(matches, 5), "Últims 5 partits · ordre del més recent")

with right:
    section_header("Brief del cos tècnic", "Senyals descriptius; no són recomanacions automàtiques")
    if not ratings.empty:
        ranked = ratings.dropna(subset=["match_rating_10"]).sort_values("match_rating_10", ascending=False)
        top = ranked.head(3)
        if not top.empty:
            names = " · ".join(f"{r.player} {float(r.match_rating_10):.1f}" for r in top.itertuples(index=False))
            insight_card("Ratings més alts · últim partit", names, "Ordenació descriptiva del Match Rating V5", "positive")
    rising, falling = describe_trend(rating_snapshot) if not rating_snapshot.empty else (pd.DataFrame(), pd.DataFrame())
    insight_card("Canvi recent positiu", names_with_delta(rising), "Delta: mitjana últims 5 menys 5 anteriors", "positive")
    insight_card("Canvi recent negatiu", names_with_delta(falling), "Delta descriptiu; no és una alerta de rendiment", "negative")
    context_text = f"{role_flags} aparicions històriques sense rol tàctic fiable"
    if int(gps_status.get("rows", 0)) == 0:
        context_text += " · GPS encara sense dades reals"
    insight_card("Qualitat de dades", context_text, "Limitacions visibles i auditables", "warning" if role_flags else "neutral")

# --- Team evolution ---------------------------------------------------------
section_header("Evolució del rendiment", "Mediana de Match Rating per partit + mitjana mòbil descriptiva de 5 partits")
if rating_history.empty:
    st.info("Encara no hi ha historial de Match Rating.")
else:
    st.plotly_chart(rating_trend_chart(rating_history), width="stretch", config={"displayModeBar": False})

# --- Squad status -----------------------------------------------------------
section_header("Plantilla · estat recent", "Nivell recent i canvi respecte als cinc partits anteriors")
col_matrix, col_latest = st.columns([1.2, 1.0], gap="large")
with col_matrix:
    if rating_snapshot.empty:
        st.info("No hi ha snapshot de plantilla disponible.")
    else:
        st.plotly_chart(squad_matrix_chart(rating_snapshot), width="stretch", config={"displayModeBar": False})
        st.caption("Cada punt és un jugador. L'eix vertical és canvi recent, no una classificació de qualitat.")
with col_latest:
    section_header("Últim partit · tots els ratings", "Ordenats per nota; la confiança es mostra al hover")
    if ratings.empty:
        st.info("No hi ha ratings disponibles.")
    else:
        chart_ratings = ratings.copy()
        chart_ratings["position_group"] = chart_ratings["position_group"].map(position_label)
        st.plotly_chart(player_rating_chart(chart_ratings), width="stretch", config={"displayModeBar": False})

# --- Review queue -----------------------------------------------------------
section_header("Cua de revisió", "Context que pot requerir verificació humana abans d'interpretar les dades")
q1, q2, q3 = st.columns(3)
with q1:
    metric_card("Limitacions de rol", str(role_flags), "Aparicions històriques amb fallback explícit")
with q2:
    metric_card("GPS", safe_int(gps_status.get("rows")), "Mostres GPS normalitzades disponibles")
with q3:
    metric_card("Plantilla", safe_int(overview.get("players")), f"{safe_int(overview.get('matches'))} partits disponibles")

if not attention.empty:
    with st.expander("Veure detall de qualitat i context"):
        detail = attention[["match_date", "player", "attention_code", "message"]].copy()
        detail["match_date"] = pd.to_datetime(detail["match_date"], errors="coerce").dt.date
        detail.columns = ["Data", "Jugador", "Codi", "Context"]
        st.dataframe(detail, hide_index=True, width="stretch", height=300)

st.caption("El Command Center consumeix analytics materialitzats. No recalcula ratings ni genera conclusions crítiques amb un LLM.")
