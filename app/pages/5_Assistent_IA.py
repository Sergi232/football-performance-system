"""Open-ended local Coach Copilot powered by Ollama + validated FPS tools."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.coach_ui import page_header
from app.data_access import list_teams
from app.ui_theme import apply_professional_theme, sidebar_navigation
from llm.coach_agent_fast import DEFAULT_MODEL, ollama_status, run_coach_agent_turn

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(page_title="Assistent IA · Football Performance System", page_icon="💬", layout="wide")
apply_professional_theme()
sidebar_navigation()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def history_key(team_id: str) -> str:
    return f"fps_local_agent_history::{team_id}"


path = db_path()
if not path.exists():
    st.error(f"No s'ha trobat la base de dades: {path}")
    st.stop()

teams = list_teams(path)
if teams.empty:
    st.info("No hi ha equips disponibles.")
    st.stop()

page_header(
    "COACH COPILOT · LOCAL",
    "Assistent IA",
    "Pregunta qualsevol cosa sobre les dades de l'equip. L'agent decideix quines eines locals necessita i pot encadenar diverses consultes abans de respondre.",
    "Ollama · sense API de pagament",
)

team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
selector, status_col, action = st.columns([1.6, 1.0, 0.55])
with selector:
    team_id = st.selectbox("Equip", list(team_labels), format_func=lambda x: team_labels[x])
with status_col:
    model = st.text_input("Model local", value=os.environ.get("FPS_LOCAL_LLM_MODEL", DEFAULT_MODEL))
with action:
    st.write("")
    st.write("")
    if st.button("Neteja xat", width="stretch"):
        st.session_state[history_key(team_id)] = []
        st.rerun()

status = ollama_status()
installed = status.get("models") or []
model_ready = status.get("available") and model in installed

if not status.get("available"):
    st.error("Ollama no està actiu en aquest ordinador.")
    st.code("ollama serve", language="powershell")
    if status.get("error"):
        st.caption(status["error"])
    st.stop()
elif not model_ready:
    st.warning(f"Ollama està actiu, però falta el model `{model}`.")
    st.code(f"ollama pull {model}", language="powershell")
    if installed:
        st.caption("Models disponibles: " + ", ".join(installed))
    st.stop()
else:
    st.success(f"Agent local disponible · {model} · dades processades al teu PC")

key = history_key(team_id)
if key not in st.session_state:
    st.session_state[key] = []

history: list[dict] = st.session_state[key]

with st.expander("Què pot fer l'agent?", expanded=not history):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            - resumir equip i partits;
            - explicar Match Ratings;
            - analitzar evolució recent;
            - comparar descriptivament jugadors;
            - consultar rols i motor expert;
            - revisar qualitat de dades i GPS.
            """
        )
    with c2:
        st.markdown(
            """
            **No pot inventar:**
            - ratings o mètriques;
            - risc de lesió/fatiga;
            - alineació ideal;
            - recomanacions tàctiques no validades.
            """
        )

suggestions = [
    "Qui presenta el canvi recent més gran i amb quina mostra?",
    "Resumeix-me l'últim partit i els jugadors més destacats descriptivament.",
    "Quines limitacions de dades tenim ara mateix?",
    "Compara descriptivament dos jugadors que tinguin un rol semblant.",
]
if not history:
    cols = st.columns(2)
    for idx, suggestion in enumerate(suggestions):
        if cols[idx % 2].button(suggestion, key=f"local_agent_suggestion_{idx}", width="stretch"):
            st.session_state["fps_local_agent_pending"] = suggestion
            st.rerun()

for message in history:
    role = message.get("role")
    content = message.get("content", "")
    if role not in {"user", "assistant"}:
        continue
    with st.chat_message(role):
        st.markdown(content)
        trace = message.get("trace")
        if role == "assistant" and trace:
            with st.expander("Evidència consultada"):
                st.write("Eines: " + (", ".join(trace.get("tools_used", [])) or "cap"))
                st.write(f"Voltes d'eines: {trace.get('tool_rounds', 0)}")
                st.write(f"Model local: `{trace.get('model', model)}`")
                if trace.get("error"):
                    st.caption(f"Incidència: {trace['error']}")

pending = st.session_state.pop("fps_local_agent_pending", None)
question = st.chat_input("Pregunta lliurement sobre l'equip, jugadors, partits, evolució, rols, GPS...")
if pending and not question:
    question = pending

if question:
    previous = [{"role": m["role"], "content": m["content"]} for m in history if m.get("role") in {"user", "assistant"}]
    history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Consultant les dades locals..."):
            result = run_coach_agent_turn(
                question,
                db_path=path,
                team_id=team_id,
                history=previous,
                model=model,
            )
        st.markdown(result.text)
        with st.expander("Evidència consultada"):
            st.write("Eines: " + (", ".join(result.tools_used) or "cap"))
            st.write(f"Voltes d'eines: {result.tool_rounds}")
            st.write(f"Model local: `{result.model}`")
            if result.error:
                st.caption(f"Incidència: {result.error}")

    history.append(
        {
            "role": "assistant",
            "content": result.text,
            "trace": {
                "tools_used": list(result.tools_used),
                "tool_rounds": result.tool_rounds,
                "model": result.model,
                "error": result.error,
            },
        }
    )
    st.session_state[key] = history

with st.expander("Arquitectura i límits"):
    st.write("Flux: DuckDB → Analytics / Expert System → eines Python read-only → Ollama local → entrenador.")
    st.write("El model local no té accés directe a DuckDB i no recalcula Match Rating, Performance Index ni decisions del motor expert.")
    st.write("Les dades del xat i de les eines s'envien només a Ollama en `127.0.0.1` per defecte.")
    st.write("La capa OpenAI antiga queda desacoblada i no és necessària per utilitzar aquest agent.")
