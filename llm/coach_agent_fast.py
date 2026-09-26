"""Low-latency Ollama runtime for the local Coach Copilot.

Keeps the existing read-only tool loop but disables model thinking for routing and
coach-facing answers. Critical analytics remain calculated outside the LLM.
"""
from __future__ import annotations

import os
from typing import Any

from llm import coach_agent as _core

# The 4B multimodal Qwen 3.5 model proved too slow on the target local PC (>120 s
# on the first grounded turn). Qwen3 1.7B is text-only, supports Ollama tools, and
# is the product default for the local MVP. It can still be overridden by env var.
DEFAULT_MODEL = os.environ.get("FPS_LOCAL_LLM_MODEL", "qwen3:1.7b")
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
            "num_ctx": int(os.environ.get("FPS_AGENT_NUM_CTX", "4096")),
            "num_predict": int(os.environ.get("FPS_AGENT_NUM_PREDICT", "256")),
        },
    }
    timeout = int(os.environ.get("FPS_AGENT_TIMEOUT", "90"))
    return _core._request_json(
        f"{base_url.rstrip('/')}/api/chat",
        payload=payload,
        timeout=timeout,
    )


# Patch only transport/generation settings. Tool definitions, analytics access,
# guardrails and the multi-step agent loop stay in the canonical module.
_core._chat = _fast_chat


def run_coach_agent_turn(*args: Any, **kwargs: Any) -> CoachAgentResult:
    kwargs.setdefault("model", DEFAULT_MODEL)
    return _core.run_coach_agent_turn(*args, **kwargs)


def run_coach_agent(*args: Any, **kwargs: Any) -> str:
    kwargs.setdefault("model", DEFAULT_MODEL)
    return _core.run_coach_agent(*args, **kwargs)
