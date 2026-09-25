from decision_tree.build_stage2 import classify_delta, classify_slope, compose_domain_state


def test_classify_delta_contract():
    assert classify_delta(None, 4, 1.0) == "CURRENT_VALUE_MISSING"
    assert classify_delta(1.0, None, 1.0) == "HISTORY_COUNT_MISSING"
    assert classify_delta(1.0, 0, None) == "NO_PRIOR_HISTORY"
    assert classify_delta(2.0, 3, 0.5) == "ABOVE_PRIOR_MEAN"
    assert classify_delta(1.0, 3, -0.5) == "BELOW_PRIOR_MEAN"
    assert classify_delta(1.0, 3, 0.0) == "EQUAL_PRIOR_MEAN"


def test_classify_slope_contract():
    assert classify_slope(None, 1.0) == "HISTORY_COUNT_MISSING"
    assert classify_slope(1, None) == "INSUFFICIENT_PRIOR_HISTORY"
    assert classify_slope(3, 0.2) == "PRIOR_TREND_UP"
    assert classify_slope(3, -0.2) == "PRIOR_TREND_DOWN"
    assert classify_slope(3, 0.0) == "PRIOR_TREND_FLAT"


def test_compose_domain_state_is_descriptive_only():
    assert compose_domain_state(None, 3, 1.0, 1.0) == "CURRENT_VALUE_MISSING"
    assert compose_domain_state(1.0, 0, None, None) == "NO_PRIOR_HISTORY"
    assert compose_domain_state(2.0, 3, 0.5, 0.1) == "ABOVE_PRIOR_MEAN__PRIOR_TREND_UP"
    assert compose_domain_state(1.0, 3, -0.5, -0.1) == "BELOW_PRIOR_MEAN__PRIOR_TREND_DOWN"
