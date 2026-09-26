"""DSAI-11: robustness checks for the pre-match source-position model.

This stage does not introduce a new product model. It stress-tests DSAI-10 against
strong simple football baselines that are genuinely available before the match:
- the player's last observed starter source_position;
- the player's historical modal starter source_position;
- the train-majority baseline already used in DSAI-10.

It also runs operator ablations of the leakage-safe FEATURE-02 representation and
reports role-stay vs role-switch behaviour. No current-match feature is allowed.
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
VERSION = "dsai_source_position_prematch_robustness_0.1.0"
SAFE_OPERATORS = ["history_n", "prev", "prior_mean", "prior_std", "prior_slope"]
ABLATIONS = {
    "all_safe": SAFE_OPERATORS,
    "prior_mean_only": ["prior_mean"],
    "prev_only": ["prev"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DSAI-11 prematch robustness checks")
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


def feature_spec() -> tuple[str, list[str], dict[str, list[str]], list[str]]:
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

    all_features = [f"{base_name}__{op}" for base_name in base_names for op in SAFE_OPERATORS]
    groups = {
        name: [f"{base_name}__{op}" for base_name in base_names for op in ops]
        for name, ops in ABLATIONS.items()
    }
    history_signal = [f"{base_name}__prior_mean" for base_name in base_names]
    return str(temporal["feature_version"]), all_features, groups, history_signal


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
        frame["detailed_role"].astype(str).str.split(" | ", n=1, regex=False).str[0].str.strip()
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


def prior_player_positions(frame: pd.DataFrame, row: pd.Series) -> pd.DataFrame:
    return frame[
        (frame["player_id"] == row["player_id"])
        & (frame["match_date"] < row["match_date"])
    ].sort_values(["match_date", "match_id"])


def modal_position_with_recent_tiebreak(prior: pd.DataFrame) -> str | None:
    if prior.empty:
        return None
    counts = prior["source_position"].astype(str).value_counts()
    top_n = int(counts.max())
    tied = set(counts[counts.eq(top_n)].index.astype(str))
    for value in reversed(prior["source_position"].astype(str).tolist()):
        if value in tied:
            return value
    return None


def run_walk_forward(
    frame: pd.DataFrame,
    feature_groups: dict[str, list[str]],
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

    for _, row in frame.iterrows():
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

        model_predictions: dict[str, str] = {}
        model_failed = False
        for group_name, group_features in feature_groups.items():
            usable = [feature for feature in group_features if train[feature].notna().any()]
            if not usable:
                model_failed = True
                diagnostics["skipped_no_usable_training_features"] += 1
                break
            x_train = train[usable]
            y_train = train["source_position"].astype(str)
            x_test = pd.DataFrame([{feature: row[feature] for feature in usable}])
            model = build_model()
            try:
                model.fit(x_train, y_train)
                model_predictions[group_name] = str(model.predict(x_test)[0])
            except Exception:
                model_failed = True
                diagnostics["skipped_model_error"] += 1
                break
        if model_failed:
            continue

        prior = prior_player_positions(frame, row)
        last_position = str(prior.iloc[-1]["source_position"]) if not prior.empty else None
        modal_position = modal_position_with_recent_tiebreak(prior)
        majority_position = str(train["source_position"].astype(str).value_counts().idxmax())

        record = {
            "match_id": row["match_id"],
            "player_id": row["player_id"],
            "match_date": clean(row["match_date"]),
            "true_position": str(row["source_position"]),
            "majority_prediction": majority_position,
            "last_position_prediction": last_position,
            "modal_position_prediction": modal_position,
            "prior_position_rows": int(len(prior)),
            "train_rows": int(len(train)),
            "train_players": int(train["player_id"].nunique()),
            "train_positions": int(train["source_position"].nunique()),
        }
        for group_name, prediction in model_predictions.items():
            record[f"model_{group_name}"] = prediction
        record["position_changed_vs_last"] = (
            None if last_position is None else str(row["source_position"]) != last_position
        )
        predictions.append(record)

    pred = pd.DataFrame(predictions)
    diagnostics["evaluated_rows"] = int(len(pred))
    diagnostics["rows_with_prior_position"] = (
        int(pred["last_position_prediction"].notna().sum()) if not pred.empty else 0
    )
    return pred, diagnostics


def metric_block(y_true: pd.Series, y_pred: pd.Series) -> dict:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }


def evaluate_available(pred: pd.DataFrame, prediction_column: str) -> dict | None:
    available = pred[pred[prediction_column].notna()].copy()
    if available.empty:
        return None
    metrics = metric_block(
        available["true_position"].astype(str), available[prediction_column].astype(str)
    )
    return {"rows": int(len(available)), **metrics}


def summarize(pred: pd.DataFrame, diagnostics: dict, feature_version: str) -> dict:
    if pred.empty:
        return {
            "version": VERSION,
            "status": "PREMATCH_ROBUSTNESS_EXPERIMENT",
            "summary": {**diagnostics, "feature_version": feature_version, "conclusion": "NO_EVALUABLE_ROWS"},
            "metrics": {},
            "switch_analysis": {},
            "head_to_head": {},
            "rules": rules(),
        }

    metric_sets = {
        "model_all_safe": evaluate_available(pred, "model_all_safe"),
        "model_prior_mean_only": evaluate_available(pred, "model_prior_mean_only"),
        "model_prev_only": evaluate_available(pred, "model_prev_only"),
        "majority_train": evaluate_available(pred, "majority_prediction"),
        "player_last_position": evaluate_available(pred, "last_position_prediction"),
        "player_modal_position": evaluate_available(pred, "modal_position_prediction"),
    }

    common = pred[
        pred["last_position_prediction"].notna()
        & pred["modal_position_prediction"].notna()
    ].copy()
    switch = common[common["position_changed_vs_last"].eq(True)].copy()
    stay = common[common["position_changed_vs_last"].eq(False)].copy()

    switch_analysis = {
        "common_rows": int(len(common)),
        "switch_rows": int(len(switch)),
        "stay_rows": int(len(stay)),
        "model_all_safe_switch_accuracy": (
            float((switch["model_all_safe"] == switch["true_position"]).mean()) if len(switch) else None
        ),
        "model_all_safe_stay_accuracy": (
            float((stay["model_all_safe"] == stay["true_position"]).mean()) if len(stay) else None
        ),
        "modal_switch_accuracy": (
            float((switch["modal_position_prediction"] == switch["true_position"]).mean()) if len(switch) else None
        ),
    }

    if len(common):
        model_correct = common["model_all_safe"].eq(common["true_position"])
        last_correct = common["last_position_prediction"].eq(common["true_position"])
        head_to_head = {
            "common_rows": int(len(common)),
            "both_correct": int((model_correct & last_correct).sum()),
            "model_only_correct": int((model_correct & ~last_correct).sum()),
            "last_only_correct": int((~model_correct & last_correct).sum()),
            "both_wrong": int((~model_correct & ~last_correct).sum()),
        }
    else:
        head_to_head = {"common_rows": 0}

    return {
        "version": VERSION,
        "status": "PREMATCH_ROBUSTNESS_EXPERIMENT",
        "summary": {
            **diagnostics,
            "feature_version": feature_version,
            "evaluated_positions": int(pred["true_position"].nunique()),
            "conclusion": "PREMATCH_ROBUSTNESS_COMPLETE_NO_DEPLOYMENT_DECISION",
        },
        "metrics": metric_sets,
        "switch_analysis": switch_analysis,
        "head_to_head_model_vs_last_position": head_to_head,
        "rules": rules(),
    }


def rules() -> list[str]:
    return [
        "All ML inputs are FEATURE-02 strict-past features available before the current match.",
        "Current-match FEATURE-01 values, delta_prev, delta_prior_mean and FEATURE-03 are forbidden.",
        "The evaluated player is excluded completely from the ML training set for that row.",
        "Player-last-position and player-modal-position are simple pre-match football baselines, not ML predictors.",
        "The modal-position baseline is computed only from that player's strictly earlier starter positions.",
        "No target classes are merged or removed for convenience.",
        "No deployment threshold, player fit, ranking or recommendation is created.",
    ]


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# DSAI-11 — Pre-match robustness and football baselines",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
    ]
    for key, value in s.items():
        lines.append(f"- {key}: {value}")

    lines.extend([
        "",
        "## Metric comparison",
        "",
        "| Method | Rows | Accuracy | Balanced accuracy | Macro-F1 |",
        "|---|---:|---:|---:|---:|",
    ])
    for name, block in result.get("metrics", {}).items():
        if block is None:
            lines.append(f"| {name} | 0 | n/a | n/a | n/a |")
        else:
            lines.append(
                f"| {name} | {block['rows']} | {block['accuracy']:.4f} | "
                f"{block['balanced_accuracy']:.4f} | {block['macro_f1']:.4f} |"
            )

    lines.extend(["", "## Position-change analysis"])
    for key, value in result.get("switch_analysis", {}).items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Head-to-head: ML all-safe vs last-position baseline"])
    for key, value in result.get("head_to_head_model_vs_last_position", {}).items():
        lines.append(f"- {key}: {value}")

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

    feature_version, all_features, feature_groups, history_signal = feature_spec()
    with duckdb.connect(str(db_path), read_only=True) as con:
        target = load_target(con)
        temporal = load_temporal_matrix(con, feature_version, all_features)

    frame = target.merge(temporal, on=["match_id", "player_id"], how="left")
    pred, diagnostics = run_walk_forward(frame, feature_groups, history_signal)
    result = summarize(pred, diagnostics, feature_version)
    s = result["summary"]

    print("DSAI-11 PREMATCH ROBUSTNESS: COMPLETE")
    print(f"db: {db_path}")
    print(
        f"candidate_rows={s['candidate_rows']} evaluated_rows={s['evaluated_rows']} "
        f"evaluated_positions={s.get('evaluated_positions', 0)} rows_with_prior_position={s['rows_with_prior_position']}"
    )
    for name in [
        "model_all_safe",
        "model_prior_mean_only",
        "model_prev_only",
        "majority_train",
        "player_last_position",
        "player_modal_position",
    ]:
        block = result.get("metrics", {}).get(name)
        if block:
            print(
                f"{name}: rows={block['rows']} accuracy={block['accuracy']:.4f} "
                f"balanced_accuracy={block['balanced_accuracy']:.4f} macro_f1={block['macro_f1']:.4f}"
            )
    sw = result.get("switch_analysis", {})
    print(
        f"switch_analysis: common={sw.get('common_rows', 0)} switches={sw.get('switch_rows', 0)} "
        f"stays={sw.get('stay_rows', 0)} ml_switch_acc={sw.get('model_all_safe_switch_accuracy')}"
    )
    hh = result.get("head_to_head_model_vs_last_position", {})
    print(
        f"head_to_head: model_only={hh.get('model_only_correct', 0)} "
        f"last_only={hh.get('last_only_correct', 0)} both_correct={hh.get('both_correct', 0)} "
        f"both_wrong={hh.get('both_wrong', 0)}"
    )
    print(f"conclusion={s['conclusion']}")
    print("No deployment threshold, player fit, ranking or recommendation was created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "source_position_prematch_robustness.json"
        md_path = OUTPUT_DIR / "source_position_prematch_robustness.md"
        csv_path = OUTPUT_DIR / "source_position_prematch_robustness_predictions.csv"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        pred.to_csv(csv_path, index=False)
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")
        print(f"predictions: {csv_path}")


if __name__ == "__main__":
    main()
