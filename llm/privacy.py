"""Local privacy layer for the coaching agent.

Real player/team/opponent names and internal IDs are pseudonymized before any
external LLM call. The reversible map lives only in local process memory.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from dataclasses import dataclass, field
from typing import Any


_PROCESS_SECRET = os.environ.get("FPS_ANON_SECRET", "") or secrets.token_urlsafe(32)


@dataclass
class AliasBook:
    # Stable during one Python process. For aliases that must survive process
    # restarts, set FPS_ANON_SECRET locally; never commit that secret.
    secret: str = field(default_factory=lambda: _PROCESS_SECRET)
    real_to_alias: dict[str, str] = field(default_factory=dict)
    alias_to_real: dict[str, str] = field(default_factory=dict)
    player_alias_to_id: dict[str, str] = field(default_factory=dict)
    match_alias_to_id: dict[str, str] = field(default_factory=dict)

    def _alias(self, kind: str, value: object) -> str:
        raw = str(value)
        digest = hmac.new(self.secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()[:8].upper()
        return f"{kind}_{digest}"

    def add(self, kind: str, value: object, *, entity_id: object | None = None) -> str | None:
        if value is None:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        if raw in self.real_to_alias:
            alias = self.real_to_alias[raw]
        else:
            alias = self._alias(kind, raw)
            self.real_to_alias[raw] = alias
            self.alias_to_real[alias] = raw
        if entity_id is not None:
            entity_raw = str(entity_id)
            id_alias = self._alias(f"{kind}ID", entity_raw)
            self.real_to_alias[entity_raw] = id_alias
            self.alias_to_real[id_alias] = entity_raw
            if kind == "PLAYER":
                self.player_alias_to_id[alias] = entity_raw
                self.player_alias_to_id[id_alias] = entity_raw
            elif kind == "MATCH":
                self.match_alias_to_id[alias] = entity_raw
                self.match_alias_to_id[id_alias] = entity_raw
        return alias

    def anonymize_text(self, text: str) -> str:
        out = str(text)
        # Longest first prevents partial replacement of nested names/IDs.
        for raw in sorted(self.real_to_alias, key=len, reverse=True):
            if not raw:
                continue
            alias = self.real_to_alias[raw]
            out = re.sub(re.escape(raw), alias, out, flags=re.IGNORECASE)
        return out

    def deanonymize_text(self, text: str) -> str:
        out = str(text)
        for alias in sorted(self.alias_to_real, key=len, reverse=True):
            out = out.replace(alias, self.alias_to_real[alias])
        return out

    def anonymize_obj(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): self.anonymize_obj(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.anonymize_obj(v) for v in value]
        if isinstance(value, tuple):
            return [self.anonymize_obj(v) for v in value]
        raw = str(value)
        if raw in self.real_to_alias:
            return self.real_to_alias[raw]
        if isinstance(value, str):
            return self.anonymize_text(value)
        return value

    def resolve_player(self, alias_or_id: str) -> str | None:
        value = str(alias_or_id).strip()
        if value in self.player_alias_to_id:
            return self.player_alias_to_id[value]
        real = self.alias_to_real.get(value)
        if real:
            for player_id in self.player_alias_to_id.values():
                if player_id == real:
                    return player_id
        return None

    def resolve_match(self, alias_or_id: str) -> str | None:
        value = str(alias_or_id).strip()
        if value in self.match_alias_to_id:
            return self.match_alias_to_id[value]
        real = self.alias_to_real.get(value)
        if real:
            for match_id in self.match_alias_to_id.values():
                if match_id == real:
                    return match_id
        return None


def assert_no_known_entities(text: str, aliases: AliasBook) -> list[str]:
    """Return any known real identifiers that leaked into external-bound text."""
    lowered = text.lower()
    leaks: list[str] = []
    for raw in aliases.real_to_alias:
        if len(raw) >= 3 and raw.lower() in lowered:
            leaks.append(raw)
    return leaks
