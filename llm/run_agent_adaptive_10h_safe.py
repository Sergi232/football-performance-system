"""Safe launcher for the 10h adaptive Coach Copilot QA.

Keeps the adaptive/replay/profile logic from run_agent_adaptive_10h, but replaces
QA paraphrase prefixes/suffixes that could accidentally change the semantic intent
of a case (for example turning a player question into a data-quality question).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm import run_agent_adaptive_10h as qa

# Intent-neutral paraphrase noise only. Do not inject words such as "evidencia",
# "limitaciones" or "datos disponibles" because those are legitimate routing cues.
qa.ES_PREFIXES[:] = [
    "Para el cuerpo técnico: ",
    "De forma breve, ",
    "En resumen, ",
    "Concretamente, ",
    "Sin inventar datos, ",
    "",
]
qa.CA_PREFIXES[:] = [
    "Per al cos tècnic: ",
    "De forma breu, ",
    "En resum, ",
    "Concretament, ",
    "Sense inventar dades, ",
    "",
]
qa.ES_SUFFIXES[:] = [
    "",
    " Sé preciso.",
    " Responde brevemente.",
    " Usa solo datos observables.",
]
qa.CA_SUFFIXES[:] = [
    "",
    " Sigues precís.",
    " Respon breument.",
    " Usa només dades observables.",
]

if __name__ == "__main__":
    qa.main()
