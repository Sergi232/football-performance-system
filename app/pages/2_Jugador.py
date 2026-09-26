"""DASHBOARD-02 — integrated player performance view for coaching staff."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import (  # noqa: E402
    get_latest_player_gate,
    get_player_feature_history,
    get_player_match_history,
    get_squad_summary,
    list_base_features,
    list_teams,
)
from app.performance_score_access import (  # noqa: E402
    SCORE_VERSION,
    get_latest_player_score,
    get_player_score_history,
)
from reports.data_builder import build_player_report_data  # noqa: E402
from reports.pdf_engine import render_pdf_bytes  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
POSITION_LABELS = {
    "CB": "Central",
    "FB_WB": "Lateral / Carriler",
    "DM_CM": "Migcentre / Interior",
    "AM_W": "Mitjapunta / Extrem",
    "ST": "Davanter",
    "GK": "Porter",
    "OTHER_OUTFIELD": "Rol no observable",
}
DIMENSIONS = [
    ("attacking_threat", "Amenaça ofensiva"),
    ("creation_progression", "Creació / progressió"),
    ("defensive_contribution", "Contribució defensiva"),
    ("finishing", "Finalització"),
    ("discipline", "Disciplina"),
]

st.set_page_config(page_title="Jugador", page_icon="👤", layout="wide")


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def safe_int(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{int(value):,}".replace(",", ".")


def safe_float(value: object, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{digits}f}"


def position_label(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    raw = str(value)
    return POSITION_LABELS.get(raw, raw)


def render_pdf(path: Path, team_id: str, player_id: str, player_name: str) -> None:
    try:
        payload = build_player_report_data(path, team_id, player_id)
        pdf_bytes = render_pdf_bytes(payload)
    except Exception as exc:
        st.warning(f"No s'ha pogut generar el PDF: {exc}")
        return
    filename = "_".join(player_name.strip().split()) or "player"
    st.download_button(
        "Descarregar informe PDF",
        data=pdf_bytes,
        file_name=f"player_{filename}.pdf",
        mime="application/pdf",
    )


path = db_path()
st.title("Jugador")
st.caption(
    f"Fitxa integrada · {SCORE_VERSION}. El score és experimental i descriptiu; "
    "no és una etiqueta bo/dolent ni una recomanació tàctica."
)

if not path.exists():
    st.error(f"No s'ha trobat la base de dades: {path}")
    st.stop()

try:
    teams = list_teams(path)
except Exception as exc:
    st.error(f"No s'ha pogut llegir DuckDB: {exc}")
    st.stop()

if teams.empty:
    st.info("No hi ha equips disponibles.")
    st.stop()

team_labels = {
    str(row.team_id): str(row.display_name)
    for row in teams.itertuples(index=False)
}
team_id = st.selectbox("Equip", options=list(team_labels), format_func=lambda x: team_labels[x])
squad = get_squad_summary(path, team_id)

if squad.empty:
    st.info("No hi ha jugadors disponibles per aquest equip.")
    st.stop()

player_labels = {
    str(row.player_id): str(row.player)
    for row in squad.itertuples(index=False)
}
player_id = st.selectbox("Jugador", options=list(player_labels), format_func=lambda x: player_labels[x])
player_name = player_labels[player_id]
row = squad.loc[squad["player_id"] == player_id].iloc[0]

st.header(player_name)
render_pdf(path, team_id, player_id, player_name)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Aparicions", safe_int(row["appearances"]))
c2.metric("Titularitats", safe_int(row["starts"]))
c3.metric("Minuts", safe_int(row["minutes"]))
c4.metric("Gols", safe_int(row["goals"]))
c5.metric("Assistències", safe_int(row["assists"]))
st.caption(
    f"Rols observats: {row['observed_roles'] if pd.notna(row['observed_roles']) else 'sense rol observat'}"
)

st.divider()
st.subheader("Rendiment")

try:
    score_history = get_player_score_history(path, team_id, player_id)
    latest_score = get_latest_player_score(path, team_id, player_id)
except Exception as exc:
    st.warning(f"No s'ha pogut llegir la capa de Performance Score: {exc}")
    score_history = pd.DataFrame()
    latest_score = None

if latest_score is None:
    st.info(
        "No hi ha cap score posicional elegible per aquest jugador. Si la font registra l'aparició "
        "com a suplent sense rol tàctic, el sistema no imputa una posició."
    )
else:
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Performance Score", f"{safe_float(latest_score['performance_score'])}/100")
    s2.metric("Confiança d'evidència", f"{safe_float(latest_score['score_evidence_confidence'])}%")
    s3.metric("Posició", position_label(latest_score["position_group"]))
    s4.metric("Dimensions disponibles", safe_int(latest_score["dimension_coverage_count"]))

    left, right = st.columns([1, 1.25])
    with left:
        dimension_rows = [
            {"Dimensió": label, "Score": latest_score.get(key)}
            for key, label in DIMENSIONS
        ]
        dimension_df = pd.DataFrame(dimension_rows)
        dimension_df["Score"] = pd.to_numeric(dimension_df["Score"], errors="coerce").round(1)
        st.caption("Dimensions de l'últim score elegible")
        st.dataframe(dimension_df, hide_index=True, width="stretch")

    with right:
        chart = score_history.dropna(subset=["performance_score"]).copy()
        st.caption("Evolució del Performance Score")
        if chart.empty:
            st.info("No hi ha prou historial de score.")
        else:
            chart["match_date"] = pd.to_datetime(chart["match_date"])
            st.line_chart(chart.set_index("match_date")[["performance_score"]])

st.divider()
st.subheader("Motor expert")
gate = get_latest_player_gate(path, team_id, player_id)
if gate is None:
    st.info("No hi ha estat N12000/N13000 disponible per aquest jugador.")
else:
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Rol observat", gate["observed_role"] or "—")
    g2.metric("Historial mateix rol", gate["same_role_history"] or "—")
    try:
        coverage = float(gate["evidence_coverage"])
    except (TypeError, ValueError):
        coverage = None
    g3.metric("Cobertura evidència", "—" if coverage is None else f"{coverage:.0%}")
    g4.metric("Senyals avaluables", gate["evaluable_signals"] or "—")
    st.code(str(gate["final_status"]), language=None)
    st.caption(
        "El gate expert i el Performance Score són capes diferents. El dashboard només mostra els resultats "
        "calculats pel motor i no converteix el score en una recomanació tàctica."
    )

st.divider()
st.subheader("Evolució de mètriques")
features = list_base_features(path, player_id)
if not features:
    st.info("No hi ha features disponibles.")
else:
    preferred = [
        "pass_completion_rate",
        "shots_total_per90",
        "goals_per90",
        "assists_per90",
        "tackle_success_rate",
        "interceptions_per90",
    ]
    ordered = [f for f in preferred if f in features] + [f for f in features if f not in preferred]
    feature_name = st.selectbox("Mètrica", ordered)
    feature_history = get_player_feature_history(path, player_id, feature_name)
    feature_chart = feature_history.dropna(subset=["feature_value"]).copy()
    if feature_chart.empty:
        st.info("No hi ha valors disponibles per aquesta mètrica.")
    else:
        feature_chart["match_date"] = pd.to_datetime(feature_chart["match_date"])
        st.line_chart(feature_chart.set_index("match_date")[["feature_value"]])

st.divider()
st.subheader("Historial de partits")
history = get_player_match_history(path, team_id, player_id)
if not history.empty:
    history = history.copy()
    history["match_date"] = pd.to_datetime(history["match_date"]).dt.date
    history = history.drop(columns=["match_id"], errors="ignore")
st.dataframe(history, hide_index=True, width="stretch")
