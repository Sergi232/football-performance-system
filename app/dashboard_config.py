"""Presentation-only configuration for the Coach Command Center.

The Product Spiral may mutate this file. Analytics, ratings and decision logic must not
depend on these values.
"""
from __future__ import annotations

DASHBOARD_CONFIG = {
    "show_quick_nav": True,
    "show_command_strip": True,
    "hero_ratio": [1.45, 1.0],
    "brief_columns": 4,
    "trend_ratio": [1.65, 0.75],
    "squad_mode": "tabs",
    "quality_mode": "cards",
    "section_order": ["coach_brief", "trend", "squad", "quality"],
}
