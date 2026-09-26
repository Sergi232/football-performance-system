"""Professional optional physical/GPS dashboard view."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import get_squad_summary, get_team_matches, list_teams
from app.gps_physical_access import (
    PHYSICAL_SUMMARY_VERSION,
    get_gps_summary_status,
    get_match_gps_summary,
    get_player_gps_history,
    get_team_gps_match_coverage,
    get_team_latest_gps_snapshot,
)
from app.ui_theme import apply_professional_theme, score_card

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(page_title="Físic / GPS · Football Performance System", page_icon="⚡", layout="wide")
apply_professional_theme()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def km(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value) / 1000.0:.2f} km"


def kmh(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value) * 3.6:.1f} km/h"


def accel(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.2f} m/s²"


def seconds(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value) / 60.0:.1f} min"


path = db_path()
if not path.exists():
    st.error(f"No s'ha trobat la base de dades: {path}")
    st.stop()

teams = list_teams(path)
if teams.empty:
    st.info("No hi ha equips disponibles.")
    st.stop()

st.markdown("<div class='fps-kicker'>PHYSICAL PERFORMANCE</div>", unsafe_allow_html=True)
st.title("Físic / GPS")
st.caption("Capa GPS opcional. Mostra agregats descriptius de dades normalitzades; no calcula fatiga, càrrega ni zones de sprint sense validació.")

team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
team_id = st.selectbox("Equip", options=list(team_labels), format_func=lambda x: team_labels[x])

status = get_gps_summary_status(path)
if not status["table_available"]:
    st.warning("La capa física encara no està materialitzada. Executa `python analytics\\build_gps_physical_summary.py --db $env:FPS_DB_PATH`.")
    st.stop()

if status["rows"] == 0:
    st.info(
        "No hi ha observacions GPS importades en aquesta base de dades. És correcte: GPS és opcional. "
        "Quan s'importi un fitxer real amb GPS-01, aquesta vista mostrarà automàticament els agregats físics disponibles."
    )
    c1, c2, c3 = st.columns(3)
    score_card("Imports GPS", str(status["imports"]), "Fitxers normalitzats disponibles")
    with c2:
        score_card("Partits amb GPS", str(status["matches"]), "Cobertura actual")
    with c3:
        score_card("Jugadors amb GPS", str(status["players"]), "Cobertura actual")
    with st.expander("Què mostrarà aquesta capa quan hi hagi GPS?"):
        st.write("Distància observada, velocitat màxima observada, acceleració màxima, desacceleració màxima, durada observada i cobertura de canals GPS.")
        st.write("No s'han definit encara zones HSR, sprints, càrrega, fatiga o readiness.")
    st.stop()

coverage = get_team_gps_match_coverage(path, team_id)
snapshot = get_team_latest_gps_snapshot(path, team_id)
squad = get_squad_summary(path, team_id)
matches = get_team_matches(path, team_id)

tab_team, tab_player, tab_match, tab_method = st.tabs(["Equip", "Jugador", "Partit", "Metodologia"])

with tab_team:
    gps_matches = coverage.loc[coverage["gps_players"] > 0].copy() if not coverage.empty else pd.DataFrame()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        score_card("Partits amb GPS", str(len(gps_matches)), "GPS disponible")
    with c2:
        score_card("Jugadors amb GPS", str(snapshot["player_id"].nunique()) if not snapshot.empty else "0", "Última observació disponible")
    with c3:
        latest_cov = gps_matches.iloc[0]["gps_player_coverage_pct"] if not gps_matches.empty else None
        score_card("Cobertura últim partit GPS", "—" if latest_cov is None or pd.isna(latest_cov) else f"{latest_cov:.0f}%", "Jugadors amb GPS / participants")
    with c4:
        score_card("Versió", "v0.1", "Agregats descriptius")

    st.subheader("Cobertura GPS per partit")
    if gps_matches.empty:
        st.info("Aquest equip encara no té partits amb GPS.")
    else:
        show = gps_matches.copy()
        show["match_date"] = pd.to_datetime(show["match_date"]).dt.date
        show["gps_player_coverage_pct"] = pd.to_numeric(show["gps_player_coverage_pct"], errors="coerce").round(0)
        show = show[["match_date", "opponent", "venue", "played_players", "gps_players", "gps_player_coverage_pct"]]
        show.columns = ["Data", "Rival", "L/V", "Participants", "Amb GPS", "Cobertura %"]
        st.dataframe(show, hide_index=True, use_container_width=True)

    st.subheader("Última observació física per jugador")
    if snapshot.empty:
        st.info("No hi ha dades GPS d'aquest equip.")
    else:
        show = snapshot.copy()
        show["match_date"] = pd.to_datetime(show["match_date"]).dt.date
        show["Distància km"] = pd.to_numeric(show["total_distance_m"], errors="coerce") / 1000.0
        show["Vel. màx km/h"] = pd.to_numeric(show["peak_speed_m_s"], errors="coerce") * 3.6
        show["Accel. màx"] = pd.to_numeric(show["max_acceleration_m_s2"], errors="coerce")
        show["Decel. màx"] = pd.to_numeric(show["min_acceleration_m_s2"], errors="coerce")
        show = show[["player", "match_date", "Distància km", "Vel. màx km/h", "Accel. màx", "Decel. màx"]]
        show.columns = ["Jugador", "Data", "Distància km", "Vel. màx km/h", "Accel. màx m/s²", "Decel. màx m/s²"]
        st.dataframe(show.round(2), hide_index=True, use_container_width=True)

with tab_player:
    player_labels = {str(r.player_id): str(r.player) for r in squad.itertuples(index=False)}
    player_id = st.selectbox("Jugador", options=list(player_labels), format_func=lambda x: player_labels[x], key="gps_player")
    history = get_player_gps_history(path, team_id, player_id)
    if history.empty:
        st.info("Aquest jugador no té dades GPS importades.")
    else:
        latest = history.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            score_card("Distància", km(latest["total_distance_m"]), "Suma de distància incremental observada")
        with c2:
            score_card("Velocitat màxima", kmh(latest["peak_speed_m_s"]), "Màxim observat")
        with c3:
            score_card("Acceleració màxima", accel(latest["max_acceleration_m_s2"]), "Màxim observat")
        with c4:
            score_card("Desacceleració màxima", accel(latest["min_acceleration_m_s2"]), "Mínim observat")

        st.caption(f"Durada GPS observada: {seconds(latest['observation_duration_s'])} · Proveïdor: {latest.get('provider') or '—'}")

        left, right = st.columns(2)
        hist = history.copy()
        hist["match_date"] = pd.to_datetime(hist["match_date"])
        with left:
            st.subheader("Evolució distància")
            chart = hist.dropna(subset=["total_distance_m"]).copy()
            if not chart.empty:
                chart["distance_km"] = chart["total_distance_m"] / 1000.0
                st.line_chart(chart.set_index("match_date")[["distance_km"]], height=280, use_container_width=True)
        with right:
            st.subheader("Evolució velocitat màxima")
            chart = hist.dropna(subset=["peak_speed_m_s"]).copy()
            if not chart.empty:
                chart["peak_speed_kmh"] = chart["peak_speed_m_s"] * 3.6
                st.line_chart(chart.set_index("match_date")[["peak_speed_kmh"]], height=280, use_container_width=True)

        st.subheader("Historial GPS")
        show = history.copy()
        show["match_date"] = pd.to_datetime(show["match_date"]).dt.date
        show["distance_km"] = pd.to_numeric(show["total_distance_m"], errors="coerce") / 1000.0
        show["speed_kmh"] = pd.to_numeric(show["peak_speed_m_s"], errors="coerce") * 3.6
        show = show[["match_date", "opponent", "venue", "distance_km", "speed_kmh", "max_acceleration_m_s2", "min_acceleration_m_s2", "sample_count"]]
        show.columns = ["Data", "Rival", "L/V", "Distància km", "Vel. màx km/h", "Accel. màx", "Decel. màx", "Mostres"]
        st.dataframe(show.round(2), hide_index=True, use_container_width=True)

with tab_match:
    gps_match_ids = coverage.loc[coverage["gps_players"] > 0, "match_id"].astype(str).tolist() if not coverage.empty else []
    if not gps_match_ids:
        st.info("Aquest equip no té partits amb GPS.")
    else:
        matches2 = matches.copy()
        matches2["match_date"] = pd.to_datetime(matches2["match_date"])
        match_rows = matches2.loc[matches2["match_id"].astype(str).isin(gps_match_ids)].copy()
        match_map = {str(r.match_id): f"{r.match_date.date()} · {r.opponent}" for r in match_rows.itertuples(index=False)}
        match_id = st.selectbox("Partit amb GPS", options=list(match_map), format_func=lambda x: match_map[x], key="gps_match")
        physical = get_match_gps_summary(path, team_id, match_id)
        show = physical.copy()
        show["Distància km"] = pd.to_numeric(show["total_distance_m"], errors="coerce") / 1000.0
        show["Vel. màx km/h"] = pd.to_numeric(show["peak_speed_m_s"], errors="coerce") * 3.6
        show = show[["player", "Distància km", "Vel. màx km/h", "max_acceleration_m_s2", "min_acceleration_m_s2", "sample_count", "provider"]]
        show.columns = ["Jugador", "Distància km", "Vel. màx km/h", "Accel. màx", "Decel. màx", "Mostres", "Proveïdor"]
        st.dataframe(show.round(2), hide_index=True, use_container_width=True)

with tab_method:
    st.subheader("Contracte físic actual")
    st.write(f"Versió: `{PHYSICAL_SUMMARY_VERSION}`")
    st.write("La distància és la suma de `distance_m`, que GPS-01 defineix com a distància incremental per mostra.")
    st.write("Velocitat, acceleració i desacceleració són màxims/mínims observats als camps canònics normalitzats.")
    st.write("La cobertura mostra quantes mostres tenen cada canal disponible; no és una nota de qualitat del jugador.")
    st.warning("Encara NO s'han definit zones de velocitat, HSR, sprints, càrrega, fatiga ni readiness. Aquestes mètriques necessiten definició i validació pròpies.")
