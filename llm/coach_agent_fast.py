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


def _current_question(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    if args:
        return str(args[0])
    return str(kwargs.get("question") or "")


def _collapse_followup_history(question: str, history: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    """Keep the latest substantive user query as the anchor for chained follow-ups.

    Example:
    base ranking -> "y el segundo?" -> "que evidencias tienes?"

    The evidence question must be resolved against the base ranking, not against the
    ordinal follow-up. This stays deterministic and avoids an unnecessary Qwen call.
    """
    if not history:
        return history

    from llm import coach_agent_general as agent

    if not agent._followup(question):
        return history

    trimmed = list(history)
    while trimmed:
        last_user_idx = None
        for idx in range(len(trimmed) - 1, -1, -1):
            item = trimmed[idx]
            if str(item.get("role") or "") == "user" and str(item.get("content") or "").strip():
                last_user_idx = idx
                break
        if last_user_idx is None:
            break

        last_user_text = str(trimmed[last_user_idx].get("content") or "").strip()
        if not agent._followup(last_user_text):
            break

        # Remove the previous follow-up and any assistant response after it. The
        # remaining history ends at the substantive anchor query/answer pair.
        trimmed = trimmed[:last_user_idx]

    return trimmed


def _prepare_kwargs(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(kwargs)
    prepared.setdefault("model", DEFAULT_MODEL)
    question = _current_question(args, prepared)
    if "history" in prepared:
        prepared["history"] = _collapse_followup_history(question, prepared.get("history"))
    return prepared


def run_coach_agent_turn(*args: Any, **kwargs: Any) -> CoachAgentResult:
    from llm.coach_agent_general import run_coach_agent_turn as _run

    return _run(*args, **_prepare_kwargs(args, kwargs))


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    from llm.coach_agent_general import run_coach_agent as _run

    return _run(*args, **_prepare_kwargs(args, kwargs))
