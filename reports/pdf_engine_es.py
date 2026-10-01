"""Compatibility entry point for Spanish PDF exports.

The professional renderer is now the canonical PDF implementation. Existing app
pages keep importing this module, so exports automatically use the validated
professional Team / Player / Match layouts without duplicating rendering logic.
"""
from __future__ import annotations

from reports.pdf_engine_final import render_pdf_bytes

__all__ = ["render_pdf_bytes"]
