"""Identity boundary for Coach Copilot presentation.

The assistant runtime may need canonical database names to locate players and
opponents, while the product UI may expose demo aliases. This module is the only
translation boundary between those two worlds. It never changes IDs or analytics.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from app.presentation import (
    build_opponent_aliases,
    build_player_alias_to_real,
    build_player_name_aliases,
    demo_mode,
    replace_known_names,
)


def _replace_case_insensitive(text: str, source: str, target: str) -> str:
    if not source:
        return text
    return re.sub(re.escape(source), lambda _m: target, text, flags=re.IGNORECASE)


@dataclass(frozen=True)
class AssistantIdentityContext:
    raw_team_name: str
    team_alias: str
    player_name_aliases: dict[str, str]
    opponent_aliases: dict[str, str]
    alias_to_runtime: dict[str, str]

    def to_runtime(self, value: object) -> str:
        """Translate only known UI aliases to canonical runtime identities."""
        text = "" if value is None else str(value)
        if not demo_mode() or not text:
            return text
        out = text
        for alias in sorted(self.alias_to_runtime, key=len, reverse=True):
            out = _replace_case_insensitive(out, alias, self.alias_to_runtime[alias])
        return out

    def to_display(self, value: object) -> str:
        """Mask every known runtime identity before text reaches the UI."""
        return replace_known_names(
            value,
            player_name_aliases=self.player_name_aliases,
            opponent_aliases=self.opponent_aliases,
            team_name=self.raw_team_name,
            team_alias=self.team_alias,
        )

    def leaked_runtime_identities(self, value: object) -> list[str]:
        """Return canonical names still visible in demo output, for validators/tests."""
        if not demo_mode():
            return []
        text = str(value or "").casefold()
        candidates = set(self.player_name_aliases)
        candidates.update(self.opponent_aliases)
        if self.raw_team_name:
            candidates.add(self.raw_team_name)
        leaks: list[str] = []
        for raw in candidates:
            token = str(raw or "").strip()
            if len(token) >= 3 and token.casefold() in text:
                leaks.append(token)
        return sorted(set(leaks), key=str.casefold)


def build_assistant_identity_context(
    squad: pd.DataFrame,
    matches: pd.DataFrame,
    *,
    raw_team_name: str,
    team_alias: str,
) -> AssistantIdentityContext:
    player_name_aliases = build_player_name_aliases(squad)
    opponent_aliases = build_opponent_aliases(
        matches.get("opponent", pd.Series(dtype=str)).tolist() if matches is not None else []
    )

    alias_to_runtime = build_player_alias_to_real(squad)
    alias_to_runtime.update({alias: raw for raw, alias in opponent_aliases.items()})
    if raw_team_name and team_alias:
        alias_to_runtime[team_alias] = raw_team_name

    return AssistantIdentityContext(
        raw_team_name=str(raw_team_name or ""),
        team_alias=str(team_alias or "Equipo Demo"),
        player_name_aliases=player_name_aliases,
        opponent_aliases=opponent_aliases,
        alias_to_runtime=alias_to_runtime,
    )
