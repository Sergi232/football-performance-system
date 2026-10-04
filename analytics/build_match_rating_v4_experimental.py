"""PERF-18 — local Match Rating V4 experimental outfield candidate.

Applies the validated anchored, position-aware PERF-18 architecture to the local
FPS demo database.

Important:
- outfield only; goalkeepers remain on their separate modelling path;
- professional reference rows are restricted to dates STRICTLY before the first
  local demo match to avoid future leakage;
- inputs are raw Collector-compatible variables only;
- Opta Points is used only inside the professional reference calibration layer;
- goals_conceded is excluded from outfield scoring until on-pitch context is valid;
- production V2 remains active. This script materializes an experimental version.
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
DSAI_DIR = ROOT / "dsai"
if str(DSAI_DIR) not in sys.path:
    sys.path.insert(0, str(DSAI_DIR))

from perf18_opta_points_benchmark_audit import discover_input_dir  # noqa: E402
import perf18_position_aware_rating_candidate_v2 as perf18_pos  # noqa: E402
from perf18_outfield_anchored_candidate import (  # noqa: E402
    ROLE_ORDER,
    fit_role_model,
    fit_calibration,
    rating,
    structural_dimensions,
)

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_v4_local"
V2_VERSION = "match_rating_v0.2-candidate"
V4_VERSION = "match_rating_v0.4-experimental-outfield"
SOURCE_VERSION = "perf18_anchored_prof_reference_pre_local_cutoff"

RAW_COLUMNS = [
    "passes_total", "passes_completed", "assists",
    "long_balls_total", "long_balls_completed",
    "crosses_total", "crosses_completed",
    "dribbles_total", "dribbles_won", "turnovers", "dispossessed",
    "shots_total", "shots_on_target", "shots_blocked", "goals",
    "tackles_total", "tackles_won", "interceptions", "blocked_passes", "clearances",
    "fouls_committed", "fouls_received", "yellow_cards", "red_cards",
    "penalties_conceded", "penalties_won",
]

DIMENSION_COLUMN_MAP = {
    "attacking_threat": "possession_1v1",
    "creation_progression": "passing_creation",
    "defensive_contribution": "defending",
    "finishing": "shooting",
    "discipline": "discipline_context",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build PERF-18 Match Rating V4 experimental outfield candidate")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--frozen-artifact", type=Path, default=None)
    return p.parse_args()


def _norm(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def map_local_role(primary_role: Any, broad_group: Any) -> tuple[str, str]:
    """Map source-supported local role text to PERF-18 seven-role taxonomy."""
    text = _norm(primary_role)
    broad = str(broad_group or "").strip().upper()
    # Official Collector V1.1 labels are observed source labels, not inferred
    # positions.  These aliases only translate those enumerated UI values to
    # the pre-existing seven-role taxonomy.
    collector_aliases = {
        "portero": "goalkeeper", "central": "central defender",
        "lateral": "full back", "carrilero": "wing back",
        "mediocentro defensivo": "defensive midfielder", "mediocentro": "central midfielder",
        "interior": "central midfielder", "mediapunta": "attacking midfielder",
        "extremo": "winger", "delantero": "striker",
    }
    text = collector_aliases.get(text, text)
    if "goalkeeper" in text or broad == "GK":
        return "GK", "LOCAL_ROLE_GK"

    parts = [p.strip() for p in text.split("|")]
    pos = parts[0] if parts else text
    side = parts[1] if len(parts) > 1 else ""
    wide = side in {"left", "right", "wide"}
    centre = side in {"centre", "center", "central"}

    if "wing back" in pos or "full back" in pos:
        return "FB", "LOCAL_ROLE_EXACT"
    if "central defender" in pos:
        return "CB", "LOCAL_ROLE_EXACT"
    if "defender" in pos:
        if wide:
            return "FB", "LOCAL_ROLE_EXACT"
        if centre:
            return "CB", "LOCAL_ROLE_EXACT"
        if broad == "FB_WB":
            return "FB", "LOCAL_ROLE_BROAD_FALLBACK"
        return "CB", "LOCAL_ROLE_BROAD_FALLBACK"
    if "defensive midfielder" in pos:
        return "DM", "LOCAL_ROLE_EXACT"
    if "attacking midfielder" in pos:
        return ("W", "LOCAL_ROLE_EXACT") if wide else ("AM", "LOCAL_ROLE_EXACT")
    if pos == "midfielder" or "central midfielder" in pos or "centre midfielder" in pos:
        return ("W", "LOCAL_ROLE_EXACT") if wide else ("CM", "LOCAL_ROLE_EXACT")
    if "winger" in pos or "wide midfielder" in pos or "wide forward" in pos:
        return "W", "LOCAL_ROLE_EXACT"
    if "striker" in pos or "centre forward" in pos or "center forward" in pos or pos == "forward":
        return "ST", "LOCAL_ROLE_EXACT"

    fallback = {
        "CB": "CB",
        "FB_WB": "FB",
        "DM_CM": "CM",
        "AM_W": "AM",
        "ST": "ST",
    }.get(broad)
    if fallback:
        return fallback, "LOCAL_ROLE_BROAD_FALLBACK"
    return "UNKNOWN", "LOCAL_ROLE_UNAVAILABLE"


def load_local_source(db_path: Path) -> pd.DataFrame:
    raw_sql = ",\n               ".join(f"rs.{c}" for c in RAW_COLUMNS)
    with duckdb.connect(str(db_path), read_only=True) as con:
        cols = {r[1] for r in con.execute("PRAGMA table_info('player_match_raw_stats')").fetchall()}
        missing = sorted(set(RAW_COLUMNS) - cols)
        if missing:
            raise RuntimeError(
                "Raw stats schema is not ready for V4; missing=" + str(missing)
                + ". Run data/init_database.py and DATA-04 v3 importer first."
            )
        frame = con.execute(
            f"""
            SELECT
                pm.match_id, m.match_date, pm.team_id, pm.player_id,
                pm.minutes_played, pm.started, pm.primary_role,
                COALESCE(v2.position_group, 'OTHER_OUTFIELD') AS broad_position_group,
                COALESCE(v2.position_mapping_status, 'NO_V2_POSITION_METADATA') AS prior_position_mapping_status,
                {raw_sql}
            FROM player_match pm
            JOIN matches m ON m.match_id=pm.match_id
            LEFT JOIN player_match_raw_stats rs
              ON rs.match_id=pm.match_id AND rs.team_id=pm.team_id AND rs.player_id=pm.player_id
            LEFT JOIN player_match_rating v2
              ON v2.match_id=pm.match_id AND v2.team_id=pm.team_id AND v2.player_id=pm.player_id
             AND v2.match_rating_version=?
            WHERE pm.minutes_played > 0
            ORDER BY m.match_date, pm.match_id, pm.player_id
            """,
            [V2_VERSION],
        ).df()
    mapped = frame.apply(
        lambda r: map_local_role(r["primary_role"], r["broad_position_group"]), axis=1
    )
    frame["position_group"] = [x[0] for x in mapped]
    frame["position_mapping_status"] = [x[1] for x in mapped]
    frame["match_date"] = pd.to_datetime(frame["match_date"], errors="coerce")
    return frame


def dimension_display(z: pd.Series) -> pd.Series:
    # Presentation-only standardized dimension scale. Rating computation uses the
    # underlying z-score directly; this transformation does not feed back into it.
    return (50.0 + 15.0 * pd.to_numeric(z, errors="coerce")).clip(0.0, 100.0)


def confidence_pct(frame: pd.DataFrame) -> pd.Series:
    raw_coverage = frame[RAW_COLUMNS].notna().mean(axis=1).astype(float)
    minutes = pd.to_numeric(frame["minutes_played"], errors="coerce").fillna(0.0)
    exposure = (minutes / 60.0).clip(0.0, 1.0)
    exact = frame["position_mapping_status"].eq("LOCAL_ROLE_EXACT").astype(float)
    conf = 100.0 * (0.55 * raw_coverage + 0.30 * exposure + 0.15 * exact)
    return conf.clip(0.0, 100.0)


def build_reference_models(input_dir: Path, cutoff: pd.Timestamp) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    reference = perf18_pos.build_frame(input_dir, 30.0)
    reference["match_date"] = pd.to_datetime(reference["match_date"], errors="coerce")
    reference = reference.loc[reference["match_date"].notna() & (reference["match_date"] < cutoff)].copy()
    models: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {}
    for role in ROLE_ORDER:
        tr = reference.loc[reference["position_group"] == role].copy()
        if len(tr) < 1000:
            raise RuntimeError(f"Insufficient pre-cutoff professional reference rows for {role}: {len(tr)}")
        model = fit_role_model(tr, role)
        intercept, slope = fit_calibration(tr, model)
        model["calibration"] = {"intercept": intercept, "slope": slope}
        models[role] = model
        counts[role] = int(len(tr))
    return models, counts


def build_candidate(db_path: Path, input_dir: Path | None, frozen_artifact: Path | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    local = load_local_source(db_path)
    if local["match_date"].isna().any():
        raise RuntimeError("Local match dates contain NULL; leakage-safe reference cutoff cannot be guaranteed")
    cutoff = pd.Timestamp(local["match_date"].min())
    if frozen_artifact is not None:
        frozen = json.loads(frozen_artifact.expanduser().resolve().read_text(encoding="utf-8"))
        if frozen.get("artifact_version") != "perf18_v4_outfield_reference_frozen_v1":
            raise RuntimeError("Unsupported frozen V4 reference artifact")
        models = frozen["models"]
        reference_counts = frozen["reference_rows_by_role"]
    else:
        if input_dir is None:
            raise RuntimeError("V4 calibration needs --input-dir or --frozen-artifact")
        models, reference_counts = build_reference_models(input_dir, cutoff)

    out_parts: list[pd.DataFrame] = []
    for role in ROLE_ORDER:
        part = local.loc[local["position_group"] == role].copy()
        if part.empty:
            continue
        model = models[role]
        dims = structural_dimensions(part, model)
        scores = rating(part, model)
        out = pd.DataFrame(index=part.index)
        out["match_id"] = part["match_id"]
        out["match_date"] = part["match_date"]
        out["team_id"] = part["team_id"]
        out["player_id"] = part["player_id"]
        out["minutes_played"] = part["minutes_played"]
        out["started"] = part["started"]
        out["primary_role"] = part["primary_role"]
        out["position_group"] = role
        out["position_mapping_status"] = part["position_mapping_status"]
        for target_col, source_dim in DIMENSION_COLUMN_MAP.items():
            out[target_col] = dimension_display(dims[source_dim])
        out["fallback_dimension_count"] = 0
        out["rating_path"] = "OUTFIELD_PERF18_ANCHORED"
        out["match_rating_10"] = scores.astype(float)
        out["match_rating_100"] = ((scores - 3.0) * (100.0 / 7.0)).clip(0.0, 100.0)
        out["match_rating_confidence"] = confidence_pct(part)
        out["match_rating_dimensions_used"] = 5
        out["match_rating_context"] = np.where(
            part["position_mapping_status"].eq("LOCAL_ROLE_EXACT"),
            "POSITION_SPECIFIC_PRO_REFERENCE",
            "POSITION_BROAD_FALLBACK_PRO_REFERENCE",
        )
        out["match_rating_status"] = "V4_EXPERIMENTAL_OUTFIELD_RATED"
        out["match_rating_version"] = V4_VERSION
        out["source_score_version"] = SOURCE_VERSION
        out_parts.append(out)

    frame = pd.concat(out_parts, ignore_index=True) if out_parts else pd.DataFrame()
    if frame.empty:
        raise RuntimeError("No outfield rows were mapped for V4")
    if frame.duplicated(["match_id", "player_id"]).any():
        raise RuntimeError("Duplicate V4 match/player rows")

    metadata = {
        "version": V4_VERSION,
        "source_version": SOURCE_VERSION,
        "local_first_match_date": str(cutoff.date()),
        "professional_reference_policy": "match_date strictly before local_first_match_date",
        "professional_reference_rows_by_role": reference_counts,
        "models": models,
        "local_rows": int(len(frame)),
        "local_matches": int(frame["match_id"].nunique()),
        "role_counts": {str(k): int(v) for k, v in frame["position_group"].value_counts().items()},
        "position_mapping_status_counts": {
            str(k): int(v) for k, v in frame["position_mapping_status"].value_counts().items()
        },
        "goalkeeper_policy": "excluded_from_v4_outfield_candidate",
        "goals_conceded_policy": "excluded_from_outfield_rating_until_on_pitch_context_validated",
        "production_status": "EXPERIMENT_ONLY_V2_REMAINS_ACTIVE",
    }
    return frame, metadata


def materialize(db_path: Path, frame: pd.DataFrame) -> None:
    with duckdb.connect(str(db_path)) as con:
        exists = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='main' AND table_name='player_match_rating'"
        ).fetchone()[0]
        if not exists:
            raise RuntimeError("player_match_rating missing")
        con.execute("DELETE FROM player_match_rating WHERE match_rating_version=?", [V4_VERSION])
        con.register("v4_df", frame)
        cols = list(frame.columns)
        con.execute(
            f"INSERT INTO player_match_rating ({', '.join(cols)}) SELECT {', '.join(cols)} FROM v4_df"
        )
        con.unregister("v4_df")


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    input_dir = None if args.frozen_artifact is not None else discover_input_dir(args.input_dir)
    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    frame, metadata = build_candidate(db_path, input_dir, args.frozen_artifact)
    materialize(db_path, frame)
    artifact = out_dir / "match_rating_v4_local_metadata.json"
    artifact.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.frozen_artifact is None:
        frozen = {
            "artifact_version": "perf18_v4_outfield_reference_frozen_v1",
            "source_version": SOURCE_VERSION,
            "reference_cutoff_before": metadata["local_first_match_date"],
            "reference_rows_by_role": metadata["professional_reference_rows_by_role"],
            "models": metadata["models"],
        }
        (out_dir / "match_rating_v4_reference_frozen.json").write_text(
            json.dumps(frozen, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print("PERF-18 MATCH RATING V4 EXPERIMENTAL OUTFIELD: MATERIALIZED")
    print(f"version={V4_VERSION}")
    print(f"rows={len(frame)} matches={frame['match_id'].nunique()}")
    print(f"mean={frame['match_rating_10'].mean():.3f} median={frame['match_rating_10'].median():.3f}")
    print(f"min={frame['match_rating_10'].min():.3f} max={frame['match_rating_10'].max():.3f}")
    print("role_counts=" + str(metadata["role_counts"]))
    print("mapping_status=" + str(metadata["position_mapping_status_counts"]))
    print("reference_rows=" + str(metadata["professional_reference_rows_by_role"]))
    print(f"reference_cutoff_before={metadata['local_first_match_date']}")
    print("goalkeepers=EXCLUDED_SEPARATE_MODEL")
    print("goals_conceded=EXCLUDED_UNTIL_ON_PITCH_CONTEXT_VALIDATED")
    print(f"artifact={artifact}")
    print("V2 remains active; no production access layer was changed.")


if __name__ == "__main__":
    main()
