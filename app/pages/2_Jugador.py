"""DASHBOARD-02 — professional integrated player performance view."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import (
    get_latest_player_gate,
    get_player_feature_history,
    get_player_match_history,
    get_squad_summary,
    list_base_features,
    list_teams,
)
from app.performance_score_access import (
    SCORE_VERSION,
    get_latest_player_score,
    get_player_score_history,
)
from app.ui_theme import (
    apply_professional_theme,
    dimension_bar,
    hero,
    position_label,
    score_card,
)
from reports.data_builder import build_player_report_data
from reports.pdf_engine import render_pdf_bytes

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
DIMENSIONS = [
    ("attacking_threat", "Amenaça ofensiva"),
    ("creation_progression", "Creació / progressió"),
    ("defensive_contribution", "Contribució defensiva"),
    ("finishing", "Finalització"),
    ("discipline", "Disciplina"),
]
FEATURE_LABELS = {
    "pass_completion_rate": "Precisió de passada",
    "shots_total_per90": "Rematades / 90",
    "goals_per90": "Gols / 90",
    "assists_per90": "Assistències / 90",
    "tackle_success_rate": "Èxit en entrades",
    "interceptions_per90": "Intercepcions / 90",
}

st.set_page_config(page_title="Jugador · Football Performance System", page_icon="⚽", layout="wide")
apply_professional_theme()


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


def render_pdf(path: Path, team_id: str, player_id: str, player_name: str) -> None:
    try:
        payload = build_player_report_data(path, team_id, player_id)
        pdf_bytes = render_pdf_bytes(payload)
    except Exception as exc:
        st.warning(f"No s'ha pogut generar l'informe: {exc}")
        return
    filename = "_".join(player_name.strip().split()) or "player"
    st.download_button(
        "Exportar informe PDF",
        data=pdf_bytes,
        file_name=f"player_{filename}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


def is_goalkeeper(row: pd.Series) -> bool:
    observed = row.get("observed_roles")
    if observed is None or pd.isna(observed):
        return False
    text = str(observed).lower()
    return any(token in text for token in ["goalkeeper", "goal keeper", "keeper", "porter", "portero"])


def latest_role_text(latest_score: dict | None, row: pd.Series) -> str:
    if latest_score is not None:
        return position_label(latest_score.get("position_group"))
    if is_goalkeeper(row):
        return "Porter"
    observed = row.get("observed_roles")
    if observed is not None and pd.notna(observed):
        return str(observed)
    return "Rol no disponible"


def evidence_label(value: object) -> str:
    mapping = {
        "DIRECT_SIGNED": "Evidència directa",
        "CONTRIBUTION_FALLBACK": "Contribució observada de suport",
        "MISSING": "Sense evidència",
    }
    if value is None or pd.isna(value):
        return "—"
    return mapping.get(str(value), str(value))


path = db_path()
if not path.exists():
    st.error(f"No s'ha trobat la base de dades: {path}")
    st.stop()

try:
    teams = list_teams(path)
except Exception as exc:
    st.error(f"No s'ha pogut llegir la base de dades: {exc}")
    st.stop()

if teams.empty:
    st.info("No hi ha equips disponibles.")
    st.stop()

select_left, select_right, select_action = st.columns([1.0, 1.5, 0.7])
team_labels = {str(row.team_id): str(row.display_name) for row in teams.itertuples(index=False)}
with select_left:
    team_id = st.selectbox("Equip", options=list(team_labels), format_func=lambda x: team_labels[x])

squad = get_squad_summary(path, team_id)
if squad.empty:
    st.info("No hi ha jugadors disponibles per aquest equip.")
    st.stop()

player_labels = {str(row.player_id): str(row.player) for row in squad.itertuples(index=False)}
with select_right:
    player_id = st.selectbox("Jugador", options=list(player_labels), format_func=lambda x: player_labels[x])

player_name = player_labels[player_id]
row = squad.loc[squad["player_id"] == player_id].iloc[0]

try:
    score_history = get_player_score_history(path, team_id, player_id)
    latest_score = get_latest_player_score(path, team_id, player_id)
except Exception:
    score_history = pd.DataFrame()
    latest_score = None

with select_action:
    st.write("")
    st.write("")
    render_pdf(path, team_id, player_id, player_name)

meta = f"{safe_int(row['minutes'])} min · {safe_int(row['appearances'])} aparicions"
hero(player_name=player_name, team_name=team_labels[team_id], role=latest_role_text(latest_score, row), meta=meta)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Aparicions", safe_int(row["appearances"]))
k2.metric("Titularitats", safe_int(row["starts"]))
k3.metric("Minuts", safe_int(row["minutes"]))
k4.metric("Gols", safe_int(row["goals"]))
k5.metric("Assistències", safe_int(row["assists"]))

st.write("")
tab_overview, tab_trend, tab_technical, tab_expert, tab_matches = st.tabs(["Resum", "Evolució", "Tècnic", "Motor expert", "Partits"])

with tab_overview:
    if latest_score is None:
        if is_goalkeeper(row):
            st.info("El Performance Score de porter encara no està activat en aquesta baseline. El camí GK es valida per separat i no es força un score amb la metodologia dels jugadors de camp.")
        else:
            st.info("No hi ha Performance Score posicional elegible per a l'historial disponible. Quan la font no informa d'un rol tàctic observable, el sistema no imputa una posició.")
    else:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            score_card("Performance Score", f"{safe_float(latest_score['performance_score'])}/100", "Comparació relativa dins del grup posicional")
        with c2:
            score_card("Confiança d'evidència", f"{safe_float(latest_score['score_evidence_confidence'])}%", "Cobertura de l'evidència prevista per al rol")
        with c3:
            score_card("Perfil posicional", position_label(latest_score.get("position_group")), f"{safe_int(latest_score.get('dimension_coverage_count'))} dimensions disponibles")

        st.write("")
        left, right = st.columns([1.0, 1.35])
        with left:
            st.subheader("Dimensions de rendiment")
            st.markdown("<div class='fps-section-note'>Lectura de l'últim score elegible. Escala relativa 0–100.</div>", unsafe_allow_html=True)
            for key, label in DIMENSIONS:
                dimension_bar(label, latest_score.get(key))
                source = latest_score.get(f"{key}_evidence")
                if source is not None and not pd.isna(source):
                    st.caption(evidence_label(source))

        with right:
            st.subheader("Evolució del score")
            chart = score_history.dropna(subset=["performance_score"]).copy()
            if chart.empty:
                st.info("Encara no hi ha prou historial per mostrar evolució.")
            else:
                chart["match_date"] = pd.to_datetime(chart["match_date"])
                st.line_chart(chart.set_index("match_date")[["performance_score"]], height=330, use_container_width=True)
                recent = chart.sort_values("match_date").tail(5)[["match_date", "position_group", "performance_score", "score_evidence_confidence"]].copy()
                recent["match_date"] = recent["match_date"].dt.date
                recent["position_group"] = recent["position_group"].map(position_label)
                recent["performance_score"] = recent["performance_score"].round(1)
                recent["score_evidence_confidence"] = recent["score_evidence_confidence"].round(0)
                recent.columns = ["Data", "Posició", "Score", "Confiança %"]
                st.dataframe(recent, hide_index=True, use_container_width=True)

    with st.expander("Metodologia i traçabilitat"):
        st.write(f"Versió: `{SCORE_VERSION}`. El score és experimental, específic per grup posicional i descriptiu. No és una etiqueta bo/dolent ni una recomanació tàctica.")
        if latest_score is not None:
            fallback_n = latest_score.get("fallback_dimension_count")
            st.write(f"Dimensions cobertes amb contribució observada de suport: {safe_int(fallback_n)}")
        if is_goalkeeper(row):
            st.write("Porter: camí GK separat; el score de jugador de camp no s'aplica.")
        observed_roles = row.get("observed_roles")
        st.write("Rols observats a la font: " + (str(observed_roles) if observed_roles is not None and pd.notna(observed_roles) else "no disponibles"))

with tab_trend:
    st.subheader("Evolució temporal")
    score_chart = score_history.dropna(subset=["performance_score"]).copy()
    if not score_chart.empty:
        score_chart["match_date"] = pd.to_datetime(score_chart["match_date"])
        st.line_chart(score_chart.set_index("match_date")[["performance_score"]], height=300, use_container_width=True)
    features = list_base_features(path, player_id)
    if features:
        preferred = ["pass_completion_rate", "shots_total_per90", "goals_per90", "assists_per90", "tackle_success_rate", "interceptions_per90"]
        ordered = [f for f in preferred if f in features] + [f for f in features if f not in preferred]
        feature_name = st.selectbox("Mètrica", ordered, format_func=lambda x: FEATURE_LABELS.get(x, x.replace("_", " ").title()), key="player_trend_metric")
        feature_history = get_player_feature_history(path, player_id, feature_name)
        feature_chart = feature_history.dropna(subset=["feature_value"]).copy()
        if not feature_chart.empty:
            feature_chart["match_date"] = pd.to_datetime(feature_chart["match_date"])
            st.line_chart(feature_chart.set_index("match_date")[["feature_value"]], height=300, use_container_width=True)

with tab_technical:
    st.subheader("Rendiment tècnic")
    history = get_player_match_history(path, team_id, player_id)
    if not history.empty:
        technical = history.copy()
        technical["match_date"] = pd.to_datetime(technical["match_date"]).dt.date
        technical = technical[["match_date", "opponent", "minutes", "primary_role", "passes_total", "passes_completed", "assists", "shots_total", "goals", "tackles_total", "tackles_won", "interceptions", "turnovers", "dispossessed"]]
        technical.columns = ["Data", "Rival", "Min", "Rol", "Passades", "Passades completades", "Assist.", "Rematades", "Gols", "Entrades", "Entrades guanyades", "Intercepcions", "Pèrdues", "Despossessions"]
        st.dataframe(technical, hide_index=True, use_container_width=True)

with tab_expert:
    st.subheader("Motor expert")
    gate = get_latest_player_gate(path, team_id, player_id)
    if gate is None:
        st.info("No hi ha estat expert disponible per aquest jugador.")
    else:
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Rol observat", gate["observed_role"] or "—")
        g2.metric("Historial mateix rol", gate["same_role_history"] or "—")
        try:
            coverage = float(gate["evidence_coverage"])
        except (TypeError, ValueError):
            coverage = None
        g3.metric("Cobertura d'evidència", "—" if coverage is None else f"{coverage:.0%}")
        g4.metric("Senyals avaluables", gate["evaluable_signals"] or "—")
        st.info(str(gate["final_status"] or "Sense estat disponible").replace("_", " ").title())
        with st.expander("Detall tècnic del gate"):
            st.json(gate)

with tab_matches:
    st.subheader("Partits")
    history = get_player_match_history(path, team_id, player_id)
    if not history.empty:
        details = history.copy()
        details["match_date"] = pd.to_datetime(details["match_date"]).dt.date
        if not score_history.empty:
            score_merge = score_history[["match_id", "performance_score", "score_evidence_confidence"]].copy()
            details = details.merge(score_merge, on="match_id", how="left")
        display_cols = ["match_date", "opponent", "venue", "started", "minutes", "primary_role", "goals", "assists", "performance_score", "score_evidence_confidence"]
        for col in display_cols:
            if col not in details.columns:
                details[col] = pd.NA
        details = details[display_cols]
        details["performance_score"] = pd.to_numeric(details["performance_score"], errors="coerce").round(1)
        details["score_evidence_confidence"] = pd.to_numeric(details["score_evidence_confidence"], errors="coerce").round(0)
        details.columns = ["Data", "Rival", "L/V", "Titular", "Min", "Rol", "Gols", "Assist.", "Score", "Confiança %"]
        st.dataframe(details, hide_index=True, use_container_width=True)
