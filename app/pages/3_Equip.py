"""DASHBOARD-03 — professional Team Mode for coaching staff."""
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
    get_squad_summary,
    get_team_matches,
    get_team_overview,
    list_teams,
)
from app.performance_score_access import SCORE_VERSION, get_team_score_snapshot  # noqa: E402
from app.ui_theme import apply_professional_theme, position_label, score_card  # noqa: E402
from reports.data_builder import build_team_report_data  # noqa: E402
from reports.pdf_engine import render_pdf_bytes  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(page_title="Equip · Football Performance System", page_icon="⚽", layout="wide")
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


def render_team_pdf(path: Path, team_id: str, team_name: str) -> None:
    try:
        payload = build_team_report_data(path, team_id)
        pdf_bytes = render_pdf_bytes(payload)
    except Exception as exc:
        st.warning(f"No s'ha pogut generar l'informe: {exc}")
        return
    filename = "_".join(team_name.strip().split()) or "team"
    st.download_button(
        "Exportar informe PDF",
        data=pdf_bytes,
        file_name=f"team_{filename}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


def result_text(score_for: object, score_against: object) -> str:
    if pd.isna(score_for) or pd.isna(score_against):
        return "—"
    sf = int(score_for)
    sa = int(score_against)
    outcome = "V" if sf > sa else "E" if sf == sa else "D"
    return f"{outcome} {sf}-{sa}"


path = db_path()
if not path.exists():
    st.error(f"No s'ha trobat la base de dades: {path}")
    st.stop()

teams = list_teams(path)
if teams.empty:
    st.info("No hi ha equips disponibles.")
    st.stop()

selector, action = st.columns([3.0, 1.0])
team_labels = {str(row.team_id): str(row.display_name) for row in teams.itertuples(index=False)}
with selector:
    team_id = st.selectbox("Equip", options=list(team_labels), format_func=lambda x: team_labels[x])
team_name = team_labels[team_id]
with action:
    st.write("")
    st.write("")
    render_team_pdf(path, team_id, team_name)

overview = get_team_overview(path, team_id)
squad = get_squad_summary(path, team_id)
matches = get_team_matches(path, team_id)
try:
    score_snapshot = get_team_score_snapshot(path, team_id)
except Exception:
    score_snapshot = pd.DataFrame()

st.markdown(
    f"""
    <div class="fps-hero">
        <div class="fps-kicker">TEAM MODE</div>
        <div class="fps-player-name">{team_name}</div>
        <div class="fps-player-meta">{safe_int(overview['matches'])} partits · {safe_int(overview['players'])} jugadors · anàlisi de rendiment</div>
    </div>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Partits", safe_int(overview["matches"]))
k2.metric("Jugadors", safe_int(overview["players"]))
k3.metric("Minuts jugador", safe_int(overview["player_minutes"]))
k4.metric("Gols", safe_int(overview["goals"]))
k5.metric("Assistències", safe_int(overview["assists"]))

st.write("")
tab_overview, tab_squad, tab_trends, tab_matches = st.tabs(
    ["Resum", "Plantilla", "Tendències", "Partits"]
)

with tab_overview:
    if score_snapshot.empty:
        st.info("La capa de Performance Score no està disponible per aquest equip.")
    else:
        scored = score_snapshot[score_snapshot["latest_score"].notna()].copy()
        players_with_score = len(scored)
        median_score = scored["latest_score"].median() if not scored.empty else None
        median_conf = scored["latest_confidence"].median() if not scored.empty else None

        c1, c2, c3 = st.columns(3)
        with c1:
            score_card(
                "Jugadors amb score",
                f"{players_with_score}/{len(score_snapshot)}",
                "Cobertura actual de la plantilla",
            )
        with c2:
            score_card(
                "Mediana score actual",
                safe_float(median_score),
                "Mediana descriptiva entre rols comparables",
            )
        with c3:
            score_card(
                "Mediana confiança",
                f"{safe_float(median_conf)}%" if median_conf is not None and not pd.isna(median_conf) else "—",
                "Cobertura de l'evidència prevista",
            )

        left, right = st.columns([1.25, 1])
        with left:
            st.subheader("Score actual per jugador")
            st.markdown(
                "<div class='fps-section-note'>Vista descriptiva. Els scores són específics per rol i no formen un rànquing global de qualitat.</div>",
                unsafe_allow_html=True,
            )
            chart = scored[["player", "latest_score"]].dropna().sort_values("player")
            if chart.empty:
                st.info("No hi ha scores elegibles.")
            else:
                st.bar_chart(chart.set_index("player")[["latest_score"]], height=420, use_container_width=True)

        with right:
            st.subheader("Últims partits")
            recent_matches = matches.head(8).copy()
            if recent_matches.empty:
                st.info("No hi ha partits disponibles.")
            else:
                recent_matches["match_date"] = pd.to_datetime(recent_matches["match_date"]).dt.date
                recent_matches["result"] = recent_matches.apply(
                    lambda r: result_text(r["score_for"], r["score_against"]), axis=1
                )
                recent_matches = recent_matches[["match_date", "venue", "opponent", "result", "starting_formation"]]
                recent_matches.columns = ["Data", "L/V", "Rival", "Resultat", "Formació"]
                st.dataframe(recent_matches, hide_index=True, use_container_width=True)

with tab_squad:
    st.subheader("Plantilla")
    st.markdown(
        "<div class='fps-section-note'>Resum operatiu de disponibilitat, participació i rendiment materialitzat.</div>",
        unsafe_allow_html=True,
    )
    roster = squad.merge(score_snapshot, on=["player_id", "player"], how="left") if not score_snapshot.empty else squad.copy()
    if "position_group" in roster.columns:
        roster["position_group"] = roster["position_group"].map(position_label)
    for col in ["latest_score", "latest_confidence", "avg_last5", "avg_previous5", "trend_delta_5v5"]:
        if col in roster.columns:
            roster[col] = pd.to_numeric(roster[col], errors="coerce").round(1)
    wanted = [
        "player", "observed_roles", "appearances", "starts", "minutes",
        "position_group", "latest_score", "latest_confidence", "avg_last5", "trend_delta_5v5",
    ]
    for col in wanted:
        if col not in roster.columns:
            roster[col] = pd.NA
    roster = roster[wanted].sort_values(["minutes", "player"], ascending=[False, True])
    roster.columns = [
        "Jugador", "Rols observats", "Aparicions", "Titularitats", "Minuts",
        "Perfil", "Score actual", "Confiança %", "Mitjana últims 5", "Delta 5 vs 5",
    ]
    st.dataframe(roster, hide_index=True, use_container_width=True)

with tab_trends:
    st.subheader("Tendències de rendiment")
    st.markdown(
        "<div class='fps-section-note'>Delta descriptiu = mitjana dels últims 5 scores elegibles − mitjana dels 5 anteriors. No s'aplica cap llindar ni etiqueta millor/pitjor.</div>",
        unsafe_allow_html=True,
    )
    if score_snapshot.empty:
        st.info("No hi ha dades de score disponibles.")
    else:
        trend = score_snapshot.copy()
        trend["Perfil"] = trend["position_group"].map(position_label)
        for col in ["latest_score", "avg_last5", "avg_previous5", "trend_delta_5v5"]:
            trend[col] = pd.to_numeric(trend[col], errors="coerce").round(1)
        trend = trend[[
            "player", "Perfil", "scored_matches", "latest_score", "avg_last5",
            "avg_previous5", "trend_delta_5v5", "n_last5", "n_previous5",
        ]].sort_values("player")
        trend.columns = [
            "Jugador", "Perfil", "Partits amb score", "Score actual", "Mitjana últims 5",
            "Mitjana 5 anteriors", "Delta 5 vs 5", "N últims", "N anteriors",
        ]
        st.dataframe(trend, hide_index=True, use_container_width=True)

with tab_matches:
    st.subheader("Partits")
    if matches.empty:
        st.info("No hi ha partits disponibles.")
    else:
        display = matches.copy()
        display["match_date"] = pd.to_datetime(display["match_date"]).dt.date
        display["result"] = display.apply(lambda r: result_text(r["score_for"], r["score_against"]), axis=1)
        display = display[["match_date", "venue", "opponent", "result", "starting_formation"]]
        display.columns = ["Data", "L/V", "Rival", "Resultat", "Formació"]
        st.dataframe(display, hide_index=True, use_container_width=True)

with st.expander("Metodologia i límits"):
    st.write(
        f"Performance Score: `{SCORE_VERSION}`. Els scores es comparen dins del grup posicional. "
        "La vista d'equip no converteix aquests valors en recomanacions ni en un rànquing global entre posicions."
    )
    st.write(
        "La tendència 5 vs 5 és una transformació descriptiva transparent i no activa cap alerta automàtica. "
        "Els llindars d'alerta es definiran només quan estiguin validats."
    )
