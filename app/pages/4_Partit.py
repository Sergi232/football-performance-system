"""Match Mode — immediate post-match review for technical staff."""
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
from app.data_access import get_team_matches, list_teams
from app.match_insights import get_match_observations
from app.match_rating_access import MATCH_RATING_VERSION, get_match_ratings
from app.ui_theme import apply_professional_theme, position_label, sidebar_navigation
from reports.data_builder import build_match_report_data
from reports.pdf_engine import render_pdf_bytes

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(page_title="Partit · Football Performance System", page_icon="⚽", layout="wide")
apply_professional_theme()
sidebar_navigation()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def result_text(sf: object, sa: object) -> str:
    if sf is None or sa is None or pd.isna(sf) or pd.isna(sa):
        return "—"
    return f"{int(sf)}-{int(sa)}"


def names_text(item: dict | None) -> str:
    if not item:
        return "—"
    players = item.get("players") or []
    value = item.get("value")
    if not players:
        return "—"
    suffix = "" if value is None else f" · {int(value) if float(value).is_integer() else round(float(value), 1)}"
    return ", ".join(players) + suffix


path = db_path()
if not path.exists():
    st.error(f"No s'ha trobat la base de dades: {path}")
    st.stop()

teams = list_teams(path)
team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
sel_team, sel_match, action = st.columns([1.0, 2.0, .65])
with sel_team:
    team_id = st.selectbox("Equip", options=list(team_labels), format_func=lambda x: team_labels[x])

matches = get_team_matches(path, team_id).copy()
if matches.empty:
    st.info("No hi ha partits disponibles.")
    st.stop()
matches["match_date"] = pd.to_datetime(matches["match_date"])
match_map = {
    str(r.match_id): f"{r.match_date.date()} · {r.opponent} · {result_text(r.score_for, r.score_against)}"
    for r in matches.itertuples(index=False)
}
with sel_match:
    match_id = st.selectbox("Partit", options=list(match_map), format_func=lambda x: match_map[x])
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

ratings = get_match_ratings(path, team_id, match_id)
observations = get_match_observations(path, team_id, match_id)

page_header(
    "MATCH MODE · POSTPARTIT",
    f"{team_labels[team_id]} vs {safe_text(match.get('opponent'), 'Rival')}",
    "Revisió immediata: marcador, distribució del rendiment, observacions i qualitat de l'evidència.",
    str(pd.to_datetime(match["match_date"]).date()),
)

scoreboard_card(
    team_labels[team_id],
    safe_text(match.get("opponent"), "Rival"),
    match.get("score_for"), match.get("score_against"),
    str(pd.to_datetime(match["match_date"]).date()),
    "Local" if match.get("venue") == "H" else "Visitant",
    safe_text(match.get("starting_formation"), "No disponible"),
)

rated = ratings.dropna(subset=["match_rating_10"]).copy()
median_rating = pd.to_numeric(rated.get("match_rating_10"), errors="coerce").median() if not rated.empty else None
median_conf = pd.to_numeric(rated.get("match_rating_confidence"), errors="coerce").median() if not rated.empty else None
fallback_rows = int((ratings["rating_path"] == "OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2").sum()) if not ratings.empty else 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    metric_card("Rating mediana", safe_number(median_rating, 2, "/10"), "Jugadors amb minuts")
with k2:
    metric_card("Confiança mediana", safe_number(median_conf, 0, "%"), "Cobertura de l'evidència")
with k3:
    metric_card("Jugadors utilitzats", str(len(ratings)), "Aparicions amb minuts")
with k4:
    metric_card("Rol no disponible", str(fallback_rows), "Fallback explícit, sense imputar posició")

st.write("")
tab_review, tab_players, tab_dimensions, tab_evidence = st.tabs(["Revisió tècnica", "Jugadors", "Dimensions", "Evidència"])

with tab_review:
    chart_col, insight_col = st.columns([1.35, 1.0], gap="large")
    with chart_col:
        section_header("Distribució del Match Rating", "Tots els jugadors utilitzats, escala fixa 3–10")
        if ratings.empty:
            st.info("No hi ha ratings.")
        else:
            chart = ratings.copy()
            chart["position_group"] = chart["position_group"].map(position_label)
            st.plotly_chart(player_rating_chart(chart), width="stretch", config={"displayModeBar": False})
    with insight_col:
        section_header("Observacions del partit", "Fets deterministes derivats de les dades registrades")
        goal_scorers = observations.get("goal_scorers") or []
        assist_providers = observations.get("assist_providers") or []
        leaders = observations.get("leaders") or {}

        goals_text = " · ".join(f"{x['player']} ({x['goals']})" for x in goal_scorers) if goal_scorers else "Sense gols registrats"
        assists_text = " · ".join(f"{x['player']} ({x['assists']})" for x in assist_providers) if assist_providers else "Sense assistències registrades"
        insight_card("Gols", goals_text, "Contribució directa", "positive" if goal_scorers else "neutral")
        insight_card("Assistències", assists_text, "Contribució directa", "positive" if assist_providers else "neutral")
        insight_card("Rematades", names_text(leaders.get("shots_total")), "Màxim observat", "neutral")
        insight_card("Passades completades", names_text(leaders.get("passes_completed")), "Màxim observat", "neutral")
        insight_card("Recuperació defensiva", f"Entrades: {names_text(leaders.get('tackles_won'))} · Intercepcions: {names_text(leaders.get('interceptions'))}", "Màxims observats", "neutral")

    if not rated.empty:
        ranked = rated.sort_values("match_rating_10", ascending=False)
        top = ranked.head(3)
        low = ranked.tail(3).sort_values("match_rating_10")
        section_header("Extrems descriptius del partit", "Ordenació de la nota; no és una recomanació de selecció")
        a, b = st.columns(2)
        with a:
            text = " · ".join(f"{r.player} {float(r.match_rating_10):.1f}" for r in top.itertuples(index=False))
            insight_card("Ratings més alts", text, "Amb la confiança disponible per cada jugador", "positive")
        with b:
            text = " · ".join(f"{r.player} {float(r.match_rating_10):.1f}" for r in low.itertuples(index=False))
            insight_card("Ratings més baixos", text, "Per prioritzar la revisió, no per concloure causes", "negative")

with tab_players:
    section_header("Fitxa de jugadors", "Rating, minuts, perfil i confiança")
    display = ratings.copy()
    if display.empty:
        st.info("No hi ha jugadors valorats.")
    else:
        display["Perfil"] = display["position_group"].map(position_label)
        display["Rating"] = pd.to_numeric(display["match_rating_10"], errors="coerce")
        display["Confiança %"] = pd.to_numeric(display["match_rating_confidence"], errors="coerce")
        display["Min"] = pd.to_numeric(display["minutes_played"], errors="coerce")
        display["Context"] = display["rating_path"].replace({
            "OUTFIELD_PERF18_ANCHORED": "Outfield posicional",
            "GOALKEEPER_PERF18_SHOT90_DIST10": "Porter específic",
            "OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2": "Rol no disponible · fallback",
        })
        table = display[["player", "Perfil", "Min", "started", "Rating", "Confiança %", "Context"]].copy()
        table.columns = ["Jugador", "Perfil", "Min", "Titular", "Rating", "Confiança %", "Context"]
        table = table.sort_values("Rating", ascending=False)
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            height=600,
            column_config={
                "Rating": st.column_config.NumberColumn(format="%.2f"),
                "Confiança %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
            },
        )

with tab_dimensions:
    section_header("Dimensions", "Explicació del rendiment per jugador")
    outfield = ratings[ratings["rating_path"] == "OUTFIELD_PERF18_ANCHORED"].copy()
    if outfield.empty:
        st.info("No hi ha dimensions outfield fiables en aquest partit.")
    else:
        table = outfield[["player", "attacking_threat", "creation_progression", "defensive_contribution", "finishing", "discipline"]].copy()
        for col in table.columns[1:]:
            table[col] = pd.to_numeric(table[col], errors="coerce").round(1)
        table.columns = ["Jugador", "Amenaça", "Creació", "Defensa", "Finalització", "Disciplina"]
        st.dataframe(table, hide_index=True, width="stretch", height=500)

    keepers = ratings[ratings["position_group"] == "GK"].copy()
    if not keepers.empty:
        st.markdown("#### Porter")
        for r in keepers.to_dict(orient="records"):
            values = {
                "Shot-stopping": r.get("defensive_contribution"),
                "Distribució": r.get("creation_progression"),
                "Disciplina": r.get("discipline"),
            }
            st.plotly_chart(dimension_chart(values), width="stretch", config={"displayModeBar": False})

with tab_evidence:
    section_header("Qualitat i traçabilitat", "Què sabem i què no sabem abans d'interpretar la nota")
    confidence = pd.to_numeric(ratings.get("match_rating_confidence"), errors="coerce") if not ratings.empty else pd.Series(dtype=float)
    e1, e2, e3 = st.columns(3)
    with e1:
        metric_card("Confiança mínima", safe_number(confidence.min() if not confidence.empty else None, 0, "%"), "Valor mínim del partit")
    with e2:
        metric_card("Confiança mediana", safe_number(confidence.median() if not confidence.empty else None, 0, "%"), "Valor central del partit")
    with e3:
        metric_card("Fallback de rol", str(fallback_rows), "Casos sense rol tàctic fiable")

    fallbacks = ratings[ratings["rating_path"] == "OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2"]
    if not fallbacks.empty:
        st.warning("Els casos següents conserven el rating V2 perquè la font històrica no permet assignar un rol posicional fiable.")
        st.dataframe(fallbacks[["player", "minutes_played", "match_rating_10", "match_rating_confidence"]], hide_index=True, width="stretch")
    else:
        st.success("Totes les aparicions outfield del partit tenen context posicional fiable.")

with st.expander("Metodologia i límits"):
    st.write(f"Match Rating actiu: `{MATCH_RATING_VERSION}`.")
    st.write("Les observacions són deterministes. Aquesta pantalla no utilitza un LLM per calcular ni modificar ratings.")
