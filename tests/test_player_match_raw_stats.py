from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
if str(DATA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_DIR))

from import_demo_player_match_stats_v2 import (  # noqa: E402
    STAT_COLUMNS,
    nullable_count,
    validate_count_frame,
)


def make_frame() -> pd.DataFrame:
    row: dict[str, object] = {
        "source_match_id": "m1",
        "source_player_id": "p1",
    }
    for name in STAT_COLUMNS:
        row[name] = None

    row.update(
        {
            "passes_total": 10.0,
            "passes_completed": 8.0,
            "long_balls_total": 2.0,
            "long_balls_completed": 1.0,
            "crosses_total": 3.0,
            "crosses_completed": 1.0,
            "dribbles_total": 2.0,
            "dribbles_won": 1.0,
            "shots_total": 2.0,
            "shots_blocked": 1.0,
            "goals": 1.0,
            "tackles_total": 4.0,
            "tackles_won": 3.0,
            "goals_conceded": 2.0,
        }
    )
    return pd.DataFrame([row])


def test_approved_v2_columns_present() -> None:
    assert STAT_COLUMNS["tackles_won"] == "wonTackle"
    assert STAT_COLUMNS["goals_conceded"] == "goalsConceded"


def test_nullable_count_preserves_null_and_accepts_integral_double() -> None:
    assert nullable_count(None) is None
    assert nullable_count(float("nan")) is None
    assert nullable_count(3.0) == 3


def test_validate_count_frame_accepts_sparse_valid_raw_counts() -> None:
    validate_count_frame(make_frame())


def test_validate_count_frame_rejects_completed_above_total() -> None:
    frame = make_frame()
    frame.loc[0, "passes_completed"] = 11.0
    with pytest.raises(RuntimeError, match="passes_completed > passes_total"):
        validate_count_frame(frame)


def test_validate_count_frame_rejects_tackles_won_above_total() -> None:
    frame = make_frame()
    frame.loc[0, "tackles_won"] = 5.0
    with pytest.raises(RuntimeError, match="tackles_won > tackles_total"):
        validate_count_frame(frame)


def test_nullable_count_rejects_negative_and_fractional_counts() -> None:
    with pytest.raises(RuntimeError, match="Negative count"):
        nullable_count(-1)
    with pytest.raises(RuntimeError, match="Non-integer count"):
        nullable_count(1.5)
