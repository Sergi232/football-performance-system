from decision_tree.build_stage1 import (
    classify_activity,
    classify_delta,
    classify_role,
    classify_slope,
)


def test_n1000_activity_states():
    assert classify_activity(True, 90) == "STARTER_ACTIVE"
    assert classify_activity(False, 25) == "SUBSTITUTE_ACTIVE"
    assert classify_activity(False, 0) == "LISTED_NO_MINUTES"
    assert classify_activity(None, None) == "MINUTES_UNKNOWN"


def test_n2000_role_state():
    assert classify_role("Centre Back") == "Centre Back"
    assert classify_role(None) == "ROLE_UNKNOWN"
    assert classify_role("  ") == "ROLE_UNKNOWN"


def test_n3000_delta_states_are_descriptive_only():
    assert classify_delta(1.2, 0, None) == "NO_PRIOR_HISTORY"
    assert classify_delta(1.2, 4, 0.3) == "ABOVE_PRIOR_MEAN"
    assert classify_delta(1.2, 4, -0.3) == "BELOW_PRIOR_MEAN"
    assert classify_delta(1.2, 4, 0.0) == "EQUAL_PRIOR_MEAN"
    assert classify_delta(None, 4, None) == "CURRENT_VALUE_MISSING"


def test_n3000_slope_requires_two_prior_values():
    assert classify_slope(0, None) == "INSUFFICIENT_PRIOR_HISTORY"
    assert classify_slope(1, None) == "INSUFFICIENT_PRIOR_HISTORY"
    assert classify_slope(3, 0.1) == "PRIOR_TREND_UP"
    assert classify_slope(3, -0.1) == "PRIOR_TREND_DOWN"
    assert classify_slope(3, 0.0) == "PRIOR_TREND_FLAT"
