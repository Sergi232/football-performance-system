from decision_tree.build_stage3 import (
    classify_venue,
    classify_result,
    classify_goal_difference,
    classify_formation,
    classify_gps,
)


def test_team_context_classifiers():
    assert classify_venue(True) == "HOME"
    assert classify_venue(False) == "AWAY"
    assert classify_venue(None) == "VENUE_UNKNOWN"
    assert classify_result(2, 1) == "WIN"
    assert classify_result(1, 2) == "LOSS"
    assert classify_result(1, 1) == "DRAW"
    assert classify_result(None, 1) == "RESULT_UNKNOWN"
    assert classify_goal_difference(2, 1) == "POSITIVE"
    assert classify_goal_difference(1, 2) == "NEGATIVE"
    assert classify_goal_difference(1, 1) == "ZERO"
    assert classify_goal_difference(None, 1) == "GOAL_DIFFERENCE_UNKNOWN"
    assert classify_formation(None) == "FORMATION_UNKNOWN"
    assert classify_formation(" ") == "FORMATION_UNKNOWN"
    assert classify_formation("4-3-3") == "4-3-3"


def test_optional_gps_gate():
    assert classify_gps(0) == "GPS_NOT_AVAILABLE"
    assert classify_gps(None) == "GPS_NOT_AVAILABLE"
    assert classify_gps(1) == "GPS_OBSERVED"
    assert classify_gps(100) == "GPS_OBSERVED"
