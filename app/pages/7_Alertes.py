"""Auditable attention centre: data/evidence/context limitations only."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.attention_access import ATTENTION_VERSION, get_attention_summary, get_team_attention_flags
from app.coach_ui import metric_card, page_header, section_header
from app.data_access import get_squad_summary, get_team_matches, list_teams
from app.presentation import (
    anonymize_frame,
    build_opponent_aliases,
    build_player_aliases,
    build_player_name_aliases,
    demo_mode,
    display_team_name,
    replace_known_names,
)
from app.ui_theme import apply_professional_theme, sidebar_navigation

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(page_title="Calidad y alertas · Football Performance System", page_icon="🚩", layout="wide")
apply_professional_theme()
sidebar_navigation()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


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
raw_team_name = raw_team_labels[team_id]
team_name = display_team_labels[team_id]

page_header(
    "ATTENTION CENTRE · DATA QUALITY",
    "Calidad y alertas",
    "Solo limitaciones auditables de datos, contexto o evidencia. No son alertas de rendimiento, fatiga ni riesgo de lesión.",
    ATTENTION_VERSION,
)

try:
    flags = get_team_attention_flags(path, team_id)
    summary = get_attention_summary(path, team_id)
except Exception as exc:
    st.warning("La capa de alertas todavía no está materializada.")
    st.caption(str(exc))
    st.stop()

squad = get_squad_summary(path, team_id)
matches = get_team_matches(path, team_id)
player_aliases = build_player_aliases(squad)
player_name_aliases = build_player_name_aliases(squad)
opponent_aliases = build_opponent_aliases(matches.get("opponent", pd.Series(dtype=str)).tolist())
flags = anonymize_frame(
    flags,
    player_aliases_by_id=player_aliases,
    player_name_aliases=player_name_aliases,
    opponent_aliases=opponent_aliases,
)
if demo_mode() and not flags.empty and "message" in flags.columns:
    flags["message"] = flags["message"].map(
        lambda x: replace_known_names(
            x,
            player_name_aliases=player_name_aliases,
            opponent_aliases=opponent_aliases,
            team_name=raw_team_name,
            team_alias=team_name,
        )
    )

counts = {str(r.attention_code): int(r.rows) for r in summary.itertuples(index=False)}
cols = st.columns(3)
with cols[0]:
    metric_card("Contexto de rol no disponible", str(counts.get("ROLE_CONTEXT_UNAVAILABLE", 0)), "No se imputa ninguna posición")
with cols[1]:
    metric_card("Evidencia insuficiente", str(counts.get("INSUFFICIENT_RATING_EVIDENCE", 0)), "Limitación explícita")
with cols[2]:
    metric_card("Incidencias GPS", str(counts.get("GPS_QUALITY_FLAGS_PRESENT", 0)), "Quality flags de importación")

section_header("Registro de limitaciones", "Filtros por grupo y trazabilidad hasta la fuente")
if flags.empty:
    st.success("No hay limitaciones auditables registradas para este equipo en esta versión.")
else:
    group_values = sorted(flags["attention_group"].dropna().astype(str).unique().tolist())
    selected_label = st.selectbox("Tipo", ["Todas"] + group_values)
    display = flags.copy()
    if selected_label != "Todas":
        display = display.loc[display["attention_group"] == selected_label].copy()
    display["match_date"] = pd.to_datetime(display["match_date"], errors="coerce").dt.date
    display = display[["match_date", "player", "attention_group", "attention_code", "message", "source_layer"]]
    display.columns = ["Fecha", "Jugador", "Grupo", "Código", "Mensaje", "Fuente"]
    st.dataframe(display, hide_index=True, width="stretch", height=560)

with st.expander("Metodología"):
    st.write(f"Versión: `{ATTENTION_VERSION}`")
    st.write("Este centro no interpreta un rating bajo como una alerta, no define fatiga/readiness y no estima riesgo de lesión.")
    st.write("Las alertas de rendimiento futuras requerirán reglas o modelos validados y quedarán separadas de estas limitaciones de datos/evidencia.")
