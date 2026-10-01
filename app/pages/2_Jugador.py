"""Player Mode — professional staff profile and recent-form view."""
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
    player_trend_chart,
    safe_int,
    safe_number,
    section_header,
)
from app.data_access import (
    get_latest_player_gate,
    get_player_feature_history,
    get_player_match_history,
    get_squad_summary,
    get_team_matches,
    list_base_features,
    list_teams,
)
from app.match_rating_access import (
    MATCH_RATING_VERSION,
    get_latest_player_match_rating,
    get_player_match_ratings,
    get_team_player_rating_snapshot,
)
from app.performance_score_access import SCORE_VERSION, get_latest_player_score, get_player_score_history
from app.presentation import (
    anonymize_frame,
    build_opponent_aliases,
    build_player_aliases,
    build_player_name_aliases,
    demo_mode,
    display_opponent,
    display_player_name,
    display_team_name,
)
from app.ui_theme import apply_professional_theme, position_label, sidebar_navigation
from reports.data_builder import build_player_report_data
from reports.pdf_engine import render_pdf_bytes

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
FEATURE_LABELS = {
    "pass_completion_rate": "Precisión de pase",
    "shots_total_per90": "Remates / 90",
    "goals_per90": "Goles / 90",
    "assists_per90": "Asistencias / 90",
    "tackle_success_rate": "Éxito en entradas",
    "interceptions_per90": "Intercepciones / 90",
}

st.set_page_config(page_title="Jugador · Football Performance System", page_icon="👤", layout="wide")
apply_professional_theme()
sidebar_navigation()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def render_pdf(path: Path, team_id: str, player_id: str, player_name: str) -> None:
    if demo_mode():
        st.caption("PDF demo: se anonimizará en el siguiente bloque de trabajo.")
        return
    try:
        payload = build_player_report_data(path, team_id, player_id)
        pdf_bytes = render_pdf_bytes(payload)
    except Exception as exc:
        st.warning(f"No se ha podido generar el informe: {exc}")
        return
    filename = "_".join(player_name.strip().split()) or "player"
    st.download_button("Exportar PDF", data=pdf_bytes, file_name=f"player_{filename}.pdf", mime="application/pdf", width="stretch")


def score_string(sf: object, sa: object) -> str:
    if sf is None or sa is None or pd.isna(sf) or pd.isna(sa):
        return "—"
    return f"{int(sf)}-{int(sa)}"


path = db_path()
if not path.exists():
    st.error(f"No se ha encontrado la base de datos: {path}")
    st.stop()

teams = list_teams(path)
if teams.empty:
    st.info("No hay equipos disponibles.")
    st.stop()

sel_team, sel_player, action = st.columns([1.0, 1.65, .65])
raw_team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
team_ids = list(raw_team_labels)
display_team_labels = {tid: display_team_name(raw_team_labels[tid], team_ids.index(tid) + 1) for tid in team_ids}
with sel_team:
    team_id = st.selectbox("Equipo", team_ids, format_func=lambda x: display_team_labels[x])

squad = get_squad_summary(path, team_id)
player_aliases = build_player_aliases(squad)
player_name_aliases = build_player_name_aliases(squad)
raw_player_labels = {str(r.player_id): str(r.player) for r in squad.itertuples(index=False)}
with sel_player:
    player_id = st.selectbox(
        "Jugador",
        list(raw_player_labels),
        format_func=lambda x: display_player_name(x, raw_player_labels[x], player_aliases),
    )
player_name = display_player_name(player_id, raw_player_labels[player_id], player_aliases)
player_row = squad.loc[squad["player_id"].astype(str) == str(player_id)].iloc[0]
with action:
    st.write("")
    st.write("")
    render_pdf(path, team_id, player_id, player_name)

matches = get_team_matches(path, team_id)
opponent_aliases = build_opponent_aliases(matches.get("opponent", pd.Series(dtype=str)).tolist())
rating_history = anonymize_frame(
    get_player_match_ratings(path, team_id, player_id),
    player_aliases_by_id=player_aliases,
    player_name_aliases=player_name_aliases,
    opponent_aliases=opponent_aliases,
)
latest_rating = get_latest_player_match_rating(path, team_id, player_id)
team_snapshot = get_team_player_rating_snapshot(path, team_id)
player_snapshot = team_snapshot.loc[team_snapshot["player_id"].astype(str) == str(player_id)]
snap = None if player_snapshot.empty else player_snapshot.iloc[0]
try:
    score_history = get_player_score_history(path, team_id, player_id)
    latest_score = get_latest_player_score(path, team_id, player_id)
except Exception:
    score_history = pd.DataFrame()
    latest_score = None

profile = "Rol no disponible"
if latest_rating is not None:
    profile = position_label(latest_rating.get("position_group"))
elif latest_score is not None:
    profile = position_label(latest_score.get("position_group"))

page_header(
    f"PLAYER MODE · {display_team_labels[team_id]}",
    player_name,
    f"{profile} · {safe_int(player_row.get('minutes'))} minutos · {safe_int(player_row.get('appearances'))} apariciones",
    "Perfil individual",
)

latest_value = latest_rating.get("match_rating_10") if latest_rating else None
latest_conf = latest_rating.get("match_rating_confidence") if latest_rating else None
avg5 = snap.get("avg_last5") if snap is not None else None
delta5 = snap.get("trend_delta_5v5") if snap is not None else None

k1, k2, k3, k4 = st.columns(4)
with k1:
    metric_card("Último Match Rating", safe_number(latest_value, 2, "/10"), "Rendimiento del partido más reciente")
with k2:
    metric_card("Media últimos 5", safe_number(avg5, 2, "/10"), "Forma reciente descriptiva")
with k3:
    delta_text = "—" if delta5 is None or pd.isna(delta5) else f"{float(delta5):+.2f}"
    tone = "positive" if delta5 is not None and pd.notna(delta5) and float(delta5) > 0 else "negative" if delta5 is not None and pd.notna(delta5) and float(delta5) < 0 else "neutral"
    metric_card("Cambio 5 vs 5", delta_text, "Últimos 5 menos 5 anteriores", tone=tone)
with k4:
    metric_card("Confianza último partido", safe_number(latest_conf, 0, "%"), "Cobertura de la evidencia")

st.write("")
tab_overview, tab_trend, tab_technical, tab_expert, tab_matches = st.tabs(["Visión técnica", "Evolución", "Técnico", "Motor experto", "Partidos"])

with tab_overview:
    context_col, chart_col = st.columns([.8, 1.35], gap="large")
    with context_col:
        section_header("Último partido", "Contexto inmediato para la revisión")
        if latest_rating is None:
            st.info("No hay Match Rating disponible.")
        else:
            opponent = display_opponent(latest_rating.get("opponent"), opponent_aliases)
            score = score_string(latest_rating.get("score_for"), latest_rating.get("score_against"))
            venue = "Local" if latest_rating.get("venue") == "H" else "Visitante"
            insight_card("Contexto", f"{opponent} · {score} · {venue}", f"{safe_number(latest_rating.get('minutes_played'), 0)} minutos", "neutral")
            insight_card("Rol del partido", position_label(latest_rating.get("position_group")), str(latest_rating.get("match_rating_context") or ""), "neutral")
            if latest_score is not None:
                insight_card("Performance Index", safe_number(latest_score.get("performance_score"), 1, "/100"), "Capa histórica/posicional complementaria", "neutral")
            if latest_rating.get("rating_path") == "OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2":
                insight_card("Limitación de rol", "La fuente no informa de un rol táctico fiable en esta aparición.", "Se utiliza fallback explícito; no se inventa la posición.", "warning")

    with chart_col:
        section_header("Dimensiones del último partido", "Scores internos para explicar la nota")
        if latest_rating is None:
            st.info("Sin dimensiones disponibles.")
        elif latest_rating.get("position_group") == "GK":
            values = {
                "Shot-stopping": latest_rating.get("defensive_contribution"),
                "Distribución": latest_rating.get("creation_progression"),
                "Disciplina": latest_rating.get("discipline"),
            }
            st.plotly_chart(dimension_chart(values), width="stretch", config={"displayModeBar": False}, key=f"player_dimensions_gk_{player_id}")
            st.caption("El portero sigue un modelo separado: 90% shot-stopping / 10% distribución en el núcleo estructural.")
        else:
            values = {
                "Amenaza ofensiva": latest_rating.get("attacking_threat"),
                "Creación / progresión": latest_rating.get("creation_progression"),
                "Contribución defensiva": latest_rating.get("defensive_contribution"),
                "Finalización": latest_rating.get("finishing"),
                "Disciplina": latest_rating.get("discipline"),
            }
            st.plotly_chart(dimension_chart(values), width="stretch", config={"displayModeBar": False}, key=f"player_dimensions_outfield_{player_id}")

    section_header("Trayectoria de Match Rating", "Evolución partido a partido; escala fija 3–10")
    if rating_history.empty:
        st.info("No hay historial disponible.")
    else:
        st.plotly_chart(player_trend_chart(rating_history, "match_rating_10", (3, 10)), width="stretch", config={"displayModeBar": False}, key=f"player_overview_rating_trend_{player_id}")

with tab_trend:
    section_header("Evolución temporal", "Match Rating, Performance Index y métricas base")
    if not rating_history.empty:
        st.plotly_chart(player_trend_chart(rating_history, "match_rating_10", (3, 10)), width="stretch", config={"displayModeBar": False}, key=f"player_tab_rating_trend_{player_id}")
    if not score_history.empty:
        st.markdown("#### Performance Index")
        st.plotly_chart(player_trend_chart(score_history, "performance_score", (0, 100), hover_col=None), width="stretch", config={"displayModeBar": False}, key=f"player_tab_performance_index_{player_id}")

    features = list_base_features(path, player_id)
    if features:
        preferred = ["pass_completion_rate", "shots_total_per90", "goals_per90", "assists_per90", "tackle_success_rate", "interceptions_per90"]
        ordered = [f for f in preferred if f in features] + [f for f in features if f not in preferred]
        feature_name = st.selectbox("Métrica técnica", ordered, format_func=lambda x: FEATURE_LABELS.get(x, x.replace("_", " ").title()), key="player_metric")
        feature_history = get_player_feature_history(path, player_id, feature_name)
        if not feature_history.empty:
            chart_data = feature_history.rename(columns={"feature_value": "value"})
            if "opponent" in chart_data.columns:
                chart_data["opponent"] = chart_data["opponent"].map(lambda x: display_opponent(x, opponent_aliases))
            st.plotly_chart(
                player_trend_chart(
                    chart_data,
                    "value",
                    (
                        float(chart_data["value"].min()) if chart_data["value"].notna().any() else 0,
                        float(chart_data["value"].max()) * 1.1 if chart_data["value"].notna().any() and float(chart_data["value"].max()) != float(chart_data["value"].min()) else 1,
                    ),
                    hover_col="opponent",
                ),
                width="stretch",
                config={"displayModeBar": False},
                key=f"player_feature_{player_id}_{feature_name}",
            )

with tab_technical:
    section_header("Rendimiento técnico", "Acciones observadas; sin convertirlas en conclusiones automáticas")
    history = get_player_match_history(path, team_id, player_id)
    if not history.empty:
        technical = history.copy()
        technical["match_date"] = pd.to_datetime(technical["match_date"]).dt.date
        technical["opponent"] = technical["opponent"].map(lambda x: display_opponent(x, opponent_aliases))
        technical = technical[["match_date", "opponent", "minutes", "primary_role", "passes_total", "passes_completed", "assists", "shots_total", "goals", "tackles_total", "tackles_won", "interceptions", "turnovers", "dispossessed"]]
        technical.columns = ["Fecha", "Rival", "Min", "Rol", "Pases", "Completados", "Asist.", "Remates", "Goles", "Entradas", "Ganadas", "Intercepciones", "Pérdidas", "Desposesiones"]
        st.dataframe(technical, hide_index=True, width="stretch", height=560)

with tab_expert:
    section_header("Motor experto", "Estado auditable del sistema jerárquico")
    gate = get_latest_player_gate(path, team_id, player_id)
    if gate is None:
        st.info("No hay estado experto disponible.")
    else:
        a, b, c, d = st.columns(4)
        a.metric("Rol observado", gate.get("observed_role") or "—")
        b.metric("Historial mismo rol", gate.get("same_role_history") or "—")
        try:
            coverage = float(gate.get("evidence_coverage"))
        except (TypeError, ValueError):
            coverage = None
        c.metric("Cobertura", "—" if coverage is None else f"{coverage:.0%}")
        d.metric("Señales", gate.get("evaluable_signals") or "—")
        insight_card("Estado final", str(gate.get("final_status") or "Sin estado").replace("_", " ").title(), "Salida del motor; no es texto generado por LLM", "neutral")
        with st.expander("Trazabilidad técnica"):
            st.json(gate)

with tab_matches:
    section_header("Historial de partidos", "Contexto, minutos y Match Rating")
    if rating_history.empty:
        st.info("No hay historial de ratings.")
    else:
        details = rating_history.copy().sort_values("match_date", ascending=False)
        details["Fecha"] = pd.to_datetime(details["match_date"]).dt.date
        details["Resultado"] = details.apply(lambda r: score_string(r.get("score_for"), r.get("score_against")), axis=1)
        details["Perfil"] = details["position_group"].map(position_label)
        table = details[["Fecha", "opponent", "Resultado", "venue", "minutes_played", "Perfil", "match_rating_10", "match_rating_confidence"]].copy()
        table.columns = ["Fecha", "Rival", "Resultado", "L/V", "Min", "Perfil", "Rating", "Confianza %"]
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

with st.expander("Metodología y trazabilidad"):
    st.write(f"Match Rating activo: `{MATCH_RATING_VERSION}`. La nota es jugador-partido y existe desde el primer partido.")
    st.write(f"Performance Index: `{SCORE_VERSION}`. Es histórico/posicional y no sustituye el Match Rating.")
