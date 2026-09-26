"""Auditable attention centre: data/evidence/context limitations only."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.attention_access import ATTENTION_VERSION, get_attention_summary, get_team_attention_flags
from app.data_access import list_teams
from app.ui_theme import apply_professional_theme, score_card

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"

st.set_page_config(page_title="Alertes · Football Performance System", page_icon="⚠️", layout="wide")
apply_professional_theme()


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


path = db_path()
if not path.exists():
    st.error(f"No s'ha trobat la base de dades: {path}")
    st.stop()

teams = list_teams(path)
if teams.empty:
    st.info("No hi ha equips disponibles.")
    st.stop()

team_labels = {str(r.team_id): str(r.display_name) for r in teams.itertuples(index=False)}
team_id = st.selectbox("Equip", options=list(team_labels), format_func=lambda x: team_labels[x])

st.markdown("<div class='fps-kicker'>ATTENTION CENTRE</div>", unsafe_allow_html=True)
st.title("Alertes i limitacions")
st.caption("Només estats auditables de dades, context o evidència. Encara no s'emeten alertes de fatiga, risc de lesió o rendiment bo/dolent.")

try:
    flags = get_team_attention_flags(path, team_id)
    summary = get_attention_summary(path, team_id)
except Exception as exc:
    st.warning("La capa d'alertes encara no està materialitzada.")
    st.caption(str(exc))
    st.stop()

counts = {str(r.attention_code): int(r.rows) for r in summary.itertuples(index=False)}
cols = st.columns(3)
with cols[0]:
    score_card("Context de rol no disponible", str(counts.get("ROLE_CONTEXT_UNAVAILABLE", 0)), "No s'imputa cap posició")
with cols[1]:
    score_card("Evidència insuficient", str(counts.get("INSUFFICIENT_RATING_EVIDENCE", 0)), "Rating neutral explícit")
with cols[2]:
    score_card("Incidències GPS", str(counts.get("GPS_QUALITY_FLAGS_PRESENT", 0)), "Quality flags d'import")

st.write("")
if flags.empty:
    st.success("No hi ha limitacions auditables registrades per aquest equip en aquesta versió.")
else:
    groups = ["Totes"] + sorted(flags["attention_group"].dropna().astype(str).unique().tolist())
    selected = st.selectbox("Tipus", groups)
    display = flags.copy()
    if selected != "Totes":
        display = display.loc[display["attention_group"] == selected].copy()
    display["match_date"] = pd.to_datetime(display["match_date"], errors="coerce").dt.date
    display = display[["match_date", "player", "attention_group", "attention_code", "message", "source_layer"]]
    display.columns = ["Data", "Jugador", "Grup", "Codi", "Missatge", "Font"]
    st.dataframe(display, hide_index=True, width="stretch")

with st.expander("Metodologia"):
    st.write(f"Versió: `{ATTENTION_VERSION}`")
    st.write("Aquest centre no interpreta un rating baix com una alerta, no defineix fatiga/readiness i no estima risc de lesió.")
    st.write("Les alertes de rendiment futures requeriran regles o models validats i quedaran separades d'aquestes limitacions de dades/evidència.")
