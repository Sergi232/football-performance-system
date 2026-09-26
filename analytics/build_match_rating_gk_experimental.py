"""PERF-18 — separate goalkeeper Match Rating candidate.

Goalkeepers are intentionally modelled independently from outfield players.

Architecture
------------
1. Professional pre-local-cutoff goalkeeper reference only (leakage-safe).
2. Shot-stopping quality = empirically shrunk save rate.
3. Distribution = goalkeeper-specific PCA of passing execution.
4. Shot-stopping and distribution are combined by a second PCA after both
   components are standardized. This avoids choosing an arbitrary 75/25 weight.
5. Public Opta Points is used only to calibrate the display scale and public
   decisive/disciplinary anchors. It is not treated as proprietary Player Rating.
6. Sparse penalty-conceded impact remains an explicit FPS hypothesis.

No production access layer is changed.
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
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DSAI_DIR = ROOT / "dsai"
if str(DSAI_DIR) not in sys.path:
    sys.path.insert(0, str(DSAI_DIR))

from perf18_opta_points_benchmark_audit import (  # noqa: E402
    ALIASES,
    WEIGHTS_GK,
    choose_aliases,
    discover_input_dir,
    sql_path,
)
import perf18_position_aware_rating_candidate_v2 as perf18_pos  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_gk_local"
V2_VERSION = "match_rating_v0.2-candidate"
GK_VERSION = "match_rating_v0.4.2-experimental-gk"
SOURCE_VERSION = "perf18_gk_latent_prof_reference_pre_local_cutoff"

GK_SOURCE = {
    "passes_total": "totalPass",
    "passes_completed": "accuratePass",
    "long_balls_total": "totalLongBalls",
    "long_balls_completed": "accurateLongBalls",
    "goals": "goals",
    "assists": "goalAssist",
    "fouls_committed": "fouls",
    "fouls_received": "wasFouled",
    "yellow_cards": "yellowCard",
    "red_cards": "redCard",
    "penalties_conceded": "penaltyConceded",
    "penalties_won": "penaltyWon",
    "saves": "saves",
    "goals_conceded": "goalsConceded",
}
LOCAL_COLUMNS = list(GK_SOURCE)
DIST_FEATURES = [
    "pass_accuracy",
    "long_ball_accuracy",
    "passes_completed_p90",
    "long_balls_completed_p90",
]
PUBLIC_SPARSE_ANCHORS = {
    "goals": +1.00,
    "assists": +0.60,
    "fouls_received": +0.10,
    "fouls_committed": -0.10,
    "yellow_cards": -0.20,
    "red_cards": -0.50,
    "penalties_won": +0.40,
}
FPS_HYPOTHESIS_ANCHORS = {"penalties_conceded": -0.40}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build PERF-18 goalkeeper Match Rating candidate")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--min-reference-minutes", type=float, default=30.0)
    p.add_argument("--max-pca-fit-rows", type=int, default=200000)
    return p.parse_args()


def _is_gk(position: object) -> bool:
    if position is None or pd.isna(position):
        return False
    t = str(position).strip().lower()
    return t == "gk" or "goalkeeper" in t or t == "keeper"


def _safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    n = pd.to_numeric(num, errors="coerce")
    d = pd.to_numeric(den, errors="coerce")
    return (n / d.where(d > 0)).clip(0.0, 1.0)


def _zero_counts(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for c in LOCAL_COLUMNS:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)
    out["minutes_played"] = pd.to_numeric(out["minutes_played"], errors="coerce")
    return out


def _add_features(frame: pd.DataFrame, prior_rate: float, prior_strength: float) -> pd.DataFrame:
    out = _zero_counts(frame)
    mins = out["minutes_played"].where(out["minutes_played"] > 0)
    factor = 90.0 / mins
    out["passes_completed_p90"] = out["passes_completed"] * factor
    out["long_balls_completed_p90"] = out["long_balls_completed"] * factor
    out["pass_accuracy"] = _safe_ratio(out["passes_completed"], out["passes_total"])
    out["long_ball_accuracy"] = _safe_ratio(out["long_balls_completed"], out["long_balls_total"])
    out["shots_faced_proxy"] = out["saves"] + out["goals_conceded"]
    out["raw_save_rate"] = _safe_ratio(out["saves"], out["shots_faced_proxy"])
    out["shrunk_save_rate"] = (
        out["saves"] + float(prior_rate) * float(prior_strength)
    ) / (out["shots_faced_proxy"] + float(prior_strength))
    return out


def _public_anchor(frame: pd.DataFrame) -> pd.Series:
    f = _zero_counts(frame)
    out = pd.Series(0.0, index=f.index, dtype=float)
    for feature, weight in PUBLIC_SPARSE_ANCHORS.items():
        out = out + f[feature] * float(weight)
    return out


def _fps_anchor(frame: pd.DataFrame) -> pd.Series:
    f = _zero_counts(frame)
    out = pd.Series(0.0, index=f.index, dtype=float)
    for feature, weight in FPS_HYPOTHESIS_ANCHORS.items():
        out = out + f[feature] * float(weight)
    return out


def _fit_distribution(reference: pd.DataFrame, max_rows: int) -> dict[str, Any]:
    x = reference[DIST_FEATURES].copy()
    medians = x.median(numeric_only=True)
    x = x.fillna(medians)
    fit = x.sample(int(max_rows), random_state=18) if len(x) > int(max_rows) else x
    scaler = StandardScaler().fit(fit)
    z_fit = scaler.transform(fit)
    pca = PCA(n_components=1, random_state=18).fit(z_fit)
    pc = pca.transform(z_fit).reshape(-1)
    desirability = np.nanmean(z_fit, axis=1)
    corr = float(np.corrcoef(pc, desirability)[0, 1])
    if np.isfinite(corr) and corr < 0:
        pca.components_[0] *= -1.0
        pc *= -1.0
        corr = -corr
    return {
        "features": DIST_FEATURES,
        "medians": {c: float(medians[c]) for c in DIST_FEATURES},
        "scaler_mean": {c: float(v) for c, v in zip(DIST_FEATURES, scaler.mean_)},
        "scaler_scale": {c: float(v) for c, v in zip(DIST_FEATURES, scaler.scale_)},
        "loadings": {c: float(v) for c, v in zip(DIST_FEATURES, pca.components_[0])},
        "explained_variance_ratio": float(pca.explained_variance_ratio_[0]),
        "orientation_corr": corr if np.isfinite(corr) else None,
    }


def _apply_distribution(frame: pd.DataFrame, model: dict[str, Any]) -> pd.Series:
    x = frame[model["features"]].copy()
    for c in model["features"]:
        x[c] = pd.to_numeric(x[c], errors="coerce").fillna(float(model["medians"][c]))
    z = np.column_stack([
        (x[c].to_numpy(dtype=float) - float(model["scaler_mean"][c]))
        / max(float(model["scaler_scale"][c]), 1e-9)
        for c in model["features"]
    ])
    load = np.array([float(model["loadings"][c]) for c in model["features"]], dtype=float)
    return pd.Series(z @ load, index=frame.index, dtype=float)


def _full_opta_points_target(frame: pd.DataFrame, opta_map: dict[str, str]) -> pd.Series:
    target = pd.Series(5.5, index=frame.index, dtype=float)
    for logical, weight in WEIGHTS_GK.items():
        src = opta_map[logical]
        target = target + pd.to_numeric(frame[src], errors="coerce").fillna(0.0) * float(weight)
    return target.clip(3.0, 10.0)


def load_reference(input_dir: Path, cutoff: pd.Timestamp, min_minutes: float) -> tuple[pd.DataFrame, dict[str, str]]:
    stats = input_dir / "opta_player_stats.parquet"
    lineups = input_dir / "opta_lineups.parquet"
    fixtures = input_dir / "opta_fixtures.parquet"
    with duckdb.connect() as con:
        schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{sql_path(stats)}')").df()
        available = schema["column_name"].astype(str).tolist()
        opta_map, missing = choose_aliases(available)
        if missing:
            raise RuntimeError("Complete Opta Points benchmark unavailable: " + str(missing))
        needed = set(GK_SOURCE.values()) | set(opta_map.values())
        missing_gk = sorted(v for v in GK_SOURCE.values() if v not in set(available))
        if missing_gk:
            raise RuntimeError("Goalkeeper source columns missing: " + str(missing_gk))
        date_expr = perf18_pos.fixture_date_expr(con, fixtures)
        select_sources = ",\n                ".join(
            f'TRY_CAST(s."{c}" AS DOUBLE) AS "{c}"' for c in sorted(needed)
        )
        q = f'''
            SELECT
                CAST(s.match_id AS VARCHAR) AS match_id,
                CAST(s.team_id AS VARCHAR) AS team_id,
                CAST(s.player_id AS VARCHAR) AS player_id,
                TRY_CAST(s.minsPlayed AS DOUBLE) AS minutes_played,
                l.position,
                {date_expr} AS match_date,
                {select_sources}
            FROM read_parquet('{sql_path(stats)}') s
            LEFT JOIN read_parquet('{sql_path(lineups)}') l
              ON CAST(l.match_id AS VARCHAR)=CAST(s.match_id AS VARCHAR)
             AND CAST(l.team_id AS VARCHAR)=CAST(s.team_id AS VARCHAR)
             AND CAST(l.player_id AS VARCHAR)=CAST(s.player_id AS VARCHAR)
            LEFT JOIN read_parquet('{sql_path(fixtures)}') f
              ON CAST(f.match_id AS VARCHAR)=CAST(s.match_id AS VARCHAR)
            WHERE TRY_CAST(s.minsPlayed AS DOUBLE) >= {float(min_minutes)}
        '''
        ref = con.execute(q).df()
    ref = ref.drop_duplicates(["match_id", "team_id", "player_id"], keep="first")
    ref["match_date"] = pd.to_datetime(ref["match_date"], errors="coerce")
    ref = ref.loc[ref["match_date"].notna() & (ref["match_date"] < cutoff)].copy()
    ref = ref.loc[ref["position"].map(_is_gk)].copy()
    for logical, src in GK_SOURCE.items():
        ref[logical] = pd.to_numeric(ref[src], errors="coerce")
    ref["opta_points_target"] = _full_opta_points_target(ref, opta_map)
    return ref, opta_map


def load_local(db_path: Path) -> pd.DataFrame:
    raw_sql = ",\n               ".join(f"rs.{c}" for c in LOCAL_COLUMNS)
    with duckdb.connect(str(db_path), read_only=True) as con:
        frame = con.execute(
            f"""
            SELECT
                pm.match_id, m.match_date, pm.team_id, pm.player_id,
                pm.minutes_played, pm.started, pm.primary_role,
                {raw_sql}
            FROM player_match pm
            JOIN matches m ON m.match_id=pm.match_id
            LEFT JOIN player_match_raw_stats rs
              ON rs.match_id=pm.match_id AND rs.team_id=pm.team_id AND rs.player_id=pm.player_id
            LEFT JOIN player_match_rating v2
              ON v2.match_id=pm.match_id AND v2.team_id=pm.team_id AND v2.player_id=pm.player_id
             AND v2.match_rating_version=?
            WHERE pm.minutes_played > 0
              AND (v2.position_group='GK' OR lower(COALESCE(pm.primary_role,'')) LIKE '%goalkeeper%')
            ORDER BY m.match_date, pm.match_id, pm.player_id
            """,
            [V2_VERSION],
        ).df()
    frame["match_date"] = pd.to_datetime(frame["match_date"], errors="coerce")
    return frame


def fit_model(reference_raw: pd.DataFrame, max_pca_rows: int) -> tuple[dict[str, Any], pd.DataFrame]:
    base = _zero_counts(reference_raw)
    faced = base["saves"] + base["goals_conceded"]
    observed = faced > 0
    if int(observed.sum()) < 1000:
        raise RuntimeError("Insufficient goalkeeper shot-stopping evidence")
    prior_rate = float(base.loc[observed, "saves"].sum() / faced[observed].sum())
    prior_strength = float(max(1.0, faced[observed].median()))
    ref = _add_features(base, prior_rate, prior_strength)

    dist_model = _fit_distribution(ref, max_pca_rows)
    ref["distribution_pc"] = _apply_distribution(ref, dist_model)

    shot_mean = float(ref["shrunk_save_rate"].mean())
    shot_sd = float(ref["shrunk_save_rate"].std(ddof=0))
    dist_mean = float(ref["distribution_pc"].mean())
    dist_sd = float(ref["distribution_pc"].std(ddof=0))
    shot_sd = shot_sd if np.isfinite(shot_sd) and shot_sd > 1e-9 else 1.0
    dist_sd = dist_sd if np.isfinite(dist_sd) and dist_sd > 1e-9 else 1.0
    ref["shot_z"] = (ref["shrunk_save_rate"] - shot_mean) / shot_sd
    ref["dist_z"] = (ref["distribution_pc"] - dist_mean) / dist_sd

    component = ref[["shot_z", "dist_z"]].fillna(0.0)
    fit_component = component.sample(int(max_pca_rows), random_state=18) if len(component) > int(max_pca_rows) else component
    combine_pca = PCA(n_components=1, random_state=18).fit(fit_component)
    load = combine_pca.components_[0].astype(float)
    pc = fit_component.to_numpy(dtype=float) @ load
    desirability = fit_component.mean(axis=1).to_numpy(dtype=float)
    corr = float(np.corrcoef(pc, desirability)[0, 1])
    if np.isfinite(corr) and corr < 0:
        load *= -1.0
        corr = -corr
    if not bool(np.all(load > 0)):
        raise RuntimeError(f"Goalkeeper latent PCA has non-positive component loading: {load.tolist()}")

    ref["latent"] = ref[["shot_z", "dist_z"]].to_numpy(dtype=float) @ load
    latent_mean = float(ref["latent"].mean())
    latent_sd = float(ref["latent"].std(ddof=0))
    latent_sd = latent_sd if np.isfinite(latent_sd) and latent_sd > 1e-9 else 1.0
    ref["latent_z"] = (ref["latent"] - latent_mean) / latent_sd

    residual_target = pd.to_numeric(ref["opta_points_target"], errors="coerce") - _public_anchor(ref)
    target_mean = float(residual_target.mean())
    target_sd = float(residual_target.std(ddof=0))
    # Distribution-only calibration: benchmark sets location/scale, not per-row weights.
    intercept = target_mean
    slope = target_sd

    model = {
        "prior_save_rate": prior_rate,
        "prior_strength_shots": prior_strength,
        "shot_mean": shot_mean,
        "shot_sd": shot_sd,
        "distribution": dist_model,
        "distribution_mean": dist_mean,
        "distribution_sd": dist_sd,
        "latent_loadings": {"shot_stopping": float(load[0]), "distribution": float(load[1])},
        "latent_orientation_corr": corr if np.isfinite(corr) else None,
        "latent_mean": latent_mean,
        "latent_sd": latent_sd,
        "calibration": {"intercept": intercept, "slope": slope},
        "reference_rows": int(len(ref)),
        "reference_rows_with_shot_evidence": int(observed.sum()),
    }
    return model, ref


def score_components(frame_raw: pd.DataFrame, model: dict[str, Any]) -> pd.DataFrame:
    f = _add_features(frame_raw, model["prior_save_rate"], model["prior_strength_shots"])
    f["distribution_pc"] = _apply_distribution(f, model["distribution"])
    f["shot_z"] = (f["shrunk_save_rate"] - float(model["shot_mean"])) / float(model["shot_sd"])
    f["dist_z"] = (f["distribution_pc"] - float(model["distribution_mean"])) / float(model["distribution_sd"])
    load_shot = float(model["latent_loadings"]["shot_stopping"])
    load_dist = float(model["latent_loadings"]["distribution"])
    f["latent"] = f["shot_z"].fillna(0.0) * load_shot + f["dist_z"].fillna(0.0) * load_dist
    f["latent_z"] = (f["latent"] - float(model["latent_mean"])) / float(model["latent_sd"])
    base = float(model["calibration"]["intercept"]) + float(model["calibration"]["slope"]) * f["latent_z"]
    f["public_anchor"] = _public_anchor(f)
    f["fps_anchor"] = _fps_anchor(f)
    f["rating"] = (base + f["public_anchor"] + f["fps_anchor"]).clip(3.0, 10.0)
    return f


def _display_z(z: pd.Series) -> pd.Series:
    return (50.0 + 15.0 * pd.to_numeric(z, errors="coerce")).clip(0.0, 100.0)


def _confidence(frame: pd.DataFrame, scored: pd.DataFrame, prior_strength: float) -> pd.Series:
    minutes = (pd.to_numeric(frame["minutes_played"], errors="coerce").fillna(0.0) / 60.0).clip(0.0, 1.0)
    shot_evidence = (pd.to_numeric(scored["shots_faced_proxy"], errors="coerce").fillna(0.0) / max(float(prior_strength), 1.0)).clip(0.0, 1.0)
    dist_coverage = frame[["passes_total", "passes_completed", "long_balls_total", "long_balls_completed"]].notna().mean(axis=1).astype(float)
    return (100.0 * (0.45 * shot_evidence + 0.35 * dist_coverage + 0.20 * minutes)).clip(0.0, 100.0)


def build_candidate(db_path: Path, input_dir: Path, max_pca_rows: int, min_ref_minutes: float) -> tuple[pd.DataFrame, dict[str, Any]]:
    local = load_local(db_path)
    if local.empty or local["match_date"].isna().any():
        raise RuntimeError("Local goalkeeper rows/date coverage unavailable")
    cutoff = pd.Timestamp(local["match_date"].min())
    reference_raw, _ = load_reference(input_dir, cutoff, min_ref_minutes)
    model, _ = fit_model(reference_raw, max_pca_rows)
    scored = score_components(local, model)

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
    out["creation_progression"] = _display_z(scored["dist_z"])
    out["defensive_contribution"] = _display_z(scored["shot_z"])
    out["finishing"] = np.nan
    discipline_anchor = _public_anchor(local) + _fps_anchor(local)
    out["discipline"] = (50.0 + 20.0 * discipline_anchor).clip(0.0, 100.0)
    out["fallback_dimension_count"] = 0
    out["rating_path"] = "GOALKEEPER_PERF18_LATENT"
    out["match_rating_10"] = scored["rating"].astype(float)
    out["match_rating_100"] = ((out["match_rating_10"] - 3.0) * (100.0 / 7.0)).clip(0.0, 100.0)
    out["match_rating_confidence"] = _confidence(local, scored, model["prior_strength_shots"])
    out["match_rating_dimensions_used"] = 3
    out["match_rating_context"] = "GOALKEEPER_SEPARATE_PRO_REFERENCE"
    out["match_rating_status"] = "V4_2_EXPERIMENTAL_GOALKEEPER_RATED"
    out["match_rating_version"] = GK_VERSION
    out["source_score_version"] = SOURCE_VERSION

    metadata = {
        "version": GK_VERSION,
        "source_version": SOURCE_VERSION,
        "local_first_match_date": str(cutoff.date()),
        "professional_reference_policy": "goalkeeper rows with match_date strictly before local_first_match_date",
        "model": model,
        "local_rows": int(len(out)),
        "local_matches": int(out["match_id"].nunique()),
        "public_sparse_anchors": PUBLIC_SPARSE_ANCHORS,
        "fps_hypothesis_anchors": FPS_HYPOTHESIS_ANCHORS,
        "production_status": "EXPERIMENT_ONLY",
    }
    return out.reset_index(drop=True), metadata


def materialize(db_path: Path, frame: pd.DataFrame) -> None:
    with duckdb.connect(str(db_path)) as con:
        con.execute("DELETE FROM player_match_rating WHERE match_rating_version=?", [GK_VERSION])
        con.register("gk_df", frame)
        cols = list(frame.columns)
        con.execute(f"INSERT INTO player_match_rating ({', '.join(cols)}) SELECT {', '.join(cols)} FROM gk_df")
        con.unregister("gk_df")


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)
    input_dir = discover_input_dir(args.input_dir)
    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    frame, metadata = build_candidate(db, input_dir, int(args.max_pca_fit_rows), float(args.min_reference_minutes))
    materialize(db, frame)
    artifact = out_dir / "goalkeeper_candidate_metadata.json"
    artifact.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    model = metadata["model"]
    print("PERF-18 GOALKEEPER MATCH RATING EXPERIMENTAL: MATERIALIZED")
    print(f"version={GK_VERSION}")
    print(f"rows={len(frame)} matches={frame['match_id'].nunique()}")
    print(f"mean={frame['match_rating_10'].mean():.3f} median={frame['match_rating_10'].median():.3f}")
    print(f"min={frame['match_rating_10'].min():.3f} max={frame['match_rating_10'].max():.3f}")
    print(f"reference_rows={model['reference_rows']} reference_shot_evidence={model['reference_rows_with_shot_evidence']}")
    print(f"prior_save_rate={model['prior_save_rate']:.4f} prior_strength={model['prior_strength_shots']:.2f}")
    print("latent_loadings=" + str(model["latent_loadings"]))
    print(f"latent_orientation_corr={model['latent_orientation_corr']}")
    print("distribution_EV1=" + str(model["distribution"]["explained_variance_ratio"]))
    print(f"artifact={artifact}")
    print("No production rating was changed.")


if __name__ == "__main__":
    main()
