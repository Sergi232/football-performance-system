import pandas as pd

from features.build_temporal_features import compute_temporal_frame


def test_same_date_rows_do_not_inform_each_other():
    base = pd.DataFrame(
        [
            {"match_id":"m1","player_id":"p1","feature_name":"x","feature_value":1.0,"match_date":pd.Timestamp("2026-01-01")},
            {"match_id":"m2","player_id":"p1","feature_name":"x","feature_value":2.0,"match_date":pd.Timestamp("2026-01-08")},
            {"match_id":"m3","player_id":"p1","feature_name":"x","feature_value":100.0,"match_date":pd.Timestamp("2026-01-08")},
            {"match_id":"m4","player_id":"p1","feature_name":"x","feature_value":4.0,"match_date":pd.Timestamp("2026-01-15")},
        ]
    )
    out = compute_temporal_frame(base, ["x"])

    def value(match_id, suffix):
        row = out[(out.match_id == match_id) & (out.feature_name == f"x__{suffix}")]
        assert len(row) == 1
        return row.iloc[0].feature_value

    assert value("m1", "history_n") == 0
    assert pd.isna(value("m1", "prev"))

    # Both matches on 2026-01-08 see only m1, never one another.
    assert value("m2", "history_n") == 1
    assert value("m3", "history_n") == 1
    assert value("m2", "prev") == 1.0
    assert value("m3", "prev") == 1.0
    assert value("m2", "prior_mean") == 1.0
    assert value("m3", "prior_mean") == 1.0

    # The later match can use all strictly earlier observations.
    assert value("m4", "history_n") == 3
    assert abs(value("m4", "prior_mean") - (103.0 / 3.0)) < 1e-12


def test_null_current_value_does_not_enter_history():
    base = pd.DataFrame(
        [
            {"match_id":"m1","player_id":"p1","feature_name":"x","feature_value":1.0,"match_date":pd.Timestamp("2026-01-01")},
            {"match_id":"m2","player_id":"p1","feature_name":"x","feature_value":None,"match_date":pd.Timestamp("2026-01-08")},
            {"match_id":"m3","player_id":"p1","feature_name":"x","feature_value":3.0,"match_date":pd.Timestamp("2026-01-15")},
        ]
    )
    out = compute_temporal_frame(base, ["x"])
    hist = out[(out.match_id == "m3") & (out.feature_name == "x__history_n")].iloc[0].feature_value
    prev = out[(out.match_id == "m3") & (out.feature_name == "x__prev")].iloc[0].feature_value
    assert hist == 1
    assert prev == 1.0
