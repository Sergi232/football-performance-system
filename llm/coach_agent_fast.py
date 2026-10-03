"""Compatibility entry point for the local Coach Copilot.

The public API is preserved while the runtime delegates to the Granite structured-
intent agent. Existing app imports continue to work unchanged.
"""
from __future__ import annotations

from typing import Any

from llm.coach_agent_granite_v2 import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    CoachAgentResult,
    ollama_status,
)
from llm.coach_query_normalizer import canonicalize_question


def _canonicalize_first_question(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """Canonicalize only the current user question, preserving the public API."""
    if args:
        args = (canonicalize_question(str(args[0])), *args[1:])
    elif "question" in kwargs:
        kwargs = dict(kwargs)
        kwargs["question"] = canonicalize_question(str(kwargs["question"]))
    return args, kwargs


def run_coach_agent_turn(*args: Any, **kwargs: Any) -> CoachAgentResult:
    from llm.coach_agent_granite_v2 import run_coach_agent_turn as _run

    kwargs.setdefault("model", DEFAULT_MODEL)
    args, kwargs = _canonicalize_first_question(args, kwargs)
    return _run(*args, **kwargs)


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    from llm.coach_agent_granite_v2 import run_coach_agent as _run

    kwargs.setdefault("model", DEFAULT_MODEL)
    args, kwargs = _canonicalize_first_question(args, kwargs)
    return _run(*args, **kwargs)
