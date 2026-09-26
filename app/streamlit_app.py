"""Professional home for the Football Performance System coaching dashboard."""
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
from app.data_access import get_team_matches, get_team_overview, list_teams
from app.gps_physical_access import get_gps_summary_status
from app.match_rating_access import (
    get_latest_team_match_ratings,
    get_team_match_rating_history,
)
from app.ui_theme import apply_professional_theme, position_label, score_card

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(
    page_title="Football Performance System",
    page_icon="⚽",
    layout="wide",
)
apply_professional_theme()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def safe_int(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{int(value):,}".replace(",", ".")


def result_text(score_for: object, score_against: object) -> str:
    if pd.isna(score_for) or pd.isna(score_against):
        return "—"
    sf, sa = int(score_for), int(score_against)
    return f"{'V' if sf > sa else 'E' if sf == sa else 'D'} {sf}-{sa}"


path = db_path()
if not path.exists():
    st.error(f"No s'ha trobat la base de dades: {path}")
    st.stop()

teams = list_teams(path)
if teams.empty:
    st.info("No hi ha equips disponibles.")
    st.stop()

team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
team_id = st.selectbox("Equip", options=list(team_labels), format_func=lambda x: team_labels[x])
team_name = team_labels[team_id]

overview = get_team_overview(path, team_id)
matches = get_team_matches(path, team_id).copy()
ratings = get_latest_team_match_ratings(path, team_id)
rating_history = get_team_match_rating_history(path, team_id)
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

st.markdown(
    f"""
    <div class="fps-hero">
        <div class="fps-kicker">FOOTBALL PERFORMANCE SYSTEM · TEAM MODE</div>
        <div class="fps-player-name">{team_name}</div>
        <div class="fps-player-meta">Centre operatiu del cos tècnic · rendiment, partit, jugadors, físic i assistent IA</div>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    score_card("Partits", safe_int(overview.get("matches")), "Historial disponible")
with c2:
    score_card("Plantilla", safe_int(overview.get("players")), "Jugadors registrats")
with c3:
    median_rating = ratings["match_rating_10"].median() if not ratings.empty else None
    score_card("Últim partit · mediana", "—" if median_rating is None else f"{median_rating:.1f}/10", "Match Rating descriptiu")
with c4:
    score_card("Atencions", str(len(attention)), "Flags auditables pendents de revisió")

st.write("")
left, right = st.columns([1.35, 1.0])

with left:
    st.subheader("Últim partit")
    if latest_match is None:
        st.info("No hi ha partits disponibles.")
    else:
        st.markdown(
            f"""
            <div class="fps-muted-card">
                <div class="fps-score-label">{latest_match['match_date'].date()} · {latest_match['venue']}</div>
                <div style="font-size:1.45rem;font-weight:800;color:#102a43;margin-top:.25rem;">{team_name} · {result_text(latest_match['score_for'], latest_match['score_against'])} · {latest_match['opponent']}</div>
                <div class="fps-score-sub">Formació: {latest_match['starting_formation'] or 'No disponible'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        if ratings.empty:
            st.info("Encara no hi ha Match Ratings materialitzats per l'últim partit.")
        else:
            display = ratings.copy()
            display["Perfil"] = display["position_group"].map(lambda x: "Porter" if x == "GK" else position_label(x))
            display["Rating"] = pd.to_numeric(display["match_rating_10"], errors="coerce").round(1)
            display["Confiança %"] = pd.to_numeric(display["match_rating_confidence"], errors="coerce").round(0)
            display["Min"] = pd.to_numeric(display["minutes_played"], errors="coerce").round(0)
            display = display[["player", "Perfil", "Min", "Rating", "Confiança %"]]
            display.columns = ["Jugador", "Perfil", "Min", "Rating", "Confiança %"]
            st.dataframe(display, hide_index=True, width="stretch", height=360)

with right:
    st.subheader("Centre d'atenció")
    if attention_summary.empty:
        st.success("No hi ha flags auditables actius per aquest equip.")
    else:
        summary = attention_summary.copy()
        summary["Tipus"] = summary["attention_code"].replace({
            "ROLE_CONTEXT_UNAVAILABLE": "Rol no disponible",
            "INSUFFICIENT_RATING_EVIDENCE": "Evidència insuficient",
            "GPS_QUALITY_FLAGS_PRESENT": "Qualitat GPS",
        })
        summary["Casos"] = pd.to_numeric(summary["rows"], errors="coerce").fillna(0).astype(int)
        st.dataframe(summary[["Tipus", "Casos"]], hide_index=True, width="stretch")
        st.caption("Són flags de traçabilitat/qualitat. No són diagnòstics de rendiment, fatiga ni risc de lesió.")

    st.subheader("GPS")
    if int(gps_status.get("rows", 0)) == 0:
        st.info("GPS opcional · encara no hi ha dades GPS reals importades.")
    else:
        g1, g2 = st.columns(2)
        g1.metric("Partits amb GPS", safe_int(gps_status.get("matches")))
        g2.metric("Jugadors amb GPS", safe_int(gps_status.get("players")))

st.write("")
st.subheader("Evolució de l'equip")
if rating_history.empty:
    st.info("Encara no hi ha historial de Match Rating.")
else:
    history = rating_history.copy()
    history["match_date"] = pd.to_datetime(history["match_date"])
    st.line_chart(history.set_index("match_date")[["median_match_rating"]], height=280, width="stretch")
    st.caption("Mediana descriptiva del Match Rating dels jugadors utilitzats en cada partit. No és una alerta ni una qualificació global de l'equip.")

st.write("")
st.subheader("Accés ràpid")
q1, q2, q3, q4 = st.columns(4)
with q1:
    st.page_link("pages/3_Equip.py", label="Equip", icon="🏟️", width="stretch")
    st.page_link("pages/2_Jugador.py", label="Jugadors", icon="👤", width="stretch")
with q2:
    st.page_link("pages/4_Partit.py", label="Partit", icon="⚽", width="stretch")
    st.page_link("pages/1_Performance_Index.py", label="Performance Index", icon="📈", width="stretch")
with q3:
    st.page_link("pages/6_Fisic_GPS.py", label="Físic / GPS", icon="📡", width="stretch")
    st.page_link("pages/7_Alertes.py", label="Alertes", icon="🚩", width="stretch")
with q4:
    st.page_link("pages/5_Assistent_IA.py", label="Assistent IA", icon="💬", width="stretch")

with st.expander("Metodologia i límits"):
    st.write("La home només consumeix dades i analytics ja materialitzats. No recalcula Match Ratings ni Performance Index.")
    st.write("Les alertes mostrades són estats auditables de qualitat/context. No s'han creat llindars de fatiga, risc de lesió, readiness ni rendiment bo/dolent.")
    st.write("GPS continua sent opcional i el producte principal funciona sense aquesta font.")
