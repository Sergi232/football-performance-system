"""Compatibility entry point for the final professional PDF renderer.

Application pages keep importing ``reports.pdf_engine_es`` while the actual final
implementation lives in ``reports.pdf_engine_elite``.
"""
from reports.pdf_engine_elite import render_pdf_bytes

__all__ = ["render_pdf_bytes"]
