"""PERF-15: repair sparse dimension coverage with contribution fallbacks.

This experiment preserves PERF-14 v2 as the primary score path, but fixes an
important product limitation: a missing signed feature must not automatically mean
"no observable contribution" when successful football actions are present.

Rules:
- existing signed dimensions remain primary;
- fallback evidence is used ONLY when an existing dimension is missing;
- fallback features are derived only from already imported raw successful actions;
- NULL is never globally converted to zero;
- a successful-child count may be set to 0 only when its observed parent-attempt
  count is exactly 0 (mathematical subset identity, e.g. tackles_won <= tackles_total);
- fallback features are normalized within the broad tactical position group, with
  global fallback only when the group distribution is not estimable;
- substitute appearances with unavailable tactical role remain OTHER_OUTFIELD and
  are not promoted into the product score;
- goalkeeper remains separate.

Fallbacks measure observed contribution volume, not universal football quality.
They are therefore explicitly labelled CONTRIBUTION_FALLBACK in the export.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

import performance_position_score_experiment_v2 as perf14v2

perf14 = perf14v2.perf14
ROOT = Path(__file__).resolve().parents[1]
PRIORS_FILE = Path(__file__).with_name("performance_position_weight_priors.json")
VERSION = "performance_position_score_experiment_0.3.0"
MIN_DIMENSIONS = 3
DIMENSIONS = list(perf14.DIMENSIONS)

# Successful/beneficial observed actions only. Context-dependent attempt volumes are
# intentionally not used here as direct positive performance signals.
FALLBACK_SPECS: dict[str, list[tuple[str, str, str | None]]] = {
    "attacking_threat": [
        ("fallback_dribbles_won_per90", "dribbles_won", "dribbles_total"),
        ("fallback_penalties_won_per90", "penalties_won", None),
    ],
    "creation_progression": [
        ("fallback_passes_completed_per90", "passes_completed", "passes_total"),
        ("fallback_long_balls_completed_per90", "long_balls_completed", "long_balls_total"),
        ("fallback_crosses_completed_per90", "crosses_completed", "crosses_total"),
        ("fallback_assists_per90", "assists", None),
    ],
    "defensive_contribution": [
        ("fallback_tackles_won_per90", "tackles_won", "tackles_total"),
        ("fallback_interceptions_per90", "interceptions", None),
        ("fallback_blocked_passes_per90", "blocked_passes", None),
        ("fallback_clearances_per90", "clearances", None),
    ],
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_child_count(child: pd.Series, parent: pd.Series) -> pd.Series:
    """Preserve NULL except when observed parent=0 logically forces child=0."""
    child_num = pd.to_numeric(child, errors="coerce")
    parent_num = pd.to_numeric(parent, errors="coerce")
    forced_zero = child_num.isna() & parent_num.eq(0)
    out = child_num.copy()
    out.loc[forced_zero] = 0.0
    return out


def positive_percentile(values: pd.Series) -> pd.Series:
    x = pd.to_numeric(values, errors="coerce")
    return x.rank(method="average", pct=True) * 100.0


def role_aware_positive_percentile(
    frame: pd.DataFrame,
    value_col: str,
) -> tuple[pd.Series, dict[str, int]]:
    global_score = positive_percentile(frame[value_col])
    out = pd.Series(np.nan, index=frame.index, dtype=float)
    role_rows = 0
    fallback_rows = 0

    for group, idx in frame.groupby("position_group", dropna=False).groups.items():
        idx = pd.Index(idx)
        x = pd.to_numeric(frame.loc[idx, value_col], errors="coerce")
        valid = x.dropna()
        if (
            pd.notna(group)
            and str(group) != "OTHER_OUTFIELD"
            and len(valid) >= 2
            and int(valid.nunique()) >= 2
        ):
            out.loc[idx] = positive_percentile(x)
            role_rows += int(x.notna().sum())
        else:
            out.loc[idx] = global_score.loc[idx]
            fallback_rows += int(x.notna().sum())

    return out, {
        "role_normalized_non_null_rows": role_rows,
        "global_fallback_non_null_rows": fallback_rows,
    }


def load_raw_contribution(db_path: Path) -> pd.DataFrame:
    needed = sorted(
        {
            source
            for specs in FALLBACK_SPECS.values()
            for _name, source, _parent in specs
        }
        | {
            parent
            for specs in FALLBACK_SPECS.values()
            for _name, _source, parent in specs
            if parent is not None
        }
    )
    cols = ",\n                   ".join(f"rs.{name}" for name in needed)
    with duckdb.connect(str(db_path), read_only=True) as con:
        raw = con.execute(
            f"""
            SELECT rs.match_id, rs.player_id, pm.minutes_played,
                   {cols}
            FROM player_match_raw_stats rs
            JOIN player_match pm
              ON pm.match_id = rs.match_id AND pm.player_id = rs.player_id
            WHERE pm.minutes_played > 0
            """
        ).fetchdf()
    if raw.duplicated(["match_id", "player_id"]).any():
        raise RuntimeError("Raw contribution source has duplicate match/player rows")
    return raw


def add_fallback_dimensions(
    scored: pd.DataFrame,
    db_path: Path,
) -> tuple[pd.DataFrame, dict]:
    frame = scored.copy()
    raw = load_raw_contribution(db_path)
    frame = frame.merge(raw, on=["match_id", "player_id"], how="left", validate="one_to_one")

    normalization: dict[str, dict] = {}
    fallback_by_dimension: dict[str, int] = {}

    for dimension, specs in FALLBACK_SPECS.items():
        feature_score_cols: list[str] = []
        for derived_name, source, parent in specs:
            source_values = pd.to_numeric(frame[source], errors="coerce")
            if parent is not None:
                source_values = safe_child_count(source_values, frame[parent])
            minutes = pd.to_numeric(frame["minutes_played_y"], errors="coerce")
            raw_col = f"{derived_name}__raw"
            score_col = f"{derived_name}__score"
            frame[raw_col] = np.where(
                minutes.gt(0) & source_values.notna(),
                source_values * 90.0 / minutes,
                np.nan,
            )
            frame[score_col], normalization[derived_name] = role_aware_positive_percentile(
                frame, raw_col
            )
            feature_score_cols.append(score_col)

        fallback_col = f"fallback__dimension__{dimension}"
        frame[fallback_col] = frame[feature_score_cols].mean(axis=1, skipna=True)
        frame.loc[frame[feature_score_cols].notna().sum(axis=1) == 0, fallback_col] = np.nan

        dim_col = f"role_aware__dimension__{dimension}"
        evidence_col = f"dimension_evidence_source__{dimension}"
        frame[evidence_col] = np.where(
            frame[dim_col].notna(),
            "DIRECT_SIGNED",
            np.where(frame[fallback_col].notna(), "CONTRIBUTION_FALLBACK", "MISSING"),
        )
        fill_mask = frame[dim_col].isna() & frame[fallback_col].notna()
        frame.loc[fill_mask, dim_col] = frame.loc[fill_mask, fallback_col]
        fallback_by_dimension[dimension] = int(fill_mask.sum())

    # Dimensions that currently need no fallback still receive explicit provenance.
    for dimension in DIMENSIONS:
        evidence_col = f"dimension_evidence_source__{dimension}"
        dim_col = f"role_aware__dimension__{dimension}"
        if evidence_col not in frame.columns:
            frame[evidence_col] = np.where(frame[dim_col].notna(), "DIRECT_SIGNED", "MISSING")
            fallback_by_dimension.setdefault(dimension, 0)

    return frame, {
        "normalization": normalization,
        "fallback_rows_by_dimension": fallback_by_dimension,
    }


def rebuild_score(frame: pd.DataFrame) -> pd.DataFrame:
    priors = load_json(PRIORS_FILE)
    out = frame.copy()
    dim_cols = {d: f"role_aware__dimension__{d}" for d in DIMENSIONS}

    scores = pd.Series(np.nan, index=out.index, dtype=float)
    confidence = pd.Series(np.nan, index=out.index, dtype=float)
    coverage = pd.Series(0, index=out.index, dtype=int)
    statuses = pd.Series("", index=out.index, dtype="object")
    fallback_count = pd.Series(0, index=out.index, dtype=int)

    for idx, row in out.iterrows():
        group = str(row["position_group"])
        cfg = priors["position_groups"].get(group, priors["position_groups"]["OTHER_OUTFIELD"])
        levels = {d: float(cfg["relevance_levels"][d]) for d in DIMENSIONS}
        required = list(cfg.get("required_dimensions", []))
        score, conf, n_dims, available = perf14.weighted_row_score(row, levels, dim_cols)
        coverage.loc[idx] = n_dims
        fallback_count.loc[idx] = sum(
            1
            for d in available
            if row.get(f"dimension_evidence_source__{d}") == "CONTRIBUTION_FALLBACK"
        )

        if n_dims < MIN_DIMENSIONS:
            statuses.loc[idx] = "INELIGIBLE_LT3_DIMENSIONS"
            continue
        missing_required = [d for d in required if d not in available]
        if missing_required:
            statuses.loc[idx] = "INELIGIBLE_MISSING_CORE_DIMENSION"
            continue
        if group == "OTHER_OUTFIELD":
            statuses.loc[idx] = "ROLE_UNAVAILABLE_NOT_PRODUCT_SCORE"
            continue

        scores.loc[idx] = score
        confidence.loc[idx] = conf
        statuses.loc[idx] = (
            "ELIGIBLE_WITH_CONTRIBUTION_FALLBACK"
            if fallback_count.loc[idx] > 0
            else "ELIGIBLE_DIRECT_SIGNED"
        )

    out["role_aware__dimension_coverage_count"] = coverage
    out["performance_score_position_experimental"] = scores
    out["score_evidence_confidence"] = confidence
    out["score_status"] = statuses
    out["fallback_dimension_count"] = fallback_count
    out["score_version"] = VERSION
    return out


def high_participation_no_score(db_path: Path, export: pd.DataFrame) -> list[dict]:
    eligible_counts = (
        export[
            export["position_group"].ne("OTHER_OUTFIELD")
            & export["performance_score_position_experimental"].notna()
        ]
        .groupby("player_id")
        .size()
        .rename("scored_matches")
    )
    outfield_ids = set(export["player_id"].astype(str))

    with duckdb.connect(str(db_path), read_only=True) as con:
        participation = con.execute(
            """
            SELECT pm.player_id, p.display_name AS player,
                   COUNT(*) FILTER (WHERE pm.minutes_played > 0) AS appearances,
                   SUM(CASE WHEN pm.started THEN 1 ELSE 0 END) AS starts,
                   SUM(pm.minutes_played) AS minutes
            FROM player_match pm
            JOIN players p ON p.player_id = pm.player_id
            GROUP BY pm.player_id, p.display_name
            """
        ).fetchdf()

    participation["player_id"] = participation["player_id"].astype(str)
    participation = participation[participation["player_id"].isin(outfield_ids)].copy()
    participation = participation.merge(
        eligible_counts,
        left_on="player_id",
        right_index=True,
        how="left",
    )
    participation["scored_matches"] = participation["scored_matches"].fillna(0).astype(int)
    flagged = participation[
        (pd.to_numeric(participation["starts"], errors="coerce").fillna(0) >= 10)
        & (participation["scored_matches"] == 0)
    ].sort_values(["starts", "minutes"], ascending=False)
    return flagged.to_dict(orient="records")


def build_experiment_v3(db_path: Path) -> tuple[dict, pd.DataFrame]:
    base_result, base_export = perf14v2.build_experiment_v2(db_path)
    before_eligible = int(
        (
            base_export["position_group"].ne("OTHER_OUTFIELD")
            & base_export["performance_score_position_experimental"].notna()
        ).sum()
    )

    enriched, fallback_meta = add_fallback_dimensions(base_export, db_path)
    export = rebuild_score(enriched)

    observable = export["position_group"].ne("OTHER_OUTFIELD")
    eligible = observable & export["performance_score_position_experimental"].notna()
    role_unavailable = export["position_mapping_status"].eq("role_unavailable_source_semantics")
    high_missing = high_participation_no_score(db_path, export)

    result = dict(base_result)
    result["version"] = VERSION
    result["status"] = "EXPERIMENTAL_COVERAGE_REPAIR"
    result["summary"] = dict(base_result["summary"])
    result["summary"].update(
        {
            "observable_mapped_role_rows": int(observable.sum()),
            "eligible_rows_observable_roles_before": before_eligible,
            "eligible_rows_observable_roles": int(eligible.sum()),
            "recovered_eligible_rows": int(eligible.sum()) - before_eligible,
            "coverage_rate_observable_roles": float(eligible.sum() / observable.sum()) if observable.any() else None,
            "source_role_unavailable_rows": int(role_unavailable.sum()),
            "high_participation_outfield_players_without_score": len(high_missing),
            "conclusion": "CONTRIBUTION_FALLBACK_READY_FOR_LOCAL_VALIDATION",
        }
    )
    result["fallback_method"] = {
        "principle": "existing signed dimension first; successful-action contribution fallback only when that dimension is missing",
        "zero_semantics": "child success count can become zero only when observed parent attempts equal zero; all other NULLs remain NULL",
        "fallback_rows_by_dimension": fallback_meta["fallback_rows_by_dimension"],
        "normalization": fallback_meta["normalization"],
        "high_participation_players_without_score": high_missing,
    }
    result["guardrails"] = list(base_result.get("guardrails", [])) + [
        "Contribution fallbacks do not redefine context-dependent attempt volume as universally good.",
        "Fallback dimensions are explicitly tagged and never hide provenance.",
        "OTHER_OUTFIELD/substitute role-unavailable rows remain outside the product score.",
    ]

    keep = [
        "match_id", "player_id", "primary_role", "raw_source_position",
        "position_group", "position_mapping_status",
        "role_aware__dimension_coverage_count",
        *[f"role_aware__dimension__{d}" for d in DIMENSIONS],
        *[f"dimension_evidence_source__{d}" for d in DIMENSIONS],
        "performance_score_position_experimental", "score_evidence_confidence",
        "fallback_dimension_count", "score_status", "score_version",
    ]
    export = export[keep].copy()
    return result, export


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="PERF-15 contribution fallback coverage repair")
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "football_performance.duckdb")
    args = parser.parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    result, export = build_experiment_v3(db_path)
    s = result["summary"]
    print("PERF-15 CONTRIBUTION FALLBACK: COMPLETE")
    print(f"version={VERSION}")
    print(f"db={db_path}")
    print(f"observable_role_rows={s['observable_mapped_role_rows']}")
    print(f"eligible_before={s['eligible_rows_observable_roles_before']}")
    print(f"eligible_after={s['eligible_rows_observable_roles']}")
    print(f"recovered={s['recovered_eligible_rows']}")
    print(f"coverage_observable_roles={s['coverage_rate_observable_roles']:.4f}")
    print(f"source_role_unavailable_rows={s['source_role_unavailable_rows']}")
    print(f"high_participation_without_score={s['high_participation_outfield_players_without_score']}")
    for dim, rows in result["fallback_method"]["fallback_rows_by_dimension"].items():
        print(f"fallback_{dim}={rows}")
    for row in result["fallback_method"]["high_participation_players_without_score"]:
        print(
            "NO_SCORE_HIGH_PARTICIPATION: "
            f"{row['player']} appearances={row['appearances']} starts={row['starts']} minutes={row['minutes']}"
        )

    out_dir = Path(__file__).with_name("output")
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "performance_position_score_experiment_v3.json"
    csv_path = out_dir / "performance_position_score_experiment_v3.csv"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    export.to_csv(csv_path, index=False)
    print(f"json={json_path}")
    print(f"csv={csv_path}")


if __name__ == "__main__":
    main()
