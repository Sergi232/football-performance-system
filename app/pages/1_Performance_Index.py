"""Historical/positional Performance Index — secondary analytical profile."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.coach_ui import dimension_chart, insight_card, metric_card, page_header, player_trend_chart, safe_number, section_header
from app.performance_score_access import SCORE_VERSION, get_latest_player_score, get_player_score_history, list_score_teams, list_team_players
from app.ui_theme import apply_professional_theme, position_label, sidebar_navigation

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
DIMENSIONS = [
    ("attacking_threat", "Amenaça ofensiva"),
    ("creation_progression", "Creació / progressió"),
    ("defensive_contribution", "Contribució defensiva"),
    ("finishing", "Finalització"),
    ("discipline", "Disciplina"),
]

st.set_page_config(page_title="Performance Index · FPS", page_icon="📈", layout="wide")
apply_professional_theme()
sidebar_navigation()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def evidence_label(value: object) -> str:
    labels = {
        "DIRECT_SIGNED": "Evidència directa",
        "CONTRIBUTION_FALLBACK": "Contribució observada de suport",
        "MISSING": "Sense evidència",
    }
    if value is None or pd.isna(value):
        return "Sense evidència"
    return labels.get(str(value), str(value))


path = db_path()
try:
    teams = list_score_teams(path)
except Exception as exc:
    st.error("La capa de Performance Index no està disponible.")
    st.caption(str(exc))
    st.stop()

if teams.empty:
    st.info("No hi ha índexs materialitzats.")
    st.stop()

sel_team, sel_player = st.columns([1, 1.6])
team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
with sel_team:
    team_id = st.selectbox("Equip", list(team_labels), format_func=lambda x: team_labels[x])
players = list_team_players(path, team_id)
if players.empty:
    st.info("No hi ha jugadors disponibles.")
    st.stop()
player_labels = {str(r.player_id): f"{r.player} · {int(r.scored_matches)} observacions" for r in players.itertuples(index=False)}
with sel_player:
    player_id = st.selectbox("Jugador", list(player_labels), format_func=lambda x: player_labels[x])

history = get_player_score_history(path, team_id, player_id)
latest = get_latest_player_score(path, team_id, player_id)
player_name = player_labels[player_id].split(" · ")[0]

page_header(
    "ANALYTICS · PERFIL HISTÒRIC",
    f"Performance Index · {player_name}",
    "Capa posicional per observar perfil i evolució. No és la nota d'un partit i no substitueix el Match Rating.",
    SCORE_VERSION,
)

if latest is None:
    st.warning("Aquest jugador no té cap Performance Index posicional elegible en aquesta baseline.")
    st.stop()

scores = history.dropna(subset=["performance_score"]).copy()
scores["performance_score"] = pd.to_numeric(scores["performance_score"], errors="coerce")
scores = scores.sort_values("match_date")
last5 = scores.tail(5)["performance_score"].mean() if not scores.empty else None
prev5 = scores.iloc[-10:-5]["performance_score"].mean() if len(scores) > 5 else None
delta = last5 - prev5 if last5 is not None and prev5 is not None and pd.notna(prev5) else None

k1, k2, k3, k4 = st.columns(4)
with k1:
    metric_card("Performance Index", safe_number(latest.get("performance_score"), 1, "/100"), "Valor posicional actual")
with k2:
    metric_card("Mitjana últims 5", safe_number(last5, 1, "/100"), "Evolució recent")
with k3:
    delta_text = "—" if delta is None or pd.isna(delta) else f"{float(delta):+.1f}"
    tone = "positive" if delta is not None and pd.notna(delta) and delta > 0 else "negative" if delta is not None and pd.notna(delta) and delta < 0 else "neutral"
    metric_card("Canvi 5 vs 5", delta_text, "Últims 5 menys 5 anteriors", tone=tone)
with k4:
    metric_card("Confiança", safe_number(latest.get("score_evidence_confidence"), 0, "%"), "Cobertura d'evidència prevista")

left, right = st.columns([1, 1.25], gap="large")
with left:
    section_header("Perfil de dimensions", "Només es mostren dimensions amb evidència disponible")
    values = {label: latest.get(key) for key, label in DIMENSIONS}
    st.plotly_chart(dimension_chart(values), width="stretch", config={"displayModeBar": False})

    missing = [label for key, label in DIMENSIONS if latest.get(key) is None or pd.isna(latest.get(key))]
    available = [label for key, label in DIMENSIONS if latest.get(key) is not None and pd.notna(latest.get(key))]
    insight_card(
        "Cobertura dimensional",
        f"{len(available)}/{len(DIMENSIONS)} dimensions amb valor",
        "Disponibles: " + (", ".join(available) if available else "cap"),
        "neutral",
    )
    if missing:
        insight_card("Sense evidència suficient", ", ".join(missing), "No es converteixen valors absents en zero.", "warning")

with right:
    section_header("Evolució de l'índex", "Escala 0–100 · perfil històric/posicional")
    if scores.empty:
        st.info("No hi ha historial disponible.")
    else:
        st.plotly_chart(player_trend_chart(scores, "performance_score", (0, 100), hover_col=None), width="stretch", config={"displayModeBar": False})

section_header("Evidència de l'última observació", "Origen de cada dimensió")
evidence_rows = []
for key, label in DIMENSIONS:
    evidence_rows.append({
        "Dimensió": label,
        "Valor": latest.get(key),
        "Evidència": evidence_label(latest.get(f"{key}_evidence")),
    })
evidence = pd.DataFrame(evidence_rows)
evidence["Valor"] = pd.to_numeric(evidence["Valor"], errors="coerce").round(1)
st.dataframe(evidence, hide_index=True, width="stretch")

with st.expander("Historial i traçabilitat"):
    details = history.copy()
    if not details.empty:
        details["match_date"] = pd.to_datetime(details["match_date"]).dt.date
        show = ["match_date", "primary_role", "position_group", "performance_score", "score_evidence_confidence", "dimension_coverage_count", "fallback_dimension_count"]
        for col in show:
            if col not in details.columns:
                details[col] = pd.NA
        details = details[show]
        details["position_group"] = details["position_group"].map(position_label)
        details.columns = ["Data", "Rol font", "Perfil", "Índex", "Confiança %", "Dimensions", "N fallback"]
        st.dataframe(details, hide_index=True, width="stretch", height=440)
    st.caption("Aquest índex és experimental i secundari. Els valors missing es mantenen com a missing.")
