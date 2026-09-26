"""PERF-18 — unified Match Rating V5 candidate.

Combines the validated rating branches without changing the active production access layer:
- position-aware outfield V4.1 for rows with reliable role context;
- separate goalkeeper model using the final validated 90% shot-stopping / 10% distribution scheme;
- explicit V2 fallback only for historical OTHER_OUTFIELD rows where role context is unavailable.

The fallback is a coverage policy, not an invented role. Future Collector data requires role context,
so the fallback is expected to be historical/demo-only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ANALYTICS_DIR = ROOT / "analytics"
DSAI_DIR = ROOT / "dsai"
for p in [ANALYTICS_DIR, DSAI_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import build_match_rating_gk_experimental as gk  # noqa: E402
import perf18_goalkeeper_final_gate as gkgate  # noqa: E402
from perf18_opta_points_benchmark_audit import discover_input_dir  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_v5_candidate"
DEFAULT_GK_GATE = ROOT / "dsai" / "output" / "perf18_gk_final_gate" / "goalkeeper_final_gate.json"

V2_VERSION = "match_rating_v0.2-candidate"
OUTFIELD_VERSION = "match_rating_v0.4.1-experimental-onpitch"
FINAL_VERSION = "match_rating_v0.5-candidate"
SHOT_WEIGHT = 0.90
DIST_WEIGHT = 0.10

RATING_COLUMNS = [
    "match_id", "match_date", "team_id", "player_id", "minutes_played", "started",
    "primary_role", "position_group", "position_mapping_status",
    "attacking_threat", "creation_progression", "defensive_contribution",
    "finishing", "discipline", "fallback_dimension_count", "rating_path",
    "match_rating_100", "match_rating_10", "match_rating_confidence",
    "match_rating_dimensions_used", "match_rating_context", "match_rating_status",
    "match_rating_version", "source_score_version",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build unified PERF-18 Match Rating V5 candidate")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--gk-gate", type=Path, default=DEFAULT_GK_GATE)
    p.add_argument("--min-reference-minutes", type=float, default=30.0)
    p.add_argument("--max-pca-fit-rows", type=int, default=200000)
    return p.parse_args()


def load_gate(path: Path) -> dict[str, Any]:
    gate_path = path.expanduser().resolve()
    if not gate_path.exists():
        raise FileNotFoundError(
            f"Goalkeeper final-gate artifact not found: {gate_path}. "
            "Run dsai/perf18_goalkeeper_final_gate.py first."
        )
    data = json.loads(gate_path.read_text(encoding="utf-8"))
    if not bool(data.get("overall_gate")):
        raise RuntimeError("Goalkeeper final gate is not PASS")
    shot = float(data.get("selected_shot_weight"))
    dist = float(data.get("selected_distribution_weight"))
    if abs(shot - SHOT_WEIGHT) > 1e-12 or abs(dist - DIST_WEIGHT) > 1e-12:
        raise RuntimeError(f"Unexpected validated GK weights: shot={shot}, distribution={dist}")
    return data


def load_existing_routes(db: Path) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    with duckdb.connect(str(db), read_only=True) as con:
        outfield = con.execute(
            f"""
            SELECT {', '.join(RATING_COLUMNS)}
            FROM player_match_rating
            WHERE match_rating_version=?
            ORDER BY match_date, match_id, player_id
            """,
            [OUTFIELD_VERSION],
        ).df()
        fallback = con.execute(
            f"""
            SELECT {', '.join(RATING_COLUMNS)}
            FROM player_match_rating
            WHERE match_rating_version=? AND position_group='OTHER_OUTFIELD'
            ORDER BY match_date, match_id, player_id
            """,
            [V2_VERSION],
        ).df()
        expected_played = int(con.execute(
            "SELECT COUNT(*) FROM player_match WHERE minutes_played>0"
        ).fetchone()[0])
    if outfield.empty:
        raise RuntimeError("V4.1 outfield candidate not materialized")
    if fallback.empty:
        raise RuntimeError("No V2 OTHER_OUTFIELD fallback rows found")
    return outfield, fallback, expected_played


def build_final_goalkeeper(
    db: Path,
    input_dir: Path,
    min_reference_minutes: float,
    max_pca_fit_rows: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    local = gk.load_local(db)
    if local.empty or local["match_date"].isna().any():
        raise RuntimeError("Local goalkeeper rows/date coverage unavailable")

    cutoff = pd.Timestamp(local["match_date"].min())
    reference, _ = gk.load_reference(input_dir, cutoff, min_reference_minutes)
    train, valid, test, split_info = gkgate.split_dates(reference)

    # Reproduce the exact methodology that passed the final gate: TRAIN-only reference
    # and calibration, validated weight locked at 90/10, untouched VALID/TEST kept for audit.
    ref = gkgate.fit_reference(train, max_pca_fit_rows)
    comp_train = gkgate.components(train, ref)
    calibration = gkgate.fit_calibration(train, comp_train, SHOT_WEIGHT)
    comp_local = gkgate.components(local, ref)
    score = gkgate.score(local, comp_local, SHOT_WEIGHT, calibration)

    out = pd.DataFrame(index=local.index)
    out["match_id"] = local["match_id"]
    out["match_date"] = local["match_date"]
    out["team_id"] = local["team_id"]
    out["player_id"] = local["player_id"]
    out["minutes_played"] = local["minutes_played"]
    out["started"] = local["started"]
    out["primary_role"] = local["primary_role"]
    out["position_group"] = "GK"
    out["position_mapping_status"] = "LOCAL_ROLE_GK"
    out["attacking_threat"] = np.nan
    out["creation_progression"] = gk._display_z(comp_local["dist_z"])
    out["defensive_contribution"] = gk._display_z(comp_local["shot_z"])
    out["finishing"] = np.nan
    out["discipline"] = (50.0 + 20.0 * gk._public_anchor(local)).clip(0.0, 100.0)
    out["fallback_dimension_count"] = 0
    out["rating_path"] = "GOALKEEPER_PERF18_SHOT90_DIST10"
    out["match_rating_100"] = ((score - 3.0) * (100.0 / 7.0)).clip(0.0, 100.0)
    out["match_rating_10"] = score
    out["match_rating_confidence"] = gk._confidence(local, comp_local, ref["prior_strength_shots"])
    out["match_rating_dimensions_used"] = 3
    out["match_rating_context"] = "GOALKEEPER_SEPARATE_PRO_REFERENCE_SHOT90_DIST10"
    out["match_rating_status"] = "V5_CANDIDATE_GOALKEEPER_RATED"
    out["match_rating_version"] = FINAL_VERSION
    out["source_score_version"] = "perf18_gk_final_gate_shot90_dist10"

    meta = {
        "local_rows": int(len(out)),
        "local_matches": int(out["match_id"].nunique()),
        "reference_cutoff_before": str(cutoff.date()),
        "reference_split": split_info,
        "reference_rows": {
            "train": int(len(train)), "valid": int(len(valid)), "test": int(len(test))
        },
        "shot_weight": SHOT_WEIGHT,
        "distribution_weight": DIST_WEIGHT,
        "calibration": calibration,
        "prior_save_rate": float(ref["prior_save_rate"]),
        "prior_strength_shots": float(ref["prior_strength_shots"]),
    }
    return out[RATING_COLUMNS].reset_index(drop=True), meta


def build_candidate(
    db: Path,
    input_dir: Path,
    gate: dict[str, Any],
    min_reference_minutes: float,
    max_pca_fit_rows: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    outfield, fallback, expected_played = load_existing_routes(db)

    outfield = outfield.copy()
    outfield["match_rating_version"] = FINAL_VERSION
    outfield["match_rating_status"] = "V5_CANDIDATE_OUTFIELD_RATED"
    outfield["source_score_version"] = "perf18_v4_1_validated_outfield"

    fallback = fallback.copy()
    fallback["rating_path"] = "OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2"
    fallback["match_rating_context"] = "ROLE_UNAVAILABLE_V2_FALLBACK"
    fallback["match_rating_status"] = "V5_CANDIDATE_ROLE_UNAVAILABLE_FALLBACK"
    fallback["match_rating_version"] = FINAL_VERSION
    fallback["source_score_version"] = "match_rating_v0.2_fallback_role_unavailable"

    goalkeeper, gk_meta = build_final_goalkeeper(
        db, input_dir, min_reference_minutes, max_pca_fit_rows
    )

    final = pd.concat([outfield[RATING_COLUMNS], goalkeeper, fallback[RATING_COLUMNS]], ignore_index=True)
    if final.duplicated(["match_id", "player_id"]).any():
        dup = final.loc[final.duplicated(["match_id", "player_id"], keep=False),
                        ["match_id", "player_id", "rating_path"]]
        raise RuntimeError("Duplicate unified V5 rows:\n" + dup.head(20).to_string(index=False))
    if len(final) != expected_played:
        raise RuntimeError(
            f"Unified V5 coverage mismatch: {len(final)}/{expected_played}; "
            f"outfield={len(outfield)} gk={len(goalkeeper)} fallback={len(fallback)}"
        )

    metadata = {
        "version": FINAL_VERSION,
        "production_status": "CANDIDATE_NOT_ACTIVE",
        "route_counts": {
            "position_aware_outfield_v4_1": int(len(outfield)),
            "goalkeeper_shot90_dist10": int(len(goalkeeper)),
            "role_unavailable_v2_fallback": int(len(fallback)),
            "total": int(len(final)),
        },
        "expected_played_rows": int(expected_played),
        "outfield_source_version": OUTFIELD_VERSION,
        "fallback_source_version": V2_VERSION,
        "fallback_policy": (
            "Historical/demo rows without reliable role context retain the validated V2 value. "
            "No role is invented; rows are explicitly flagged as fallback."
        ),
        "goalkeeper": gk_meta,
        "goalkeeper_final_gate": {
            "overall_gate": bool(gate.get("overall_gate")),
            "selected_shot_weight": float(gate["selected_shot_weight"]),
            "selected_distribution_weight": float(gate["selected_distribution_weight"]),
            "test_metrics_vs_opta_points": gate.get("test_metrics_vs_opta_points"),
            "monotonicity_gate": bool(gate.get("monotonicity_gate")),
            "local_weight_sensitivity_gate": bool(gate.get("local_weight_sensitivity_gate")),
        },
    }
    return final.sort_values(["match_date", "match_id", "player_id"]).reset_index(drop=True), metadata


def materialize(db: Path, frame: pd.DataFrame) -> None:
    with duckdb.connect(str(db)) as con:
        con.execute("DELETE FROM player_match_rating WHERE match_rating_version=?", [FINAL_VERSION])
        con.register("v5_df", frame)
        con.execute(
            f"INSERT INTO player_match_rating ({', '.join(RATING_COLUMNS)}) "
            f"SELECT {', '.join(RATING_COLUMNS)} FROM v5_df"
        )
        con.unregister("v5_df")


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)
    input_dir = discover_input_dir(args.input_dir)
    gate = load_gate(args.gk_gate)
    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    frame, metadata = build_candidate(
        db,
        input_dir,
        gate,
        float(args.min_reference_minutes),
        int(args.max_pca_fit_rows),
    )
    materialize(db, frame)
    artifact = out_dir / "match_rating_v5_candidate_metadata.json"
    artifact.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    print("PERF-18 UNIFIED MATCH RATING V5 CANDIDATE: MATERIALIZED")
    print(f"version={FINAL_VERSION}")
    print(f"rows={len(frame)} matches={frame['match_id'].nunique()}")
    print("route_counts=" + str(metadata["route_counts"]))
    print(f"mean={frame['match_rating_10'].mean():.3f} median={frame['match_rating_10'].median():.3f}")
    print(f"min={frame['match_rating_10'].min():.3f} max={frame['match_rating_10'].max():.3f}")
    print("gk_weights=shot:0.90 distribution:0.10")
    print(f"artifact={artifact}")
    print("V2 remains active; no app/attention/report access layer was changed.")


if __name__ == "__main__":
    main()
