"""Performance Index histórico y posicional: perfil analítico secundario."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.coach_ui import dimension_chart, insight_card, metric_card, page_header, player_trend_chart, safe_number, section_header
from app.performance_score_access import SCORE_VERSION, get_latest_player_score, get_player_score_history, list_score_teams, list_team_players
from app.presentation import build_player_aliases, display_player_name, display_team_name
from app.ui_theme import apply_professional_theme, position_label, sidebar_navigation

DEFAULT_DB = ROOT / "data" / "football_performance_synthetic_demo.duckdb"
DIMENSIONS = [
    ("attacking_threat", "Amenaza ofensiva"),
    ("creation_progression", "Creación / progresión"),
    ("defensive_contribution", "Contribución defensiva"),
    ("finishing", "Finalización"),
    ("discipline", "Disciplina"),
]

st.set_page_config(page_title="Performance Index · FPS", page_icon="📈", layout="wide")
apply_professional_theme()
sidebar_navigation()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def evidence_label(value: object) -> str:
    labels = {
        "DIRECT_SIGNED": "Evidencia directa",
        "CONTRIBUTION_FALLBACK": "Contribución observada de apoyo",
        "MISSING": "Sin evidencia",
    }
    if value is None or pd.isna(value):
        return "Sin evidencia"
    return labels.get(str(value), "Evidencia no clasificada")


path = db_path()
try:
    teams = list_score_teams(path)
except Exception as exc:
    st.error("La capa de Performance Index no está disponible.")
    st.caption(str(exc))
    st.stop()

if teams.empty:
    st.info("No hay índices materializados.")
    st.stop()

sel_team, sel_player = st.columns([1, 1.6])
raw_team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
team_ids = list(raw_team_labels)
display_team_labels = {tid: display_team_name(raw_team_labels[tid], team_ids.index(tid) + 1) for tid in team_ids}
with sel_team:
    team_id = st.selectbox("Equipo", team_ids, format_func=lambda x: display_team_labels[x])
players = list_team_players(path, team_id)
if players.empty:
    st.info("No hay jugadores disponibles.")
    st.stop()
player_aliases = build_player_aliases(players)
raw_player_labels = {str(r.player_id): str(r.player) for r in players.itertuples(index=False)}
scored_matches = {str(r.player_id): int(r.scored_matches) for r in players.itertuples(index=False)}
with sel_player:
    player_id = st.selectbox(
        "Jugador",
        list(raw_player_labels),
        format_func=lambda x: f"{display_player_name(x, raw_player_labels[x], player_aliases)} · {scored_matches[x]} observaciones",
    )

history = get_player_score_history(path, team_id, player_id)
latest = get_latest_player_score(path, team_id, player_id)
player_name = display_player_name(player_id, raw_player_labels[player_id], player_aliases)

page_header(
    "ANÁLISIS · PERFIL HISTÓRICO",
    f"Performance Index · {player_name}",
    "Capa posicional para observar perfil y evolución. No es la nota de un partido y no sustituye el Match Rating.",
    SCORE_VERSION,
)

if latest is None:
    st.warning("Este jugador no tiene ningún Performance Index posicional elegible en la versión actual.")
    st.stop()

scores = history.dropna(subset=["performance_score"]).copy()
scores["performance_score"] = pd.to_numeric(scores["performance_score"], errors="coerce")
scores = scores.sort_values("match_date")
last5 = scores.tail(5)["performance_score"].mean() if not scores.empty else None
prev5 = scores.iloc[-10:-5]["performance_score"].mean() if len(scores) > 5 else None
delta = last5 - prev5 if last5 is not None and prev5 is not None and pd.notna(prev5) else None

k1, k2, k3, k4 = st.columns(4)
with k1:
    metric_card("Performance Index", safe_number(latest.get("performance_score"), 1, "/100"), "Valor posicional actual")
with k2:
    metric_card("Media últimos 5", safe_number(last5, 1, "/100"), "Evolución reciente")
with k3:
    delta_text = "—" if delta is None or pd.isna(delta) else f"{float(delta):+.1f}"
    tone = "positive" if delta is not None and pd.notna(delta) and delta > 0 else "negative" if delta is not None and pd.notna(delta) and delta < 0 else "neutral"
    metric_card("Cambio 5 vs 5", delta_text, "Últimos 5 menos 5 anteriores", tone=tone)
with k4:
    metric_card("Confianza", safe_number(latest.get("score_evidence_confidence"), 0, "%"), "Cobertura de evidencia prevista")

left, right = st.columns([1, 1.25], gap="large")
with left:
    section_header("Perfil de dimensiones", "Solo se muestran dimensiones con evidencia disponible")
    values = {label: latest.get(key) for key, label in DIMENSIONS}
    st.plotly_chart(dimension_chart(values), width="stretch", config={"displayModeBar": False}, key=f"pi_dimensions_{player_id}")

    missing = [label for key, label in DIMENSIONS if latest.get(key) is None or pd.isna(latest.get(key))]
    available = [label for key, label in DIMENSIONS if latest.get(key) is not None and pd.notna(latest.get(key))]
    insight_card(
        "Cobertura dimensional",
        f"{len(available)}/{len(DIMENSIONS)} dimensiones con valor",
        "Disponibles: " + (", ".join(available) if available else "ninguna"),
        "neutral",
    )
    if missing:
        insight_card("Sin evidencia suficiente", ", ".join(missing), "Los valores ausentes no se convierten en cero.", "warning")

with right:
    section_header("Evolución del índice", "Escala 0–100 · perfil histórico y posicional")
    if scores.empty:
        st.info("No hay historial disponible.")
    else:
        st.plotly_chart(player_trend_chart(scores, "performance_score", (0, 100), hover_col=None), width="stretch", config={"displayModeBar": False}, key=f"pi_trend_{player_id}")

section_header("Evidencia de la última observación", "Origen de cada dimensión")
evidence_rows = []
for key, label in DIMENSIONS:
    evidence_rows.append({
        "Dimensión": label,
        "Valor": latest.get(key),
        "Evidencia": evidence_label(latest.get(f"{key}_evidence")),
    })
evidence = pd.DataFrame(evidence_rows)
evidence["Valor"] = pd.to_numeric(evidence["Valor"], errors="coerce").round(1)
st.dataframe(evidence, hide_index=True, width="stretch")

with st.expander("Historial y trazabilidad"):
    details = history.copy()
    if not details.empty:
        details["match_date"] = pd.to_datetime(details["match_date"]).dt.date
        show = ["match_date", "primary_role", "position_group", "performance_score", "score_evidence_confidence", "dimension_coverage_count", "fallback_dimension_count"]
        for col in show:
            if col not in details.columns:
                details[col] = pd.NA
        details = details[show]
        details["position_group"] = details["position_group"].map(position_label)
        details.columns = ["Fecha", "Rol fuente", "Perfil", "Índice", "Confianza %", "Dimensiones", "Dim. de respaldo"]
        st.dataframe(details, hide_index=True, width="stretch", height=440)
    st.caption("Este índice es experimental y secundario. Los valores ausentes se mantienen como ausentes.")
