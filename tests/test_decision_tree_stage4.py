from decision_tree.build_stage4 import classify_role_relative, clean_role


def test_clean_role_contract():
    assert clean_role(None) is None
    assert clean_role("") is None
    assert clean_role("   ") is None
    assert clean_role("  CF ") == "CF"


def test_classify_role_relative_missing_contract():
    assert classify_role_relative(None, 1.0, 3.0, 0.2) == "ROLE_UNKNOWN"
    assert classify_role_relative("CF", None, 3.0, 0.2) == "CURRENT_VALUE_MISSING"
    assert classify_role_relative("CF", 1.0, None, 0.2) == "ROLE_HISTORY_MISSING"
    assert classify_role_relative("CF", 1.0, 0.0, None) == "NO_PRIOR_METRIC_HISTORY_IN_ROLE"
    assert classify_role_relative("CF", 1.0, 2.0, None) == "ROLE_DELTA_NOT_EVALUABLE"


def test_classify_role_relative_direction_is_descriptive():
    assert classify_role_relative("CF", 2.0, 3.0, 0.5) == "ABOVE_ROLE_PRIOR_MEAN"
    assert classify_role_relative("CF", 1.0, 3.0, -0.5) == "BELOW_ROLE_PRIOR_MEAN"
    assert classify_role_relative("CF", 1.0, 3.0, 0.0) == "EQUAL_ROLE_PRIOR_MEAN"
