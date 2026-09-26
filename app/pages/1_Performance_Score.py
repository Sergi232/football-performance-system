"""Performance Score page for the Football Performance System dashboard."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.performance_score_access import (  # noqa: E402
    SCORE_VERSION,
    get_latest_player_score,
    get_player_score_history,
    list_score_teams,
    list_team_players,
)

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
DIMENSIONS = [
    ("attacking_threat", "Amenaça ofensiva"),
    ("creation_progression", "Creació / progressió"),
    ("defensive_contribution", "Contribució defensiva"),
    ("finishing", "Finalització"),
    ("discipline", "Disciplina"),
]

st.set_page_config(page_title="Performance Score", page_icon="📊", layout="wide")


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def fmt_score(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.1f}"


st.title("Performance Score")
st.caption(
    f"{SCORE_VERSION} · score experimental 0–100 específic per grup posicional. "
    "No és una etiqueta bo/dolent ni una recomanació tàctica."
)

path = db_path()
try:
    teams = list_score_teams(path)
except Exception as exc:
    st.error(
        "La capa de score encara no està materialitzada a DuckDB. "
        "Executa `python analytics\\build_performance_score.py` i torna a carregar la pàgina."
    )
    st.caption(str(exc))
    st.stop()

if teams.empty:
    st.info("No hi ha scores materialitzats per aquesta versió.")
    st.stop()

team_labels = {str(row.team_id): str(row.display_name) for row in teams.itertuples(index=False)}
team_id = st.selectbox("Equip", list(team_labels), format_func=lambda x: team_labels[x])
players = list_team_players(path, team_id)

if players.empty:
    st.info("No hi ha jugadors disponibles per aquest equip.")
    st.stop()

player_labels = {
    str(row.player_id): f"{row.player} · {int(row.scored_matches)} partits amb score"
    for row in players.itertuples(index=False)
}
player_id = st.selectbox("Jugador", list(player_labels), format_func=lambda x: player_labels[x])
history = get_player_score_history(path, team_id, player_id)
latest = get_latest_player_score(path, team_id, player_id)

if latest is None:
    st.warning(
        "Aquest jugador no té cap score posicional elegible. Si les aparicions són com a suplent i la font "
        "no informa del rol tàctic, el sistema no imputa una posició."
    )
else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Performance Score", f"{fmt_score(latest['performance_score'])}/100")
    c2.metric("Confiança d'evidència", f"{fmt_score(latest['score_evidence_confidence'])}%")
    c3.metric("Grup posicional", str(latest["position_group"]))
    c4.metric("Dimensions disponibles", int(latest["dimension_coverage_count"]))

    st.subheader("Dimensions de l'últim score")
    dimension_rows = []
    for key, label in DIMENSIONS:
        dimension_rows.append({"Dimensió": label, "Score": latest.get(key)})
    dimension_df = pd.DataFrame(dimension_rows)
    dimension_df["Score"] = pd.to_numeric(dimension_df["Score"], errors="coerce").round(1)
    st.dataframe(dimension_df, hide_index=True, width="stretch")

st.subheader("Evolució")
chart = history.dropna(subset=["performance_score"]).copy()
if chart.empty:
    st.info("No hi ha historial de scores elegibles.")
else:
    chart["match_date"] = pd.to_datetime(chart["match_date"])
    st.line_chart(chart.set_index("match_date")[["performance_score"]])

st.subheader("Historial jugador-partit")
details = history.copy()
if not details.empty:
    details["match_date"] = pd.to_datetime(details["match_date"]).dt.date
    numeric = [
        "attacking_threat",
        "creation_progression",
        "defensive_contribution",
        "finishing",
        "discipline",
        "performance_score",
        "score_evidence_confidence",
    ]
    for col in numeric:
        details[col] = pd.to_numeric(details[col], errors="coerce").round(1)
    details = details.rename(
        columns={
            "match_date": "Data",
            "primary_role": "Rol font",
            "position_group": "Grup",
            "dimension_coverage_count": "N dimensions",
            "attacking_threat": "Amenaça",
            "creation_progression": "Creació",
            "defensive_contribution": "Defensa",
            "finishing": "Finalització",
            "discipline": "Disciplina",
            "performance_score": "Score",
            "score_evidence_confidence": "Confiança %",
            "score_status": "Estat",
        }
    )
    details = details.drop(columns=["match_id", "position_mapping_status"], errors="ignore")
    st.dataframe(details, hide_index=True, width="stretch")

st.caption(
    "Metodologia: percentils dins del grup posicional, mínim 3 dimensions i pesos posicionals experimentals. "
    "Els suplents sense rol tàctic observable no reben posició imputada. Porter en camí separat."
)
