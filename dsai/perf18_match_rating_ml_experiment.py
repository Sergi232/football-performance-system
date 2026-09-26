"""PERF-18 — position-aware multidimensional Match Rating ML experiment.

Purpose
-------
Learn whether collector-compatible match statistics can approximate an external
professional player-match rating while preserving the product constraints:
- only variables collectable by the amateur workflow are model inputs;
- chronological split only (no future leakage);
- position context is explicit;
- goalkeeper rows are modelled separately;
- external provider rating, when available, is a benchmark/target only;
- this script NEVER promotes a model to the product rating layer.

If no usable external rating target exists in the source, the script still writes
an auditable ML matrix summary and exits without inventing a target.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18"

# Exact provider columns already verified by DATA-04 v2.
SOURCE_FEATURES: dict[str, str] = {
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
    "saves": "saves",
    "goals_conceded": "goalsConceded",
}

# We deliberately exclude provider-only advanced variables (xG/xA, possession value,
# pressure, tracking, etc.) so the model can later run from our own collector/GPS stack.
NUMERIC_FEATURES = ["minutes_played", *SOURCE_FEATURES.keys()]
CATEGORICAL_FEATURES = ["position_group"]

PREFERRED_TARGET_NAMES = [
    "rating", "playerRating", "player_rating", "optaRating", "opta_rating",
    "performanceRating", "performance_rating", "matchRating", "match_rating",
]
TARGET_NAME_PATTERN = re.compile(r"(^|_)(rating|player.?rating|performance.?rating|match.?rating)($|_)", re.I)


@dataclass
class Metrics:
    model: str
    scope: str
    train_rows: int
    valid_rows: int
    test_rows: int
    mae_valid: float | None
    rmse_valid: float | None
    corr_valid: float | None
    mae_test: float | None
    rmse_test: float | None
    corr_test: float | None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-18 position-aware Match Rating ML")
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--target", default=None, help="Optional explicit target column in opta_player_stats")
    p.add_argument("--min-minutes", type=float, default=10.0)
    return p.parse_args()


def discover_input_dir(explicit: Path | None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    env = os.environ.get("FPS_INPUT_DIR")
    if env:
        candidates.append(Path(env))
    candidates.extend([
        Path(r"D:\Data\Sergi\Desktop\analisi_futbol\input\pannadata"),
        Path(r"C:\Users\sergi\Desktop\analisi_futbol\input\pannadata"),
        Path(r"D:\Data\Sergi\Desktop\analisi_futbol\pannadata"),
        Path(r"C:\Users\sergi\Desktop\analisi_futbol\pannadata"),
    ])
    required = {"opta_player_stats.parquet", "opta_lineups.parquet", "opta_fixtures.parquet"}
    for candidate in candidates:
        path = candidate.expanduser().resolve()
        if path.exists() and all((path / name).exists() for name in required):
            return path
    raise FileNotFoundError("Could not find PannaData player_stats + lineups + fixtures input directory")


def sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def norm_position(value: Any) -> str:
    if value is None or pd.isna(value):
        return "OTHER_OUTFIELD"
    text = str(value).strip().lower()
    if not text or text == "substitute":
        return "OTHER_OUTFIELD"
    if "goalkeeper" in text or text in {"gk", "keeper"}:
        return "GK"
    if any(k in text for k in ["centre back", "center back", "central defender", "defender central"]):
        return "CB"
    if any(k in text for k in ["full back", "wing back", "left back", "right back", "lateral"]):
        return "FB_WB"
    if any(k in text for k in ["defensive midfielder", "central midfielder", "centre midfielder", "midfielder"]):
        return "DM_CM"
    if any(k in text for k in ["attacking midfielder", "winger", "wide midfielder", "left wing", "right wing"]):
        return "AM_W"
    if any(k in text for k in ["striker", "forward", "centre forward", "center forward"]):
        return "ST"
    return "OTHER_OUTFIELD"


def numeric_target_summary(con: duckdb.DuckDBPyConnection, source: Path, col: str) -> dict[str, Any] | None:
    escaped = col.replace('"', '""')
    try:
        row = con.execute(
            f'''SELECT
                    COUNT(*) AS rows,
                    COUNT(TRY_CAST("{escaped}" AS DOUBLE)) AS non_null,
                    MIN(TRY_CAST("{escaped}" AS DOUBLE)) AS min_v,
                    MAX(TRY_CAST("{escaped}" AS DOUBLE)) AS max_v,
                    AVG(TRY_CAST("{escaped}" AS DOUBLE)) AS mean_v,
                    STDDEV_SAMP(TRY_CAST("{escaped}" AS DOUBLE)) AS sd_v
                FROM read_parquet('{sql_path(source)}')'''
        ).fetchone()
    except Exception:
        return None
    if row is None or int(row[1] or 0) < 100:
        return None
    return {
        "column": col,
        "rows": int(row[0] or 0),
        "non_null": int(row[1] or 0),
        "min": None if row[2] is None else float(row[2]),
        "max": None if row[3] is None else float(row[3]),
        "mean": None if row[4] is None else float(row[4]),
        "sd": None if row[5] is None else float(row[5]),
    }


def detect_target(con: duckdb.DuckDBPyConnection, source: Path, explicit: str | None) -> tuple[str | None, list[dict[str, Any]]]:
    schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{sql_path(source)}')").df()
    cols = schema["column_name"].astype(str).tolist()
    if explicit:
        if explicit not in cols:
            raise RuntimeError(f"Explicit target not present in source: {explicit}")
        summary = numeric_target_summary(con, source, explicit)
        if summary is None:
            raise RuntimeError(f"Explicit target is not sufficiently numeric/populated: {explicit}")
        return explicit, [summary]

    ordered: list[str] = []
    for name in PREFERRED_TARGET_NAMES:
        if name in cols and name not in ordered:
            ordered.append(name)
    for col in cols:
        if TARGET_NAME_PATTERN.search(col) and col not in ordered:
            ordered.append(col)

    candidates: list[dict[str, Any]] = []
    for col in ordered:
        summary = numeric_target_summary(con, source, col)
        if summary is None:
            continue
        # Professional player ratings are normally compact continuous scales.
        # These guards prevent accidentally selecting goals/team scores/index IDs.
        mn, mx, sd = summary["min"], summary["max"], summary["sd"]
        if mn is None or mx is None or sd is None:
            continue
        if -1 <= mn <= 10 and 1 <= mx <= 100 and sd > 0.05:
            candidates.append(summary)

    if not candidates:
        return None, []
    # Prefer compact 0-10-ish scales, then coverage.
    candidates.sort(key=lambda d: (0 if d["max"] <= 10.5 else 1, -d["non_null"]))
    return str(candidates[0]["column"]), candidates


def build_matrix(con: duckdb.DuckDBPyConnection, input_dir: Path, target: str | None, min_minutes: float) -> pd.DataFrame:
    stats = input_dir / "opta_player_stats.parquet"
    lineups = input_dir / "opta_lineups.parquet"
    fixtures = input_dir / "opta_fixtures.parquet"

    stats_cols = ["match_id", "team_id", "player_id", "minsPlayed", *SOURCE_FEATURES.values()]
    if target and target not in stats_cols:
        stats_cols.append(target)
    stats_select = ", ".join(f's."{c}"' for c in stats_cols)

    # Fixture schemas vary slightly across provider exports. Use whichever date-like
    # column is present, otherwise fall back to match_id order and refuse ML training.
    fixture_schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{sql_path(fixtures)}')").df()
    fixture_cols = set(fixture_schema["column_name"].astype(str))
    date_col = next((c for c in ["match_date", "matchDate", "date", "start_date", "startDate", "kickoff", "kick_off"] if c in fixture_cols), None)
    if date_col is None:
        date_expr = "NULL::TIMESTAMP AS match_date"
    else:
        date_expr = f'TRY_CAST(f."{date_col}" AS TIMESTAMP) AS match_date'

    query = f'''
        SELECT
            {stats_select},
            l.position,
            l.position_side,
            l.is_starter,
            {date_expr}
        FROM read_parquet('{sql_path(stats)}') s
        LEFT JOIN read_parquet('{sql_path(lineups)}') l
          ON CAST(l.match_id AS VARCHAR)=CAST(s.match_id AS VARCHAR)
         AND CAST(l.team_id AS VARCHAR)=CAST(s.team_id AS VARCHAR)
         AND CAST(l.player_id AS VARCHAR)=CAST(s.player_id AS VARCHAR)
        LEFT JOIN read_parquet('{sql_path(fixtures)}') f
          ON CAST(f.match_id AS VARCHAR)=CAST(s.match_id AS VARCHAR)
    '''
    frame = con.execute(query).df()
    frame = frame.drop_duplicates(["match_id", "team_id", "player_id"], keep="first")
    frame["minutes_played"] = pd.to_numeric(frame["minsPlayed"], errors="coerce")
    frame = frame.loc[frame["minutes_played"].fillna(0) >= float(min_minutes)].copy()
    frame["position_group"] = frame["position"].map(norm_position)
    frame["match_date"] = pd.to_datetime(frame["match_date"], errors="coerce")
    for logical, source_name in SOURCE_FEATURES.items():
        frame[logical] = pd.to_numeric(frame[source_name], errors="coerce")
    if target:
        frame["target_rating"] = pd.to_numeric(frame[target], errors="coerce")
        frame = frame.loc[frame["target_rating"].notna()].copy()
    return frame


def chronological_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if frame["match_date"].notna().sum() < max(100, int(len(frame) * 0.8)):
        raise RuntimeError("Cannot create leakage-safe temporal split: match_date coverage is insufficient")
    work = frame.loc[frame["match_date"].notna()].sort_values(["match_date", "match_id", "player_id"]).copy()
    dates = np.array(sorted(work["match_date"].dt.normalize().unique()))
    if len(dates) < 10:
        raise RuntimeError(f"Too few distinct match dates for temporal validation: {len(dates)}")
    train_end = dates[max(1, int(len(dates) * 0.70)) - 1]
    valid_end = dates[max(2, int(len(dates) * 0.85)) - 1]
    train = work.loc[work["match_date"].dt.normalize() <= train_end].copy()
    valid = work.loc[(work["match_date"].dt.normalize() > train_end) & (work["match_date"].dt.normalize() <= valid_end)].copy()
    test = work.loc[work["match_date"].dt.normalize() > valid_end].copy()
    if min(len(train), len(valid), len(test)) == 0:
        raise RuntimeError("Temporal split produced an empty partition")
    return train, valid, test


def corr(y_true: pd.Series | np.ndarray, y_pred: np.ndarray) -> float | None:
    a = np.asarray(y_true, dtype=float)
    b = np.asarray(y_pred, dtype=float)
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def evaluate(model: Pipeline, train: pd.DataFrame, valid: pd.DataFrame, test: pd.DataFrame, name: str, scope: str) -> Metrics:
    X_train = train[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_train = train["target_rating"]
    X_valid = valid[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_valid = valid["target_rating"]
    X_test = test[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_test = test["target_rating"]
    model.fit(X_train, y_train)
    pv = model.predict(X_valid)
    pt = model.predict(X_test)
    return Metrics(
        model=name,
        scope=scope,
        train_rows=len(train), valid_rows=len(valid), test_rows=len(test),
        mae_valid=float(mean_absolute_error(y_valid, pv)),
        rmse_valid=float(mean_squared_error(y_valid, pv) ** 0.5),
        corr_valid=corr(y_valid, pv),
        mae_test=float(mean_absolute_error(y_test, pt)),
        rmse_test=float(mean_squared_error(y_test, pt) ** 0.5),
        corr_test=corr(y_test, pt),
    )


def ridge_pipeline() -> Pipeline:
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    pre = ColumnTransformer([
        ("num", numeric, NUMERIC_FEATURES),
        ("cat", categorical, CATEGORICAL_FEATURES),
    ])
    return Pipeline([("pre", pre), ("model", Ridge(alpha=10.0))])


def hgb_pipeline() -> Pipeline:
    # One-hot gives position context to the global model while the role-specific
    # experiments below remove that categorical column and fit within-role models.
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    pre = ColumnTransformer([
        ("num", numeric, NUMERIC_FEATURES),
        ("cat", categorical, CATEGORICAL_FEATURES),
    ], sparse_threshold=0.0)
    return Pipeline([
        ("pre", pre),
        ("model", HistGradientBoostingRegressor(
            learning_rate=0.05,
            max_iter=250,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            random_state=42,
        )),
    ])


def permutation_table(model: Pipeline, test: pd.DataFrame) -> pd.DataFrame:
    X = test[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    y = test["target_rating"].copy()
    result = permutation_importance(
        model, X, y, scoring="neg_mean_absolute_error", n_repeats=8, random_state=42
    )
    return pd.DataFrame({
        "feature": X.columns,
        "importance_mean": result.importances_mean,
        "importance_std": result.importances_std,
    }).sort_values("importance_mean", ascending=False)


def main() -> None:
    args = parse_args()
    input_dir = discover_input_dir(args.input_dir)
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stats = input_dir / "opta_player_stats.parquet"

    with duckdb.connect() as con:
        target, candidates = detect_target(con, stats, args.target)
        audit = {
            "input_dir": str(input_dir),
            "target_selected": target,
            "target_candidates": candidates,
            "collector_compatible_numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "min_minutes": args.min_minutes,
        }
        frame = build_matrix(con, input_dir, target, args.min_minutes)

    matrix_summary = {
        **audit,
        "rows": int(len(frame)),
        "matches": int(frame["match_id"].nunique()) if not frame.empty else 0,
        "players": int(frame["player_id"].nunique()) if not frame.empty else 0,
        "teams": int(frame["team_id"].nunique()) if not frame.empty else 0,
        "position_counts": {str(k): int(v) for k, v in frame["position_group"].value_counts(dropna=False).to_dict().items()},
        "date_non_null": int(frame["match_date"].notna().sum()) if not frame.empty else 0,
    }
    (output_dir / "matrix_summary.json").write_text(json.dumps(matrix_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("PERF-18 ML MATRIX: READY")
    print(f"input_dir={input_dir}")
    print(f"rows={matrix_summary['rows']} matches={matrix_summary['matches']} players={matrix_summary['players']} teams={matrix_summary['teams']}")
    print(f"position_counts={matrix_summary['position_counts']}")
    print(f"target_selected={target}")

    if target is None:
        print("PERF-18 SUPERVISED TRAINING: NOT RUN")
        print("reason=no usable professional player-match rating target found in opta_player_stats")
        print(f"audit={output_dir / 'matrix_summary.json'}")
        print("No pseudo-target was invented.")
        return

    train, valid, test = chronological_split(frame)
    metrics: list[Metrics] = []

    ridge = ridge_pipeline()
    hgb = hgb_pipeline()
    metrics.append(evaluate(ridge, train, valid, test, "Ridge", "GLOBAL"))
    metrics.append(evaluate(hgb, train, valid, test, "HistGradientBoosting", "GLOBAL"))

    # Position-specific experiments. A role is evaluated only when every temporal
    # partition has enough observations to make the comparison interpretable.
    for role in ["GK", "CB", "FB_WB", "DM_CM", "AM_W", "ST", "OTHER_OUTFIELD"]:
        tr = train.loc[train["position_group"] == role]
        va = valid.loc[valid["position_group"] == role]
        te = test.loc[test["position_group"] == role]
        if len(tr) < 150 or len(va) < 30 or len(te) < 30:
            continue
        model = hgb_pipeline()
        metrics.append(evaluate(model, tr, va, te, "HistGradientBoosting", f"ROLE:{role}"))

    result_frame = pd.DataFrame([asdict(m) for m in metrics])
    result_frame.to_csv(output_dir / "model_metrics.csv", index=False)

    # Refit the best global candidate by validation MAE and explain on untouched test.
    global_rows = result_frame[result_frame["scope"] == "GLOBAL"].sort_values("mae_valid")
    best_name = str(global_rows.iloc[0]["model"])
    best_model = ridge_pipeline() if best_name == "Ridge" else hgb_pipeline()
    best_model.fit(train[NUMERIC_FEATURES + CATEGORICAL_FEATURES], train["target_rating"])
    importance = permutation_table(best_model, test)
    importance.to_csv(output_dir / "permutation_importance.csv", index=False)

    target_meta = next((c for c in candidates if c["column"] == target), None)
    run_summary = {
        **matrix_summary,
        "chronological_split": {
            "train_rows": len(train), "valid_rows": len(valid), "test_rows": len(test),
            "train_max_date": str(train["match_date"].max()),
            "valid_min_date": str(valid["match_date"].min()),
            "valid_max_date": str(valid["match_date"].max()),
            "test_min_date": str(test["match_date"].min()),
        },
        "best_global_model_by_valid_mae": best_name,
        "target_metadata": target_meta,
        "product_promotion": False,
    }
    (output_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("PERF-18 POSITION-AWARE MATCH RATING ML: COMPLETE")
    print(f"target={target}")
    print(f"train={len(train)} valid={len(valid)} test={len(test)}")
    for m in metrics:
        print(
            f"{m.scope} {m.model}: "
            f"valid_MAE={m.mae_valid:.4f} valid_RMSE={m.rmse_valid:.4f} valid_corr={m.corr_valid} "
            f"test_MAE={m.mae_test:.4f} test_RMSE={m.rmse_test:.4f} test_corr={m.corr_test}"
        )
    print(f"best_global_model={best_name}")
    print("future_leakage_guard=PASS (chronological split)")
    print("product_promotion=False")
    print(f"outputs={output_dir}")


if __name__ == "__main__":
    main()
