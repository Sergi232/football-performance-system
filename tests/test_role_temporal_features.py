import pandas as pd

from features.build_role_temporal_features import (
    compute_role_match_history,
    compute_role_metric_frame,
)


def test_role_metric_history_is_strict_past_and_same_role_only():
    base = pd.DataFrame(
        [
            {"match_id":"m1","player_id":"p1","feature_name":"shots_total_per90","feature_value":1.0,"match_date":pd.Timestamp("2026-01-01"),"primary_role":"CF"},
            {"match_id":"m2","player_id":"p1","feature_name":"shots_total_per90","feature_value":3.0,"match_date":pd.Timestamp("2026-01-02"),"primary_role":"CF"},
            {"match_id":"m3","player_id":"p1","feature_name":"shots_total_per90","feature_value":9.0,"match_date":pd.Timestamp("2026-01-03"),"primary_role":"LW"},
            {"match_id":"m4","player_id":"p1","feature_name":"shots_total_per90","feature_value":5.0,"match_date":pd.Timestamp("2026-01-04"),"primary_role":"CF"},
        ]
    )
    out = compute_role_metric_frame(base, ["shots_total_per90"])
    hist = out[out.feature_name == "shots_total_per90__role_history_n"].set_index("match_id")
    mean = out[out.feature_name == "shots_total_per90__role_prior_mean"].set_index("match_id")
    assert hist.loc["m1", "feature_value"] == 0
    assert hist.loc["m2", "feature_value"] == 1
    assert hist.loc["m3", "feature_value"] == 0
    assert hist.loc["m4", "feature_value"] == 2
    assert mean.loc["m4", "feature_value"] == 2.0


def test_same_date_rows_do_not_inform_each_other():
    base = pd.DataFrame(
        [
            {"match_id":"m1","player_id":"p1","feature_name":"x","feature_value":1.0,"match_date":pd.Timestamp("2026-01-01"),"primary_role":"CM"},
            {"match_id":"m2","player_id":"p1","feature_name":"x","feature_value":3.0,"match_date":pd.Timestamp("2026-01-01"),"primary_role":"CM"},
            {"match_id":"m3","player_id":"p1","feature_name":"x","feature_value":5.0,"match_date":pd.Timestamp("2026-01-02"),"primary_role":"CM"},
        ]
    )
    out = compute_role_metric_frame(base, ["x"])
    hist = out[out.feature_name == "x__role_history_n"].set_index("match_id")
    mean = out[out.feature_name == "x__role_prior_mean"].set_index("match_id")
    assert hist.loc["m1", "feature_value"] == 0
    assert hist.loc["m2", "feature_value"] == 0
    assert hist.loc["m3", "feature_value"] == 2
    assert mean.loc["m3", "feature_value"] == 2.0


def test_missing_role_remains_missing():
    base = pd.DataFrame(
        [
            {"match_id":"m1","player_id":"p1","feature_name":"x","feature_value":2.0,"match_date":pd.Timestamp("2026-01-01"),"primary_role":None},
        ]
    )
    out = compute_role_metric_frame(base, ["x"])
    assert len(out) == 5
    assert out.feature_value.isna().all()
    assert out.feature_text.isna().all()


def test_role_match_history_counts_prior_played_matches_only():
    pm = pd.DataFrame(
        [
            {"match_id":"m1","player_id":"p1","match_date":pd.Timestamp("2026-01-01"),"primary_role":"CM","minutes_played":90},
            {"match_id":"m2","player_id":"p1","match_date":pd.Timestamp("2026-01-02"),"primary_role":"CM","minutes_played":0},
            {"match_id":"m3","player_id":"p1","match_date":pd.Timestamp("2026-01-03"),"primary_role":"CM","minutes_played":45},
        ]
    )
    out = compute_role_match_history(pm).set_index("match_id")
    assert out.loc["m1", "feature_value"] == 0
    assert out.loc["m2", "feature_value"] == 1
    assert out.loc["m3", "feature_value"] == 1
