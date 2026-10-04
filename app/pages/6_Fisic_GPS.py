"""Vista profesional de la capa física/GPS opcional."""
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
from app.presentation import (
    anonymize_frame,
    build_opponent_aliases,
    build_player_aliases,
    build_player_name_aliases,
    display_opponent,
    display_player_name,
    display_team_name,
)
from app.ui_theme import apply_professional_theme, sidebar_navigation

DEFAULT_DB = ROOT / "data" / "football_performance_synthetic_demo.duckdb"
SYNTHETIC_PROVIDER = "FPS Synthetic Demo"
VENUE_LABELS = {"H": "L", "A": "V", "Home": "L", "Away": "V", "Local": "L", "Visitante": "V"}

st.set_page_config(page_title="Físico / GPS · Football Performance System", page_icon="📡", layout="wide")
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


def venue_short(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return VENUE_LABELS.get(str(value), str(value))


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
display_team_labels = {tid: display_team_name(raw_team_labels[tid], team_ids.index(tid) + 1) for tid in team_ids}
team_id = st.selectbox("Equipo", options=team_ids, format_func=lambda x: display_team_labels[x])

page_header(
    "RENDIMIENTO FÍSICO · GPS OPCIONAL",
    "Físico / GPS",
    "Capa descriptiva sobre datos GPS normalizados. No estima fatiga, carga ni disponibilidad física sin una definición validada.",
    PHYSICAL_SUMMARY_VERSION,
)

status = get_gps_summary_status(path)
if not status["table_available"]:
    st.warning("La capa física todavía no está materializada. Ejecuta `python analytics\\build_gps_physical_summary.py --db $env:FPS_DB_PATH`.")
    st.stop()

if status["rows"] == 0:
    st.info("No hay observaciones GPS importadas en esta base. Es correcto: el GPS es complementario y el producto principal funciona sin esta fuente.")
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Importaciones GPS", str(status["imports"]), "Ficheros normalizados disponibles")
    with c2:
        metric_card("Partidos con GPS", str(status["matches"]), "Cobertura actual")
    with c3:
        metric_card("Jugadores con GPS", str(status["players"]), "Cobertura actual")
    with st.expander("¿Qué mostrará esta capa cuando haya GPS?"):
        st.write("Distancia observada, velocidad máxima, aceleración máxima, desaceleración máxima, duración observada y cobertura de canales.")
        st.write("Todavía no se han definido zonas HSR, esprints, carga, fatiga o disponibilidad física.")
    st.stop()

coverage = get_team_gps_match_coverage(path, team_id)
snapshot = get_team_latest_gps_snapshot(path, team_id)
squad = get_squad_summary(path, team_id)
matches = get_team_matches(path, team_id)
player_aliases = build_player_aliases(squad)
player_name_aliases = build_player_name_aliases(squad)
opponent_aliases = build_opponent_aliases(matches.get("opponent", pd.Series(dtype=str)).tolist())
snapshot = anonymize_frame(snapshot, player_aliases_by_id=player_aliases, player_name_aliases=player_name_aliases, opponent_aliases=opponent_aliases)
if not coverage.empty and "opponent" in coverage.columns:
    coverage = coverage.copy()
    coverage["opponent"] = coverage["opponent"].map(lambda x: display_opponent(x, opponent_aliases))

if not snapshot.empty and "provider" in snapshot.columns and SYNTHETIC_PROVIDER in set(snapshot["provider"].dropna().astype(str)):
    st.warning(
        "DATOS DEMO · GPS sintético. Estos valores se han generado para demostrar el flujo del producto; "
        "no son observaciones reales de los jugadores y no validan fatiga, disponibilidad física ni riesgo de lesión."
    )

tab_team, tab_player, tab_match, tab_method = st.tabs(["Equipo", "Jugador", "Partido", "Metodología"])

with tab_team:
    gps_matches = coverage.loc[coverage["gps_players"] > 0].copy() if not coverage.empty else pd.DataFrame()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Partidos con GPS", str(len(gps_matches)), "GPS disponible")
    with c2:
        metric_card("Jugadores con GPS", str(snapshot["player_id"].nunique()) if not snapshot.empty else "0", "Última observación")
    with c3:
        latest_cov = gps_matches.iloc[0]["gps_player_coverage_pct"] if not gps_matches.empty else None
        metric_card("Cobertura último GPS", "—" if latest_cov is None or pd.isna(latest_cov) else f"{latest_cov:.0f}%", "Jugadores con GPS / participantes")
    with c4:
        metric_card("Versión", "v0.1", "Agregados descriptivos")

    section_header("Cobertura GPS por partido")
    if gps_matches.empty:
        st.info("Este equipo todavía no tiene partidos con GPS.")
    else:
        show = gps_matches.copy()
        show["match_date"] = pd.to_datetime(show["match_date"]).dt.date
        show["venue"] = show["venue"].map(venue_short)
        show["gps_player_coverage_pct"] = pd.to_numeric(show["gps_player_coverage_pct"], errors="coerce").round(0)
        show = show[["match_date", "opponent", "venue", "played_players", "gps_players", "gps_player_coverage_pct"]]
        show.columns = ["Fecha", "Rival", "L/V", "Participantes", "Con GPS", "Cobertura %"]
        st.dataframe(show, hide_index=True, width="stretch")

    section_header("Última observación física por jugador")
    if snapshot.empty:
        st.info("No hay datos GPS de este equipo.")
    else:
        show = snapshot.copy()
        show["match_date"] = pd.to_datetime(show["match_date"]).dt.date
        show["Distancia km"] = pd.to_numeric(show["total_distance_m"], errors="coerce") / 1000.0
        show["Vel. máx km/h"] = pd.to_numeric(show["peak_speed_m_s"], errors="coerce") * 3.6
        show["Acel. máx"] = pd.to_numeric(show["max_acceleration_m_s2"], errors="coerce")
        show["Decel. máx"] = pd.to_numeric(show["min_acceleration_m_s2"], errors="coerce")
        show = show[["player", "match_date", "Distancia km", "Vel. máx km/h", "Acel. máx", "Decel. máx"]]
        show.columns = ["Jugador", "Fecha", "Distancia km", "Vel. máx km/h", "Acel. máx m/s²", "Decel. máx m/s²"]
        st.dataframe(show.round(2), hide_index=True, width="stretch")

with tab_player:
    raw_player_labels = {str(r.player_id): str(r.player) for r in squad.itertuples(index=False)}
    player_id = st.selectbox(
        "Jugador",
        options=list(raw_player_labels),
        format_func=lambda x: display_player_name(x, raw_player_labels[x], player_aliases),
        key="gps_player",
    )
    history = get_player_gps_history(path, team_id, player_id)
    if history.empty:
        st.info("Este jugador no tiene datos GPS importados.")
    else:
        latest = history.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Distancia", km(latest["total_distance_m"]), "Suma incremental observada")
        with c2:
            metric_card("Velocidad máxima", kmh(latest["peak_speed_m_s"]), "Máximo observado")
        with c3:
            metric_card("Aceleración máxima", accel(latest["max_acceleration_m_s2"]), "Máximo observado")
        with c4:
            metric_card("Desaceleración máxima", accel(latest["min_acceleration_m_s2"]), "Mínimo observado")
        st.caption(f"Duración GPS observada: {seconds(latest['observation_duration_s'])} · Proveedor: {latest.get('provider') or '—'}")

        left, right = st.columns(2)
        hist = history.copy()
        hist["match_date"] = pd.to_datetime(hist["match_date"])
        with left:
            section_header("Evolución de distancia")
            chart = hist.dropna(subset=["total_distance_m"]).copy()
            if not chart.empty:
                chart["distance_km"] = chart["total_distance_m"] / 1000.0
                st.line_chart(chart.set_index("match_date")[["distance_km"]], height=280, width="stretch")
        with right:
            section_header("Evolución de velocidad máxima")
            chart = hist.dropna(subset=["peak_speed_m_s"]).copy()
            if not chart.empty:
                chart["peak_speed_kmh"] = chart["peak_speed_m_s"] * 3.6
                st.line_chart(chart.set_index("match_date")[["peak_speed_kmh"]], height=280, width="stretch")

        section_header("Historial GPS")
        show = history.copy()
        show["match_date"] = pd.to_datetime(show["match_date"]).dt.date
        if "opponent" in show.columns:
            show["opponent"] = show["opponent"].map(lambda x: display_opponent(x, opponent_aliases))
        if "venue" in show.columns:
            show["venue"] = show["venue"].map(venue_short)
        show["distance_km"] = pd.to_numeric(show["total_distance_m"], errors="coerce") / 1000.0
        show["speed_kmh"] = pd.to_numeric(show["peak_speed_m_s"], errors="coerce") * 3.6
        show = show[["match_date", "opponent", "venue", "distance_km", "speed_kmh", "max_acceleration_m_s2", "min_acceleration_m_s2", "sample_count"]]
        show.columns = ["Fecha", "Rival", "L/V", "Distancia km", "Vel. máx km/h", "Acel. máx", "Decel. máx", "Muestras"]
        st.dataframe(show.round(2), hide_index=True, width="stretch")

with tab_match:
    gps_match_ids = coverage.loc[coverage["gps_players"] > 0, "match_id"].astype(str).tolist() if not coverage.empty else []
    if not gps_match_ids:
        st.info("Este equipo no tiene partidos con GPS.")
    else:
        matches2 = matches.copy()
        matches2["match_date"] = pd.to_datetime(matches2["match_date"])
        match_rows = matches2.loc[matches2["match_id"].astype(str).isin(gps_match_ids)].copy()
        match_map = {str(r.match_id): f"{r.match_date.date()} · {display_opponent(r.opponent, opponent_aliases)}" for r in match_rows.itertuples(index=False)}
        match_id = st.selectbox("Partido con GPS", options=list(match_map), format_func=lambda x: match_map[x], key="gps_match")
        physical = anonymize_frame(
            get_match_gps_summary(path, team_id, match_id),
            player_aliases_by_id=player_aliases,
            player_name_aliases=player_name_aliases,
            opponent_aliases=opponent_aliases,
        )
        show = physical.copy()
        show["Distancia km"] = pd.to_numeric(show["total_distance_m"], errors="coerce") / 1000.0
        show["Vel. máx km/h"] = pd.to_numeric(show["peak_speed_m_s"], errors="coerce") * 3.6
        show = show[["player", "Distancia km", "Vel. máx km/h", "max_acceleration_m_s2", "min_acceleration_m_s2", "sample_count", "provider"]]
        show.columns = ["Jugador", "Distancia km", "Vel. máx km/h", "Acel. máx", "Decel. máx", "Muestras", "Proveedor"]
        st.dataframe(show.round(2), hide_index=True, width="stretch")

with tab_method:
    section_header("Contrato físico actual")
    st.write(f"Versión técnica: `{PHYSICAL_SUMMARY_VERSION}`")
    st.write("La distancia es la suma de `distance_m`, definida como distancia incremental por muestra.")
    st.write("Velocidad, aceleración y desaceleración son máximos y mínimos observados en los campos canónicos normalizados.")
    st.write("La cobertura muestra cuántas muestras tienen cada canal disponible; no es una nota de calidad del jugador.")
    st.warning("Todavía NO se han definido zonas de velocidad, HSR, esprints, carga, fatiga ni disponibilidad física.")
