"""Compatibility entry point for the low-latency local Coach Copilot.

The original all-tools LLM loop proved too slow on the target PC. The public
functions now delegate to the hybrid runtime: deterministic/auditable local tool
routing + compact Ollama synthesis. Existing imports in the app/evaluation runner
continue to work unchanged.
"""
from __future__ import annotations

import os
from typing import Any

from llm import coach_agent as _core

DEFAULT_MODEL = os.environ.get("FPS_LOCAL_LLM_MODEL", "qwen3:1.7b")
DEFAULT_OLLAMA_URL = _core.DEFAULT_OLLAMA_URL
ollama_status = _core.ollama_status
CoachAgentResult = _core.CoachAgentResult


def run_coach_agent_turn(*args: Any, **kwargs: Any) -> CoachAgentResult:
    from llm.coach_agent_hybrid import run_coach_agent_turn as _run_hybrid

    kwargs.setdefault("model", DEFAULT_MODEL)
    return _run_hybrid(*args, **kwargs)


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    from llm.coach_agent_hybrid import run_coach_agent as _run_hybrid

    kwargs.setdefault("model", DEFAULT_MODEL)
    return _run_hybrid(*args, **kwargs)
