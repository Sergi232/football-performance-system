"""Stable entry point for the unattended Coach Copilot self-improvement run.

Keeps the runner portable while the main module evolves. This shim fixes default
team selection before delegating to the full self-improvement loop and removes
stress mutations that materially change the user's intent.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import list_teams
from llm import run_agent_self_improve as impl


def _choose_team(db_path: Path, explicit: str | None) -> tuple[str, str]:
    teams = list_teams(db_path)
    if teams.empty:
        raise RuntimeError("No teams available")
    if explicit:
        selected = teams.loc[teams["team_id"].astype(str) == str(explicit)]
        if selected.empty:
            raise RuntimeError(f"Unknown team_id: {explicit}")
        row = selected.iloc[0]
    else:
        row = teams.iloc[0]
    return str(row["team_id"]), str(row["display_name"])


impl.choose_team = _choose_team

# A wording mutation must preserve intent. Asking to "indicate limitations" adds a
# genuine data-quality intent, so it is not a neutral router stress variant.
for _lang in tuple(impl.MUTATIONS):
    impl.MUTATIONS[_lang] = [
        mutation for mutation in impl.MUTATIONS[_lang]
        if mutation[0] != "limitations_suffix"
    ]

if __name__ == "__main__":
    impl.main()
