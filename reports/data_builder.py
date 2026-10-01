"""Build read-only structured payloads for Team / Player / Match PDF reports.

The report layer consumes validated analytics only. In demo mode it anonymises
presentation identities before PDF rendering; IDs and analytical values remain intact.
"""
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
from app.performance_score_access import SCORE_VERSION, get_latest_player_score, get_player_score_history
from app.presentation import (
    anonymize_frame,
    build_opponent_aliases,
    build_player_aliases,
    build_player_name_aliases,
    demo_mode,
    display_team_name,
    replace_known_names,
)
from reports.report_data_access import get_team_match_technical_history
from reports.report_metrics import (
    REPORT_METRIC_VERSION,
    build_match_technical_profile,
    build_player_technical_profile,
    build_team_technical_profile,
)

REPORT_SCHEMA_VERSION = "0.6.0"


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


def _clean_nested(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _clean_nested(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean_nested(v) for v in value]
    if isinstance(value, tuple):
        return [_clean_nested(v) for v in value]
    return _clean(value)


def _guardrails() -> dict[str, bool]:
    return {
        "recommendation_policy_validated": False,
        "cross_player_ranking_allowed": False,
        "report_may_recalculate_critical_metrics": False,
        "report_may_issue_tactical_recommendation": False,
    }


def _context(db_path: Path, team_id: str) -> dict[str, Any]:
    teams = list_teams(db_path)
    ids = teams["team_id"].astype(str).tolist() if not teams.empty else []
    if str(team_id) not in ids:
        raise ValueError(f"Unknown or unauthorized team_id: {team_id}")
    row = teams.loc[teams["team_id"].astype(str) == str(team_id)].iloc[0]
    raw_team = str(row["display_name"])
    team_index = ids.index(str(team_id)) + 1
    squad = get_squad_summary(db_path, team_id)
    matches = get_team_matches(db_path, team_id)
    player_aliases = build_player_aliases(squad)
    player_name_aliases = build_player_name_aliases(squad)
    opponent_aliases = build_opponent_aliases(matches.get("opponent", pd.Series(dtype=str)).tolist())
    return {
        "raw_team": raw_team,
        "team_display": display_team_name(raw_team, team_index),
        "squad": squad,
        "matches": matches,
        "player_aliases": player_aliases,
        "player_name_aliases": player_name_aliases,
        "opponent_aliases": opponent_aliases,
    }


def _team_identity(team_id: str, ctx: dict[str, Any]) -> dict[str, Any]:
    return {"team_id": str(team_id), "display_name": ctx["team_display"]}


def _anon(frame: pd.DataFrame, ctx: dict[str, Any]) -> pd.DataFrame:
    return anonymize_frame(
        frame,
        player_aliases_by_id=ctx["player_aliases"],
        player_name_aliases=ctx["player_name_aliases"],
        opponent_aliases=ctx["opponent_aliases"],
    )


def _mask_nested(value: Any, ctx: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {k: _mask_nested(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_nested(v, ctx) for v in value]
    if isinstance(value, tuple):
        return tuple(_mask_nested(v, ctx) for v in value)
    if isinstance(value, str):
        return replace_known_names(
            value,
            player_name_aliases=ctx["player_name_aliases"],
            opponent_aliases=ctx["opponent_aliases"],
            team_name=ctx["raw_team"],
            team_alias=ctx["team_display"],
        )
    return _clean(value)


def _finalize_payload(payload: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Fail-safe presentation sanitization for every demo report payload."""
    if not demo_mode():
        return payload
    return _mask_nested(payload, ctx)


def build_team_report_data(db_path: Path, team_id: str) -> dict[str, Any]:
    db_path = Path(db_path)
    ctx = _context(db_path, team_id)
    squad = _anon(ctx["squad"], ctx)
    matches = _anon(ctx["matches"], ctx)
    technical_history_raw = get_team_match_technical_history(db_path, team_id)
    technical_history = _anon(technical_history_raw, ctx)
    technical_profile = build_team_technical_profile(technical_history_raw)
    try:
        rating_snapshot = _anon(get_team_player_rating_snapshot(db_path, team_id), ctx)
        rating_history = _anon(get_team_match_rating_history(db_path, team_id), ctx)
    except Exception:
        rating_snapshot = pd.DataFrame()
        rating_history = pd.DataFrame()

    payload = {
        "report_type": "team",
        "schema_version": REPORT_SCHEMA_VERSION,
        "language": "es",
        "demo_mode": demo_mode(),
        "engine_version": FINAL_ENGINE_VERSION,
        "feature_version": BASE_FEATURE_VERSION,
        "report_metric_version": REPORT_METRIC_VERSION,
        "match_rating_version": MATCH_RATING_VERSION,
        "performance_index_version": SCORE_VERSION,
        "team": _team_identity(team_id, ctx),
        "overview": {k: _clean(v) for k, v in get_team_overview(db_path, team_id).items()},
        "matches": _records(matches),
        "squad": _records(squad),
        "rating_snapshot": _records(rating_snapshot),
        "rating_history": _records(rating_history),
        "technical_history": _records(technical_history),
        "technical_profile": _clean_nested(technical_profile),
        "guardrails": _guardrails(),
    }
    return _finalize_payload(payload, ctx)


def build_player_report_data(db_path: Path, team_id: str, player_id: str) -> dict[str, Any]:
    db_path = Path(db_path)
    ctx = _context(db_path, team_id)
    squad = ctx["squad"]
    selected = squad.loc[squad["player_id"].astype(str) == str(player_id)]
    if selected.empty:
        raise ValueError(f"Unknown player_id for team: {player_id}")

    summary = _records(_anon(selected, ctx), 1)[0]
    history_raw = get_player_match_history(db_path, team_id, player_id)
    history = _anon(history_raw, ctx)
    ratings = _anon(get_player_match_ratings(db_path, team_id, player_id), ctx)
    gate = get_latest_player_gate(db_path, team_id, player_id)
    technical_profile = build_player_technical_profile(history_raw)

    try:
        team_snapshot = _anon(get_team_player_rating_snapshot(db_path, team_id), ctx)
        selected_snapshot = team_snapshot.loc[team_snapshot["player_id"].astype(str) == str(player_id)]
        player_snapshot = None if selected_snapshot.empty else _records(selected_snapshot, 1)[0]
    except Exception:
        player_snapshot = None

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
        if "opponent" in frame.columns:
            frame = _anon(frame, ctx)
        feature_history[feature_name] = _records(frame, 10)

    payload = {
        "report_type": "player",
        "schema_version": REPORT_SCHEMA_VERSION,
        "language": "es",
        "demo_mode": demo_mode(),
        "engine_version": FINAL_ENGINE_VERSION,
        "feature_version": BASE_FEATURE_VERSION,
        "report_metric_version": REPORT_METRIC_VERSION,
        "match_rating_version": MATCH_RATING_VERSION,
        "performance_index_version": SCORE_VERSION,
        "team": _team_identity(team_id, ctx),
        "player_id": str(player_id),
        "summary": summary,
        "player_snapshot": player_snapshot,
        "match_history": _records(history, 15),
        "match_ratings": _records(ratings.sort_values("match_date", ascending=False), 15),
        "performance_index": None if latest_index is None else {k: _clean(v) for k, v in latest_index.items()},
        "performance_index_history": _records(index_history.sort_values("match_date", ascending=False), 15),
        "latest_role_fit_gate": None if gate is None else {k: _clean(v) for k, v in gate.items()},
        "feature_history": feature_history,
        "technical_profile": _clean_nested(technical_profile),
        "guardrails": _guardrails(),
    }
    return _finalize_payload(payload, ctx)


def build_match_report_data(db_path: Path, team_id: str, match_id: str) -> dict[str, Any]:
    db_path = Path(db_path)
    ctx = _context(db_path, team_id)
    matches = ctx["matches"]
    selected = matches.loc[matches["match_id"].astype(str) == str(match_id)]
    if selected.empty:
        raise ValueError(f"Unknown match_id for team: {match_id}")

    selected = _anon(selected, ctx)
    lineup = _anon(get_match_lineup(db_path, team_id, match_id), ctx)
    ratings = _anon(get_match_ratings(db_path, team_id, match_id), ctx)
    observations = _mask_nested(get_match_observations(db_path, team_id, match_id), ctx)
    technical_history_raw = get_team_match_technical_history(db_path, team_id)
    technical_profile = build_match_technical_profile(technical_history_raw, match_id)
    try:
        team_history = _anon(get_team_match_rating_history(db_path, team_id), ctx)
        selected_summary = team_history.loc[team_history["match_id"].astype(str) == str(match_id)]
        match_summary = None if selected_summary.empty else _records(selected_summary, 1)[0]
    except Exception:
        match_summary = None

    if not ratings.empty:
        merge_cols = [
            "player", "match_rating_10", "match_rating_confidence",
            "match_rating_status", "match_rating_context", "position_group",
        ]
        rating_names = ratings[[c for c in merge_cols if c in ratings.columns]].copy()
        if "player" in lineup.columns and "player" in rating_names.columns:
            lineup = lineup.merge(rating_names, on="player", how="left")

    payload = {
        "report_type": "match",
        "schema_version": REPORT_SCHEMA_VERSION,
        "language": "es",
        "demo_mode": demo_mode(),
        "engine_version": FINAL_ENGINE_VERSION,
        "feature_version": BASE_FEATURE_VERSION,
        "report_metric_version": REPORT_METRIC_VERSION,
        "match_rating_version": MATCH_RATING_VERSION,
        "performance_index_version": SCORE_VERSION,
        "team": _team_identity(team_id, ctx),
        "match": _records(selected, 1)[0],
        "match_summary": match_summary,
        "lineup": _records(lineup),
        "ratings": _records(ratings),
        "observations": observations,
        "technical_profile": _clean_nested(technical_profile),
        "guardrails": _guardrails(),
    }
    return _finalize_payload(payload, ctx)
