"""In-app AI assistant over structured, validated football-performance context."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import get_squad_summary, get_team_matches, list_teams
from app.ui_theme import apply_professional_theme
from llm.context_builder import build_match_context, build_player_context, build_team_context
from llm.openai_provider import answer_question, provider_available

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(page_title="Assistent IA · Football Performance System", page_icon="⚽", layout="wide")
apply_professional_theme()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def result_text(sf: object, sa: object) -> str:
    if pd.isna(sf) or pd.isna(sa):
        return "—"
    return f"{int(sf)}-{int(sa)}"


path = db_path()
if not path.exists():
    st.error(f"No s'ha trobat la base de dades: {path}")
    st.stop()

teams = list_teams(path)
if teams.empty:
    st.info("No hi ha equips disponibles.")
    st.stop()

st.markdown("<div class='fps-kicker'>COACH ASSISTANT</div>", unsafe_allow_html=True)
st.title("Assistent IA")
st.caption("Explica resultats ja calculats pel sistema. No calcula ratings, no inventa mètriques i no emet recomanacions tàctiques no validades.")

left, right = st.columns([1, 1])
team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
with left:
    team_id = st.selectbox("Equip", list(team_labels), format_func=lambda x: team_labels[x])
with right:
    scope_label = st.selectbox("Context", ["Equip", "Jugador", "Partit"])

context = None
context_title = team_labels[team_id]

if scope_label == "Equip":
    context = build_team_context(path, team_id)
    suggestions = [
        "Resumeix les dades disponibles de l'equip.",
        "Quina informació de Match Rating tenim disponible?",
        "Explica'm què puc consultar sobre l'evolució de l'equip.",
    ]
elif scope_label == "Jugador":
    squad = get_squad_summary(path, team_id)
    labels = {str(r.player_id): str(r.player) for r in squad.itertuples(index=False)}
    player_id = st.selectbox("Jugador", list(labels), format_func=lambda x: labels[x])
    context_title = labels[player_id]
    context = build_player_context(path, team_id, player_id)
    suggestions = [
        "Quina nota ha tret a l'últim partit?",
        "Per què té aquest Match Rating?",
        "Quin és el seu Performance Index actual?",
        "Explica'm el seu rol i l'evidència disponible.",
    ]
else:
    matches = get_team_matches(path, team_id).copy()
    matches["match_date"] = pd.to_datetime(matches["match_date"])
    labels = {
        str(r.match_id): f"{r.match_date.date()} · {r.opponent} · {result_text(r.score_for, r.score_against)}"
        for r in matches.itertuples(index=False)
    }
    match_id = st.selectbox("Partit", list(labels), format_func=lambda x: labels[x])
    context_title = labels[match_id]
    context = build_match_context(path, team_id, match_id)
    suggestions = [
        "Resumeix què ha passat en aquest partit.",
        "Quants Match Ratings tenim en aquest partit?",
        "Quines observacions directes tenim del partit?",
    ]

st.markdown(f"#### Context actiu · {context_title}")
cols = st.columns(len(suggestions))
for idx, suggestion in enumerate(suggestions):
    if cols[idx].button(suggestion, use_container_width=True, key=f"suggest_{scope_label}_{idx}"):
        st.session_state["fps_assistant_question"] = suggestion

question = st.text_input(
    "Pregunta",
    value=st.session_state.get("fps_assistant_question", ""),
    placeholder="Ex.: Per què té aquest Match Rating?",
)

if st.button("Preguntar", type="primary", use_container_width=False):
    if not question.strip():
        st.warning("Escriu una pregunta.")
    else:
        result = answer_question(question, context or {}, prefer_llm=True)
        st.markdown("### Resposta")
        st.write(result.text)
        with st.expander("Traçabilitat de l'assistent"):
            st.write(f"Mode: `{result.mode}`")
            if result.model:
                st.write(f"Model: `{result.model}`")
            st.write("Provider extern configurat: " + ("sí" if provider_available() else "no"))
            if result.error:
                st.write(f"Fallback activat: `{result.error}`")

with st.expander("Límits i seguretat"):
    st.write("L'assistent rep dades estructurades de Data / Analytics / Decision Engine.")
    st.write("Pot explicar Match Rating, Performance Index, features i resultats del motor expert, però no els recalcula.")
    st.write("Preguntes que exigeixen rankings o recomanacions tàctiques no validades queden bloquejades.")
