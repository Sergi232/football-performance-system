"""Build read-only structured payloads for Team / Player / Match PDF reports."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.data_access import (
    BASE_FEATURE_VERSION,
    FINAL_ENGINE_VERSION,
    get_latest_player_gate,
    get_match_lineup,
    get_player_feature_history,
    get_player_match_history,
    get_squad_summary,
    get_team_matches,
    get_team_overview,
    list_base_features,
    list_teams,
)
from app.match_insights import get_match_observations
from app.match_rating_access import (
    MATCH_RATING_VERSION,
    get_match_ratings,
    get_player_match_ratings,
    get_team_match_rating_history,
    get_team_player_rating_snapshot,
)
from app.performance_score_access import (
    SCORE_VERSION,
    get_latest_player_score,
    get_player_score_history,
)

REPORT_SCHEMA_VERSION = "0.3.0"


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
    return [{str(key): _clean(value) for key, value in row.items()} for row in frame.to_dict(orient="records")]


def _team_identity(db_path: Path, team_id: str) -> dict[str, Any]:
    teams = list_teams(db_path)
    selected = teams.loc[teams["team_id"] == team_id]
    if selected.empty:
        raise ValueError(f"Unknown team_id: {team_id}")
    row = selected.iloc[0]
    return {"team_id": team_id, "display_name": _clean(row["display_name"])}


def _guardrails() -> dict[str, bool]:
    return {
        "recommendation_policy_validated": False,
        "cross_player_ranking_allowed": False,
        "report_may_recalculate_critical_metrics": False,
        "report_may_issue_tactical_recommendation": False,
    }


def build_team_report_data(db_path: Path, team_id: str) -> dict[str, Any]:
    db_path = Path(db_path)
    try:
        rating_snapshot = get_team_player_rating_snapshot(db_path, team_id)
        rating_history = get_team_match_rating_history(db_path, team_id)
    except Exception:
        rating_snapshot = pd.DataFrame()
        rating_history = pd.DataFrame()

    return {
        "report_type": "team",
        "schema_version": REPORT_SCHEMA_VERSION,
        "engine_version": FINAL_ENGINE_VERSION,
        "feature_version": BASE_FEATURE_VERSION,
        "match_rating_version": MATCH_RATING_VERSION,
        "performance_index_version": SCORE_VERSION,
        "team": _team_identity(db_path, team_id),
        "overview": {k: _clean(v) for k, v in get_team_overview(db_path, team_id).items()},
        "matches": _records(get_team_matches(db_path, team_id)),
        "squad": _records(get_squad_summary(db_path, team_id)),
        "rating_snapshot": _records(rating_snapshot),
        "rating_history": _records(rating_history),
        "guardrails": _guardrails(),
    }


def build_player_report_data(db_path: Path, team_id: str, player_id: str) -> dict[str, Any]:
    db_path = Path(db_path)
    squad = get_squad_summary(db_path, team_id)
    selected = squad.loc[squad["player_id"] == player_id]
    if selected.empty:
        raise ValueError(f"Unknown player_id for team: {player_id}")

    summary = _records(selected, 1)[0]
    history = get_player_match_history(db_path, team_id, player_id)
    ratings = get_player_match_ratings(db_path, team_id, player_id)
    gate = get_latest_player_gate(db_path, team_id, player_id)

    try:
        latest_index = get_latest_player_score(db_path, team_id, player_id)
        index_history = get_player_score_history(db_path, team_id, player_id)
    except Exception:
        latest_index = None
        index_history = pd.DataFrame()

    available = set(list_base_features(db_path, player_id))
    preferred = [
        "pass_completion_rate", "shots_total_per90", "goals_per90",
        "assists_per90", "tackle_success_rate", "interceptions_per90",
    ]
    feature_history: dict[str, list[dict[str, Any]]] = {}
    for feature_name in preferred:
        if feature_name not in available:
            continue
        frame = get_player_feature_history(db_path, player_id, feature_name)
        frame = frame.loc[frame["feature_value"].notna()].sort_values("match_date", ascending=False)
        feature_history[feature_name] = _records(frame, 5)

    return {
        "report_type": "player",
        "schema_version": REPORT_SCHEMA_VERSION,
        "engine_version": FINAL_ENGINE_VERSION,
        "feature_version": BASE_FEATURE_VERSION,
        "match_rating_version": MATCH_RATING_VERSION,
        "performance_index_version": SCORE_VERSION,
        "team": _team_identity(db_path, team_id),
        "player_id": player_id,
        "summary": summary,
        "match_history": _records(history, 15),
        "match_ratings": _records(ratings.sort_values("match_date", ascending=False), 15),
        "performance_index": None if latest_index is None else {k: _clean(v) for k, v in latest_index.items()},
        "performance_index_history": _records(index_history.sort_values("match_date", ascending=False), 15),
        "latest_role_fit_gate": None if gate is None else {k: _clean(v) for k, v in gate.items()},
        "feature_history": feature_history,
        "guardrails": _guardrails(),
    }


def build_match_report_data(db_path: Path, team_id: str, match_id: str) -> dict[str, Any]:
    db_path = Path(db_path)
    matches = get_team_matches(db_path, team_id)
    selected = matches.loc[matches["match_id"] == match_id]
    if selected.empty:
        raise ValueError(f"Unknown match_id for team: {match_id}")

    lineup = get_match_lineup(db_path, team_id, match_id)
    ratings = get_match_ratings(db_path, team_id, match_id)
    observations = get_match_observations(db_path, team_id, match_id)
    if not ratings.empty:
        rating_names = ratings[[
            "player", "match_rating_10", "match_rating_confidence",
            "match_rating_status", "match_rating_context", "position_group",
        ]].copy()
        lineup = lineup.merge(rating_names, on="player", how="left")

    return {
        "report_type": "match",
        "schema_version": REPORT_SCHEMA_VERSION,
        "engine_version": FINAL_ENGINE_VERSION,
        "feature_version": BASE_FEATURE_VERSION,
        "match_rating_version": MATCH_RATING_VERSION,
        "performance_index_version": SCORE_VERSION,
        "team": _team_identity(db_path, team_id),
        "match": _records(selected, 1)[0],
        "lineup": _records(lineup),
        "ratings": _records(ratings),
        "observations": observations,
        "guardrails": _guardrails(),
    }
