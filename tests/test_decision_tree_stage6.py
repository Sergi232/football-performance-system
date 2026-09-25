from decision_tree.build_stage6 import summarize_role_evidence


def test_player_fit_summary_partitions_exactly():
    families = {
        "N10000.400": "N4000",
        "N10000.500": "N5000",
        "N10000.600": "N6000",
        "N10000.700": "N7000",
    }
    values = {
        "N10000.400": "ABOVE_ROLE_PRIOR_MEAN",
        "N10000.500": "BELOW_ROLE_PRIOR_MEAN",
        "N10000.600": "EQUAL_ROLE_PRIOR_MEAN",
        "N10000.700": "NO_PRIOR_METRIC_HISTORY_IN_ROLE",
    }
    out = summarize_role_evidence("CM", "5", values, families)
    assert out["N12000.120"] == "3"
    assert out["N12000.130"] == "1"
    assert out["N12000.140"] == "1"
    assert out["N12000.150"] == "1"
    assert out["N12000.160"] == "1"
    assert float(out["N12000.170"]) == 0.75
    assert out["N12000.180"] == "ROLE_EVIDENCE_AVAILABLE"
    assert out["N12000.400"] == "1"
    assert out["N12000.500"] == "1"
    assert out["N12000.600"] == "1"
    assert out["N12000.700"] == "0"


def test_player_fit_summary_does_not_infer_fit_when_role_unknown():
    families = {"N10000.400": "N4000"}
    values = {"N10000.400": "ROLE_UNKNOWN"}
    out = summarize_role_evidence("ROLE_UNKNOWN", "ROLE_UNKNOWN", values, families)
    assert out["N12000.120"] == "0"
    assert out["N12000.130"] == "1"
    assert out["N12000.180"] == "ROLE_UNKNOWN"
