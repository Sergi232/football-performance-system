from decision_tree.build_stage5 import encode_temporal_numeric


def test_encode_temporal_numeric_requires_two_prior_observations():
    assert encode_temporal_numeric(0.0, None, "MISSING") == "INSUFFICIENT_PRIOR_HISTORY"
    assert encode_temporal_numeric(1.0, None, "MISSING") == "INSUFFICIENT_PRIOR_HISTORY"


def test_encode_temporal_numeric_preserves_missing_state_after_history_exists():
    assert encode_temporal_numeric(2.0, None, "PRIOR_STD_NOT_EVALUABLE") == "PRIOR_STD_NOT_EVALUABLE"


def test_encode_temporal_numeric_exposes_exact_numeric_evidence_without_label():
    result = encode_temporal_numeric(3.0, 0.125, "MISSING")
    assert float(result) == 0.125
    assert "HIGH" not in result
    assert "LOW" not in result


def test_missing_history_count_is_explicit():
    assert encode_temporal_numeric(None, 0.5, "MISSING") == "HISTORY_COUNT_MISSING"
