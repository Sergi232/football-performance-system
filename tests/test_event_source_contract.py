from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
if str(DATA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_DIR))

from import_demo_events_contract import validate_shot_contract  # noqa: E402


def make_sources(shots_on_target: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    shot_events = pd.DataFrame(
        [
            {
                "match_id": "m1",
                "event_id": 1,
                "player_id": "p1",
                "is_own_goal": False,
                "type_id": 16,
                "is_goal": True,
                "is_blocked": False,
                "situation": "OpenPlay",
            },
            {
                "match_id": "m1",
                "event_id": 2,
                "player_id": "p1",
                "is_own_goal": False,
                "type_id": 13,
                "is_goal": False,
                "is_blocked": False,
                "situation": "OpenPlay",
            },
            {
                "match_id": "m1",
                "event_id": 3,
                "player_id": "p1",
                "is_own_goal": False,
                "type_id": 15,
                "is_goal": False,
                "is_blocked": True,
                "situation": "OpenPlay",
            },
            {
                "match_id": "m1",
                "event_id": 4,
                "player_id": "p1",
                "is_own_goal": False,
                "type_id": 15,
                "is_goal": False,
                "is_blocked": False,
                "situation": "Penalty",
            },
        ]
    )
    shot_totals = pd.DataFrame(
        [
            {
                "match_id": "m1",
                "player_id": "p1",
                "total_shots": 4,
                "shots_on_target": shots_on_target,
                "shots_off_target": 1,
                "shots_blocked": 1,
                "goals": 1,
                "shots_penalty": 1,
            }
        ]
    )
    return shot_events, shot_totals


def test_source_contract_accepts_ambiguous_block_without_inventing_identity() -> None:
    shot_events, shot_totals = make_sources(shots_on_target=2)
    normalized, checks = validate_shot_contract(shot_events, shot_totals)

    assert len(normalized) == 4
    assert checks["total_shots"] == 0
    assert checks["shots_off_target"] == 0
    assert checks["goals"] == 0
    assert checks["shots_penalty"] == 0
    assert checks["shots_on_target"] == 0
    assert checks["on_target_plus_blocked_partition"] == 0
    assert checks["shots_blocked"] == "AGGREGATE_CANONICAL"

    blocked = normalized.loc[normalized["event_id"] == 3].iloc[0]
    assert blocked["normalized_outcome"] == "BLOCKED"
    assert blocked["source_on_target"] is None


def test_source_contract_rejects_impossible_on_target_aggregate() -> None:
    shot_events, shot_totals = make_sources(shots_on_target=4)

    with pytest.raises(RuntimeError, match="shots_on_target bounds"):
        validate_shot_contract(shot_events, shot_totals)
