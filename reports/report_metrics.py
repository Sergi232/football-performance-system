"""Transparent descriptive metrics for professional reports.

These calculations are intentionally simple, documented and auditable. They are not
model outputs, do not create good/bad thresholds, and never alter Match Rating,
Performance Index or expert-system decisions.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

REPORT_METRIC_VERSION = "report_descriptive_v0.1"

TEAM_METRICS = [
    ("pass_completion_pct", "Precisión de pase", "%", 1),
    ("shots_total", "Remates", "", 1),
    ("goals", "Goles", "", 2),
    ("tackles_won", "Entradas ganadas", "", 1),
    ("interceptions", "Intercepciones", "", 1),
    ("turnovers", "Pérdidas", "", 1),
    ("dispossessed", "Desposesiones", "", 1),
]

PLAYER_METRICS = [
    ("pass_completion_pct", "Precisión de pase", "%", 1),
    ("passes_completed_per90", "Pases completados / 90", "", 1),
    ("shots_per90", "Remates / 90", "", 2),
    ("goals_per90", "Goles / 90", "", 2),
    ("assists_per90", "Asistencias / 90", "", 2),
    ("tackles_won_per90", "Entradas ganadas / 90", "", 2),
    ("interceptions_per90", "Intercepciones / 90", "", 2),
    ("turnovers_per90", "Pérdidas / 90", "", 2),
    ("dispossessed_per90", "Desposesiones / 90", "", 2),
]


def _to_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _block_value(frame: pd.DataFrame, metric: str) -> float | None:
    if frame.empty:
        return None
    if metric == "pass_completion_pct":
        total = pd.to_numeric(frame.get("passes_total"), errors="coerce").fillna(0).sum()
        completed = pd.to_numeric(frame.get("passes_completed"), errors="coerce").fillna(0).sum()
        return None if total <= 0 else float(completed / total * 100.0)
    series = pd.to_numeric(frame.get(metric), errors="coerce")
    return None if series.dropna().empty else float(series.mean())


def build_team_technical_profile(history: pd.DataFrame) -> list[dict[str, Any]]:
    if history.empty:
        return []
    ordered = history.copy()
    ordered["match_date"] = pd.to_datetime(ordered["match_date"])
    ordered = ordered.sort_values(["match_date", "match_id"], ascending=[False, False])
    latest = ordered.head(1)
    last5 = ordered.head(5)
    previous5 = ordered.iloc[5:10]
    profile = []
    for key, label, suffix, decimals in TEAM_METRICS:
        current = _block_value(latest, key)
        recent = _block_value(last5, key)
        previous = _block_value(previous5, key)
        delta = None if recent is None or previous is None else recent - previous
        profile.append({
            "key": key,
            "label": label,
            "suffix": suffix,
            "decimals": decimals,
            "current": current,
            "last5": recent,
            "previous5": previous,
            "delta_5v5": delta,
        })
    return profile


def build_match_technical_profile(history: pd.DataFrame, match_id: str) -> list[dict[str, Any]]:
    """Compare the selected match only with matches that happened strictly before it."""
    if history.empty:
        return []
    ordered = history.copy()
    ordered["match_date"] = pd.to_datetime(ordered["match_date"])
    selected = ordered.loc[ordered["match_id"].astype(str) == str(match_id)]
    if selected.empty:
        return []
    row = selected.iloc[0]
    selected_date = row["match_date"]
    prior = ordered.loc[ordered["match_date"] < selected_date].sort_values(
        ["match_date", "match_id"], ascending=[False, False]
    ).head(5)
    profile = []
    for key, label, suffix, decimals in TEAM_METRICS:
        current = _block_value(selected.head(1), key)
        baseline = _block_value(prior, key)
        delta = None if current is None or baseline is None else current - baseline
        profile.append({
            "key": key,
            "label": label,
            "suffix": suffix,
            "decimals": decimals,
            "current": current,
            "prior5": baseline,
            "delta_vs_prior5": delta,
            "baseline_matches": int(len(prior)),
        })
    return profile


def _player_enrich(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    out = frame.copy()
    minutes = pd.to_numeric(out.get("minutes"), errors="coerce").fillna(0)
    for col in [
        "passes_total", "passes_completed", "shots_total", "goals", "assists",
        "tackles_won", "interceptions", "turnovers", "dispossessed",
    ]:
        out[col] = pd.to_numeric(out.get(col), errors="coerce").fillna(0)
    out["pass_completion_pct"] = out.apply(
        lambda r: None if float(r["passes_total"]) <= 0 else float(r["passes_completed"] / r["passes_total"] * 100.0),
        axis=1,
    )
    denom = minutes.replace(0, pd.NA)
    out["passes_completed_per90"] = out["passes_completed"] * 90.0 / denom
    out["shots_per90"] = out["shots_total"] * 90.0 / denom
    out["goals_per90"] = out["goals"] * 90.0 / denom
    out["assists_per90"] = out["assists"] * 90.0 / denom
    out["tackles_won_per90"] = out["tackles_won"] * 90.0 / denom
    out["interceptions_per90"] = out["interceptions"] * 90.0 / denom
    out["turnovers_per90"] = out["turnovers"] * 90.0 / denom
    out["dispossessed_per90"] = out["dispossessed"] * 90.0 / denom
    return out


def build_player_technical_profile(history: pd.DataFrame) -> list[dict[str, Any]]:
    if history.empty:
        return []
    ordered = _player_enrich(history)
    ordered["match_date"] = pd.to_datetime(ordered["match_date"])
    ordered = ordered.loc[pd.to_numeric(ordered["minutes"], errors="coerce").fillna(0) > 0]
    ordered = ordered.sort_values(["match_date", "match_id"], ascending=[False, False])
    latest = ordered.head(1)
    last5 = ordered.head(5)
    previous5 = ordered.iloc[5:10]
    profile = []
    for key, label, suffix, decimals in PLAYER_METRICS:
        current = _block_value(latest, key)
        recent = _block_value(last5, key)
        previous = _block_value(previous5, key)
        delta = None if recent is None or previous is None else recent - previous
        profile.append({
            "key": key,
            "label": label,
            "suffix": suffix,
            "decimals": decimals,
            "current": current,
            "last5": recent,
            "previous5": previous,
            "delta_5v5": delta,
        })
    return profile
