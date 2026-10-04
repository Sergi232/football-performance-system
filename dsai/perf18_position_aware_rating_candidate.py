"""PERF-18 — position-aware outfield Match Rating candidate.

Purpose
-------
Build an interpretable, position-aware outfield rating using only collector-compatible
variables, while using reconstructed public Opta Points as an external benchmark.

Method
------
1. Keep goalkeepers out: they have a separate model.
2. Map reliable outfield roles from provider lineup labels.
3. Build five signed dimensions from collector-compatible variables.
4. Standardize each dimension inside each role using TRAIN data only.
5. Fit a positive Ridge model per role against reconstructed public Opta Points.
6. Validate strictly out-of-time.

The target is a transparent external benchmark, not the proprietary Opta Player Rating.
No production rating is changed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

from perf18_opta_points_benchmark_audit import (
    ALIASES,
    ROOT,
    WEIGHTS_OUTFIELD,
    choose_aliases,
    discover_input_dir,
    sql_path,
)

DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_position_aware_candidate"

COLLECTOR_SOURCE = {
    "passes_total": "totalPass",
    "passes_completed": "accuratePass",
    "assists": "goalAssist",
    "long_balls_total": "totalLongBalls",
    "long_balls_completed": "accurateLongBalls",
    "crosses_total": "totalCross",
    "crosses_completed": "accurateCross",
    "dribbles_total": "totalContest",
    "dribbles_won": "wonContest",
    "turnovers": "turnover",
    "dispossessed": "dispossessed",
    "shots_total": "totalScoringAtt",
    "shots_on_target": "ontargetScoringAtt",
    "shots_blocked": "blockedScoringAtt",
    "goals": "goals",
    "tackles_total": "totalTackle",
    "tackles_won": "wonTackle",
    "interceptions": "interception",
    "blocked_passes": "blockedPass",
    "clearances": "totalClearance",
    "fouls_committed": "fouls",
    "fouls_received": "wasFouled",
    "yellow_cards": "yellowCard",
    "red_cards": "redCard",
    "penalties_conceded": "penaltyConceded",
    "penalties_won": "penaltyWon",
    "goals_conceded": "goalsConceded",
}

# Signed features. +1 = more is favourable; -1 = more is unfavourable.
# Features are deliberately grouped once to avoid double counting across dimensions.
DIMENSIONS: dict[str, dict[str, float]] = {
    "shooting": {
        "goals": +1.0,
        "shots_on_target": +1.0,
        "shots_total": +1.0,
        "shots_blocked": +1.0,
    },
    "passing_creation": {
        "passes_completed": +1.0,
        "pass_accuracy": +1.0,
        "long_balls_completed": +1.0,
        "crosses_completed": +1.0,
        "assists": +1.0,
    },
    "possession_1v1": {
        "dribbles_won": +1.0,
        "dribble_success": +1.0,
        "turnovers": -1.0,
        "dispossessed": -1.0,
    },
    "defending": {
        "tackles_won": +1.0,
        "tackle_success": +1.0,
        "interceptions": +1.0,
        "blocked_passes": +1.0,
        "clearances": +1.0,
        "penalties_conceded": -1.0,
        "goals_conceded": -1.0,
    },
    "discipline_context": {
        "fouls_received": +1.0,
        "penalties_won": +1.0,
        "fouls_committed": -1.0,
        "yellow_cards": -1.0,
        "red_cards": -1.0,
    },
}

ROLE_ORDER = ["CB", "FB", "DM", "CM", "AM", "W", "ST"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-18 position-aware outfield rating candidate")
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--min-minutes", type=float, default=30.0)
    p.add_argument("--alpha", type=float, default=5.0)
    return p.parse_args()


def safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    n = pd.to_numeric(num, errors="coerce")
    d = pd.to_numeric(den, errors="coerce")
    return (n / d.where(d > 0)).clip(0.0, 1.0)


def fixture_date_expr(con: duckdb.DuckDBPyConnection, fixtures: Path) -> str:
    schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{sql_path(fixtures)}')").df()
    available = set(schema["column_name"].astype(str))
    date_col = next(
        (c for c in ["match_date", "matchDate", "date", "start_date", "startDate", "kickoff", "kick_off"] if c in available),
        None,
    )
    if date_col is None:
        raise RuntimeError("No fixture date column available for leakage-safe temporal split")
    return f'TRY_CAST(f."{date_col}" AS TIMESTAMP)'


def map_roles(frame: pd.DataFrame) -> pd.Series:
    p = frame["position"].fillna("").astype(str).str.strip().str.lower()
    s = frame["position_side"].fillna("").astype(str).str.strip().str.lower()

    defender_count = (
        frame.assign(_is_def=p.eq("defender").astype(int))
        .groupby(["match_id", "team_id"])["_is_def"]
        .transform("sum")
    )

    role = pd.Series("UNKNOWN", index=frame.index, dtype="object")
    role.loc[p.eq("defensive midfielder")] = "DM"
    role.loc[p.eq("striker")] = "ST"
    role.loc[p.eq("wing back")] = "FB"

    am = p.eq("attacking midfielder")
    role.loc[am & s.isin(["left", "right", "wide"])] = "W"
    role.loc[am & ~s.isin(["left", "right", "wide"])] = "AM"

    cm = p.eq("midfielder")
    role.loc[cm & s.isin(["left", "right", "wide"])] = "W"
    role.loc[cm & ~s.isin(["left", "right", "wide"])] = "CM"

    defender = p.eq("defender")
    wide = s.isin(["left", "right", "wide"])
    # In a back three, all generic defenders are treated as centre-backs.
    # In a back four/five, wide generic defenders are treated as full-backs.
    role.loc[defender & ((defender_count <= 3) | ~wide)] = "CB"
    role.loc[defender & (defender_count >= 4) & wide] = "FB"

    return role


def build_frame(input_dir: Path, min_minutes: float) -> pd.DataFrame:
    stats = input_dir / "opta_player_stats.parquet"
    lineups = input_dir / "opta_lineups.parquet"
    fixtures = input_dir / "opta_fixtures.parquet"

    with duckdb.connect() as con:
        schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{sql_path(stats)}')").df()
        available = schema["column_name"].astype(str).tolist()
        opta_map, missing = choose_aliases(available)
        if missing:
            raise RuntimeError("Opta Points target reconstruction incomplete: " + str(missing))

        needed_sources = set(COLLECTOR_SOURCE.values()) | set(opta_map.values())
        missing_collector = sorted(c for c in COLLECTOR_SOURCE.values() if c not in set(available))
        if missing_collector:
            raise RuntimeError("Collector-compatible source columns missing: " + str(missing_collector))

        date_expr = fixture_date_expr(con, fixtures)
        source_select = ",\n                ".join(
            f'TRY_CAST(s."{c}" AS DOUBLE) AS "{c}"' for c in sorted(needed_sources)
        )
        q = f'''
            WITH lineup_one AS (
                SELECT
                    CAST(match_id AS VARCHAR) AS match_id,
                    CAST(team_id AS VARCHAR) AS team_id,
                    CAST(player_id AS VARCHAR) AS player_id,
                    position, position_side, formation_place,
                    ROW_NUMBER() OVER (
                        PARTITION BY CAST(match_id AS VARCHAR), CAST(team_id AS VARCHAR), CAST(player_id AS VARCHAR)
                        ORDER BY position, position_side, formation_place
                    ) AS rn
                FROM read_parquet('{sql_path(lineups)}')
            )
            SELECT
                CAST(s.match_id AS VARCHAR) AS match_id,
                CAST(s.team_id AS VARCHAR) AS team_id,
                CAST(s.player_id AS VARCHAR) AS player_id,
                TRY_CAST(s.minsPlayed AS DOUBLE) AS minutes_played,
                l.position,
                l.position_side,
                l.formation_place,
                {date_expr} AS match_date,
                {source_select}
            FROM read_parquet('{sql_path(stats)}') s
            LEFT JOIN lineup_one l
              ON l.match_id=CAST(s.match_id AS VARCHAR)
             AND l.team_id=CAST(s.team_id AS VARCHAR)
             AND l.player_id=CAST(s.player_id AS VARCHAR)
             AND l.rn=1
            LEFT JOIN read_parquet('{sql_path(fixtures)}') f
              ON CAST(f.match_id AS VARCHAR)=CAST(s.match_id AS VARCHAR)
            WHERE TRY_CAST(s.minsPlayed AS DOUBLE) >= {float(min_minutes)}
        '''
        # Preserve the exact query and row order while avoiding a second full-size
        # in-memory conversion peak on constrained machines.  This is an execution
        # detail only: subsequent role mapping, reference fitting and calibration
        # receive the same complete frame.
        reader = con.execute(q).fetch_record_batch(rows_per_batch=50_000)
        batches = []
        while True:
            try:
                batch = reader.read_next_batch()
            except StopIteration:
                break
            batches.append(batch.to_pandas())
        frame = pd.concat(batches, ignore_index=True) if batches else pd.DataFrame()

    frame = frame.drop_duplicates(["match_id", "team_id", "player_id"], keep="first")
    frame["match_date"] = pd.to_datetime(frame["match_date"], errors="coerce")
    frame = frame.loc[frame["match_date"].notna()].copy()
    frame["position_group"] = map_roles(frame)
    frame = frame.loc[frame["position_group"].isin(ROLE_ORDER)].copy()

    for logical, src in COLLECTOR_SOURCE.items():
        frame[logical] = pd.to_numeric(frame[src], errors="coerce")
    frame["pass_accuracy"] = safe_ratio(frame["passes_completed"], frame["passes_total"])
    frame["dribble_success"] = safe_ratio(frame["dribbles_won"], frame["dribbles_total"])
    frame["tackle_success"] = safe_ratio(frame["tackles_won"], frame["tackles_total"])

    target = pd.Series(5.5, index=frame.index, dtype=float)
    for logical, weight in WEIGHTS_OUTFIELD.items():
        src = opta_map[logical]
        target = target + pd.to_numeric(frame[src], errors="coerce").fillna(0.0) * float(weight)
    frame["opta_points_target"] = target.clip(3.0, 10.0)
    return frame


def split_dates(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, str]]:
    dates = np.array(sorted(frame["match_date"].dt.normalize().unique()))
    if len(dates) < 20:
        raise RuntimeError(f"Too few match dates for temporal split: {len(dates)}")
    train_end = dates[max(1, int(len(dates) * 0.70)) - 1]
    valid_end = dates[max(2, int(len(dates) * 0.85)) - 1]
    train = frame.loc[frame["match_date"].dt.normalize() <= train_end].copy()
    valid = frame.loc[(frame["match_date"].dt.normalize() > train_end) & (frame["match_date"].dt.normalize() <= valid_end)].copy()
    test = frame.loc[frame["match_date"].dt.normalize() > valid_end].copy()
    return train, valid, test, {
        "train_end": str(pd.Timestamp(train_end).date()),
        "valid_end": str(pd.Timestamp(valid_end).date()),
    }


def fit_dimension_reference(train: pd.DataFrame, dimension: str) -> dict[str, Any]:
    mapping = DIMENSIONS[dimension]
    ref: dict[str, Any] = {"features": {}}
    for feature, sign in mapping.items():
        s = pd.to_numeric(train[feature], errors="coerce")
        median = float(s.median()) if s.notna().any() else 0.0
        filled = s.fillna(median)
        mean = float(filled.mean())
        sd = float(filled.std(ddof=0))
        if not np.isfinite(sd) or sd < 1e-9:
            sd = 1.0
        ref["features"][feature] = {
            "sign": float(sign),
            "median": median,
            "mean": mean,
            "sd": sd,
        }
    return ref


def apply_dimension(frame: pd.DataFrame, ref: dict[str, Any]) -> pd.Series:
    parts: list[pd.Series] = []
    for feature, meta in ref["features"].items():
        raw = pd.to_numeric(frame[feature], errors="coerce").fillna(float(meta["median"]))
        z = ((raw - float(meta["mean"])) / float(meta["sd"])) * float(meta["sign"])
        parts.append(z.clip(-3.0, 3.0))
    if not parts:
        return pd.Series(0.0, index=frame.index)
    return pd.concat(parts, axis=1).mean(axis=1)


def metric(y: pd.Series, p: np.ndarray) -> dict[str, float | int | None]:
    a = pd.to_numeric(y, errors="coerce")
    b = pd.Series(np.asarray(p, dtype=float), index=a.index)
    valid = a.notna() & b.notna()
    a, b = a[valid], b[valid]
    if a.empty:
        return {"n": 0, "mae": None, "rmse": None, "pearson": None, "spearman": None}
    pearson = float(a.corr(b)) if len(a) >= 3 else None
    spearman = float(a.rank(method="average").corr(b.rank(method="average"))) if len(a) >= 3 else None
    return {
        "n": int(len(a)),
        "mae": float(mean_absolute_error(a, b)),
        "rmse": float(mean_squared_error(a, b) ** 0.5),
        "pearson": pearson,
        "spearman": spearman,
    }


def main() -> None:
    args = parse_args()
    input_dir = discover_input_dir(args.input_dir)
    out = args.output_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    frame = build_frame(input_dir, args.min_minutes)
    train, valid, test, split_info = split_dates(frame)

    print("PERF-18 POSITION-AWARE OUTFIELD CANDIDATE")
    print(f"input_dir={input_dir}")
    print(f"rows={len(frame)} train={len(train)} valid={len(valid)} test={len(test)}")
    print(f"split={split_info}")
    print("position_counts=" + str(frame["position_group"].value_counts().to_dict()))

    result: dict[str, Any] = {
        "method": "role_specific_signed_z_dimensions_plus_positive_ridge",
        "target": "reconstructed_public_opta_points",
        "input_scope": "collector_compatible_outfield_only",
        "min_minutes": float(args.min_minutes),
        "split": split_info,
        "rows": int(len(frame)),
        "roles": {},
        "production_status": "EXPERIMENT_ONLY",
    }

    pooled_true: list[pd.Series] = []
    pooled_pred: list[pd.Series] = []

    for role in ROLE_ORDER:
        tr = train.loc[train["position_group"] == role].copy()
        va = valid.loc[valid["position_group"] == role].copy()
        te = test.loc[test["position_group"] == role].copy()
        if min(len(tr), len(va), len(te)) < 200:
            print(f"{role}: SKIP train={len(tr)} valid={len(va)} test={len(te)}")
            continue

        refs: dict[str, Any] = {}
        for dim in DIMENSIONS:
            refs[dim] = fit_dimension_reference(tr, dim)
            tr[dim] = apply_dimension(tr, refs[dim])
            va[dim] = apply_dimension(va, refs[dim])
            te[dim] = apply_dimension(te, refs[dim])

        dims = list(DIMENSIONS)
        model = Ridge(alpha=float(args.alpha), positive=True)
        model.fit(tr[dims], tr["opta_points_target"])
        pv = np.clip(model.predict(va[dims]), 3.0, 10.0)
        pt = np.clip(model.predict(te[dims]), 3.0, 10.0)

        coef = {d: float(c) for d, c in zip(dims, model.coef_)}
        coef_sum = sum(max(0.0, x) for x in coef.values())
        relative = {
            d: (float(max(0.0, coef[d]) / coef_sum) if coef_sum > 0 else 0.0)
            for d in dims
        }
        valid_metrics = metric(va["opta_points_target"], pv)
        test_metrics = metric(te["opta_points_target"], pt)

        result["roles"][role] = {
            "train_rows": int(len(tr)),
            "valid_rows": int(len(va)),
            "test_rows": int(len(te)),
            "intercept": float(model.intercept_),
            "coefficients": coef,
            "relative_dimension_weights": relative,
            "dimension_reference": refs,
            "valid": valid_metrics,
            "test": test_metrics,
        }
        pooled_true.append(te["opta_points_target"])
        pooled_pred.append(pd.Series(pt, index=te.index))

        print(f"\nPOSITION={role} train={len(tr)} valid={len(va)} test={len(te)}")
        print(" weights=" + str({k: round(v, 4) for k, v in relative.items()}))
        print(" test=" + str(test_metrics))

    if pooled_true:
        y_all = pd.concat(pooled_true).sort_index()
        p_all = pd.concat(pooled_pred).reindex(y_all.index).to_numpy()
        result["overall_test"] = metric(y_all, p_all)
    else:
        result["overall_test"] = None

    artifact = out / "position_aware_outfield_candidate.json"
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nPERF-18 POSITION-AWARE CANDIDATE: COMPLETE")
    print("overall_test=" + str(result["overall_test"]))
    print(f"artifact={artifact}")
    print("Goalkeepers were excluded and remain on their separate modelling path.")
    print("No production rating was changed.")


if __name__ == "__main__":
    main()
