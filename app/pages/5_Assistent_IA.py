"""Asistente IA híbrido: runtime local y proveedor OpenAI opcional con clave del usuario."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.assistant_identity import build_assistant_identity_context
from app.coach_ui import page_header
from app.data_access import get_squad_summary, get_team_matches, list_teams
from app.presentation import demo_mode, display_team_name
from app.ui_theme import apply_professional_theme, sidebar_navigation
from llm.coach_agent_external import DEFAULT_OPENAI_MODEL, run_coach_agent_turn as run_openai_agent_turn
from llm.coach_agent_fast import DEFAULT_MODEL, ollama_status, run_coach_agent_turn as run_local_agent_turn

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
TOOL_LABELS = {
    "rank_players": "Ranking estructurado de jugadores",
    "compare_role_players": "Comparación estructurada por posición",
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


def history_key(team_id: str, provider: str) -> str:
    return f"fps_agent_history::{provider}::{team_id}"


def tools_label(values: list[str] | tuple[str, ...]) -> str:
    if not values:
        return "ninguna"
    return ", ".join(TOOL_LABELS.get(str(value), "Consulta estructurada") for value in values)


def render_trace(trace: dict, *, fallback_provider: str, fallback_model: str) -> None:
    """Render evidence without implying that an LLM ran when the route was deterministic."""
    tools = list(trace.get("tools_used") or [])
    rounds = int(trace.get("tool_rounds") or 0)
    provider = str(trace.get("provider_label") or fallback_provider)
    model = str(trace.get("model") or fallback_model)

    if rounds == 0 and tools:
        st.write("Ruta: **determinista + herramientas FPS**")
        st.write("LLM utilizado: **no**")
        st.write("Cálculo crítico: **Python / DuckDB / analytics materializados**")
    elif rounds == 0:
        st.write("Ruta: **preflight / guardrail local**")
        st.write("LLM utilizado: **no**")
    else:
        st.write("Ruta: **interpretación semántica + herramientas FPS**")
        st.write(f"Rondas de interpretación semántica: **{rounds}**")
        st.write(f"Proveedor semántico: **{provider}**")
        st.write(f"Modelo semántico: `{model}`")
        if tools:
            st.write("Cálculo crítico: **Python / DuckDB / analytics materializados**")

    st.write("Consultas utilizadas: " + tools_label(tools))
    if trace.get("error"):
        st.caption(f"Incidencia: {trace['error']}")


path = db_path()
if not path.exists():
    st.error(f"No se ha encontrado la base de datos: {path}")
    st.stop()

teams = list_teams(path)
if teams.empty:
    st.info("No hay equipos disponibles.")
    st.stop()

page_header(
    "ASISTENTE IA",
    "Asistente IA",
    "Pregunta de forma natural. Las consultas claras se resuelven de forma determinista; el modelo de lenguaje solo interviene cuando hace falta interpretar una consulta ambigua dentro del dominio.",
    "Los cálculos y métricas proceden de Football Performance System",
)

raw_team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
team_ids = list(raw_team_labels)
display_team_labels = {tid: display_team_name(raw_team_labels[tid], team_ids.index(tid) + 1) for tid in team_ids}

selector, provider_col, model_col, action = st.columns([1.45, 1.15, 1.15, 0.55])
with selector:
    team_id = st.selectbox("Equipo", team_ids, format_func=lambda x: display_team_labels[x])
with provider_col:
    provider_label = st.selectbox(
        "Fallback semántico",
        ["Local · Qwen", "OpenAI API · clave propia"],
        index=0,
        help="Las consultas claras no usan este modelo: se resuelven con routing determinista y herramientas FPS.",
    )
provider = "openai" if provider_label.startswith("OpenAI") else "local"
with model_col:
    if provider == "local":
        model = st.text_input("Modelo de fallback", value=os.environ.get("FPS_LOCAL_LLM_MODEL", DEFAULT_MODEL))
    else:
        model = st.text_input("Modelo de fallback", value=os.environ.get("FPS_OPENAI_MODEL", DEFAULT_OPENAI_MODEL))
with action:
    st.write("")
    st.write("")
    if st.button("Limpiar chat", width="stretch"):
        st.session_state[history_key(team_id, provider)] = []
        st.rerun()

api_key = ""
if provider == "openai":
    api_key = st.text_input(
        "OpenAI API key",
        value=os.environ.get("OPENAI_API_KEY", ""),
        type="password",
        placeholder="sk-...",
        help="Se usa para las llamadas de esta sesión. Football Performance System no la guarda en DuckDB ni en archivos del proyecto.",
    )

raw_team_name = raw_team_labels[team_id]
team_name = display_team_labels[team_id]
squad = get_squad_summary(path, team_id)
matches = get_team_matches(path, team_id)
identity = build_assistant_identity_context(
    squad,
    matches,
    raw_team_name=raw_team_name,
    team_alias=team_name,
)


def to_display(text: object) -> str:
    return identity.to_display(text)


def to_runtime(text: object) -> str:
    return identity.to_runtime(text)


if provider == "local":
    status = ollama_status()
    installed = status.get("models") or []
    model_ready = bool(status.get("available") and model in installed)

    if model_ready:
        st.success(f"Ruta determinista activa · {model} disponible solo como fallback semántico")
    elif not status.get("available"):
        st.warning("La ruta determinista está disponible. Ollama no está activo, por lo que solo fallarán las consultas ambiguas que requieran interpretación semántica.")
        st.code("ollama serve", language="powershell")
        if status.get("error"):
            st.caption(status["error"])
    else:
        st.warning(f"La ruta determinista está disponible. Falta `{model}` únicamente para interpretar consultas ambiguas.")
        st.code(f"ollama pull {model}", language="powershell")
        if installed:
            st.caption("Modelos disponibles: " + ", ".join(installed))
else:
    if api_key.strip():
        st.success(
            f"Ruta determinista activa · {model} disponible como fallback externo cuando haga falta interpretación semántica."
        )
    else:
        st.info("Introduce tu propia OpenAI API key para activar el fallback externo. Las consultas deterministas no necesitan API.")

key = history_key(team_id, provider)
if key not in st.session_state:
    st.session_state[key] = []

history: list[dict] = st.session_state[key]

with st.expander("¿Qué puede hacer el agente?", expanded=not history):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            - crear rankings descriptivos por Match Rating, goles, asistencias, remates, minutos y métricas GPS disponibles;
            - comparar jugadores de una misma posición con métricas relevantes y criterio explícito de Match Rating cuando se pregunta por rendimiento;
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
            - quién es «el mejor», «el más completo» o «el más determinante» sin una métrica o contexto validado;
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
    "Compárame las principales estadísticas de los delanteros",
    "¿Quién ha rendido mejor en la posición de central? Muéstrame las métricas",
    f"¿Cómo ha evolucionado {suggested_player}?",
]
if not history:
    cols = st.columns(2)
    for idx, suggestion in enumerate(suggestions):
        if cols[idx % 2].button(suggestion, key=f"agent_suggestion_{provider}_{idx}", width="stretch"):
            st.session_state[f"fps_agent_pending::{provider}"] = suggestion
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
                render_trace(trace, fallback_provider=provider_label, fallback_model=model)

pending = st.session_state.pop(f"fps_agent_pending::{provider}", None)
question = st.chat_input("Pregunta sobre el equipo, jugadores, partidos, evolución, estadísticas, posiciones o GPS...")
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
        with st.spinner("Consultando Football Performance System..."):
            if provider == "openai":
                if not api_key.strip():
                    result = None
                else:
                    result = run_openai_agent_turn(
                        runtime_question,
                        db_path=path,
                        team_id=team_id,
                        history=previous,
                        model=model,
                        api_key=api_key,
                    )
            else:
                result = run_local_agent_turn(
                    runtime_question,
                    db_path=path,
                    team_id=team_id,
                    history=previous,
                    model=model,
                )

        if result is None:
            st.error("Falta la OpenAI API key para usar este modo.")
        else:
            display_answer = to_display(result.text)
            leaks = identity.leaked_runtime_identities(display_answer)
            if leaks and demo_mode():
                st.error("Se ha bloqueado una respuesta por una incidencia de anonimización en la capa de presentación.")
            else:
                st.markdown(display_answer)
                trace = {
                    "tools_used": list(result.tools_used),
                    "tool_rounds": result.tool_rounds,
                    "model": result.model,
                    "provider_label": provider_label,
                    "error": result.error,
                }
                with st.expander("Evidencia consultada"):
                    render_trace(trace, fallback_provider=provider_label, fallback_model=model)

                history.append(
                    {
                        "role": "assistant",
                        "content": display_answer,
                        "trace": trace,
                    }
                )
                st.session_state[key] = history

with st.expander("Arquitectura y límites"):
    st.write(
        "Flujo: pregunta → preflight/guardrails → router determinista de alta confianza → modelo de lenguaje solo si la intención sigue siendo ambigua dentro del dominio → herramientas Python de solo lectura → DuckDB / Analytics / Expert System → evidencia estructurada → respuesta → entrenador."
    )
    st.write(
        "Ni Qwen ni OpenAI tienen acceso directo a DuckDB. Match Rating, Performance Index, rankings y decisiones críticas se calculan fuera del LLM."
    )
    if provider == "local":
        st.write("En modo local, la interpretación semántica se procesa mediante Ollama en `127.0.0.1` únicamente cuando hace falta.")
    else:
        st.write(
            "En modo OpenAI, solo la pregunta/contexto necesario y la evidencia estructurada requerida se envían al proveedor externo; la API key pertenece al usuario y no se persiste en DuckDB."
        )
    if demo_mode():
        st.caption("Modo demo activo: el chat usa exactamente las mismas identidades anónimas visibles en la plataforma; la traducción a nombres internos ocurre solo antes de consultar las herramientas y nunca se muestra al usuario.")
