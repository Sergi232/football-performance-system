"""DSAI-10: leakage-safe pre-match source-position classification baseline.

This experiment tests whether a player's strict-past statistical history contains
signal about the source-observed position they will start in next. Unlike DSAI-09,
no current-match feature is allowed.

Allowed FEATURE-02 operators:
- history_n
- prev
- prior_mean
- prior_std
- prior_slope

Explicitly forbidden:
- delta_prev and delta_prior_mean, because they use the current-match value;
- FEATURE-03 role-conditioned features;
- player identity and the target role itself;
- N12000/N13000 outputs.

Evaluation remains strict:
- train rows must be from dates strictly earlier than the test row;
- the evaluated player is fully excluded from that row's train set;
- the true source_position must already have been observed in another player;
- the test row must contain at least one real strict-past prior_mean value;
- preprocessing is fitted inside each training fold only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

try:
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
except ModuleNotFoundError as exc:  # pragma: no cover
    if exc.name and exc.name.startswith("sklearn"):
        raise SystemExit(
            'scikit-learn is required. Install once with: '
            'python -m pip install "scikit-learn>=1.6"'
        ) from exc
    raise

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
BASE_CATALOG = ROOT / "features" / "catalog.json"
TEMPORAL_CATALOG = ROOT / "features" / "temporal_catalog.json"
OUTPUT_DIR = Path(__file__).with_name("output")
VERSION = "dsai_source_position_prematch_0.1.0"
SAFE_OPERATORS = ["history_n", "prev", "prior_mean", "prior_std", "prior_slope"]
HISTORY_SIGNAL_OPERATOR = "prior_mean"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run leakage-safe pre-match source-position baseline"
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def clean(value):
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def feature_spec() -> tuple[str, list[str], list[str]]:
    base = load_json(BASE_CATALOG)
    temporal = load_json(TEMPORAL_CATALOG)
    base_names = [
        item["name"]
        for item in base.get("ratio_features", []) + base.get("per90_features", [])
    ]
    available_ops = {item["name"] for item in temporal.get("operators", [])}
    missing = [op for op in SAFE_OPERATORS if op not in available_ops]
    if missing:
        raise RuntimeError(f"Missing required FEATURE-02 operators: {missing}")
    names = [f"{base_name}__{op}" for base_name in base_names for op in SAFE_OPERATORS]
    history_signal = [
        f"{base_name}__{HISTORY_SIGNAL_OPERATOR}" for base_name in base_names
    ]
    return str(temporal["feature_version"]), names, history_signal


def load_target(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    frame = con.execute(
        """
        SELECT
            pm.match_id,
            pm.player_id,
            m.match_date,
            TRIM(pm.primary_role) AS detailed_role
        FROM player_match pm
        JOIN matches m ON m.match_id = pm.match_id
        WHERE pm.started IS TRUE
          AND pm.primary_role IS NOT NULL
          AND TRIM(pm.primary_role) <> ''
          AND LOWER(TRIM(pm.primary_role)) <> 'substitute'
        ORDER BY m.match_date, pm.match_id, pm.player_id
        """
    ).fetchdf()
    if frame.empty:
        frame["source_position"] = pd.Series(dtype="object")
        return frame
    frame["source_position"] = (
        frame["detailed_role"]
        .astype(str)
        .str.split(" | ", n=1, regex=False)
        .str[0]
        .str.strip()
    )
    return frame


def load_temporal_matrix(
    con: duckdb.DuckDBPyConnection,
    feature_version: str,
    feature_names: list[str],
) -> pd.DataFrame:
    long = con.execute(
        """
        SELECT match_id, player_id, feature_name, feature_value
        FROM player_match_features
        WHERE feature_version = ?
          AND feature_name IN (SELECT * FROM UNNEST(?))
        """,
        [feature_version, feature_names],
    ).fetchdf()
    if long.empty:
        return pd.DataFrame(columns=["match_id", "player_id", *feature_names])

    wide = long.pivot_table(
        index=["match_id", "player_id"],
        columns="feature_name",
        values="feature_value",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    for feature in feature_names:
        if feature not in wide.columns:
            wide[feature] = pd.NA
    return wide[["match_id", "player_id", *feature_names]]


def build_model() -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=3000, solver="lbfgs")),
        ]
    )


def has_real_history(row: pd.Series, history_signal_features: list[str]) -> bool:
    return bool(row[history_signal_features].notna().any())


def run_walk_forward(
    frame: pd.DataFrame,
    feature_names: list[str],
    history_signal_features: list[str],
) -> tuple[pd.DataFrame, dict]:
    frame = frame.sort_values(["match_date", "match_id", "player_id"]).reset_index(drop=True)
    predictions: list[dict] = []
    diagnostics = {
        "candidate_rows": int(len(frame)),
        "skipped_no_prematch_history": 0,
        "skipped_position_not_in_other_player_strict_past": 0,
        "skipped_less_than_two_training_classes": 0,
        "skipped_no_usable_training_features": 0,
        "skipped_model_error": 0,
    }

    for idx, row in frame.iterrows():
        if not has_real_history(row, history_signal_features):
            diagnostics["skipped_no_prematch_history"] += 1
            continue

        train = frame[
            (frame["match_date"] < row["match_date"])
            & (frame["player_id"] != row["player_id"])
        ].copy()

        if train.empty or row["source_position"] not in set(train["source_position"].astype(str)):
            diagnostics["skipped_position_not_in_other_player_strict_past"] += 1
            continue

        if train["source_position"].nunique() < 2:
            diagnostics["skipped_less_than_two_training_classes"] += 1
            continue

        usable = [feature for feature in feature_names if train[feature].notna().any()]
        if not usable:
            diagnostics["skipped_no_usable_training_features"] += 1
            continue

        x_train = train[usable]
        y_train = train["source_position"].astype(str)
        x_test = pd.DataFrame([{feature: row[feature] for feature in usable}])
        majority_label = str(y_train.value_counts().idxmax())

        model = build_model()
        try:
            model.fit(x_train, y_train)
            model_pred = str(model.predict(x_test)[0])
        except Exception:
            diagnostics["skipped_model_error"] += 1
            continue

        predictions.append(
            {
                "match_id": row["match_id"],
                "player_id": row["player_id"],
                "match_date": clean(row["match_date"]),
                "true_position": str(row["source_position"]),
                "model_prediction": model_pred,
                "majority_prediction": majority_label,
                "train_rows": int(len(train)),
                "train_players": int(train["player_id"].nunique()),
                "train_positions": int(train["source_position"].nunique()),
                "usable_features": int(len(usable)),
                "test_non_null_safe_features": int(row[usable].notna().sum()),
                "test_prior_mean_features": int(row[history_signal_features].notna().sum()),
            }
        )

    pred = pd.DataFrame(predictions)
    diagnostics["evaluated_rows"] = int(len(pred))
    return pred, diagnostics


def metric_block(y_true: pd.Series, y_pred: pd.Series) -> dict:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }


def rules() -> list[str]:
    return [
        "Only FEATURE-02 strict-past history_n, prev, prior_mean, prior_std and prior_slope are allowed.",
        "delta_prev and delta_prior_mean are forbidden because they use current-match values.",
        "FEATURE-03 is forbidden because it is role-conditioned.",
        "Training data are strictly earlier than each evaluated row.",
        "The evaluated player is completely excluded from that row's training set.",
        "A row is evaluated only when its true source_position exists previously in another player.",
        "A row must have at least one non-null strict-past prior_mean value.",
        "Imputation and scaling are fitted inside each training fold only.",
        "No deployment threshold, player fit, ranking or recommendation is created.",
    ]


def summarize(
    pred: pd.DataFrame,
    diagnostics: dict,
    feature_version: str,
    feature_names: list[str],
) -> dict:
    if pred.empty:
        return {
            "version": VERSION,
            "status": "PREMATCH_BASELINE_EXPERIMENT",
            "summary": {
                **diagnostics,
                "feature_version": feature_version,
                "safe_feature_names": len(feature_names),
                "conclusion": "NO_EVALUABLE_ROWS",
            },
            "model_metrics": None,
            "majority_baseline_metrics": None,
            "per_position": [],
            "rules": rules(),
        }

    y_true = pred["true_position"].astype(str)
    y_model = pred["model_prediction"].astype(str)
    y_majority = pred["majority_prediction"].astype(str)
    model_metrics = metric_block(y_true, y_model)
    majority_metrics = metric_block(y_true, y_majority)

    per_position = []
    for position, group in pred.groupby("true_position", sort=True):
        per_position.append(
            {
                "source_position": str(position),
                "support": int(len(group)),
                "model_recall": float((group["model_prediction"] == position).mean()),
                "majority_recall": float((group["majority_prediction"] == position).mean()),
            }
        )

    summary = {
        **diagnostics,
        "feature_version": feature_version,
        "safe_feature_names": len(feature_names),
        "evaluated_positions": int(pred["true_position"].nunique()),
        "evaluated_players": int(pred["player_id"].nunique()),
        "first_evaluation_date": clean(pd.to_datetime(pred["match_date"]).min()),
        "last_evaluation_date": clean(pd.to_datetime(pred["match_date"]).max()),
        "conclusion": "PREMATCH_SOURCE_POSITION_BASELINE_COMPLETE_NO_DEPLOYMENT_DECISION",
    }

    return {
        "version": VERSION,
        "status": "PREMATCH_BASELINE_EXPERIMENT",
        "summary": summary,
        "model": {
            "type": "multinomial_logistic_regression",
            "preprocessing": "train-only median imputation + missing indicators + standard scaling",
            "input_timing": "strict-past only; available before current match",
        },
        "model_metrics": model_metrics,
        "majority_baseline_metrics": majority_metrics,
        "metric_delta_model_minus_majority": {
            key: float(model_metrics[key] - majority_metrics[key]) for key in model_metrics
        },
        "per_position": per_position,
        "rules": rules(),
    }


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# DSAI-10 — Pre-match source-position baseline",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
    ]
    for key, value in s.items():
        lines.append(f"- {key}: {value}")

    if result.get("model_metrics"):
        lines.extend([
            "",
            "## Metrics",
            "",
            "| Metric | Logistic regression | Majority baseline | Delta |",
            "|---|---:|---:|---:|",
        ])
        for metric in ["accuracy", "balanced_accuracy", "macro_f1"]:
            lines.append(
                f"| {metric} | {result['model_metrics'][metric]:.4f} | "
                f"{result['majority_baseline_metrics'][metric]:.4f} | "
                f"{result['metric_delta_model_minus_majority'][metric]:+.4f} |"
            )

        lines.extend([
            "",
            "## Per-position error analysis",
            "",
            "| Position | Support | Model recall | Majority recall |",
            "|---|---:|---:|---:|",
        ])
        for row in result["per_position"]:
            lines.append(
                f"| {row['source_position']} | {row['support']} | "
                f"{row['model_recall']:.4f} | {row['majority_recall']:.4f} |"
            )

    lines.extend(["", "## Rules"])
    for rule in result["rules"]:
        lines.append(f"- {rule}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    feature_version, feature_names, history_signal_features = feature_spec()
    with duckdb.connect(str(db_path), read_only=True) as con:
        target = load_target(con)
        temporal = load_temporal_matrix(con, feature_version, feature_names)

    frame = target.merge(temporal, on=["match_id", "player_id"], how="left")
    pred, diagnostics = run_walk_forward(frame, feature_names, history_signal_features)
    result = summarize(pred, diagnostics, feature_version, feature_names)
    s = result["summary"]

    print("DSAI-10 PREMATCH SOURCE POSITION BASELINE: COMPLETE")
    print(f"db: {db_path}")
    print(
        f"candidate_rows={s['candidate_rows']} evaluated_rows={s['evaluated_rows']} "
        f"evaluated_positions={s.get('evaluated_positions', 0)} safe_features={s['safe_feature_names']}"
    )
    print(
        "skipped: "
        f"no_prematch_history={s['skipped_no_prematch_history']} "
        f"no_other_player_prior_position={s['skipped_position_not_in_other_player_strict_past']} "
        f"lt2_train_classes={s['skipped_less_than_two_training_classes']} "
        f"no_features={s['skipped_no_usable_training_features']} "
        f"model_error={s['skipped_model_error']}"
    )
    if result.get("model_metrics"):
        mm = result["model_metrics"]
        bm = result["majority_baseline_metrics"]
        print(
            f"logreg accuracy={mm['accuracy']:.4f} balanced_accuracy={mm['balanced_accuracy']:.4f} "
            f"macro_f1={mm['macro_f1']:.4f}"
        )
        print(
            f"majority accuracy={bm['accuracy']:.4f} balanced_accuracy={bm['balanced_accuracy']:.4f} "
            f"macro_f1={bm['macro_f1']:.4f}"
        )
    print(f"conclusion={s['conclusion']}")
    print("Only strict-past features were used; no player fit, ranking or recommendation was created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "source_position_prematch_baseline.json"
        md_path = OUTPUT_DIR / "source_position_prematch_baseline.md"
        csv_path = OUTPUT_DIR / "source_position_prematch_baseline_predictions.csv"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        pred.to_csv(csv_path, index=False)
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")
        print(f"predictions: {csv_path}")


if __name__ == "__main__":
    main()
