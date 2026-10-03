"""Compatibility entry point for the local Coach Copilot.

The public API is preserved while the runtime delegates to the Granite tool-driven
agent. Existing app imports continue to work unchanged.
"""
from __future__ import annotations

from typing import Any

from llm.coach_agent_granite import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    CoachAgentResult,
    ollama_status,
)


def run_coach_agent_turn(*args: Any, **kwargs: Any) -> CoachAgentResult:
    from llm.coach_agent_granite import run_coach_agent_turn as _run

    kwargs.setdefault("model", DEFAULT_MODEL)
    return _run(*args, **kwargs)


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    from llm.coach_agent_granite import run_coach_agent as _run

    kwargs.setdefault("model", DEFAULT_MODEL)
    return _run(*args, **kwargs)
