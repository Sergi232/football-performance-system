"""Team Mode — staff-oriented squad and form dashboard."""
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
    describe_trend,
    insight_card,
    metric_card,
    names_with_delta,
    page_header,
    player_trend_chart,
    rating_trend_chart,
    recent_record,
    safe_int,
    safe_number,
    safe_text,
    scoreboard_card,
    section_header,
    squad_matrix_chart,
)
from app.data_access import get_squad_summary, get_team_matches, get_team_overview, list_teams
from app.match_rating_access import (
    MATCH_RATING_VERSION,
    get_latest_team_match_ratings,
    get_team_match_rating_history,
    get_team_player_rating_snapshot,
)
from app.performance_score_access import SCORE_VERSION, get_team_score_snapshot
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
from reports.data_builder import build_team_report_data
from reports.pdf_engine_es import render_pdf_bytes

DEFAULT_DB = ROOT / "data" / "football_performance_synthetic_demo.duckdb"

st.set_page_config(page_title="Equipo · Football Performance System", page_icon="⚽", layout="wide")
apply_professional_theme()
sidebar_navigation()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def render_team_pdf(path: Path, team_id: str, team_name: str) -> None:
    try:
        payload = build_team_report_data(path, team_id)
        pdf_bytes = render_pdf_bytes(payload)
    except Exception as exc:
        st.warning(f"No se ha podido generar el informe: {exc}")
        return
    filename = "_".join(team_name.strip().split()) or "team"
    st.download_button("Exportar PDF", data=pdf_bytes, file_name=f"team_{filename}.pdf", mime="application/pdf", width="stretch")


def result_label(row: pd.Series) -> str:
    if pd.isna(row.get("score_for")) or pd.isna(row.get("score_against")):
        return "—"
    sf, sa = int(row["score_for"]), int(row["score_against"])
    return f"{'G' if sf > sa else 'E' if sf == sa else 'P'} {sf}-{sa}"


path = db_path()
if not path.exists():
    st.error(f"No se ha encontrado la base de datos: {path}")
    st.stop()

teams = list_teams(path)
if teams.empty:
    st.info("No hay equipos disponibles.")
    st.stop()

selector, action = st.columns([3.2, .8])
raw_team_labels = {str(row.team_id): str(row.display_name) for row in teams.itertuples(index=False)}
team_ids = list(raw_team_labels)
display_team_labels = {tid: display_team_name(raw_team_labels[tid], team_ids.index(tid) + 1) for tid in team_ids}
with selector:
    team_id = st.selectbox("Equipo", options=team_ids, format_func=lambda x: display_team_labels[x])
raw_team_name = raw_team_labels[team_id]
team_name = display_team_labels[team_id]
with action:
    st.write("")
    st.write("")
    render_team_pdf(path, team_id, team_name)

overview = get_team_overview(path, team_id)
squad = get_squad_summary(path, team_id)
matches = get_team_matches(path, team_id).copy()
if not matches.empty:
    matches["match_date"] = pd.to_datetime(matches["match_date"])
    matches = matches.sort_values(["match_date", "match_id"], ascending=[False, False])

player_aliases = build_player_aliases(squad)
player_name_aliases = build_player_name_aliases(squad)
opponent_aliases = build_opponent_aliases(matches.get("opponent", pd.Series(dtype=str)).tolist())

latest_match_ratings = anonymize_frame(
    get_latest_team_match_ratings(path, team_id),
    player_aliases_by_id=player_aliases,
    player_name_aliases=player_name_aliases,
    opponent_aliases=opponent_aliases,
)
rating_snapshot = anonymize_frame(
    get_team_player_rating_snapshot(path, team_id),
    player_aliases_by_id=player_aliases,
    player_name_aliases=player_name_aliases,
    opponent_aliases=opponent_aliases,
)
rating_history = get_team_match_rating_history(path, team_id)
try:
    performance_snapshot = anonymize_frame(
        get_team_score_snapshot(path, team_id),
        player_aliases_by_id=player_aliases,
        player_name_aliases=player_name_aliases,
        opponent_aliases=opponent_aliases,
    )
except Exception:
    performance_snapshot = pd.DataFrame()

page_header(
    "TEAM MODE",
    team_name,
    "Forma del equipo, cambios recientes de la plantilla y contexto operativo para preparar la revisión técnica.",
    f"{MATCH_RATING_VERSION}",
)

latest_match = matches.iloc[0] if not matches.empty else None
median_latest = pd.to_numeric(latest_match_ratings.get("match_rating_10"), errors="coerce").median() if not latest_match_ratings.empty else None
median_conf = pd.to_numeric(latest_match_ratings.get("match_rating_confidence"), errors="coerce").median() if not latest_match_ratings.empty else None

# Collector matches use their event ledger. Historical matches use deterministic sums
# from player-match raw statistics. A null still means that neither source captured the
# family, so the UI keeps N/D rather than manufacturing a zero.
result_rows = matches.dropna(subset=["score_for", "score_against"]).copy()
if result_rows.empty:
    record_text = "N/D"
else:
    sf = pd.to_numeric(result_rows["score_for"], errors="coerce")
    sa = pd.to_numeric(result_rows["score_against"], errors="coerce")
    record_text = f"{int((sf > sa).sum())}V · {int((sf == sa).sum())}E · {int((sf < sa).sum())}D"

def event_total(column: str) -> str:
    values = pd.to_numeric(matches.get(column), errors="coerce")
    return "N/D" if values.dropna().empty else str(int(values.sum()))


def event_difference(left: str, right: str) -> str:
    values_left = pd.to_numeric(matches.get(left), errors="coerce")
    values_right = pd.to_numeric(matches.get(right), errors="coerce")
    if values_left.dropna().empty or values_right.dropna().empty:
        return "N/D"
    return f"{int(values_left.sum() - values_right.sum()):+d}"


def team_pass_completion() -> str:
    attempted = pd.to_numeric(matches.get("passes_total"), errors="coerce")
    completed = pd.to_numeric(matches.get("passes_completed"), errors="coerce")
    if attempted.dropna().empty or completed.dropna().empty or attempted.sum() <= 0:
        return "N/D"
    return f"{100.0 * completed.sum() / attempted.sum():.0f}%"

if latest_match is not None:
    board, signals = st.columns([1.55, 1], gap="large")
    with board:
        scoreboard_card(
            team_name,
            display_opponent(latest_match.get("opponent"), opponent_aliases),
            latest_match.get("score_for"), latest_match.get("score_against"),
            str(latest_match["match_date"].date()),
            "Local" if latest_match.get("venue") == "H" else "Visitante",
            safe_text(latest_match.get("starting_formation"), "No disponible"),
        )
        section_header("Indicadores de la temporada disponible", "Agregados directos de todos los partidos cargados")
        a, b, c, d = st.columns(4)
        with a:
            metric_card("Partidos", safe_int(overview.get("matches")), "Partidos cargados")
        with b:
            metric_card("V / E / D", record_text, "Resultados registrados")
        with c:
            metric_card("GF", event_total("score_for"), "Goles a favor")
        with d:
            metric_card("GC", event_total("score_against"), "Goles en contra")
        basic_a, basic_b, basic_c = st.columns(3)
        with basic_a:
            metric_card("Diferencia de goles", event_difference("score_for", "score_against"), "GF menos GC")
        with basic_b:
            metric_card("Remates", event_total("shots_total"), "Total registrado")
        with basic_c:
            metric_card("A puerta", event_total("shots_on_target"), "Gol + a puerta")
        basic_a, basic_b, basic_c = st.columns(3)
        with basic_a:
            metric_card("Faltas cometidas", event_total("fouls_committed"), "Total registrado")
        with basic_b:
            metric_card("Faltas recibidas", event_total("fouls_received"), "Total registrado")
        with basic_c:
            metric_card("Pase completado", team_pass_completion(), "Completados / intentados")

        section_header("Disciplina y penaltis", "Eventos registrados en los partidos cargados")
        basic_a, basic_b, basic_c, basic_d = st.columns(4)
        with basic_a:
            metric_card("Amarillas", event_total("yellow_cards"), "Total registrado")
        with basic_b:
            metric_card("Rojas", event_total("red_cards"), "Total registrado")
        with basic_c:
            metric_card("Penaltis a favor", event_total("penalties_won"), "Total registrado")
        with basic_d:
            metric_card("Penaltis en contra", event_total("penalties_conceded"), "Total registrado")

        a, b, c = st.columns(3)
        with a:
            metric_card("Rating mediano", safe_number(median_latest, 2, "/10"), "Último partido")
        with b:
            metric_card("Confianza mediana", safe_number(median_conf, 0, "%"), "Último partido")
        with c:
            metric_card("Forma", recent_record(matches, 5), "Últimos 5 · más reciente primero")
    with signals:
        section_header("Cambios recientes", "Comparación descriptiva de bloques de cinco partidos")
        rising, falling = describe_trend(rating_snapshot) if not rating_snapshot.empty else (pd.DataFrame(), pd.DataFrame())
        insight_card("Mayor subida reciente", names_with_delta(rising), "Delta 5 vs 5", "positive")
        insight_card("Mayor bajada reciente", names_with_delta(falling), "Delta 5 vs 5", "negative")
        insight_card("Cobertura", f"{safe_int(overview.get('players'))} jugadores · {safe_int(overview.get('matches'))} partidos", "Base actual del equipo", "neutral")

st.write("")
tab_staff, tab_squad, tab_matches, tab_index = st.tabs(["Visión técnica", "Plantilla", "Partidos", "Performance Index"])

with tab_staff:
    trend_col, matrix_col = st.columns([1.08, 1], gap="large")
    with trend_col:
        section_header("Tendencia del equipo", "Mediana de rating de los jugadores utilizados")
        if rating_history.empty:
            st.info("No hay historial de ratings.")
        else:
            st.plotly_chart(rating_trend_chart(rating_history), width="stretch", config={"displayModeBar": False})
    with matrix_col:
        section_header("Mapa de plantilla", "Nivel reciente × cambio reciente")
        if rating_snapshot.empty:
            st.info("No hay snapshot de plantilla.")
        else:
            st.plotly_chart(squad_matrix_chart(rating_snapshot), width="stretch", config={"displayModeBar": False})
            st.caption("No es un ranking de calidad: muestra posición relativa en forma reciente y cambio 5 vs 5.")

    section_header("Evolución de producción", "Serie por partido de un agregado ya registrado")
    available_trends = {
        "Goles a favor": "score_for",
        "Goles en contra": "score_against",
        "Remates": "shots_total",
        "Remates a puerta": "shots_on_target",
        "Córners a favor": "corners_for",
        "Faltas cometidas": "fouls_committed",
        "Faltas recibidas": "fouls_received",
    }
    trend_label = st.selectbox("Variable de evolución", list(available_trends), key="team_event_trend")
    trend_column = available_trends[trend_label]
    trend_frame = matches[["match_date", "opponent", trend_column]].rename(columns={trend_column: "value"}).dropna(subset=["value"])
    if trend_frame.empty:
        st.info("No hay eventos registrados para mostrar esta evolución.")
    else:
        upper = max(1.0, float(pd.to_numeric(trend_frame["value"], errors="coerce").max()) * 1.15)
        st.plotly_chart(player_trend_chart(trend_frame, "value", (0, upper)), width="stretch", config={"displayModeBar": False}, key=f"team_event_trend_chart_{trend_column}")

    section_header("Movimiento reciente de la plantilla", "Jugadores con historial comparable")
    if rating_snapshot.empty:
        st.info("No hay datos comparables.")
    else:
        movement = rating_snapshot.copy()
        movement["Perfil"] = movement["latest_position_group"].map(position_label)
        for col in ["latest_match_rating", "avg_last5", "avg_previous5", "trend_delta_5v5", "latest_confidence"]:
            movement[col] = pd.to_numeric(movement[col], errors="coerce")
        movement = movement.dropna(subset=["avg_last5"]).sort_values("trend_delta_5v5", ascending=False, na_position="last")
        movement = movement[["player", "Perfil", "latest_match_rating", "avg_last5", "avg_previous5", "trend_delta_5v5", "latest_confidence"]]
        movement.columns = ["Jugador", "Perfil", "Último", "Últimos 5", "5 anteriores", "Delta", "Confianza %"]
        movement = movement.round({"Último": 2, "Últimos 5": 2, "5 anteriores": 2, "Delta": 2, "Confianza %": 0})
        st.dataframe(
            movement,
            hide_index=True,
            width="stretch",
            height=420,
            column_config={
                "Último": st.column_config.NumberColumn(format="%.2f"),
                "Últimos 5": st.column_config.NumberColumn(format="%.2f"),
                "5 anteriores": st.column_config.NumberColumn(format="%.2f"),
                "Delta": st.column_config.NumberColumn(format="%+.2f"),
                "Confianza %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
            },
        )

with tab_squad:
    section_header("Plantilla", "Participación, rol observado y estado reciente")
    roster = squad.merge(rating_snapshot, on=["player_id", "player"], how="left") if not rating_snapshot.empty and not demo_mode() else squad.copy()
    if demo_mode():
        roster = anonymize_frame(squad, player_aliases_by_id=player_aliases, player_name_aliases=player_name_aliases)
        if not rating_snapshot.empty:
            merge_cols = [c for c in rating_snapshot.columns if c != "player"]
            roster = roster.merge(rating_snapshot[merge_cols], on="player_id", how="left")
    if "latest_position_group" in roster.columns:
        roster["Perfil"] = roster["latest_position_group"].map(position_label)
    else:
        roster["Perfil"] = "—"
    for col in ["latest_match_rating", "latest_confidence", "avg_last5", "trend_delta_5v5"]:
        if col not in roster.columns:
            roster[col] = pd.NA
        roster[col] = pd.to_numeric(roster[col], errors="coerce")
    table = roster[["player", "Perfil", "appearances", "starts", "minutes", "latest_match_rating", "avg_last5", "trend_delta_5v5", "latest_confidence"]].copy()
    table.columns = ["Jugador", "Perfil", "Apar.", "Tit.", "Minutos", "Último rating", "Media 5", "Delta 5v5", "Confianza %"]
    table = table.sort_values(["Minutos", "Jugador"], ascending=[False, True])
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        height=560,
        column_config={
            "Último rating": st.column_config.NumberColumn(format="%.2f"),
            "Media 5": st.column_config.NumberColumn(format="%.2f"),
            "Delta 5v5": st.column_config.NumberColumn(format="%+.2f"),
            "Confianza %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
        },
    )

with tab_matches:
    section_header("Historial de partidos", "Resultado, formación y rating agregado")
    display = matches.copy()
    if display.empty:
        st.info("No hay partidos disponibles.")
    else:
        hist = rating_history[["match_id", "median_match_rating", "median_confidence"]].copy() if not rating_history.empty else pd.DataFrame()
        if not hist.empty:
            display = display.merge(hist, on="match_id", how="left")
        display["Fecha"] = display["match_date"].dt.date
        display["Resultado"] = display.apply(result_label, axis=1)
        display["L/V"] = display["venue"].map({"H": "L", "A": "V"}).fillna(display["venue"])
        display["Formación"] = display["starting_formation"].apply(lambda x: safe_text(x, "—"))
        display["opponent"] = display["opponent"].map(lambda x: display_opponent(x, opponent_aliases))
        for col in ["median_match_rating", "median_confidence"]:
            if col not in display.columns:
                display[col] = pd.NA
        for col in ["corners_for", "corners_against", "fouls_received", "fouls_committed", "yellow_cards", "red_cards", "penalties_won", "penalties_conceded"]:
            display[col] = pd.to_numeric(display.get(col), errors="coerce")
        def pair_or_nd(row: pd.Series, left: str, right: str) -> str:
            if pd.isna(row.get(left)) or pd.isna(row.get(right)):
                return "N/D"
            return f"{int(row[left])} · {int(row[right])}"

        display["Córners F/C"] = display.apply(lambda r: pair_or_nd(r, "corners_for", "corners_against"), axis=1)
        display["Faltas R/C"] = display.apply(lambda r: pair_or_nd(r, "fouls_received", "fouls_committed"), axis=1)
        display["Tarjetas A/R"] = display.apply(lambda r: pair_or_nd(r, "yellow_cards", "red_cards"), axis=1)
        display["Penaltis F/C"] = display.apply(lambda r: pair_or_nd(r, "penalties_won", "penalties_conceded"), axis=1)
        display = display[["Fecha", "L/V", "opponent", "Resultado", "Formación", "Córners F/C", "Faltas R/C", "Tarjetas A/R", "Penaltis F/C", "median_match_rating", "median_confidence"]]
        display.columns = ["Fecha", "L/V", "Rival", "Resultado", "Formación", "Córners F/C", "Faltas R/C", "Tarjetas A/R", "Penaltis F/C", "Rating mediano", "Confianza mediana %"]
        st.dataframe(display, hide_index=True, width="stretch", height=600)

with tab_index:
    section_header("Performance Index", "Perfil histórico/posicional complementario al Match Rating")
    if performance_snapshot.empty:
        st.info("No hay Performance Index disponible.")
    else:
        index_table = performance_snapshot.copy()
        index_table["Perfil"] = index_table["position_group"].map(position_label)
        for col in ["latest_score", "latest_confidence", "avg_last5", "trend_delta_5v5"]:
            index_table[col] = pd.to_numeric(index_table[col], errors="coerce").round(1)
        index_table = index_table[["player", "Perfil", "latest_score", "latest_confidence", "avg_last5", "trend_delta_5v5"]]
        index_table.columns = ["Jugador", "Perfil", "Performance Index", "Confianza %", "Media 5", "Delta 5v5"]
        st.dataframe(index_table, hide_index=True, width="stretch")

with st.expander("Metodología y límites"):
    st.write(f"Match Rating activo: `{MATCH_RATING_VERSION}`.")
    st.write(f"Performance Index: `{SCORE_VERSION}`. Es una capa histórica complementaria.")
    st.write("Los deltas 5 vs 5 son descriptivos y no activan recomendaciones tácticas automáticas.")
