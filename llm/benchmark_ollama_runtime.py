"""Quick local Ollama diagnostic: plain generation vs minimal tool calling.

No DuckDB access, no paid API, no project analytics mutation.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request

BASE_URL = os.environ.get("FPS_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
MODEL = os.environ.get("FPS_LOCAL_LLM_MODEL", "qwen3:1.7b")
TIMEOUT = int(os.environ.get("FPS_AGENT_TIMEOUT", "90"))


def post(payload: dict) -> tuple[dict, float]:
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        out = json.loads(response.read().decode("utf-8"))
    return out, time.monotonic() - start


def main() -> None:
    print("OLLAMA LOCAL BENCHMARK")
    print(f"model={MODEL} timeout={TIMEOUT}s")

    plain = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Respon exactament amb la paraula OK."}],
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {"temperature": 0, "num_ctx": 2048, "num_predict": 16},
    }
    try:
        result, elapsed = post(plain)
        text = str((result.get("message") or {}).get("content") or "").strip()
        print(f"plain_generation: PASS elapsed={elapsed:.1f}s answer={text[:80]!r}")
    except Exception as exc:
        print(f"plain_generation: FAIL {type(exc).__name__}: {exc}")
        raise SystemExit(2)

    tool_payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Fes servir l'eina ping una vegada."}],
        "tools": [{
            "type": "function",
            "function": {
                "name": "ping",
                "description": "Return a local ping result.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }],
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {"temperature": 0, "num_ctx": 2048, "num_predict": 32},
    }
    try:
        result, elapsed = post(tool_payload)
        msg = result.get("message") or {}
        calls = msg.get("tool_calls") or []
        print(f"minimal_tool_call: {'PASS' if calls else 'FAIL'} elapsed={elapsed:.1f}s calls={len(calls)}")
    except Exception as exc:
        print(f"minimal_tool_call: FAIL {type(exc).__name__}: {exc}")
        raise SystemExit(3)


if __name__ == "__main__":
    main()
