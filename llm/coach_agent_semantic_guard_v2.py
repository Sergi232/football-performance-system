"""V5 evidence normalization for the Coach Copilot semantic guard.

The validated analytics layer uses concrete V5 column names such as
match_rating_10, primary_role, position_group, latest_position_group and
median_match_rating. The original compact synthesis adapter still expected older
aliases in several places. This module normalizes those fields before synthesis and
before deterministic semantic rendering.
"""
from __future__ import annotations

from typing import Any

from llm import coach_agent_hybrid as _hybrid
from llm import coach_agent_semantic_guard as _guard  # installs safe final renderer


def _scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _pick(mapping: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(mapping, dict):
        return {}
    return {key: mapping.get(key) for key in keys if key in mapping and _scalar(mapping.get(key))}


def _alias(mapping: Any, aliases: dict[str, tuple[str, ...]]) -> dict[str, Any]:
    if not isinstance(mapping, dict):
        return {}
    out: dict[str, Any] = {}
    for target, sources in aliases.items():
        for source in sources:
            if source in mapping and _scalar(mapping.get(source)):
                out[target] = mapping.get(source)
                break
    return out


def compact_payload_v5(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if name == "get_team_snapshot":
        history: list[dict[str, Any]] = []
        for row in (payload.get("recent_team_rating_history") or [])[-4:]:
            item = _alias(row, {
                "match_date": ("match_date",),
                "opponent": ("opponent",),
                "score_for": ("score_for",),
                "score_against": ("score_against",),
                "team_avg_rating": ("median_match_rating", "team_avg_rating", "avg_match_rating"),
                "confidence": ("median_confidence", "confidence"),
                "rated_players": ("players_rated", "rated_players"),
            })
            history.append(item)

        form: list[dict[str, Any]] = []
        for row in (payload.get("player_recent_form") or [])[:6]:
            form.append(_alias(row, {
                "player": ("player",),
                "position": ("latest_position_group", "position", "role"),
                "latest_match_rating": ("latest_match_rating",),
                "avg_last5": ("avg_last5",),
                "avg_previous5": ("avg_previous5",),
                "trend_delta_5v5": ("trend_delta_5v5",),
                "n_last5": ("n_last5",),
                "n_previous5": ("n_previous5",),
                "latest_confidence": ("latest_confidence",),
                "appearances": ("rated_matches", "appearances"),
            }))

        return {
            "overview": _pick(payload.get("overview"), ("matches", "players", "player_minutes", "goals", "assists")),
            "match_rating_version": payload.get("match_rating_version"),
            "recent_team_rating_history": history,
            "player_recent_form": form,
            "definition": payload.get("definition"),
        }

    if name == "get_player_profile":
        summary = _alias(payload.get("summary"), {
            "player_id": ("player_id",),
            "player": ("player",),
            "appearances": ("appearances",),
            "starts": ("starts",),
            "minutes": ("minutes",),
            "goals": ("goals",),
            "assists": ("assists",),
            "role": ("observed_roles", "primary_role", "role", "position"),
        })
        ratings: list[dict[str, Any]] = []
        for row in (payload.get("recent_match_ratings") or [])[-5:]:
            ratings.append(_alias(row, {
                "match_date": ("match_date",),
                "opponent": ("opponent",),
                "minutes": ("minutes_played", "minutes"),
                "role": ("primary_role", "role"),
                "position": ("position_group", "position"),
                "match_rating": ("match_rating_10", "match_rating", "rating"),
                "confidence": ("match_rating_confidence", "confidence"),
                "route": ("rating_path", "route", "rating_route"),
            }))
        return {
            "player": payload.get("player"),
            "summary": summary,
            "recent_match_ratings": ratings,
            "latest_performance_index": _hybrid._pick_scalars(payload.get("latest_performance_index"), 10),
            "latest_expert_gate": _hybrid._pick_scalars(payload.get("latest_expert_gate"), 10),
        }

    if name == "get_player_match_stats":
        rows = payload.get("rows") or []
        return {
            "player": payload.get("player"),
            "rows": [_hybrid._pick_scalars(r, 16) for r in rows[:5] if isinstance(r, dict)],
            "note": payload.get("note"),
        }

    if name == "get_match_detail":
        ratings: list[dict[str, Any]] = []
        for row in (payload.get("ratings") or [])[:16]:
            ratings.append(_alias(row, {
                "player": ("player",),
                "role": ("primary_role", "role"),
                "position": ("position_group", "position"),
                "minutes": ("minutes_played", "minutes"),
                "match_rating": ("match_rating_10", "match_rating", "rating"),
                "confidence": ("match_rating_confidence", "confidence"),
                "route": ("rating_path", "route", "rating_route"),
            }))
        return {
            "match": _pick(payload.get("match"), (
                "match_id", "match_date", "venue", "opponent", "score_for", "score_against", "starting_formation"
            )),
            "ratings": ratings,
            "observations": payload.get("observations"),
            "note": payload.get("note"),
        }

    if name == "compare_players":
        players: list[dict[str, Any]] = []
        for row in (payload.get("players") or [])[:6]:
            players.append(_alias(row, {
                "player": ("player",),
                "position": ("latest_position_group", "position_group", "position", "role"),
                "rated_matches": ("rated_matches",),
                "latest_match_rating": ("latest_match_rating",),
                "latest_confidence": ("latest_confidence",),
                "avg_last5": ("avg_last5",),
                "avg_previous5": ("avg_previous5",),
                "n_last5": ("n_last5",),
                "n_previous5": ("n_previous5",),
                "trend_delta_5v5": ("trend_delta_5v5",),
            }))
        return {
            "players": players,
            "unresolved": (payload.get("unresolved") or [])[:6],
            "comparison_policy": payload.get("comparison_policy"),
        }

    if name == "get_data_quality":
        return {
            "attention_summary": [_hybrid._pick_scalars(r, 8) for r in (payload.get("attention_summary") or [])[:6] if isinstance(r, dict)],
            "recent_flags": [_hybrid._pick_scalars(r, 6) for r in (payload.get("recent_flags") or [])[:5] if isinstance(r, dict)],
            "attention_error": payload.get("attention_error"),
            "gps_status": _hybrid._pick_scalars(payload.get("gps_status"), 8),
            "policy": payload.get("policy"),
        }

    if name == "get_player_gps":
        return {
            "player": payload.get("player"),
            "gps_history": [_hybrid._pick_scalars(r, 10) for r in (payload.get("gps_history") or [])[-5:] if isinstance(r, dict)],
            "interpretation": payload.get("interpretation"),
            "error": payload.get("error"),
        }

    return _hybrid._pick_scalars(payload, 12)


def install() -> None:
    _hybrid._compact_payload = compact_payload_v5
    _hybrid._postprocess_grounded = _guard.postprocess_grounded_safe


install()
