"""Compatibility entry point for the final professional PDF renderer.

Application pages keep importing ``reports.pdf_engine_es`` while the active
staff-facing implementation lives in ``reports.pdf_engine_elite_v3``.
"""
from reports.pdf_engine_elite_v3 import render_pdf_bytes

__all__ = ["render_pdf_bytes"]
