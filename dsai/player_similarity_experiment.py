"""DSAI-03: exploratory player-role similarity profiles.

Builds player-role profiles from validated FEATURE-01 values and evaluates
nearest-neighbour stability without turning similarity into quality, ranking or
recommendation.
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
OUTPUT_DIR = Path(__file__).with_name("output")
BASE_VERSION = "0.1.0"
EXPERIMENT_VERSION = "dsai_similarity_0.1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DSAI-03 player similarity experiment")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def load_rows(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute(
        """
        SELECT f.match_id, f.player_id, TRIM(pm.primary_role) AS primary_role,
               f.feature_name, f.feature_value, m.match_date
        FROM player_match_features f
        JOIN player_match pm
          ON pm.match_id = f.match_id AND pm.player_id = f.player_id
        JOIN matches m ON m.match_id = f.match_id
        WHERE f.feature_version = ?
          AND f.feature_value IS NOT NULL
          AND pm.minutes_played > 0
          AND pm.primary_role IS NOT NULL
          AND TRIM(pm.primary_role) <> ''
          AND TRIM(pm.primary_role) <> 'Substitute'
        ORDER BY m.match_date, f.player_id, f.feature_name
        """,
        [BASE_VERSION],
    ).fetchdf()


def aggregate_profiles(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame()
    agg = (
        rows.groupby(["player_id", "primary_role", "feature_name"], as_index=False)
        .agg(feature_value=("feature_value", "mean"))
    )
    return agg.pivot_table(
        index=["player_id", "primary_role"],
        columns="feature_name",
        values="feature_value",
        aggfunc="first",
    ).sort_index()


def fit_scaler(matrix: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    means = matrix.mean(axis=0, skipna=True)
    stds = matrix.std(axis=0, skipna=True, ddof=0)
    stds = stds.where(stds > 0)
    return means, stds


def apply_scaler(matrix: pd.DataFrame, means: pd.Series, stds: pd.Series) -> pd.DataFrame:
    return (matrix - means) / stds


def pair_distance(a: pd.Series, b: pd.Series) -> tuple[float | None, int]:
    common = a.notna() & b.notna()
    n = int(common.sum())
    if n == 0:
        return None, 0
    diff = a[common] - b[common]
    return math.sqrt(float((diff * diff).mean())), n


def nearest_neighbours(matrix: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    if matrix.empty:
        return pd.DataFrame(rows)
    for role, role_matrix in matrix.groupby(level="primary_role", sort=True):
        idx = list(role_matrix.index)
        for current in idx:
            best = None
            for other in idx:
                if current == other:
                    continue
                distance, common_n = pair_distance(role_matrix.loc[current], role_matrix.loc[other])
                if distance is None:
                    continue
                candidate = (distance, -common_n, str(other[0]), other, common_n)
                if best is None or candidate[:3] < best[:3]:
                    best = candidate
            if best is not None:
                rows.append(
                    {
                        "player_id": current[0],
                        "primary_role": role,
                        "nearest_player_id": best[3][0],
                        "distance": float(best[0]),
                        "common_features": int(best[4]),
                    }
                )
    return pd.DataFrame(rows)


def pairwise_map(matrix: pd.DataFrame) -> dict[tuple[str, str, str], float]:
    distances: dict[tuple[str, str, str], float] = {}
    if matrix.empty:
        return distances
    for role, role_matrix in matrix.groupby(level="primary_role", sort=True):
        idx = list(role_matrix.index)
        for i in range(len(idx)):
            for j in range(i + 1, len(idx)):
                distance, common_n = pair_distance(role_matrix.loc[idx[i]], role_matrix.loc[idx[j]])
                if distance is None or common_n == 0:
                    continue
                a, b = sorted([str(idx[i][0]), str(idx[j][0])])
                distances[(str(role), a, b)] = float(distance)
    return distances


def temporal_split(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    dates = sorted(pd.to_datetime(rows["match_date"].dropna().unique()))
    if len(dates) < 2:
        return rows.iloc[0:0].copy(), rows.iloc[0:0].copy(), ""
    split_idx = len(dates) // 2
    second_start = pd.Timestamp(dates[split_idx])
    first = rows[pd.to_datetime(rows["match_date"]) < second_start].copy()
    second = rows[pd.to_datetime(rows["match_date"]) >= second_start].copy()
    return first, second, second_start.date().isoformat()


def run_experiment(rows: pd.DataFrame) -> dict:
    if rows.empty:
        raise RuntimeError("No FEATURE-01 rows with observed tactical role are available")

    full = aggregate_profiles(rows)
    means, stds = fit_scaler(full)
    full_z = apply_scaler(full, means, stds)
    nearest = nearest_neighbours(full_z)

    first_rows, second_rows, split_date = temporal_split(rows)
    first = aggregate_profiles(first_rows)
    second = aggregate_profiles(second_rows)

    # For stability, fit scaling only on the first half and apply the same
    # transformation to both halves. This avoids using second-half information
    # to define the representation being compared.
    if first.empty:
        first_z = first
        second_z = second
    else:
        first_means, first_stds = fit_scaler(first)
        first_z = apply_scaler(first, first_means, first_stds)
        second_z = apply_scaler(second.reindex(columns=first.columns), first_means, first_stds)

    first_nn = nearest_neighbours(first_z)
    second_nn = nearest_neighbours(second_z)
    stability = first_nn.merge(
        second_nn,
        on=["player_id", "primary_role"],
        how="inner",
        suffixes=("_first", "_second"),
    )
    if stability.empty:
        retained = 0
        retention_rate = None
    else:
        retained_mask = stability["nearest_player_id_first"] == stability["nearest_player_id_second"]
        retained = int(retained_mask.sum())
        retention_rate = float(retained_mask.mean())

    first_pairs = pairwise_map(first_z)
    second_pairs = pairwise_map(second_z)
    common_keys = sorted(set(first_pairs) & set(second_pairs))
    pair_corr = None
    if len(common_keys) >= 2:
        s1 = pd.Series([first_pairs[k] for k in common_keys], dtype="float64")
        s2 = pd.Series([second_pairs[k] for k in common_keys], dtype="float64")
        corr = s1.corr(s2)
        pair_corr = None if pd.isna(corr) else float(corr)

    role_counts = (
        full.reset_index()
        .groupby("primary_role", as_index=False)
        .agg(profiles=("player_id", "nunique"))
        .sort_values(["profiles", "primary_role"], ascending=[False, True])
    )

    feature_non_null = full.notna().sum(axis=0).sort_values(ascending=False)
    common_feature_counts = nearest["common_features"] if not nearest.empty else pd.Series(dtype=float)

    result = {
        "experiment_version": EXPERIMENT_VERSION,
        "status": "EXPLORATORY_NOT_DEPLOYED",
        "coverage": {
            "rows_used": int(len(rows)),
            "players": int(rows["player_id"].nunique()),
            "roles": int(rows["primary_role"].nunique()),
            "player_role_profiles": int(len(full)),
            "feature_dimensions": int(full.shape[1]),
            "profiles_with_neighbour": int(len(nearest)),
            "median_common_features_neighbour": (
                None if common_feature_counts.empty else float(common_feature_counts.median())
            ),
        },
        "temporal_stability": {
            "split_second_half_start": split_date,
            "eligible_profiles_both_halves": int(len(stability)),
            "same_nearest_neighbour": retained,
            "nearest_neighbour_retention_rate": retention_rate,
            "common_pair_distances": int(len(common_keys)),
            "pairwise_distance_pearson": pair_corr,
        },
        "role_profile_counts": role_counts.to_dict(orient="records"),
        "feature_profile_coverage": [
            {"feature_name": str(name), "profiles_non_null": int(count)}
            for name, count in feature_non_null.items()
        ],
        "nearest_neighbours": nearest.to_dict(orient="records"),
        "method": {
            "unit": "player_id + exact observed primary_role",
            "profile": "mean FEATURE-01 value across played matches in that role",
            "scaling": "z-standardisation by feature; no missing-value imputation",
            "distance": "root mean squared z-difference over pairwise common non-null features",
            "comparison_scope": "exact same observed role only",
            "excluded_role_labels": ["Substitute"],
        },
        "limitations": [
            "Only one development team/season is available, so the player pool is small.",
            "Many exact observed roles contain few distinct players, limiting neighbour choice.",
            "Missing features are not imputed; pairwise distances can use different numbers of common dimensions.",
            "Nearest-neighbour retention measures descriptive stability, not footballing validity or quality.",
            "Similarity does not imply tactical fit, superiority or recommendation.",
        ],
    }
    return result


def render_markdown(result: dict) -> str:
    c = result["coverage"]
    s = result["temporal_stability"]
    lines = [
        "# DSAI-03 — Player similarity / profiles",
        "",
        f"Version: `{result['experiment_version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Coverage",
        f"- Player-role profiles: {c['player_role_profiles']}",
        f"- Players: {c['players']}",
        f"- Roles: {c['roles']}",
        f"- Feature dimensions: {c['feature_dimensions']}",
        f"- Profiles with same-role neighbour: {c['profiles_with_neighbour']}",
        f"- Median common features in chosen neighbour pair: {c['median_common_features_neighbour']}",
        "",
        "## Temporal stability",
        f"- Second half starts: {s['split_second_half_start']}",
        f"- Eligible profiles in both halves: {s['eligible_profiles_both_halves']}",
        f"- Same nearest neighbour: {s['same_nearest_neighbour']}",
        f"- Retention rate: {s['nearest_neighbour_retention_rate']}",
        f"- Common pair distances: {s['common_pair_distances']}",
        f"- Pairwise distance Pearson: {s['pairwise_distance_pearson']}",
        "",
        "## Interpretation",
        "This experiment measures descriptive similarity only. It does not create a quality ranking, tactical fit score or recommendation.",
        "",
        "## Limitations",
    ]
    lines.extend(f"- {item}" for item in result["limitations"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with duckdb.connect(str(db_path), read_only=True) as con:
        rows = load_rows(con)
    result = run_experiment(rows)

    c = result["coverage"]
    s = result["temporal_stability"]
    print("DSAI-03 PLAYER SIMILARITY EXPERIMENT: COMPLETE")
    print(f"db: {db_path}")
    print(
        f"profiles={c['player_role_profiles']} players={c['players']} roles={c['roles']} "
        f"features={c['feature_dimensions']} profiles_with_neighbour={c['profiles_with_neighbour']}"
    )
    print(
        f"temporal_eligible={s['eligible_profiles_both_halves']} "
        f"same_neighbour={s['same_nearest_neighbour']} "
        f"retention_rate={s['nearest_neighbour_retention_rate']} "
        f"pair_distance_corr={s['pairwise_distance_pearson']}"
    )
    print("Similarity only: no quality ranking, fit score or tactical recommendation was created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "player_similarity_experiment.json"
        md_path = OUTPUT_DIR / "player_similarity_experiment.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
