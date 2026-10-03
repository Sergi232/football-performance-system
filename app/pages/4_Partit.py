"""Modo Partido: revisión inmediata postpartido para el cuerpo técnico."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.coach_ui import (
    dimension_chart,
    insight_card,
    metric_card,
    page_header,
    player_rating_chart,
    safe_number,
    safe_text,
    scoreboard_card,
    section_header,
)
from app.data_access import get_squad_summary, get_team_matches, list_teams
from app.match_insights import get_match_observations
from app.match_rating_access import MATCH_RATING_VERSION, get_match_ratings
from app.presentation import (
    anonymize_frame,
    build_opponent_aliases,
    build_player_aliases,
    build_player_name_aliases,
    demo_mode,
    display_opponent,
    display_team_name,
)
from app.ui_theme import apply_professional_theme, position_label, sidebar_navigation
from reports.data_builder import build_match_report_data
from reports.pdf_engine_es import render_pdf_bytes

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(page_title="Partido · Football Performance System", page_icon="⚽", layout="wide")
apply_professional_theme()
sidebar_navigation()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def result_text(sf: object, sa: object) -> str:
    if sf is None or sa is None or pd.isna(sf) or pd.isna(sa):
        return "—"
    return f"{int(sf)}-{int(sa)}"


def names_text(item: dict | None, aliases: dict[str, str]) -> str:
    if not item:
        return "—"
    players = item.get("players") or []
    value = item.get("value")
    if not players:
        return "—"
    shown = [aliases.get(str(name), str(name)) if demo_mode() else str(name) for name in players]
    suffix = "" if value is None else f" · {int(value) if float(value).is_integer() else round(float(value), 1)}"
    return ", ".join(shown) + suffix


def alias_player(name: object, aliases: dict[str, str]) -> str:
    raw = str(name or "Jugador")
    return aliases.get(raw, raw) if demo_mode() else raw


path = db_path()
if not path.exists():
    st.error(f"No se ha encontrado la base de datos: {path}")
    st.stop()

teams = list_teams(path)
raw_team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
team_ids = list(raw_team_labels)
display_team_labels = {tid: display_team_name(raw_team_labels[tid], team_ids.index(tid) + 1) for tid in team_ids}
sel_team, sel_match, action = st.columns([1.0, 2.0, .65])
with sel_team:
    team_id = st.selectbox("Equipo", options=team_ids, format_func=lambda x: display_team_labels[x])

team_name = display_team_labels[team_id]
matches = get_team_matches(path, team_id).copy()
if matches.empty:
    st.info("No hay partidos disponibles.")
    st.stop()
matches["match_date"] = pd.to_datetime(matches["match_date"])
squad = get_squad_summary(path, team_id)
player_aliases = build_player_aliases(squad)
player_name_aliases = build_player_name_aliases(squad)
opponent_aliases = build_opponent_aliases(matches.get("opponent", pd.Series(dtype=str)).tolist())

match_map = {
    str(r.match_id): f"{r.match_date.date()} · {display_opponent(r.opponent, opponent_aliases)} · {result_text(r.score_for, r.score_against)}"
    for r in matches.itertuples(index=False)
}
with sel_match:
    match_id = st.selectbox("Partido", options=list(match_map), format_func=lambda x: match_map[x])
match = matches.loc[matches["match_id"].astype(str) == match_id].iloc[0]
with action:
    st.write("")
    st.write("")
    try:
        payload = build_match_report_data(path, team_id, match_id)
        pdf_bytes = render_pdf_bytes(payload)
        st.download_button("Exportar PDF", pdf_bytes, file_name=f"match_{match_id}.pdf", mime="application/pdf", width="stretch")
    except Exception as exc:
        st.warning(f"PDF no disponible: {exc}")

ratings = anonymize_frame(
    get_match_ratings(path, team_id, match_id),
    player_aliases_by_id=player_aliases,
    player_name_aliases=player_name_aliases,
    opponent_aliases=opponent_aliases,
)
observations = get_match_observations(path, team_id, match_id)
match_opponent = display_opponent(match.get("opponent"), opponent_aliases)

page_header(
    "MODO PARTIDO · POSTPARTIDO",
    f"{team_name} vs {match_opponent}",
    "Revisión inmediata: marcador, distribución del rendimiento, observaciones y calidad de la evidencia.",
    str(pd.to_datetime(match["match_date"]).date()),
)

scoreboard_card(
    team_name,
    match_opponent,
    match.get("score_for"), match.get("score_against"),
    str(pd.to_datetime(match["match_date"]).date()),
    "Local" if match.get("venue") == "H" else "Visitante",
    safe_text(match.get("starting_formation"), "No disponible"),
)

rated = ratings.dropna(subset=["match_rating_10"]).copy()
median_rating = pd.to_numeric(rated.get("match_rating_10"), errors="coerce").median() if not rated.empty else None
median_conf = pd.to_numeric(rated.get("match_rating_confidence"), errors="coerce").median() if not rated.empty else None
fallback_rows = int((ratings["rating_path"] == "OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2").sum()) if not ratings.empty else 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    metric_card("Rating mediano", safe_number(median_rating, 2, "/10"), "Jugadores con minutos")
with k2:
    metric_card("Confianza mediana", safe_number(median_conf, 0, "%"), "Cobertura de la evidencia")
with k3:
    metric_card("Jugadores utilizados", str(len(ratings)), "Apariciones con minutos")
with k4:
    metric_card("Rol no disponible", str(fallback_rows), "Modelo de respaldo explícito, sin imputar posición")

st.write("")
tab_review, tab_players, tab_dimensions, tab_evidence = st.tabs(["Revisión técnica", "Jugadores", "Dimensiones", "Evidencia"])

with tab_review:
    chart_col, insight_col = st.columns([1.35, 1.0], gap="large")
    with chart_col:
        section_header("Distribución del Match Rating", "Todos los jugadores utilizados, escala fija 3–10")
        if ratings.empty:
            st.info("No hay ratings.")
        else:
            chart = ratings.copy()
            chart["position_group"] = chart["position_group"].map(position_label)
            st.plotly_chart(player_rating_chart(chart), width="stretch", config={"displayModeBar": False})
    with insight_col:
        section_header("Observaciones del partido", "Hechos deterministas derivados de los datos registrados")
        goal_scorers = observations.get("goal_scorers") or []
        assist_providers = observations.get("assist_providers") or []
        leaders = observations.get("leaders") or {}

        goals_text = " · ".join(f"{alias_player(x['player'], player_name_aliases)} ({x['goals']})" for x in goal_scorers) if goal_scorers else "Sin goles registrados"
        assists_text = " · ".join(f"{alias_player(x['player'], player_name_aliases)} ({x['assists']})" for x in assist_providers) if assist_providers else "Sin asistencias registradas"
        insight_card("Goles", goals_text, "Contribución directa", "positive" if goal_scorers else "neutral")
        insight_card("Asistencias", assists_text, "Contribución directa", "positive" if assist_providers else "neutral")
        insight_card("Remates", names_text(leaders.get("shots_total"), player_name_aliases), "Máximo observado", "neutral")
        insight_card("Pases completados", names_text(leaders.get("passes_completed"), player_name_aliases), "Máximo observado", "neutral")
        insight_card(
            "Recuperación defensiva",
            f"Entradas: {names_text(leaders.get('tackles_won'), player_name_aliases)} · Intercepciones: {names_text(leaders.get('interceptions'), player_name_aliases)}",
            "Máximos observados",
            "neutral",
        )

    if not rated.empty:
        ranked = rated.sort_values("match_rating_10", ascending=False)
        top = ranked.head(3)
        low = ranked.tail(3).sort_values("match_rating_10")
        section_header("Extremos descriptivos del partido", "Ordenación de la nota; no es una recomendación de selección")
        a, b = st.columns(2)
        with a:
            text = " · ".join(f"{r.player} {float(r.match_rating_10):.1f}" for r in top.itertuples(index=False))
            insight_card("Ratings más altos", text, "Con la confianza disponible para cada jugador", "positive")
        with b:
            text = " · ".join(f"{r.player} {float(r.match_rating_10):.1f}" for r in low.itertuples(index=False))
            insight_card("Ratings más bajos", text, "Para priorizar la revisión, no para concluir causas", "negative")

with tab_players:
    section_header("Ficha de jugadores", "Rating, minutos, perfil y confianza")
    display = ratings.copy()
    if display.empty:
        st.info("No hay jugadores valorados.")
    else:
        display["Perfil"] = display["position_group"].map(position_label)
        display["Rating"] = pd.to_numeric(display["match_rating_10"], errors="coerce")
        display["Confianza %"] = pd.to_numeric(display["match_rating_confidence"], errors="coerce")
        display["Min"] = pd.to_numeric(display["minutes_played"], errors="coerce")
        display["Titular"] = display["started"].map({True: "Sí", False: "No", 1: "Sí", 0: "No"}).fillna("—")
        display["Contexto"] = display["rating_path"].replace({
            "OUTFIELD_PERF18_ANCHORED": "Jugador de campo · contexto posicional",
            "GOALKEEPER_PERF18_SHOT90_DIST10": "Portero · modelo específico",
            "OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2": "Rol no disponible · modelo de respaldo",
        })
        table = display[["player", "Perfil", "Min", "Titular", "Rating", "Confianza %", "Contexto"]].copy()
        table.columns = ["Jugador", "Perfil", "Min", "Titular", "Rating", "Confianza %", "Contexto"]
        table = table.sort_values("Rating", ascending=False)
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            height=600,
            column_config={
                "Rating": st.column_config.NumberColumn(format="%.2f"),
                "Confianza %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
            },
        )

with tab_dimensions:
    section_header("Dimensiones", "Explicación del rendimiento por jugador")
    outfield = ratings[ratings["rating_path"] == "OUTFIELD_PERF18_ANCHORED"].copy()
    if outfield.empty:
        st.info("No hay dimensiones de jugadores de campo fiables en este partido.")
    else:
        table = outfield[["player", "attacking_threat", "creation_progression", "defensive_contribution", "finishing", "discipline"]].copy()
        for col in table.columns[1:]:
            table[col] = pd.to_numeric(table[col], errors="coerce").round(1)
        table.columns = ["Jugador", "Amenaza", "Creación", "Defensa", "Finalización", "Disciplina"]
        st.dataframe(table, hide_index=True, width="stretch", height=500)

    keepers = ratings[ratings["position_group"] == "GK"].copy()
    if not keepers.empty:
        st.markdown("#### Portero")
        for r in keepers.to_dict(orient="records"):
            values = {
                "Paradas": r.get("defensive_contribution"),
                "Distribución": r.get("creation_progression"),
                "Disciplina": r.get("discipline"),
            }
            st.plotly_chart(dimension_chart(values), width="stretch", config={"displayModeBar": False}, key=f"match_gk_dim_{r.get('player_id', r.get('player'))}")

with tab_evidence:
    section_header("Calidad y trazabilidad", "Qué sabemos y qué no sabemos antes de interpretar la nota")
    confidence = pd.to_numeric(ratings.get("match_rating_confidence"), errors="coerce") if not ratings.empty else pd.Series(dtype=float)
    e1, e2, e3 = st.columns(3)
    with e1:
        metric_card("Confianza mínima", safe_number(confidence.min() if not confidence.empty else None, 0, "%"), "Valor mínimo del partido")
    with e2:
        metric_card("Confianza mediana", safe_number(confidence.median() if not confidence.empty else None, 0, "%"), "Valor central del partido")
    with e3:
        metric_card("Rol no disponible", str(fallback_rows), "Casos sin rol táctico fiable")

    fallbacks = ratings[ratings["rating_path"] == "OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2"].copy()
    if not fallbacks.empty:
        st.warning("Las apariciones siguientes utilizan el modelo de respaldo de Match Rating V5 porque la fuente histórica no permite asignar un rol posicional fiable.")
        fallbacks["Minutos"] = pd.to_numeric(fallbacks["minutes_played"], errors="coerce")
        fallbacks["Match Rating"] = pd.to_numeric(fallbacks["match_rating_10"], errors="coerce")
        fallbacks["Confianza %"] = pd.to_numeric(fallbacks["match_rating_confidence"], errors="coerce")
        table = fallbacks[["player", "Minutos", "Match Rating", "Confianza %"]].copy()
        table.columns = ["Jugador", "Minutos", "Match Rating", "Confianza %"]
        st.dataframe(table, hide_index=True, width="stretch")
    else:
        st.success("Todas las apariciones de jugadores de campo del partido tienen contexto posicional fiable.")

with st.expander("Metodología y límites"):
    st.write(f"Versión técnica del Match Rating: `{MATCH_RATING_VERSION}`.")
    st.write("Las observaciones son deterministas. Esta pantalla no utiliza un LLM para calcular ni modificar ratings.")
