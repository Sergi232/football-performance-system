"""Asistente IA local basado en Ollama y herramientas validadas del sistema."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.coach_ui import page_header
from app.data_access import get_squad_summary, get_team_matches, list_teams
from app.presentation import (
    build_opponent_aliases,
    build_player_name_aliases,
    demo_mode,
    display_team_name,
    replace_known_names,
)
from app.ui_theme import apply_professional_theme, sidebar_navigation
from llm.coach_agent_fast import DEFAULT_MODEL, ollama_status, run_coach_agent_turn

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
TOOL_LABELS = {
    "rank_players": "Ranking estructurado de jugadores",
    "query_team_stats": "Estadísticas observadas del equipo",
    "get_team_snapshot": "Resumen del equipo",
    "get_data_quality": "Calidad de datos",
    "get_player_profile": "Perfil del jugador",
    "get_player_match_stats": "Historial del jugador",
    "get_match_detail": "Resumen del partido",
    "compare_players": "Comparación de jugadores",
    "get_player_gps": "Datos GPS del jugador",
}

st.set_page_config(page_title="Asistente IA · Football Performance System", page_icon="💬", layout="wide")
apply_professional_theme()
sidebar_navigation()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def history_key(team_id: str) -> str:
    return f"fps_local_agent_history::{team_id}"


def _replace_aliases_with_real(text: str, reverse_map: dict[str, str]) -> str:
    if not demo_mode():
        return text
    out = str(text)
    for alias in sorted(reverse_map, key=len, reverse=True):
        out = out.replace(alias, reverse_map[alias])
    return out


def tools_label(values: list[str] | tuple[str, ...]) -> str:
    if not values:
        return "ninguna"
    return ", ".join(TOOL_LABELS.get(str(value), "Consulta estructurada") for value in values)


path = db_path()
if not path.exists():
    st.error(f"No se ha encontrado la base de datos: {path}")
    st.stop()

teams = list_teams(path)
if teams.empty:
    st.info("No hay equipos disponibles.")
    st.stop()

page_header(
    "ASISTENTE IA · LOCAL",
    "Asistente IA",
    "Pregunta de forma natural. Las consultas claras se resuelven de forma determinista y el modelo local solo interpreta lenguaje ambiguo cuando hace falta.",
    "Procesamiento local · Ollama opcional para lenguaje ambiguo",
)

raw_team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
team_ids = list(raw_team_labels)
display_team_labels = {tid: display_team_name(raw_team_labels[tid], team_ids.index(tid) + 1) for tid in team_ids}
selector, status_col, action = st.columns([1.6, 1.0, 0.55])
with selector:
    team_id = st.selectbox("Equipo", team_ids, format_func=lambda x: display_team_labels[x])
with status_col:
    model = st.text_input("Modelo local", value=os.environ.get("FPS_LOCAL_LLM_MODEL", DEFAULT_MODEL))
with action:
    st.write("")
    st.write("")
    if st.button("Limpiar chat", width="stretch"):
        st.session_state[history_key(team_id)] = []
        st.rerun()

raw_team_name = raw_team_labels[team_id]
team_name = display_team_labels[team_id]
squad = get_squad_summary(path, team_id)
matches = get_team_matches(path, team_id)
player_name_aliases = build_player_name_aliases(squad)
opponent_aliases = build_opponent_aliases(matches.get("opponent", pd.Series(dtype=str)).tolist())
reverse_aliases = {alias: real for real, alias in player_name_aliases.items()}
reverse_aliases.update({alias: real for real, alias in opponent_aliases.items()})
if demo_mode():
    reverse_aliases[team_name] = raw_team_name


def to_display(text: object) -> str:
    return replace_known_names(
        text,
        player_name_aliases=player_name_aliases,
        opponent_aliases=opponent_aliases,
        team_name=raw_team_name,
        team_alias=team_name,
    )


def to_runtime(text: object) -> str:
    return _replace_aliases_with_real(str(text), reverse_aliases)


status = ollama_status()
installed = status.get("models") or []
model_ready = bool(status.get("available") and model in installed)

if model_ready:
    st.success(f"Modo híbrido disponible · {model} · consultas claras sin LLM, lenguaje ambiguo con Qwen")
elif not status.get("available"):
    st.warning("Modo determinista disponible. Ollama no está activo, por lo que las consultas que requieran interpretación semántica no podrán resolverse.")
    st.code("ollama serve", language="powershell")
    if status.get("error"):
        st.caption(status["error"])
else:
    st.warning(f"Modo determinista disponible. Falta `{model}` para interpretar consultas ambiguas.")
    st.code(f"ollama pull {model}", language="powershell")
    if installed:
        st.caption("Modelos disponibles: " + ", ".join(installed))

key = history_key(team_id)
if key not in st.session_state:
    st.session_state[key] = []

history: list[dict] = st.session_state[key]

with st.expander("¿Qué puede hacer el agente?", expanded=not history):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            - crear rankings descriptivos por Match Rating, goles, asistencias, remates, minutos y métricas GPS disponibles;
            - aplicar agregaciones y ventanas temporales soportadas;
            - resumir equipo y partidos;
            - explicar perfiles y evolución reciente;
            - comparar descriptivamente jugadores;
            - revisar calidad y cobertura de datos.
            """
        )
    with c2:
        st.markdown(
            """
            **No puede inventar:**
            - métricas o criterios no definidos;
            - quién es «el mejor», «el más completo» o «el más determinante» sin una métrica validada;
            - riesgo de lesión o fatiga;
            - alineación ideal;
            - recomendaciones tácticas no validadas.
            """
        )

if squad.empty:
    suggested_player = "un jugador"
else:
    suggested_player = to_display(str(squad.iloc[0]["player"]))
suggestions = [
    "¿Qué jugador tiene más rating?",
    "¿Quién corre más distancia por partido?",
    f"¿Cómo ha evolucionado {suggested_player}?",
    "¿Qué limitaciones de datos tenemos ahora mismo?",
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
            with st.expander("Evidencia consultada"):
                st.write("Consultas utilizadas: " + tools_label(trace.get("tools_used", [])))
                st.write(f"Rondas de interpretación semántica: {trace.get('tool_rounds', 0)}")
                st.write(f"Modelo local: `{trace.get('model', model)}`")
                if trace.get("error"):
                    st.caption(f"Incidencia: {trace['error']}")

pending = st.session_state.pop("fps_local_agent_pending", None)
question = st.chat_input("Pregunta sobre el equipo, jugadores, partidos, evolución, estadísticas o GPS...")
if pending and not question:
    question = pending

if question:
    runtime_question = to_runtime(question)
    previous = [
        {"role": m["role"], "content": to_runtime(m["content"])}
        for m in history
        if m.get("role") in {"user", "assistant"}
    ]
    history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Consultando los datos locales..."):
            result = run_coach_agent_turn(
                runtime_question,
                db_path=path,
                team_id=team_id,
                history=previous,
                model=model,
            )
        display_answer = to_display(result.text)
        st.markdown(display_answer)
        with st.expander("Evidencia consultada"):
            st.write("Consultas utilizadas: " + tools_label(list(result.tools_used)))
            st.write(f"Rondas de interpretación semántica: {result.tool_rounds}")
            st.write(f"Modelo local: `{result.model}`")
            if result.error:
                st.caption(f"Incidencia: {result.error}")

    history.append(
        {
            "role": "assistant",
            "content": display_answer,
            "trace": {
                "tools_used": list(result.tools_used),
                "tool_rounds": result.tool_rounds,
                "model": result.model,
                "error": result.error,
            },
        }
    )
    st.session_state[key] = history

with st.expander("Arquitectura y límites"):
    st.write("Flujo: pregunta → router determinista de alta confianza → Qwen solo si la intención sigue siendo ambigua → herramientas Python de solo lectura → DuckDB / Analytics / Expert System → respuesta factual determinista → entrenador.")
    st.write("Qwen no tiene acceso directo a DuckDB, no calcula Match Rating, Performance Index ni decisiones del motor experto y no redacta valores numéricos críticos por su cuenta.")
    st.write("Las consultas deterministas siguen disponibles aunque Ollama no esté activo; solo el fallback semántico depende del modelo local.")
    if demo_mode():
        st.caption("Modo demo activo: las identidades se sustituyen solo en la capa de presentación; los cálculos internos conservan los IDs originales.")
