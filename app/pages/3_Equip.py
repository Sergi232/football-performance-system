"""DASHBOARD-03 — professional Team Mode for coaching staff."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import get_squad_summary, get_team_matches, get_team_overview, list_teams
from app.match_rating_access import (
    MATCH_RATING_VERSION,
    get_latest_team_match_ratings,
    get_team_match_rating_history,
    get_team_player_rating_snapshot,
)
from app.performance_score_access import SCORE_VERSION, get_team_score_snapshot
from app.ui_theme import apply_professional_theme, position_label, score_card
from reports.data_builder import build_team_report_data
from reports.pdf_engine import render_pdf_bytes

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(page_title="Equip · Football Performance System", page_icon="⚽", layout="wide")
apply_professional_theme()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def safe_int(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{int(value):,}".replace(",", ".")


def safe_float(value: object, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{digits}f}"


def render_team_pdf(path: Path, team_id: str, team_name: str) -> None:
    try:
        payload = build_team_report_data(path, team_id)
        pdf_bytes = render_pdf_bytes(payload)
    except Exception as exc:
        st.warning(f"No s'ha pogut generar l'informe: {exc}")
        return
    filename = "_".join(team_name.strip().split()) or "team"
    st.download_button(
        "Exportar informe PDF",
        data=pdf_bytes,
        file_name=f"team_{filename}.pdf",
        mime="application/pdf",
        width="stretch",
    )


def result_text(score_for: object, score_against: object) -> str:
    if pd.isna(score_for) or pd.isna(score_against):
        return "—"
    sf = int(score_for)
    sa = int(score_against)
    outcome = "V" if sf > sa else "E" if sf == sa else "D"
    return f"{outcome} {sf}-{sa}"


path = db_path()
if not path.exists():
    st.error(f"No s'ha trobat la base de dades: {path}")
    st.stop()

teams = list_teams(path)
if teams.empty:
    st.info("No hi ha equips disponibles.")
    st.stop()

selector, action = st.columns([3.0, 1.0])
team_labels = {str(row.team_id): str(row.display_name) for row in teams.itertuples(index=False)}
with selector:
    team_id = st.selectbox("Equip", options=list(team_labels), format_func=lambda x: team_labels[x])
team_name = team_labels[team_id]
with action:
    st.write("")
    st.write("")
    render_team_pdf(path, team_id, team_name)

overview = get_team_overview(path, team_id)
squad = get_squad_summary(path, team_id)
matches = get_team_matches(path, team_id)

try:
    latest_match_ratings = get_latest_team_match_ratings(path, team_id)
    rating_snapshot = get_team_player_rating_snapshot(path, team_id)
    rating_history = get_team_match_rating_history(path, team_id)
except Exception:
    latest_match_ratings = pd.DataFrame()
    rating_snapshot = pd.DataFrame()
    rating_history = pd.DataFrame()

try:
    performance_snapshot = get_team_score_snapshot(path, team_id)
except Exception:
    performance_snapshot = pd.DataFrame()

st.markdown(
    f"""
    <div class="fps-hero">
        <div class="fps-kicker">TEAM MODE</div>
        <div class="fps-player-name">{team_name}</div>
        <div class="fps-player-meta">{safe_int(overview['matches'])} partits · {safe_int(overview['players'])} jugadors · seguiment operatiu del rendiment</div>
    </div>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Partits", safe_int(overview["matches"]))
k2.metric("Jugadors", safe_int(overview["players"]))
k3.metric("Minuts jugador", safe_int(overview["player_minutes"]))
k4.metric("Gols", safe_int(overview["goals"]))
k5.metric("Assistències", safe_int(overview["assists"]))

st.write("")
tab_overview, tab_squad, tab_trends, tab_index, tab_matches = st.tabs(
    ["Resum", "Plantilla", "Evolució", "Performance Index", "Partits"]
)

with tab_overview:
    if latest_match_ratings.empty:
        st.info("La capa de Match Rating encara no està disponible per aquest equip.")
    else:
        median_rating = pd.to_numeric(latest_match_ratings["match_rating_10"], errors="coerce").median()
        median_conf = pd.to_numeric(latest_match_ratings["match_rating_confidence"], errors="coerce").median()
        latest_players = len(latest_match_ratings)
        latest_date = rating_snapshot["latest_rating_date"].max() if not rating_snapshot.empty else None

        c1, c2, c3 = st.columns(3)
        with c1:
            score_card("Últim partit · rating mediana", f"{safe_float(median_rating)}/10", "Resum player-match del partit més recent")
        with c2:
            score_card("Jugadors valorats", str(latest_players), "Participants amb minuts a l'últim partit")
        with c3:
            score_card("Confiança mediana", f"{safe_float(median_conf)}%", "Cobertura d'evidència de l'últim partit")

        left, right = st.columns([1.25, 1])
        with left:
            st.subheader("Últim Match Rating per jugador")
            chart = rating_snapshot[["player", "latest_match_rating"]].dropna().sort_values("player") if not rating_snapshot.empty else pd.DataFrame()
            if chart.empty:
                st.info("No hi ha ratings disponibles.")
            else:
                st.bar_chart(chart.set_index("player")[["latest_match_rating"]], height=420, width="stretch")
                if latest_date is not None and not pd.isna(latest_date):
                    st.caption(f"Última data amb rating: {pd.to_datetime(latest_date).date()}")

        with right:
            st.subheader("Últims partits")
            recent_matches = matches.head(8).copy()
            if recent_matches.empty:
                st.info("No hi ha partits disponibles.")
            else:
                recent_matches["match_date"] = pd.to_datetime(recent_matches["match_date"]).dt.date
                recent_matches["result"] = recent_matches.apply(lambda r: result_text(r["score_for"], r["score_against"]), axis=1)
                recent_matches = recent_matches[["match_date", "venue", "opponent", "result", "starting_formation"]]
                recent_matches.columns = ["Data", "L/V", "Rival", "Resultat", "Formació"]
                st.dataframe(recent_matches, hide_index=True, width="stretch")

with tab_squad:
    st.subheader("Plantilla")
    st.caption("Participació + Match Rating operatiu. El rating existeix des de la primera aparició amb minuts.")
    roster = squad.merge(rating_snapshot, on=["player_id", "player"], how="left") if not rating_snapshot.empty else squad.copy()
    if "latest_position_group" in roster.columns:
        roster["latest_position_group"] = roster["latest_position_group"].map(lambda x: "Porter" if x == "GK" else position_label(x))
    for col in ["latest_match_rating", "latest_confidence", "avg_last5", "avg_previous5", "trend_delta_5v5"]:
        if col in roster.columns:
            roster[col] = pd.to_numeric(roster[col], errors="coerce").round(1)
    wanted = [
        "player", "observed_roles", "appearances", "starts", "minutes",
        "latest_position_group", "latest_match_rating", "latest_confidence", "avg_last5", "trend_delta_5v5",
    ]
    for col in wanted:
        if col not in roster.columns:
            roster[col] = pd.NA
    roster = roster[wanted].sort_values(["minutes", "player"], ascending=[False, True])
    roster.columns = [
        "Jugador", "Rols observats", "Aparicions", "Titularitats", "Minuts",
        "Perfil últim partit", "Match Rating", "Confiança %", "Mitjana últims 5", "Delta 5 vs 5",
    ]
    st.dataframe(roster, hide_index=True, width="stretch")

with tab_trends:
    st.subheader("Evolució del rendiment")
    st.caption("El Match Rating és player-match. L'historial posterior permet estudiar forma i tendència sense afectar la nota original del partit.")

    if not rating_history.empty:
        timeline = rating_history.copy()
        timeline["match_date"] = pd.to_datetime(timeline["match_date"])
        st.markdown("#### Mediana de Match Rating per partit")
        st.line_chart(timeline.set_index("match_date")[["median_match_rating"]], height=300, width="stretch")

    if rating_snapshot.empty:
        st.info("No hi ha historial de ratings disponible.")
    else:
        trend = rating_snapshot.copy()
        trend["Perfil"] = trend["latest_position_group"].map(lambda x: "Porter" if x == "GK" else position_label(x))
        for col in ["latest_match_rating", "avg_last5", "avg_previous5", "trend_delta_5v5"]:
            trend[col] = pd.to_numeric(trend[col], errors="coerce").round(1)
        trend = trend[[
            "player", "Perfil", "rated_matches", "latest_match_rating", "avg_last5",
            "avg_previous5", "trend_delta_5v5", "n_last5", "n_previous5",
        ]].sort_values("player")
        trend.columns = [
            "Jugador", "Perfil", "Partits amb rating", "Rating actual", "Mitjana últims 5",
            "Mitjana 5 anteriors", "Delta 5 vs 5", "N últims", "N anteriors",
        ]
        st.dataframe(trend, hide_index=True, width="stretch")

with tab_index:
    st.subheader("Performance Index")
    st.caption("Capa històrica/posicional complementària. No és la nota del partit.")
    if performance_snapshot.empty:
        st.info("No hi ha Performance Index disponible.")
    else:
        index_table = performance_snapshot.copy()
        index_table["Perfil"] = index_table["position_group"].map(position_label)
        for col in ["latest_score", "latest_confidence", "avg_last5", "trend_delta_5v5"]:
            index_table[col] = pd.to_numeric(index_table[col], errors="coerce").round(1)
        index_table = index_table[["player", "Perfil", "latest_score", "latest_confidence", "avg_last5", "trend_delta_5v5"]]
        index_table.columns = ["Jugador", "Perfil", "Performance Index", "Confiança %", "Mitjana últims 5", "Delta 5 vs 5"]
        st.dataframe(index_table, hide_index=True, width="stretch")

with tab_matches:
    st.subheader("Partits")
    if matches.empty:
        st.info("No hi ha partits disponibles.")
    else:
        display = matches.copy()
        display["match_date"] = pd.to_datetime(display["match_date"]).dt.date
        display["result"] = display.apply(lambda r: result_text(r["score_for"], r["score_against"]), axis=1)
        display = display[["match_date", "venue", "opponent", "result", "starting_formation"]]
        display.columns = ["Data", "L/V", "Rival", "Resultat", "Formació"]
        st.dataframe(display, hide_index=True, width="stretch")

with st.expander("Metodologia i límits"):
    st.write(f"Match Rating: `{MATCH_RATING_VERSION}`. És la nota operativa player-match i funciona des del primer partit.")
    st.write(f"Performance Index: `{SCORE_VERSION}`. És una capa històrica/posicional complementària, no la nota del partit.")
    st.write("La tendència 5 vs 5 és descriptiva i no activa cap alerta automàtica ni recomanació tàctica.")
