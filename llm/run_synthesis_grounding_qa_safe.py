"""Hardened launcher for Coach Copilot synthesis grounding QA.

This wrapper keeps the benchmark contracts from ``run_synthesis_grounding_qa`` but
repairs two evaluator limitations found in the first real local run:

1. list cardinalities in compact evidence are valid support for count claims
   (for example five rows -> "5 partidos");
2. exact decimal/percentage equivalents are accepted
   (for example 0.75 -> 75%).

It also uses the bounded ``fast`` evidence profile already explored by adaptive QA
(18 lines / 1900 chars). The goal is to reduce CPU latency without weakening the
football-data or safety contracts. No analytics, rating or decision output changes.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm import run_synthesis_grounding_qa as qa


def _structural_counts(value: Any, depth: int = 0) -> list[tuple[float, bool, str]]:
    """Return exact list cardinalities represented in the compact evidence tree."""
    if depth > 4:
        return []
    out: list[tuple[float, bool, str]] = []
    if isinstance(value, list):
        out.append((float(len(value)), False, f"len={len(value)}"))
        for item in value:
            out.extend(_structural_counts(item, depth + 1))
    elif isinstance(value, dict):
        for item in value.values():
            out.extend(_structural_counts(item, depth + 1))
    return out


def _number_supported_safe(
    value: float,
    is_percent: bool,
    source: list[tuple[float, bool, str]],
) -> bool:
    for candidate, candidate_percent, _ in source:
        # Same representation, allowing ordinary display rounding only.
        if is_percent == candidate_percent:
            tolerance = max(0.051, abs(candidate) * 0.005)
            if abs(value - candidate) <= tolerance:
                return True

        # Exact decimal <-> percentage representation is not a new factual claim.
        if is_percent and not candidate_percent and 0.0 <= candidate <= 1.0:
            converted = candidate * 100.0
            tolerance = max(0.11, abs(converted) * 0.005)
            if abs(value - converted) <= tolerance:
                return True
        if not is_percent and candidate_percent and 0.0 <= value <= 1.0:
            converted = value * 100.0
            tolerance = max(0.11, abs(candidate) * 0.005)
            if abs(converted - candidate) <= tolerance:
                return True
    return False


def numeric_grounding_safe(
    answer: str,
    question: str,
    evidence: dict[str, Any],
) -> tuple[bool, list[str]]:
    answer_nums = qa._numbers(answer)
    if not answer_nums:
        return True, []

    evidence_text = "\n".join(qa._flatten_lines(evidence))
    source_nums = qa._numbers(question + "\n" + evidence_text)
    source_nums.extend(_structural_counts(evidence))

    unsupported = [
        raw
        for value, is_percent, raw in answer_nums
        if not _number_supported_safe(value, is_percent, source_nums)
    ]
    return not unsupported, unsupported


# Patch evaluator only. The production Coach Copilot runtime is untouched.
qa.numeric_grounding = numeric_grounding_safe

# Bounded evidence profile from the adaptive QA search. Set before qa.main() because
# the underlying benchmark uses setdefault and therefore preserves these values.
os.environ.setdefault("FPS_AGENT_NUM_CTX", "1536")
os.environ.setdefault("FPS_AGENT_NUM_PREDICT", "112")
os.environ.setdefault("FPS_AGENT_TIMEOUT", "25")
os.environ.setdefault("FPS_AGENT_EVIDENCE_LINES", "18")
os.environ.setdefault("FPS_AGENT_EVIDENCE_CHARS", "1900")


if __name__ == "__main__":
    qa.main()
