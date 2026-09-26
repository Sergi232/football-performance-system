"""Professional Match Mode: immediate post-match staff view."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import get_team_matches, list_teams
from app.match_rating_access import MATCH_RATING_VERSION, get_match_ratings
from app.ui_theme import apply_professional_theme, position_label, score_card
from reports.data_builder import build_match_report_data
from reports.pdf_engine import render_pdf_bytes

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(page_title="Partit · Football Performance System", page_icon="⚽", layout="wide")
apply_professional_theme()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def result_text(sf: object, sa: object) -> str:
    if pd.isna(sf) or pd.isna(sa):
        return "—"
    a, b = int(sf), int(sa)
    return f"{'V' if a>b else 'E' if a==b else 'D'} {a}-{b}"


path = db_path()
if not path.exists():
    st.error(f"No s'ha trobat la base de dades: {path}")
    st.stop()

teams = list_teams(path)
team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
team_id = st.selectbox("Equip", options=list(team_labels), format_func=lambda x: team_labels[x])

matches = get_team_matches(path, team_id)
if matches.empty:
    st.info("No hi ha partits disponibles.")
    st.stop()

matches = matches.copy()
matches["match_date"] = pd.to_datetime(matches["match_date"])
match_map = {
    str(r.match_id): f"{r.match_date.date()} · {r.opponent} · {result_text(r.score_for, r.score_against)}"
    for r in matches.itertuples(index=False)
}
match_id = st.selectbox("Partit", options=list(match_map), format_func=lambda x: match_map[x])
match = matches.loc[matches["match_id"].astype(str) == match_id].iloc[0]

try:
    ratings = get_match_ratings(path, team_id, match_id)
except Exception as exc:
    st.warning(f"El Match Rating encara no està materialitzat: {exc}")
    st.stop()

left, right = st.columns([3, 1])
with left:
    st.markdown(
        f"""
        <div class="fps-hero">
            <div class="fps-kicker">MATCH MODE</div>
            <div class="fps-player-name">{team_labels[team_id]} vs {match['opponent']}</div>
            <div class="fps-player-meta">{match['match_date'].date()} · {result_text(match['score_for'], match['score_against'])} · {match['starting_formation'] or 'Formació no disponible'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with right:
    try:
        payload = build_match_report_data(path, team_id, match_id)
        pdf_bytes = render_pdf_bytes(payload)
        st.download_button("Exportar informe PDF", pdf_bytes, file_name=f"match_{match_id}.pdf", mime="application/pdf", use_container_width=True)
    except Exception as exc:
        st.warning(f"PDF no disponible: {exc}")

rated = ratings[ratings["match_rating_10"].notna()].copy()
median_rating = rated["match_rating_10"].median() if not rated.empty else None
median_conf = rated["match_rating_confidence"].median() if not rated.empty else None

c1, c2, c3, c4 = st.columns(4)
with c1:
    score_card("Jugadors utilitzats", str(len(ratings)), "Participants amb minuts")
with c2:
    score_card("Jugadors amb rating", f"{len(rated)}/{len(ratings)}", "Cobertura del partit")
with c3:
    score_card("Rating mediana", "—" if median_rating is None else f"{median_rating:.1f}/10", "Resum descriptiu")
with c4:
    score_card("Confiança mediana", "—" if median_conf is None else f"{median_conf:.0f}%", "Cobertura d'evidència")

st.write("")
tab_summary, tab_players, tab_dimensions = st.tabs(["Resum", "Jugadors", "Dimensions"])

with tab_summary:
    st.subheader("Ratings del partit")
    display = ratings.copy()
    display["Perfil"] = display["position_group"].map(lambda x: "Porter" if x == "GK" else position_label(x))
    display["Rating"] = pd.to_numeric(display["match_rating_10"], errors="coerce").round(1)
    display["Confiança %"] = pd.to_numeric(display["match_rating_confidence"], errors="coerce").round(0)
    display["Min"] = pd.to_numeric(display["minutes_played"], errors="coerce").round(0)
    display = display[["player", "Perfil", "Min", "started", "Rating", "Confiança %"]]
    display.columns = ["Jugador", "Perfil", "Min", "Titular", "Rating", "Confiança %"]
    st.dataframe(display, hide_index=True, use_container_width=True)

with tab_players:
    for r in ratings.itertuples(index=False):
        profile = "Porter" if r.position_group == "GK" else position_label(r.position_group)
        with st.expander(f"{r.player} · {r.match_rating_10:.1f}/10 · {profile}"):
            a, b, c = st.columns(3)
            a.metric("Rating", f"{r.match_rating_10:.1f}/10")
            b.metric("Confiança", f"{r.match_rating_confidence:.0f}%")
            c.metric("Minuts", f"{r.minutes_played:.0f}")
            st.caption(f"{r.match_rating_status} · {r.match_rating_context}")

with tab_dimensions:
    outfield = ratings[ratings["rating_path"] == "OUTFIELD"].copy()
    if outfield.empty:
        st.info("No hi ha dimensions de jugadors de camp disponibles.")
    else:
        cols = [
            "player", "attacking_threat", "creation_progression",
            "defensive_contribution", "finishing", "discipline",
        ]
        table = outfield[cols].copy()
        for col in cols[1:]:
            table[col] = pd.to_numeric(table[col], errors="coerce").round(1)
        table.columns = ["Jugador", "Amenaça ofensiva", "Creació / progressió", "Contribució defensiva", "Finalització", "Disciplina"]
        st.dataframe(table, hide_index=True, use_container_width=True)

with st.expander("Metodologia i límits"):
    st.write(f"Match Rating: `{MATCH_RATING_VERSION}`. La nota existeix des del primer partit i no necessita historial del club.")
    st.write("La confiança indica cobertura d'evidència. Els casos amb evidència insuficient mantenen una nota neutral explícitament marcada; no s'inventen accions.")
