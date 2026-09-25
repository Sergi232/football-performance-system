from reports.pdf_engine import render_pdf_bytes


def _base(report_type: str) -> dict:
    return {
        "report_type": report_type,
        "engine_version": "expert_test",
        "feature_version": "feature_test",
        "team": {"display_name": "TEAM_001"},
        "guardrails": {
            "recommendation_policy_validated": False,
            "cross_player_ranking_allowed": False,
            "report_may_recalculate_critical_metrics": False,
            "report_may_issue_tactical_recommendation": False,
        },
    }


def test_team_pdf_is_generated():
    payload = _base("team")
    payload.update({"overview": {"matches": 1, "players": 1, "player_minutes": 90, "goals": 1, "assists": 1}, "matches": [], "squad": []})
    pdf = render_pdf_bytes(payload)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_player_pdf_accepts_safe_recommendation_gate():
    payload = _base("player")
    payload.update(
        {
            "summary": {"player": "PLAYER_001", "appearances": 1, "starts": 1, "minutes": 90, "goals": 0, "assists": 0, "observed_roles": "CB"},
            "latest_role_fit_gate": {"observed_role": "CB", "same_role_history": "1", "evaluable_signals": "0", "evidence_coverage": "0", "final_status": "RECOMMENDATION_NOT_ISSUED_NO_EVIDENCE"},
            "feature_history": {},
            "match_history": [],
        }
    )
    pdf = render_pdf_bytes(payload)
    assert pdf.startswith(b"%PDF-")


def test_match_pdf_is_generated():
    payload = _base("match")
    payload.update({"match": {"match_date": "2026-01-01", "venue": "H", "opponent": "OPP_001", "score_for": 1, "score_against": 0, "starting_formation": None}, "lineup": []})
    pdf = render_pdf_bytes(payload)
    assert pdf.startswith(b"%PDF-")
