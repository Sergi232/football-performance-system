"""DASHBOARD-01 — first functional Football Performance System web app."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import (  # noqa: E402
    FINAL_ENGINE_VERSION,
    get_latest_player_gate,
    get_match_lineup,
    get_player_feature_history,
    get_player_match_history,
    get_squad_summary,
    get_team_matches,
    get_team_overview,
    list_base_features,
    list_teams,
)

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(
    page_title="Football Performance System",
    page_icon="⚽",
    layout="wide",
)


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


@st.cache_data(show_spinner=False)
def cached_teams(path: str) -> pd.DataFrame:
    return list_teams(Path(path))


@st.cache_data(show_spinner=False)
def cached_overview(path: str, team_id: str) -> dict:
    return get_team_overview(Path(path), team_id)


@st.cache_data(show_spinner=False)
def cached_matches(path: str, team_id: str) -> pd.DataFrame:
    return get_team_matches(Path(path), team_id)


@st.cache_data(show_spinner=False)
def cached_squad(path: str, team_id: str) -> pd.DataFrame:
    return get_squad_summary(Path(path), team_id)


@st.cache_data(show_spinner=False)
def cached_player_history(path: str, team_id: str, player_id: str) -> pd.DataFrame:
    return get_player_match_history(Path(path), team_id, player_id)


@st.cache_data(show_spinner=False)
def cached_features(path: str, player_id: str) -> list[str]:
    return list_base_features(Path(path), player_id)


@st.cache_data(show_spinner=False)
def cached_feature_history(path: str, player_id: str, feature_name: str) -> pd.DataFrame:
    return get_player_feature_history(Path(path), player_id, feature_name)


@st.cache_data(show_spinner=False)
def cached_gate(path: str, team_id: str, player_id: str) -> dict | None:
    return get_latest_player_gate(Path(path), team_id, player_id)


@st.cache_data(show_spinner=False)
def cached_lineup(path: str, team_id: str, match_id: str) -> pd.DataFrame:
    return get_match_lineup(Path(path), team_id, match_id)


def safe_int(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{int(value):,}".replace(",", ".")


def safe_float(value, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{digits}f}"


def result_label(row: pd.Series) -> str:
    if pd.isna(row.get("score_for")) or pd.isna(row.get("score_against")):
        return "—"
    sf = int(row["score_for"])
    sa = int(row["score_against"])
    outcome = "W" if sf > sa else "D" if sf == sa else "L"
    return f"{outcome} {sf}-{sa}"


def render_team(path: str, team_id: str, team_name: str) -> None:
    overview = cached_overview(path, team_id)
    matches = cached_matches(path, team_id)
    squad = cached_squad(path, team_id)

    st.header(team_name)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Partits", safe_int(overview["matches"]))
    c2.metric("Jugadors", safe_int(overview["players"]))
    c3.metric("Minuts jugador", safe_int(overview["player_minutes"]))
    c4.metric("Gols", safe_int(overview["goals"]))
    c5.metric("Assistències", safe_int(overview["assists"]))

    left, right = st.columns([1.15, 1])
    with left:
        st.subheader("Plantilla")
        display = squad.drop(columns=["player_id"], errors="ignore").copy()
        st.dataframe(display, hide_index=True, use_container_width=True)

    with right:
        st.subheader("Partits")
        if matches.empty:
            st.info("No hi ha partits disponibles.")
        else:
            display = matches.copy()
            display["result"] = display.apply(result_label, axis=1)
            display["match_date"] = pd.to_datetime(display["match_date"]).dt.date
            display = display[["match_date", "venue", "opponent", "result", "starting_formation"]]
            display.columns = ["Data", "L/V", "Rival", "Resultat", "Formació"]
            st.dataframe(display, hide_index=True, use_container_width=True)


def render_player(path: str, team_id: str) -> None:
    squad = cached_squad(path, team_id)
    if squad.empty:
        st.info("No hi ha jugadors disponibles.")
        return

    labels = {
        str(row.player_id): str(row.player)
        for row in squad.itertuples(index=False)
    }
    player_id = st.selectbox(
        "Jugador",
        options=list(labels),
        format_func=lambda value: labels[value],
    )
    player_name = labels[player_id]
    row = squad.loc[squad["player_id"] == player_id].iloc[0]
    history = cached_player_history(path, team_id, player_id)
    gate = cached_gate(path, team_id, player_id)

    st.header(player_name)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Aparicions", safe_int(row["appearances"]))
    c2.metric("Titularitats", safe_int(row["starts"]))
    c3.metric("Minuts", safe_int(row["minutes"]))
    c4.metric("Gols", safe_int(row["goals"]))
    c5.metric("Assistències", safe_int(row["assists"]))

    st.caption(f"Rols observats: {row['observed_roles'] if pd.notna(row['observed_roles']) else 'sense rol observat'}")

    if gate is None:
        st.info("Aquest jugador encara no té un partit jugat amb estat N12000/N13000 disponible.")
    else:
        st.subheader("Evidència de rol i gate final")
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Rol observat", gate["observed_role"] or "—")
        g2.metric("Historial mateix rol", gate["same_role_history"] or "—")
        coverage = None
        try:
            coverage = float(gate["evidence_coverage"])
        except (TypeError, ValueError):
            pass
        g3.metric("Cobertura evidència", "—" if coverage is None else f"{coverage:.0%}")
        g4.metric("Senyals avaluables", gate["evaluable_signals"] or "—")
        st.code(str(gate["final_status"]), language=None)
        st.caption(
            "N13000 no emet una recomanació tàctica perquè la política final encara no està validada. "
            "El dashboard mostra evidència calculada pel motor, no una conclusió inventada per la interfície."
        )

    features = cached_features(path, player_id)
    if features:
        st.subheader("Evolució de feature")
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
        feature_history = cached_feature_history(path, player_id, feature_name)
        chart = feature_history.dropna(subset=["feature_value"]).copy()
        if chart.empty:
            st.info("No hi ha valors disponibles per aquesta feature.")
        else:
            chart["match_date"] = pd.to_datetime(chart["match_date"])
            st.line_chart(chart.set_index("match_date")[["feature_value"]])
            details = feature_history.copy()
            details["match_date"] = pd.to_datetime(details["match_date"]).dt.date
            details.columns = ["Data", "Rival", "Rol", "Minuts", "Valor"]
            st.dataframe(details, hide_index=True, use_container_width=True)

    st.subheader("Historial de partits")
    details = history.copy()
    if not details.empty:
        details["match_date"] = pd.to_datetime(details["match_date"]).dt.date
        details = details.drop(columns=["match_id"], errors="ignore")
    st.dataframe(details, hide_index=True, use_container_width=True)


def render_matches(path: str, team_id: str) -> None:
    matches = cached_matches(path, team_id)
    if matches.empty:
        st.info("No hi ha partits disponibles.")
        return

    options = {}
    for row in matches.itertuples(index=False):
        date_text = pd.to_datetime(row.match_date).date().isoformat()
        score = "—" if pd.isna(row.score_for) or pd.isna(row.score_against) else f"{int(row.score_for)}-{int(row.score_against)}"
        options[str(row.match_id)] = f"{date_text} · {row.venue} · {row.opponent} · {score}"

    match_id = st.selectbox(
        "Partit",
        options=list(options),
        format_func=lambda value: options[value],
    )
    lineup = cached_lineup(path, team_id, match_id)
    st.header(options[match_id])
    st.subheader("Jugadors i estadístiques brutes")
    st.dataframe(lineup, hide_index=True, use_container_width=True)
    st.caption("Aquesta vista mostra dades player-match brutes/observades. Les features derivades es calculen en la capa Feature Engine.")


def main() -> None:
    path = db_path()
    st.title("Football Performance System")
    st.caption(f"Dashboard MVP · motor {FINAL_ENGINE_VERSION}")

    if not path.exists():
        st.error(
            f"No s'ha trobat la base de dades: {path}. "
            "Defineix FPS_DB_PATH si la base de dades és en una altra ubicació."
        )
        st.stop()

    try:
        teams = cached_teams(str(path))
    except Exception as exc:
        st.error(f"No s'ha pogut llegir DuckDB: {exc}")
        st.stop()

    if teams.empty:
        st.warning("La base de dades no conté cap equip amb player_match.")
        st.stop()

    team_labels = {
        str(row.team_id): f"{row.display_name} · {int(row.matches)} partits"
        for row in teams.itertuples(index=False)
    }

    st.sidebar.title("Navegació")
    mode = st.sidebar.radio("Mode", ["Equip", "Jugador", "Partits"])
    team_id = st.sidebar.selectbox(
        "Equip",
        options=list(team_labels),
        format_func=lambda value: team_labels[value],
    )
    team_name = str(teams.loc[teams["team_id"] == team_id, "display_name"].iloc[0])
    st.sidebar.caption(f"DB: {path.name}")

    if mode == "Equip":
        render_team(str(path), team_id, team_name)
    elif mode == "Jugador":
        render_player(str(path), team_id)
    else:
        render_matches(str(path), team_id)


if __name__ == "__main__":
    main()
