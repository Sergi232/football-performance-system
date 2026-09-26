"""Structured, read-only context for the LLM assistant.

The context builder exposes validated/materialized data and decision outputs. It does
not calculate new performance ratings, rankings, thresholds or recommendations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.data_access import (
    FINAL_ENGINE_VERSION,
    get_latest_player_gate,
    get_match_lineup,
    get_player_feature_history,
    get_player_match_history,
    get_squad_summary,
    get_team_matches,
    get_team_overview,
)
from app.match_insights import get_match_observations
from app.match_rating_access import (
    MATCH_RATING_VERSION,
    get_latest_player_match_rating,
    get_match_ratings,
    get_player_match_ratings,
    get_team_match_rating_history,
    get_team_player_rating_snapshot,
)
from app.performance_score_access import SCORE_VERSION, get_latest_player_score


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _records(frame: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if limit is not None:
        frame = frame.head(limit)
    return [
        {str(key): _clean(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def build_team_context(db_path: Path, team_id: str) -> dict[str, Any]:
    overview = get_team_overview(db_path, team_id)
    matches = get_team_matches(db_path, team_id)
    squad = get_squad_summary(db_path, team_id)
    rating_snapshot = get_team_player_rating_snapshot(db_path, team_id)
    rating_history = get_team_match_rating_history(db_path, team_id)
    return {
        "scope": "team",
        "engine_version": FINAL_ENGINE_VERSION,
        "match_rating_version": MATCH_RATING_VERSION,
        "overview": {key: _clean(value) for key, value in overview.items()},
        "matches": _records(matches),
        "squad": _records(squad),
        "match_rating_snapshot": _records(rating_snapshot),
        "match_rating_history": _records(rating_history),
        "guardrails": {
            "recommendation_policy_validated": False,
            "cross_player_ranking_allowed": False,
            "llm_may_recalculate_critical_metrics": False,
            "llm_may_explain_materialized_match_rating": True,
        },
    }


def build_player_context(
    db_path: Path,
    team_id: str,
    player_id: str,
    feature_name: str | None = None,
) -> dict[str, Any]:
    squad = get_squad_summary(db_path, team_id)
    selected = squad.loc[squad["player_id"] == player_id]
    summary = None if selected.empty else _records(selected, 1)[0]
    history = get_player_match_history(db_path, team_id, player_id)
    gate = get_latest_player_gate(db_path, team_id, player_id)
    match_ratings = get_player_match_ratings(db_path, team_id, player_id)
    latest_match_rating = get_latest_player_match_rating(db_path, team_id, player_id)
    latest_index = get_latest_player_score(db_path, team_id, player_id)

    feature_history: list[dict[str, Any]] | None = None
    if feature_name:
        feature_history = _records(get_player_feature_history(db_path, player_id, feature_name))

    return {
        "scope": "player",
        "engine_version": FINAL_ENGINE_VERSION,
        "match_rating_version": MATCH_RATING_VERSION,
        "performance_index_version": SCORE_VERSION,
        "player_id": player_id,
        "summary": summary,
        "match_history": _records(history),
        "match_ratings": _records(match_ratings),
        "latest_match_rating": None if latest_match_rating is None else {k: _clean(v) for k, v in latest_match_rating.items()},
        "latest_performance_index": None if latest_index is None else {k: _clean(v) for k, v in latest_index.items()},
        "latest_role_fit_gate": None if gate is None else {key: _clean(value) for key, value in gate.items()},
        "feature_name": feature_name,
        "feature_history": feature_history,
        "guardrails": {
            "recommendation_policy_validated": False,
            "same_role_evidence_is_descriptive_only": True,
            "llm_may_convert_above_below_to_good_bad": False,
            "llm_may_recalculate_match_rating": False,
            "llm_may_explain_materialized_match_rating": True,
        },
    }


def build_match_context(db_path: Path, team_id: str, match_id: str) -> dict[str, Any]:
    matches = get_team_matches(db_path, team_id)
    selected = matches.loc[matches["match_id"] == match_id]
    match = None if selected.empty else _records(selected, 1)[0]
    lineup = get_match_lineup(db_path, team_id, match_id)
    ratings = get_match_ratings(db_path, team_id, match_id)
    observations = get_match_observations(db_path, team_id, match_id)
    return {
        "scope": "match",
        "engine_version": FINAL_ENGINE_VERSION,
        "match_rating_version": MATCH_RATING_VERSION,
        "match": match,
        "lineup": _records(lineup),
        "match_ratings": _records(ratings),
        "observations": observations,
        "guardrails": {
            "raw_stats_are_observations": True,
            "derived_metrics_must_come_from_feature_engine": True,
            "recommendation_policy_validated": False,
            "llm_may_recalculate_match_rating": False,
            "llm_may_explain_materialized_match_rating": True,
        },
    }
