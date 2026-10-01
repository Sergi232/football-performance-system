"""Presentation-only language and demo anonymisation helpers.

This module never changes IDs, analytics, ratings or database values. It only
changes what the Streamlit/PDF presentation layer displays. Demo masking is enabled
by default to avoid accidental exposure in screenshots or demonstrations; set
FPS_DEMO_MODE=0 explicitly for a private local real-identity view.
"""
from __future__ import annotations

import os
from collections.abc import Iterable

import pandas as pd


TRUE_VALUES = {"1", "true", "yes", "on", "si", "sí"}


def demo_mode() -> bool:
    """Return whether public/demo identity masking is enabled."""
    return str(os.environ.get("FPS_DEMO_MODE", "1")).strip().lower() in TRUE_VALUES


def display_team_name(raw_name: object, index: int = 1) -> str:
    if not demo_mode():
        return str(raw_name or "Equipo")
    return "Equipo Demo" if index == 1 else f"Equipo Demo {index:02d}"


def build_player_aliases(squad: pd.DataFrame) -> dict[str, str]:
    """Stable per-squad aliases while keeping player IDs untouched."""
    if squad is None or squad.empty or "player_id" not in squad.columns:
        return {}
    frame = squad[[c for c in ("player_id", "player") if c in squad.columns]].copy()
    frame["player_id"] = frame["player_id"].astype(str)
    frame = frame.drop_duplicates("player_id").sort_values("player_id", kind="stable")
    return {str(row.player_id): f"Jugador {i:02d}" for i, row in enumerate(frame.itertuples(index=False), start=1)}


def build_player_name_aliases(squad: pd.DataFrame) -> dict[str, str]:
    by_id = build_player_aliases(squad)
    if not by_id or "player" not in squad.columns:
        return {}
    out: dict[str, str] = {}
    for row in squad[["player_id", "player"]].drop_duplicates("player_id").itertuples(index=False):
        alias = by_id.get(str(row.player_id))
        if alias and row.player is not None:
            out[str(row.player)] = alias
    return out


def build_opponent_aliases(values: Iterable[object]) -> dict[str, str]:
    names = sorted({str(v).strip() for v in values if v is not None and str(v).strip()})
    return {name: f"Rival {i:02d}" for i, name in enumerate(names, start=1)}


def display_player_name(player_id: object, raw_name: object, aliases: dict[str, str]) -> str:
    if not demo_mode():
        return str(raw_name or "Jugador")
    return aliases.get(str(player_id), "Jugador")


def display_opponent(raw_name: object, aliases: dict[str, str]) -> str:
    raw = str(raw_name or "Rival")
    if not demo_mode():
        return raw
    return aliases.get(raw, "Rival")


def replace_known_names(
    value: object,
    *,
    player_name_aliases: dict[str, str] | None = None,
    opponent_aliases: dict[str, str] | None = None,
    team_name: str | None = None,
    team_alias: str = "Equipo Demo",
) -> str:
    """Mask known identities inside free-text presentation strings."""
    text = "" if value is None else str(value)
    if not demo_mode() or not text:
        return text
    replacements: dict[str, str] = {}
    replacements.update(player_name_aliases or {})
    replacements.update(opponent_aliases or {})
    if team_name:
        replacements[str(team_name)] = team_alias
    for source in sorted(replacements, key=len, reverse=True):
        if source:
            text = text.replace(source, replacements[source])
    return text


def anonymize_frame(
    frame: pd.DataFrame,
    *,
    player_aliases_by_id: dict[str, str] | None = None,
    player_name_aliases: dict[str, str] | None = None,
    opponent_aliases: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Return a copy with only display-name columns masked."""
    if frame is None:
        return frame
    out = frame.copy()
    if not demo_mode():
        return out
    by_id = player_aliases_by_id or {}
    by_name = player_name_aliases or {}
    opp = opponent_aliases or {}
    if "player" in out.columns:
        if "player_id" in out.columns and by_id:
            out["player"] = [by_id.get(str(pid), by_name.get(str(name), str(name))) for pid, name in zip(out["player_id"], out["player"])]
        else:
            out["player"] = out["player"].map(lambda x: by_name.get(str(x), str(x)))
    if "opponent" in out.columns:
        out["opponent"] = out["opponent"].map(lambda x: opp.get(str(x), str(x)))
    return out
