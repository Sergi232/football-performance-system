"""Validate Spanish-only presentation and privacy-first demo identity masking."""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import get_squad_summary, get_team_matches, list_teams  # noqa: E402
from app.presentation import (  # noqa: E402
    build_opponent_aliases,
    build_player_aliases,
    demo_mode,
    display_opponent,
    display_player_name,
    display_team_name,
)

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
PRESENTATION_FILES = [
    ROOT / "app" / "streamlit_app.py",
    ROOT / "app" / "ui_theme.py",
    ROOT / "app" / "coach_ui.py",
    ROOT / "app" / "pages" / "1_Performance_Index.py",
    ROOT / "app" / "pages" / "2_Jugador.py",
    ROOT / "app" / "pages" / "3_Equip.py",
    ROOT / "app" / "pages" / "4_Partit.py",
    ROOT / "app" / "pages" / "5_Assistent_IA.py",
    ROOT / "app" / "pages" / "6_Fisic_GPS.py",
    ROOT / "app" / "pages" / "7_Alertes.py",
]
CATALAN_MARKERS = (
    "No hi ha",
    "No s'ha",
    "Últim partit",
    "Últims ",
    "Mitjana ",
    "Confiança",
    "Evidència",
    "Metodologia",
    "Qualitat",
    "Assistent IA",
    "Físic / GPS",
    "Partits",
    "Aparicions",
    "Jugadors",
    "Rendiment",
    "Evolució",
    "Distribució",
    "Creació",
    "Finalització",
    "Amenaça",
    "Desacceleració",
    "Distància",
    "Mostres",
    "Proveïdor",
    "Sense dades",
    "Sense historial",
    "Equip",
)


def db_path() -> Path:
    return Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()


def visible_strings(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value
            if "pages/" in text or "pages\\" in text:
                continue
            if any(marker in text for marker in CATALAN_MARKERS):
                found.append((getattr(node, "lineno", 0), text.replace("\n", " ")[:180]))
    return found


def main() -> None:
    if not demo_mode():
        raise SystemExit("DEMO PRESENTATION: FAIL — FPS_DEMO_MODE is disabled")

    path = db_path()
    if not path.exists():
        raise SystemExit(f"DEMO PRESENTATION: FAIL — database not found: {path}")

    teams = list_teams(path)
    if teams.empty:
        raise SystemExit("DEMO PRESENTATION: FAIL — no teams available")

    row = teams.iloc[0]
    team_id = str(row["team_id"])
    raw_team = str(row["display_name"])
    shown_team = display_team_name(raw_team, 1)
    if shown_team == raw_team or not shown_team.startswith("Equipo Demo"):
        raise SystemExit("DEMO PRESENTATION: FAIL — team identity is not masked")

    squad = get_squad_summary(path, team_id)
    player_aliases = build_player_aliases(squad)
    if not squad.empty:
        raw_players = {str(r.player_id): str(r.player) for r in squad.itertuples(index=False)}
        shown = [display_player_name(pid, name, player_aliases) for pid, name in raw_players.items()]
        if len(set(shown)) != len(shown):
            raise SystemExit("DEMO PRESENTATION: FAIL — player aliases are not unique")
        if any(alias == raw_players[pid] for pid, alias in zip(raw_players, shown)):
            raise SystemExit("DEMO PRESENTATION: FAIL — at least one player identity is not masked")

    matches = get_team_matches(path, team_id)
    opponent_aliases = build_opponent_aliases(matches.get("opponent", pd.Series(dtype=str)).tolist())
    for raw, alias in opponent_aliases.items():
        if display_opponent(raw, opponent_aliases) != alias or raw == alias:
            raise SystemExit("DEMO PRESENTATION: FAIL — opponent identity is not masked")

    residuals: list[str] = []
    for source in PRESENTATION_FILES:
        for line, text in visible_strings(source):
            residuals.append(f"{source.relative_to(ROOT)}:{line}: {text}")

    print("DEMO PRESENTATION CONTRACT")
    print(f"team={shown_team}")
    print(f"players_masked={len(player_aliases)}")
    print(f"opponents_masked={len(opponent_aliases)}")
    print(f"catalan_visible_strings={len(residuals)}")
    if residuals:
        print("\nResidual Catalan UI strings:")
        for item in residuals:
            print(f"- {item}")
        raise SystemExit("DEMO PRESENTATION: FAIL")

    print("DEMO PRESENTATION: PASS")


if __name__ == "__main__":
    main()
