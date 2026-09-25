"""FEATURE-03: leakage-safe role-conditioned temporal features.

This stage conditions FEATURE-01 metrics on the player's observed primary_role.
Only matches with match_date strictly earlier than the current match can enter a
baseline. The current match, same-date matches and future matches never enter.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
BASE_CATALOG = Path(__file__).with_name("catalog.json")
ROLE_CATALOG = Path(__file__).with_name("role_temporal_catalog.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FEATURE-03 role-conditioned temporal features")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def base_feature_names() -> list[str]:
    catalog = load_json(BASE_CATALOG)
    return [f["name"] for f in catalog["ratio_features"] + catalog["per90_features"]]


def clean_role(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def ols_slope(values: list[float]) -> float | None:
    n = len(values)
    if n < 2:
        return None
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return None
    return numerator / denominator


def prior_stats(history: list[float]) -> dict[str, float | None]:
    n = len(history)
    if n == 0:
        return {
            "role_history_n": 0.0,
            "role_prior_mean": None,
            "role_prior_std": None,
            "role_prior_slope": None,
        }
    mean = sum(history) / n
    std = None
    if n >= 2:
        variance = sum((v - mean) ** 2 for v in history) / n
        std = math.sqrt(variance)
    return {
        "role_history_n": float(n),
        "role_prior_mean": mean,
        "role_prior_std": std,
        "role_prior_slope": ols_slope(history),
    }


def compute_role_metric_frame(base: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    required = {
        "match_id", "player_id", "feature_name", "feature_value",
        "match_date", "primary_role",
    }
    missing = required - set(base.columns)
    if missing:
        raise ValueError(f"Missing columns for FEATURE-03 metric build: {sorted(missing)}")
    if base["match_date"].isna().any():
        raise ValueError("FEATURE-03 requires non-null match_date")

    base = base[base["feature_name"].isin(feature_names)].copy()
    base["primary_role"] = base["primary_role"].map(clean_role)
    rows: list[dict] = []
    operators = [
        "role_history_n", "role_prior_mean", "role_prior_std",
        "role_delta_prior_mean", "role_prior_slope",
    ]

    missing_role = base[base["primary_role"].isna()]
    for row in missing_role.itertuples(index=False):
        for operator in operators:
            rows.append(
                {
                    "match_id": row.match_id,
                    "player_id": row.player_id,
                    "feature_name": f"{row.feature_name}__{operator}",
                    "feature_value": None,
                    "feature_text": None,
                }
            )

    known = base[base["primary_role"].notna()].copy()
    known = known.sort_values(
        ["player_id", "feature_name", "primary_role", "match_date", "match_id"]
    )

    for (player_id, feature_name, role), group in known.groupby(
        ["player_id", "feature_name", "primary_role"], sort=False
    ):
        history: list[float] = []
        for match_date, same_date in group.groupby("match_date", sort=True):
            stats = prior_stats(history)
            same_date = same_date.sort_values("match_id")
            for row in same_date.itertuples(index=False):
                current = None if pd.isna(row.feature_value) else float(row.feature_value)
                values = dict(stats)
                values["role_delta_prior_mean"] = None
                if current is not None and stats["role_prior_mean"] is not None:
                    values["role_delta_prior_mean"] = current - float(stats["role_prior_mean"])

                for operator in operators:
                    rows.append(
                        {
                            "match_id": row.match_id,
                            "player_id": player_id,
                            "feature_name": f"{feature_name}__{operator}",
                            "feature_value": values[operator],
                            "feature_text": role,
                        }
                    )

            # Same-date values enter history only after every row on that date
            # has been calculated, preventing same-date leakage.
            for row in same_date.itertuples(index=False):
                if not pd.isna(row.feature_value):
                    history.append(float(row.feature_value))

    return pd.DataFrame(rows)


def compute_role_match_history(player_matches: pd.DataFrame) -> pd.DataFrame:
    required = {"match_id", "player_id", "match_date", "primary_role", "minutes_played"}
    missing = required - set(player_matches.columns)
    if missing:
        raise ValueError(f"Missing columns for FEATURE-03 role history: {sorted(missing)}")
    if player_matches["match_date"].isna().any():
        raise ValueError("FEATURE-03 requires non-null match_date")

    frame = player_matches.copy()
    frame["primary_role"] = frame["primary_role"].map(clean_role)
    rows: list[dict] = []

    for row in frame[frame["primary_role"].isna()].itertuples(index=False):
        rows.append(
            {
                "match_id": row.match_id,
                "player_id": row.player_id,
                "feature_name": "role_match_history_n",
                "feature_value": None,
                "feature_text": None,
            }
        )

    known = frame[frame["primary_role"].notna()].copy()
    known = known.sort_values(["player_id", "primary_role", "match_date", "match_id"])
    for (player_id, role), group in known.groupby(["player_id", "primary_role"], sort=False):
        prior_played = 0
        for match_date, same_date in group.groupby("match_date", sort=True):
            same_date = same_date.sort_values("match_id")
            for row in same_date.itertuples(index=False):
                rows.append(
                    {
                        "match_id": row.match_id,
                        "player_id": player_id,
                        "feature_name": "role_match_history_n",
                        "feature_value": float(prior_played),
                        "feature_text": role,
                    }
                )
            prior_played += sum(
                1
                for row in same_date.itertuples(index=False)
                if row.minutes_played is not None
                and not pd.isna(row.minutes_played)
                and float(row.minutes_played) > 0.0
            )

    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    base_catalog = load_json(BASE_CATALOG)
    role_catalog = load_json(ROLE_CATALOG)
    base_version = role_catalog["base_feature_version"]
    version = role_catalog["feature_version"]
    names = base_feature_names()
    operators = [o["name"] for o in role_catalog["metric_operators"]]

    if base_catalog["feature_version"] != base_version:
        raise RuntimeError("FEATURE-03 base feature version mismatch")
    if len(names) != len(set(names)):
        raise RuntimeError("Duplicate base feature names")

    with duckdb.connect(str(db_path)) as con:
        base = con.execute(
            """
            SELECT f.match_id, f.player_id, f.feature_name, f.feature_value,
                   m.match_date, pm.primary_role
            FROM player_match_features f
            JOIN matches m ON m.match_id = f.match_id
            JOIN player_match pm
              ON pm.match_id = f.match_id AND pm.player_id = f.player_id
            WHERE f.feature_version = ?
            ORDER BY f.player_id, f.feature_name, m.match_date, f.match_id
            """,
            [base_version],
        ).fetchdf()

        player_matches = con.execute(
            """
            SELECT pm.match_id, pm.player_id, m.match_date,
                   pm.primary_role, pm.minutes_played
            FROM player_match pm
            JOIN matches m ON m.match_id = pm.match_id
            ORDER BY pm.player_id, m.match_date, pm.match_id
            """
        ).fetchdf()

        expected_base = len(player_matches) * len(names)
        if len(base) != expected_base:
            raise RuntimeError(
                f"Expected {expected_base} FEATURE-01 rows, found {len(base)}. "
                "Run features/run_stage1.py first."
            )

        metric_frame = compute_role_metric_frame(base, names)
        history_frame = compute_role_match_history(player_matches)
        combined = pd.concat([metric_frame, history_frame], ignore_index=True)
        expected = len(base) * len(operators) + len(player_matches)
        if len(combined) != expected:
            raise RuntimeError(f"Expected {expected} FEATURE-03 rows, built {len(combined)}")

        combined["feature_version"] = version
        con.execute("DELETE FROM player_match_features WHERE feature_version = ?", [version])
        con.register("role_temporal_df", combined)
        con.execute(
            """
            INSERT INTO player_match_features (
                match_id, player_id, feature_name, feature_value,
                feature_text, feature_version
            )
            SELECT match_id, player_id, feature_name, feature_value,
                   feature_text, feature_version
            FROM role_temporal_df
            """
        )
        con.unregister("role_temporal_df")

        written = con.execute(
            "SELECT COUNT(*) FROM player_match_features WHERE feature_version = ?",
            [version],
        ).fetchone()[0]
        non_null = con.execute(
            """
            SELECT COUNT(*) FROM player_match_features
            WHERE feature_version = ? AND feature_value IS NOT NULL
            """,
            [version],
        ).fetchone()[0]
        role_pm = con.execute(
            "SELECT COUNT(*) FROM player_match WHERE primary_role IS NOT NULL AND TRIM(primary_role) <> ''"
        ).fetchone()[0]
        distinct_roles = con.execute(
            "SELECT COUNT(DISTINCT primary_role) FROM player_match WHERE primary_role IS NOT NULL AND TRIM(primary_role) <> ''"
        ).fetchone()[0]

    print("FEATURE-03 role-conditioned temporal build complete")
    print(f"feature_version: {version}")
    print(f"base features: {len(names)}")
    print(f"metric operators: {len(operators)}")
    print(f"player_match rows: {len(player_matches)}")
    print(f"player_match rows with observed role: {role_pm}")
    print(f"distinct observed role labels: {distinct_roles}")
    print(f"feature rows written: {written}")
    print(f"non-null feature values: {non_null}")
    print("Strict-past + same-role contract applied; same-date/future matches never inform the current row.")
    print("No role was inferred and no score, percentile, weight, minimum-sample threshold or fit judgement was created.")


if __name__ == "__main__":
    main()
