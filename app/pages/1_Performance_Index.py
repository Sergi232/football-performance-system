"""Historical/positional Performance Index detail page."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.performance_score_access import SCORE_VERSION, get_latest_player_score, get_player_score_history, list_score_teams, list_team_players
from app.ui_theme import apply_professional_theme, dimension_bar, position_label, score_card

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
DIMENSIONS = [
    ("attacking_threat", "Amenaça ofensiva"),
    ("creation_progression", "Creació / progressió"),
    ("defensive_contribution", "Contribució defensiva"),
    ("finishing", "Finalització"),
    ("discipline", "Disciplina"),
]

st.set_page_config(page_title="Performance Index · Football Performance System", page_icon="📊", layout="wide")
apply_professional_theme()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def fmt(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.1f}"


def evidence_label(value: object) -> str:
    labels = {"DIRECT_SIGNED": "Evidència directa", "CONTRIBUTION_FALLBACK": "Contribució observada de suport", "MISSING": "Sense evidència"}
    if value is None or pd.isna(value):
        return "—"
    return labels.get(str(value), str(value))


path = db_path()
try:
    teams = list_score_teams(path)
except Exception as exc:
    st.error("La capa de Performance Index no està disponible a la base seleccionada.")
    st.caption(str(exc))
    st.stop()

if teams.empty:
    st.info("No hi ha índexs materialitzats per aquesta versió.")
    st.stop()

st.markdown("<div class='fps-kicker'>ANALYTICS · HISTÒRIC / POSICIONAL</div>", unsafe_allow_html=True)
st.title("Performance Index")
st.caption(f"{SCORE_VERSION} · índex experimental específic per grup posicional. No és la nota d'un partit; el Match Rating és la capa postpartit.")

team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
team_id = st.selectbox("Equip", list(team_labels), format_func=lambda x: team_labels[x])
players = list_team_players(path, team_id)
if players.empty:
    st.info("No hi ha jugadors disponibles.")
    st.stop()

player_labels = {str(r.player_id): f"{r.player} · {int(r.scored_matches)} observacions" for r in players.itertuples(index=False)}
player_id = st.selectbox("Jugador", list(player_labels), format_func=lambda x: player_labels[x])
history = get_player_score_history(path, team_id, player_id)
latest = get_latest_player_score(path, team_id, player_id)

if latest is None:
    st.warning("Aquest jugador no té cap Performance Index posicional elegible en aquesta baseline.")
else:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        score_card("Performance Index", f"{fmt(latest['performance_score'])}/100", "Comparació relativa dins del rol")
    with c2:
        score_card("Confiança", f"{fmt(latest['score_evidence_confidence'])}%", "Cobertura de l'evidència prevista")
    with c3:
        score_card("Perfil", position_label(latest.get("position_group")), "Grup posicional")
    with c4:
        score_card("Dimensions", str(int(latest["dimension_coverage_count"])), "Dimensions disponibles")

    left, right = st.columns([1, 1.2])
    with left:
        st.subheader("Dimensions")
        for key, label in DIMENSIONS:
            dimension_bar(label, latest.get(key))
            st.caption(evidence_label(latest.get(f"{key}_evidence")))
    with right:
        st.subheader("Evolució de l'índex")
        chart = history.dropna(subset=["performance_score"]).copy()
        if not chart.empty:
            chart["match_date"] = pd.to_datetime(chart["match_date"])
            st.line_chart(chart.set_index("match_date")[["performance_score"]], height=360, width="stretch")

with st.expander("Metodologia i traçabilitat"):
    st.write(f"Versió: `{SCORE_VERSION}`")
    st.write("Aquest índex serveix per perfil/evolució posicional. La nota immediata del partit és Match Rating.")
    if latest is not None:
        st.write(f"Dimensions cobertes amb fallback de contribució: {int(latest.get('fallback_dimension_count') or 0)}")

st.subheader("Historial de l'índex")
details = history.copy()
if not details.empty:
    details["match_date"] = pd.to_datetime(details["match_date"]).dt.date
    for col in ["attacking_threat", "creation_progression", "defensive_contribution", "finishing", "discipline", "performance_score", "score_evidence_confidence"]:
        if col in details.columns:
            details[col] = pd.to_numeric(details[col], errors="coerce").round(1)
    show = ["match_date", "primary_role", "position_group", "attacking_threat", "creation_progression", "defensive_contribution", "finishing", "discipline", "performance_score", "score_evidence_confidence", "fallback_dimension_count"]
    for col in show:
        if col not in details.columns:
            details[col] = pd.NA
    details = details[show]
    details["position_group"] = details["position_group"].map(position_label)
    details.columns = ["Data", "Rol font", "Perfil", "Amenaça", "Creació", "Defensa", "Finalització", "Disciplina", "Índex", "Confiança %", "N fallback"]
    st.dataframe(details, hide_index=True, width="stretch")
