"""Compatibility entry point for the local Coach Copilot.

The public API is preserved while the runtime delegates to the hybrid generic-query
agent. Natural user wording is kept intact; high-confidence routing is handled by
Python and ambiguous queries fall back to the local semantic router.
"""
from __future__ import annotations

from typing import Any

from llm.coach_agent_general import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    CoachAgentResult,
    ollama_status,
)


def run_coach_agent_turn(*args: Any, **kwargs: Any) -> CoachAgentResult:
    from llm.coach_agent_general import run_coach_agent_turn as _run

    kwargs.setdefault("model", DEFAULT_MODEL)
    return _run(*args, **kwargs)


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    from llm.coach_agent_general import run_coach_agent as _run

    kwargs.setdefault("model", DEFAULT_MODEL)
    return _run(*args, **kwargs)
