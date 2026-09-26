"""PERF-13: candidate score policies + role-aware validation.

Compares experimental player-match performance-score policies after applying only
PERF-11 validated NULL-as-zero semantics in memory.

No production weight, threshold, ranking, recommendation or DB mutation is approved.
Goalkeepers remain outside the outfield score path.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
FEATURE_CATALOG = ROOT / "features" / "catalog.json"
DIMENSION_MAP = Path(__file__).with_name("performance_dimension_map.json")
DIRECTION_FILE = Path(__file__).with_name("performance_direction_evidence.json")
OUTPUT_DIR = Path(__file__).with_name("output")

VERSION = "performance_score_policy_experiment_0.1.0"
SIGNED = {"POSITIVE_SUPPORTED", "NEGATIVE_SUPPORTED"}
VALIDATED_ZERO_RAW = {"shots_total", "goals", "red_cards"}
GK_POSITION = "Goalkeeper"

POLICIES = {
    "COMPLETE_5D": 5,
    "AVAILABLE_4PLUS": 4,
    "AVAILABLE_3PLUS": 3,
    "AVAILABLE_2PLUS": 2,
}
VARIANTS = ("GLOBAL", "ROLE_AWARE")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-13 candidate score policy experiment")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--no-write", action="store_true")
    return p.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_position(role: object) -> str | None:
    if role is None or pd.isna(role):
        return None
    text = str(role).strip()
    if not text or text == "Substitute":
        return None
    return text.split(" | ", 1)[0].strip() or None


def empirical_score(values: pd.Series, direction: str) -> pd.Series:
    x = pd.to_numeric(values, errors="coerce")
    if direction == "POSITIVE_SUPPORTED":
        return x.rank(method="average", pct=True) * 100.0
    if direction == "NEGATIVE_SUPPORTED":
        return (-x).rank(method="average", pct=True) * 100.0
    raise ValueError(f"Unsupported direction: {direction}")


def role_aware_score(
    frame: pd.DataFrame,
    value_col: str,
    direction: str,
) -> tuple[pd.Series, dict[str, int]]:
    """Percentile within source_position where estimable; otherwise global fallback."""
    global_score = empirical_score(frame[value_col], direction)
    out = pd.Series(np.nan, index=frame.index, dtype=float)
    fallback_rows = 0
    role_rows = 0

    for position, idx in frame.groupby("source_position", dropna=False).groups.items():
        idx = pd.Index(idx)
        x = pd.to_numeric(frame.loc[idx, value_col], errors="coerce")
        valid = x.dropna()
        if pd.notna(position) and len(valid) >= 2 and int(valid.nunique()) >= 2:
            out.loc[idx] = empirical_score(x, direction)
            role_rows += int(x.notna().sum())
        else:
            out.loc[idx] = global_score.loc[idx]
            fallback_rows += int(x.notna().sum())

    return out, {
        "role_normalized_non_null_rows": role_rows,
        "global_fallback_non_null_rows": fallback_rows,
    }


def describe_score(values: pd.Series) -> dict[str, float | int | None]:
    x = pd.to_numeric(values, errors="coerce").dropna()
    if x.empty:
        return {
            "rows": 0,
            "min": None,
            "p25": None,
            "median": None,
            "mean": None,
            "p75": None,
            "max": None,
            "std": None,
        }
    return {
        "rows": int(len(x)),
        "min": float(x.min()),
        "p25": float(x.quantile(0.25)),
        "median": float(x.median()),
        "mean": float(x.mean()),
        "p75": float(x.quantile(0.75)),
        "max": float(x.max()),
        "std": float(x.std(ddof=0)),
    }


def safe_spearman(a: pd.Series, b: pd.Series) -> float | None:
    pair = pd.concat(
        [pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce")],
        axis=1,
    ).dropna()
    if len(pair) < 3:
        return None
    if pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
        return None
    value = pair.iloc[:, 0].corr(pair.iloc[:, 1], method="spearman")
    return None if pd.isna(value) else float(value)


def build_base_frame(db_path: Path) -> tuple[pd.DataFrame, dict, dict, list[str], list[str]]:
    catalog = load_json(FEATURE_CATALOG)
    directions = load_json(DIRECTION_FILE)
    mapping = load_json(DIMENSION_MAP)
    feature_version = str(catalog["feature_version"])

    direction_by_feature = {
        str(x["feature_name"]): str(x["direction_status"])
        for x in directions.get("features", [])
    }
    primary_dimension = {
        str(x["feature_name"]): str(x["primary_dimension"])
        for x in mapping.get("feature_mapping", [])
    }
    signed_features = [
        f for f, status in direction_by_feature.items() if status in SIGNED
    ]
    outfield_dimensions = [
        str(name)
        for name, meta in mapping.get("dimensions", {}).items()
        if str(meta.get("scope")) != "goalkeeper_only"
    ]

    with duckdb.connect(str(db_path), read_only=True) as con:
        played = con.execute(
            """
            SELECT match_id, player_id, minutes_played, primary_role
            FROM player_match
            WHERE minutes_played > 0
            """
        ).fetchdf()

        raw = con.execute(
            """
            SELECT rs.*
            FROM player_match_raw_stats rs
            JOIN player_match pm
              ON pm.match_id=rs.match_id AND pm.player_id=rs.player_id
            WHERE pm.minutes_played > 0
            """
        ).fetchdf()

        feature_long = con.execute(
            """
            SELECT f.match_id, f.player_id, f.feature_name, f.feature_value
            FROM player_match_features f
            JOIN player_match pm
              ON pm.match_id=f.match_id AND pm.player_id=f.player_id
            WHERE f.feature_version=? AND pm.minutes_played > 0
            """,
            [feature_version],
        ).fetchdf()

    played["source_position"] = played["primary_role"].map(source_position)
    raw = raw.merge(
        played[["match_id", "player_id", "minutes_played", "source_position"]],
        on=["match_id", "player_id"],
        how="left",
    )

    raw["__saves_num"] = pd.to_numeric(raw.get("saves"), errors="coerce")
    direct_gk_keys = set(
        map(
            tuple,
            raw.loc[
                raw["source_position"] == GK_POSITION,
                ["match_id", "player_id"],
            ].to_numpy(),
        )
    )
    unknown_gk_keys = set(
        map(
            tuple,
            raw.loc[
                raw["source_position"].isna()
                & (raw["__saves_num"].fillna(0) > 0),
                ["match_id", "player_id"],
            ].to_numpy(),
        )
    )

    played["__key"] = list(zip(played["match_id"], played["player_id"]))
    outfield = played[
        ~played["__key"].isin(direct_gk_keys | unknown_gk_keys)
    ].copy()
    outfield_keys = set(outfield["__key"])

    signed_long = feature_long[
        feature_long["feature_name"].isin(signed_features)
    ].copy()
    signed_long["__key"] = list(zip(signed_long["match_id"], signed_long["player_id"]))
    signed_long = signed_long[signed_long["__key"].isin(outfield_keys)]

    wide = (
        signed_long.pivot_table(
            index=["match_id", "player_id"],
            columns="feature_name",
            values="feature_value",
            aggfunc="first",
        )
        .reset_index()
    )
    wide.columns.name = None

    frame = outfield[
        ["match_id", "player_id", "minutes_played", "primary_role", "source_position"]
    ].merge(wide, on=["match_id", "player_id"], how="left")

    raw["__key"] = list(zip(raw["match_id"], raw["player_id"]))
    raw_out = raw[raw["__key"].isin(outfield_keys)].copy()
    raw_indexed = raw_out.set_index(["match_id", "player_id"], drop=False)

    # PERF-11 validated NULL-as-zero semantics, in memory only.
    goals = pd.to_numeric(raw_indexed["goals"], errors="coerce").fillna(0.0)
    shots = pd.to_numeric(raw_indexed["shots_total"], errors="coerce").fillna(0.0)
    reds = pd.to_numeric(raw_indexed["red_cards"], errors="coerce").fillna(0.0)
    minutes = pd.to_numeric(raw_indexed["minutes_played"], errors="coerce")

    derived = pd.DataFrame(index=raw_indexed.index)
    derived["goals_per90"] = np.where(minutes > 0, goals * 90.0 / minutes, np.nan)
    derived["red_cards_per90"] = np.where(minutes > 0, reds * 90.0 / minutes, np.nan)
    derived["goal_per_shot_rate"] = np.where(shots > 0, goals / shots, np.nan)
    derived = derived.reset_index(drop=True)
    derived.insert(0, "player_id", raw_out["player_id"].to_numpy())
    derived.insert(0, "match_id", raw_out["match_id"].to_numpy())

    override = ["goals_per90", "red_cards_per90", "goal_per_shot_rate"]
    frame = frame.drop(columns=[c for c in override if c in frame.columns])
    frame = frame.merge(
        derived[["match_id", "player_id", *override]],
        on=["match_id", "player_id"],
        how="left",
    )

    # Preserve PERF-09/12 degeneracy rule.
    used_features: list[str] = []
    degenerate_features: list[str] = []
    for feature in signed_features:
        if feature not in frame.columns:
            degenerate_features.append(feature)
            continue
        x = pd.to_numeric(frame[feature], errors="coerce")
        if int(x.nunique(dropna=True)) < 2:
            degenerate_features.append(feature)
        else:
            used_features.append(feature)

    return frame, direction_by_feature, primary_dimension, used_features, outfield_dimensions


def add_variant_scores(
    base: pd.DataFrame,
    variant: str,
    direction_by_feature: dict[str, str],
    primary_dimension: dict[str, str],
    used_features: list[str],
    dimensions: list[str],
) -> tuple[pd.DataFrame, dict]:
    frame = base.copy()
    normalization_diag: dict[str, dict] = {}

    for feature in used_features:
        value_col = feature
        score_col = f"{variant.lower()}__feature__{feature}"
        if variant == "GLOBAL":
            frame[score_col] = empirical_score(
                frame[value_col],
                direction_by_feature[feature],
            )
            normalization_diag[feature] = {
                "role_normalized_non_null_rows": 0,
                "global_fallback_non_null_rows": int(
                    pd.to_numeric(frame[value_col], errors="coerce").notna().sum()
                ),
            }
        elif variant == "ROLE_AWARE":
            score, diag = role_aware_score(
                frame,
                value_col,
                direction_by_feature[feature],
            )
            frame[score_col] = score
            normalization_diag[feature] = diag
        else:
            raise ValueError(variant)

    dim_cols: list[str] = []
    for dim in dimensions:
        feature_score_cols = [
            f"{variant.lower()}__feature__{f}"
            for f in used_features
            if primary_dimension.get(f) == dim
        ]
        dim_col = f"{variant.lower()}__dimension__{dim}"
        evidence_col = f"{variant.lower()}__dimension_n__{dim}"
        dim_cols.append(dim_col)
        if feature_score_cols:
            frame[evidence_col] = frame[feature_score_cols].notna().sum(axis=1)
            frame[dim_col] = frame[feature_score_cols].mean(axis=1, skipna=True)
            frame.loc[frame[evidence_col] == 0, dim_col] = np.nan
        else:
            frame[evidence_col] = 0
            frame[dim_col] = np.nan

    coverage_col = f"{variant.lower()}__dimension_coverage_count"
    frame[coverage_col] = frame[dim_cols].notna().sum(axis=1).astype(int)
    frame[f"{variant.lower()}__evidence_coverage_pct"] = (
        frame[coverage_col] / max(len(dimensions), 1) * 100.0
    )

    for policy, threshold in POLICIES.items():
        score_col = f"{variant.lower()}__score__{policy}"
        eligible = frame[coverage_col] >= threshold
        frame[score_col] = np.nan
        frame.loc[eligible, score_col] = frame.loc[eligible, dim_cols].mean(
            axis=1,
            skipna=True,
        )

    return frame, {
        "normalization": normalization_diag,
        "dimension_columns": dim_cols,
        "coverage_column": coverage_col,
    }


def evaluate_variant(
    frame: pd.DataFrame,
    variant: str,
    dimensions: list[str],
) -> dict:
    prefix = variant.lower()
    coverage_col = f"{prefix}__dimension_coverage_count"
    dim_cols = {d: f"{prefix}__dimension__{d}" for d in dimensions}

    policies: dict[str, dict] = {}
    for policy, threshold in POLICIES.items():
        score_col = f"{prefix}__score__{policy}"
        eligible = frame[score_col].notna()

        by_position = []
        for position, group in frame.groupby("source_position", dropna=False):
            gscore = pd.to_numeric(group[score_col], errors="coerce")
            by_position.append(
                {
                    "source_position": None if pd.isna(position) else str(position),
                    "rows": int(len(group)),
                    "eligible_rows": int(gscore.notna().sum()),
                    "coverage_rate": float(gscore.notna().mean()) if len(group) else None,
                    "score": describe_score(gscore),
                }
            )

        loo = []
        for dim, dim_col in dim_cols.items():
            original = pd.to_numeric(frame[score_col], errors="coerce")
            remaining = [c for d, c in dim_cols.items() if d != dim]
            reduced = frame[remaining].mean(axis=1, skipna=True)
            remaining_n = frame[remaining].notna().sum(axis=1)
            common = original.notna() & (remaining_n >= 1) & reduced.notna()
            delta = (original[common] - reduced[common]).abs()
            loo.append(
                {
                    "removed_dimension": dim,
                    "rows": int(common.sum()),
                    "mean_abs_delta": float(delta.mean()) if len(delta) else None,
                    "median_abs_delta": float(delta.median()) if len(delta) else None,
                    "p95_abs_delta": float(delta.quantile(0.95)) if len(delta) else None,
                    "spearman": safe_spearman(original[common], reduced[common]),
                }
            )

        policies[policy] = {
            "threshold_dimensions": threshold,
            "eligible_rows": int(eligible.sum()),
            "coverage_rate": float(eligible.mean()) if len(frame) else None,
            "score_distribution": describe_score(frame[score_col]),
            "coverage_and_bias_by_source_position": by_position,
            "leave_one_dimension_out": loo,
        }

    correlations = []
    policy_names = list(POLICIES)
    for i, left in enumerate(policy_names):
        for right in policy_names[i + 1 :]:
            left_col = f"{prefix}__score__{left}"
            right_col = f"{prefix}__score__{right}"
            pair = frame[[left_col, right_col]].dropna()
            correlations.append(
                {
                    "left": left,
                    "right": right,
                    "common_rows": int(len(pair)),
                    "spearman": safe_spearman(pair[left_col], pair[right_col]),
                }
            )

    return {
        "dimension_count_distribution": {
            str(i): int((frame[coverage_col] == i).sum())
            for i in range(len(dimensions) + 1)
        },
        "policies": policies,
        "policy_rank_correlations": correlations,
    }


def build_experiment(db_path: Path) -> tuple[dict, pd.DataFrame]:
    (
        base,
        direction_by_feature,
        primary_dimension,
        used_features,
        dimensions,
    ) = build_base_frame(db_path)

    combined = base.copy()
    evaluations = {}

    for variant in VARIANTS:
        scored, _meta = add_variant_scores(
            base,
            variant,
            direction_by_feature,
            primary_dimension,
            used_features,
            dimensions,
        )
        new_cols = [c for c in scored.columns if c not in combined.columns]
        combined = pd.concat([combined, scored[new_cols]], axis=1)
        evaluations[variant] = evaluate_variant(scored, variant, dimensions)

    cross_variant = []
    for policy in POLICIES:
        g = combined[f"global__score__{policy}"]
        r = combined[f"role_aware__score__{policy}"]
        pair = pd.concat([g, r], axis=1).dropna()
        pair.columns = ["global", "role_aware"]
        cross_variant.append(
            {
                "policy": policy,
                "common_rows": int(len(pair)),
                "spearman": safe_spearman(pair["global"], pair["role_aware"]),
                "mean_abs_delta": (
                    float((pair["global"] - pair["role_aware"]).abs().mean())
                    if len(pair)
                    else None
                ),
            }
        )

    result = {
        "version": VERSION,
        "status": "EXPERIMENTAL_NO_DEPLOY",
        "summary": {
            "outfield_rows": int(len(base)),
            "used_signed_features": used_features,
            "dimensions": dimensions,
            "validated_zero_raw_metrics": sorted(VALIDATED_ZERO_RAW),
            "candidate_policies": POLICIES,
            "normalization_variants": list(VARIANTS),
            "conclusion": "CANDIDATE_POLICY_EVALUATION_READY_MANUAL_GATE",
        },
        "variant_evaluation": evaluations,
        "cross_variant_comparison": cross_variant,
        "guardrails": [
            "Only PERF-11 validated NULL-as-zero semantics are applied in memory.",
            "yellow_cards missingness is not reinterpreted.",
            "goal_per_shot_rate remains undefined when shots_total is zero.",
            "Role-aware normalization uses source_position only as comparison context, never as target or direct weight.",
            "If a source_position group cannot estimate a percentile, that feature falls back to the global percentile.",
            "All candidate policies use equal mean of available dimension scores; no production dimension weights are approved.",
            "Goalkeepers are excluded from the outfield policy experiment.",
            "DuckDB and FEATURE-01 are not modified.",
            "No good/bad threshold, product ranking or recommendation is approved.",
            "The LLM does not calculate or alter the score.",
        ],
    }

    export_cols = [
        "match_id",
        "player_id",
        "minutes_played",
        "primary_role",
        "source_position",
    ]
    export_cols += [
        c
        for c in combined.columns
        if "__dimension__" in c
        or "__dimension_coverage_count" in c
        or "__evidence_coverage_pct" in c
        or "__score__" in c
    ]
    export = combined[export_cols].copy()
    export["score_version"] = VERSION
    return result, export


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# PERF-13 — Candidate score policies + role-aware validation",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
        f"- outfield_rows: {s['outfield_rows']}",
        f"- used_signed_features: {len(s['used_signed_features'])}",
        f"- dimensions: {', '.join(s['dimensions'])}",
        f"- conclusion: `{s['conclusion']}`",
        "",
    ]

    for variant, evaluation in result["variant_evaluation"].items():
        lines += [f"## {variant}", ""]
        lines.append(
            "- dimension_count_distribution: "
            + json.dumps(evaluation["dimension_count_distribution"], ensure_ascii=False)
        )
        for policy, meta in evaluation["policies"].items():
            dist = meta["score_distribution"]
            lines.append(
                f"- `{policy}`: rows={meta['eligible_rows']} "
                f"coverage={meta['coverage_rate']:.3f} "
                f"median={dist['median'] if dist['median'] is not None else 'NA'}"
            )
        lines.append("")

    lines += ["## Cross-variant comparison", ""]
    for row in result["cross_variant_comparison"]:
        lines.append(
            f"- `{row['policy']}`: common={row['common_rows']} "
            f"spearman={row['spearman']} mean_abs_delta={row['mean_abs_delta']}"
        )

    lines += ["", "## Guardrails", ""]
    lines.extend(f"- {x}" for x in result["guardrails"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    result, export = build_experiment(db_path)

    print("PERF-13 SCORE POLICY EXPERIMENT: COMPLETE")
    print(f"version={VERSION}")
    print(f"db={db_path}")
    print(f"outfield_rows={result['summary']['outfield_rows']}")
    for variant, evaluation in result["variant_evaluation"].items():
        print(f"[{variant}]")
        for policy, meta in evaluation["policies"].items():
            print(
                f"{policy}: rows={meta['eligible_rows']} "
                f"coverage={meta['coverage_rate']:.4f} "
                f"median={meta['score_distribution']['median']}"
            )
    print(f"conclusion={result['summary']['conclusion']}")

    if args.no_write:
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "performance_score_policy_experiment.json"
    csv_path = OUTPUT_DIR / "performance_score_policy_experiment.csv"
    md_path = OUTPUT_DIR / "performance_score_policy_experiment.md"

    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    export.to_csv(csv_path, index=False)
    md_path.write_text(render_markdown(result), encoding="utf-8")

    print(f"json={json_path}")
    print(f"csv={csv_path}")
    print(f"md={md_path}")


if __name__ == "__main__":
    main()
