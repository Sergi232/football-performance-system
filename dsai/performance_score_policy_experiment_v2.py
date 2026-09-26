"""PERF-13 compatibility runner for pandas 3.x.

Wraps performance_score_policy_experiment.py and replaces NULL-sensitive grouping
with explicit sentinel grouping. Analytical semantics are unchanged:
- unknown source_position never receives role-aware normalization;
- it falls back to the global percentile;
- no DB mutation, production weight, threshold, ranking or recommendation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import performance_score_policy_experiment as perf

UNKNOWN_POSITION = "__UNKNOWN_SOURCE_POSITION__"


def safe_role_aware_score(
    frame: pd.DataFrame,
    value_col: str,
    direction: str,
) -> tuple[pd.Series, dict[str, int]]:
    """Percentile within known source_position; unknown/unstable groups use global fallback."""
    global_score = perf.empirical_score(frame[value_col], direction)
    out = pd.Series(np.nan, index=frame.index, dtype=float)
    fallback_rows = 0
    role_rows = 0

    grouping = frame["source_position"].astype("object").where(
        frame["source_position"].notna(), UNKNOWN_POSITION
    )

    for position, idx in grouping.groupby(grouping, sort=False).groups.items():
        idx = pd.Index(idx)
        x = pd.to_numeric(frame.loc[idx, value_col], errors="coerce")
        valid = x.dropna()
        known_position = position != UNKNOWN_POSITION

        if known_position and len(valid) >= 2 and int(valid.nunique()) >= 2:
            out.loc[idx] = perf.empirical_score(x, direction)
            role_rows += int(x.notna().sum())
        else:
            out.loc[idx] = global_score.loc[idx]
            fallback_rows += int(x.notna().sum())

    return out, {
        "role_normalized_non_null_rows": role_rows,
        "global_fallback_non_null_rows": fallback_rows,
    }


_original_build_base_frame = perf.build_base_frame


def safe_build_base_frame(db_path):
    frame, direction_by_feature, primary_dimension, used_features, dimensions = (
        _original_build_base_frame(db_path)
    )
    # Keep analytical NULL semantics available via a flag while using a non-null
    # grouping key so pandas 3.x does not build a Categorical with null categories.
    frame["source_position_missing"] = frame["source_position"].isna()
    frame["source_position"] = frame["source_position"].astype("object").where(
        frame["source_position"].notna(), UNKNOWN_POSITION
    )
    return frame, direction_by_feature, primary_dimension, used_features, dimensions


perf.role_aware_score = safe_role_aware_score
perf.build_base_frame = safe_build_base_frame


if __name__ == "__main__":
    perf.main()
