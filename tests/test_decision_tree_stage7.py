from decision_tree.build_stage7 import recommendation_gate


def test_role_unknown_is_not_recommended():
    out = recommendation_gate("ROLE_UNKNOWN")
    assert out["N13000.100"] == "ROLE_UNKNOWN"
    assert out["N13000.110"] == "RECOMMENDATION_POLICY_NOT_VALIDATED"
    assert out["N13000.120"] == "RECOMMENDATION_NOT_ISSUED_ROLE_UNKNOWN"


def test_no_evidence_is_not_recommended():
    out = recommendation_gate("NO_EVALUABLE_ROLE_EVIDENCE")
    assert out["N13000.100"] == "NO_EVALUABLE_ROLE_EVIDENCE"
    assert out["N13000.120"] == "RECOMMENDATION_NOT_ISSUED_NO_EVIDENCE"


def test_available_evidence_still_requires_validated_policy():
    out = recommendation_gate("ROLE_EVIDENCE_AVAILABLE")
    assert out["N13000.100"] == "EVIDENCE_AVAILABLE"
    assert out["N13000.110"] == "RECOMMENDATION_POLICY_NOT_VALIDATED"
    assert out["N13000.120"] == "RECOMMENDATION_NOT_ISSUED_POLICY_UNVALIDATED"
