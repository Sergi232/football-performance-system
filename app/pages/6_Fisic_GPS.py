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

from app.coach_ui import metric_card, page_header, section_header
from app.data_access import get_squad_summary, get_team_matches, list_teams
from app.gps_physical_access import (
    PHYSICAL_SUMMARY_VERSION,
    get_gps_summary_status,
    get_match_gps_summary,
    get_player_gps_history,
    get_team_gps_match_coverage,
    get_team_latest_gps_snapshot,
)
from app.ui_theme import apply_professional_theme, sidebar_navigation

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(page_title="Físic / GPS · Football Performance System", page_icon="📡", layout="wide")
apply_professional_theme()
sidebar_navigation()


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

team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
team_id = st.selectbox("Equip", options=list(team_labels), format_func=lambda x: team_labels[x])

page_header(
    "PHYSICAL PERFORMANCE · GPS OPCIONAL",
    "Físic / GPS",
    "Capa descriptiva sobre dades GPS normalitzades. No estima fatiga, càrrega ni readiness sense una definició validada.",
    PHYSICAL_SUMMARY_VERSION,
)

status = get_gps_summary_status(path)
if not status["table_available"]:
    st.warning("La capa física encara no està materialitzada. Executa `python analytics\\build_gps_physical_summary.py --db $env:FPS_DB_PATH`.")
    st.stop()

if status["rows"] == 0:
    st.info("No hi ha observacions GPS importades en aquesta base. És correcte: el GPS és complementari i el producte principal funciona sense aquesta font.")
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Imports GPS", str(status["imports"]), "Fitxers normalitzats disponibles")
    with c2:
        metric_card("Partits amb GPS", str(status["matches"]), "Cobertura actual")
    with c3:
        metric_card("Jugadors amb GPS", str(status["players"]), "Cobertura actual")
    with st.expander("Què mostrarà aquesta capa quan hi hagi GPS?"):
        st.write("Distància observada, velocitat màxima, acceleració màxima, desacceleració màxima, durada observada i cobertura de canals.")
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
        metric_card("Partits amb GPS", str(len(gps_matches)), "GPS disponible")
    with c2:
        metric_card("Jugadors amb GPS", str(snapshot["player_id"].nunique()) if not snapshot.empty else "0", "Última observació")
    with c3:
        latest_cov = gps_matches.iloc[0]["gps_player_coverage_pct"] if not gps_matches.empty else None
        metric_card("Cobertura últim GPS", "—" if latest_cov is None or pd.isna(latest_cov) else f"{latest_cov:.0f}%", "Jugadors amb GPS / participants")
    with c4:
        metric_card("Versió", "v0.1", "Agregats descriptius")

    section_header("Cobertura GPS per partit")
    if gps_matches.empty:
        st.info("Aquest equip encara no té partits amb GPS.")
    else:
        show = gps_matches.copy()
        show["match_date"] = pd.to_datetime(show["match_date"]).dt.date
        show["gps_player_coverage_pct"] = pd.to_numeric(show["gps_player_coverage_pct"], errors="coerce").round(0)
        show = show[["match_date", "opponent", "venue", "played_players", "gps_players", "gps_player_coverage_pct"]]
        show.columns = ["Data", "Rival", "L/V", "Participants", "Amb GPS", "Cobertura %"]
        st.dataframe(show, hide_index=True, width="stretch")

    section_header("Última observació física per jugador")
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
        st.dataframe(show.round(2), hide_index=True, width="stretch")

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
            metric_card("Distància", km(latest["total_distance_m"]), "Suma incremental observada")
        with c2:
            metric_card("Velocitat màxima", kmh(latest["peak_speed_m_s"]), "Màxim observat")
        with c3:
            metric_card("Acceleració màxima", accel(latest["max_acceleration_m_s2"]), "Màxim observat")
        with c4:
            metric_card("Desacceleració màxima", accel(latest["min_acceleration_m_s2"]), "Mínim observat")
        st.caption(f"Durada GPS observada: {seconds(latest['observation_duration_s'])} · Proveïdor: {latest.get('provider') or '—'}")

        left, right = st.columns(2)
        hist = history.copy()
        hist["match_date"] = pd.to_datetime(hist["match_date"])
        with left:
            section_header("Evolució distància")
            chart = hist.dropna(subset=["total_distance_m"]).copy()
            if not chart.empty:
                chart["distance_km"] = chart["total_distance_m"] / 1000.0
                st.line_chart(chart.set_index("match_date")[["distance_km"]], height=280, width="stretch")
        with right:
            section_header("Evolució velocitat màxima")
            chart = hist.dropna(subset=["peak_speed_m_s"]).copy()
            if not chart.empty:
                chart["peak_speed_kmh"] = chart["peak_speed_m_s"] * 3.6
                st.line_chart(chart.set_index("match_date")[["peak_speed_kmh"]], height=280, width="stretch")

        section_header("Historial GPS")
        show = history.copy()
        show["match_date"] = pd.to_datetime(show["match_date"]).dt.date
        show["distance_km"] = pd.to_numeric(show["total_distance_m"], errors="coerce") / 1000.0
        show["speed_kmh"] = pd.to_numeric(show["peak_speed_m_s"], errors="coerce") * 3.6
        show = show[["match_date", "opponent", "venue", "distance_km", "speed_kmh", "max_acceleration_m_s2", "min_acceleration_m_s2", "sample_count"]]
        show.columns = ["Data", "Rival", "L/V", "Distància km", "Vel. màx km/h", "Accel. màx", "Decel. màx", "Mostres"]
        st.dataframe(show.round(2), hide_index=True, width="stretch")

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
        st.dataframe(show.round(2), hide_index=True, width="stretch")

with tab_method:
    section_header("Contracte físic actual")
    st.write(f"Versió: `{PHYSICAL_SUMMARY_VERSION}`")
    st.write("La distància és la suma de `distance_m`, definida com a distància incremental per mostra.")
    st.write("Velocitat, acceleració i desacceleració són màxims/mínims observats als camps canònics normalitzats.")
    st.write("La cobertura mostra quantes mostres tenen cada canal disponible; no és una nota de qualitat del jugador.")
    st.warning("Encara NO s'han definit zones de velocitat, HSR, sprints, càrrega, fatiga ni readiness.")
