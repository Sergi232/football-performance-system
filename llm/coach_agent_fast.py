"""Low-latency Ollama runtime patch for the local Coach Copilot.

Keeps the existing read-only tool loop but disables model thinking for routing and
coach-facing answers. Critical analytics remain calculated outside the LLM.
"""
from __future__ import annotations

import os
from typing import Any

from llm import coach_agent as _core

DEFAULT_MODEL = _core.DEFAULT_MODEL
DEFAULT_OLLAMA_URL = _core.DEFAULT_OLLAMA_URL
ollama_status = _core.ollama_status
CoachAgentResult = _core.CoachAgentResult


def _fast_chat(messages: list[dict[str, Any]], *, model: str, base_url: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "tools": _core.TOOLS,
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.1,
            "num_ctx": int(os.environ.get("FPS_AGENT_NUM_CTX", "8192")),
            "num_predict": int(os.environ.get("FPS_AGENT_NUM_PREDICT", "384")),
        },
    }
    timeout = int(os.environ.get("FPS_AGENT_TIMEOUT", "120"))
    return _core._request_json(
        f"{base_url.rstrip('/')}/api/chat",
        payload=payload,
        timeout=timeout,
    )


# Patch only the transport/generation settings. Tool definitions, analytics access,
# guardrails and the multi-step agent loop stay in the canonical coach_agent module.
_core._chat = _fast_chat


def run_coach_agent_turn(*args: Any, **kwargs: Any) -> CoachAgentResult:
    return _core.run_coach_agent_turn(*args, **kwargs)


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    return _core.run_coach_agent(*args, **kwargs)
