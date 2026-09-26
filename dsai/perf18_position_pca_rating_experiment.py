"""PERF-18 — position-aware multidimensional latent Match Rating experiment.

Methodological inspiration (public Stats Perform / Opta descriptions):
- six performance subcomponents: shooting, passing, possession, defending, attacking,
  goalkeeping;
- position-specific treatment;
- standardized/z-score based rating transformation;
- PCA applied separately by position as a dimensionality-reduction tool.

This experiment does NOT reproduce the proprietary Opta Player Rating formula.
It uses only collector-compatible variables available in PannaData and learns a
position-specific latent structure from the professional reference database.
No supervised target is invented.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_pca"

SOURCE_FEATURES = {
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

# Six Opta-like conceptual dimensions, restricted to our collector-compatible data.
# Sign: +1 means more is favourable, -1 means more is unfavourable.
DIMENSION_FEATURES: dict[str, dict[str, float]] = {
    "shooting": {
        "goals_p90": +1.0,
        "shots_total_p90": +1.0,
        "shots_blocked_p90": -1.0,
    },
    "passing": {
        "pass_accuracy": +1.0,
        "passes_completed_p90": +1.0,
        "long_balls_completed_p90": +1.0,
        "crosses_completed_p90": +1.0,
        "assists_p90": +1.0,
    },
    "possession": {
        "dribbles_won_p90": +1.0,
        "dribble_success": +1.0,
        "turnovers_p90": -1.0,
        "dispossessed_p90": -1.0,
    },
    "defending": {
        "tackles_won_p90": +1.0,
        "tackle_success": +1.0,
        "interceptions_p90": +1.0,
        "blocked_passes_p90": +1.0,
        "clearances_p90": +1.0,
        "penalties_conceded_p90": -1.0,
    },
    "attacking": {
        "assists_p90": +1.0,
        "crosses_completed_p90": +1.0,
        "dribbles_won_p90": +1.0,
        "fouls_received_p90": +1.0,
        "penalties_won_p90": +1.0,
        "fouls_committed_p90": -1.0,
        "yellow_cards_p90": -1.0,
        "red_cards_p90": -1.0,
    },
    "goalkeeping": {
        "saves_p90": +1.0,
        "goals_conceded_p90": -1.0,
    },
}

OUTFIELD_POSITIONS = ["CB", "FB", "DM", "CM", "AM", "W", "ST"]
ALL_POSITIONS = ["GK", *OUTFIELD_POSITIONS]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-18 position-aware PCA rating experiment")
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--min-minutes", type=float, default=30.0)
    p.add_argument("--max-fit-rows-per-position", type=int, default=150000)
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
    required = {"opta_player_stats.parquet", "opta_lineups.parquet"}
    for candidate in candidates:
        path = candidate.expanduser().resolve()
        if path.exists() and all((path / name).exists() for name in required):
            return path
    raise FileNotFoundError("Could not find PannaData player_stats + lineups")


def sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def norm_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def map_position(position: Any, side: Any, formation_place: Any) -> str:
    """Eight-position map using position + side before falling back to broad labels."""
    p = norm_text(position)
    s = norm_text(side)
    fp = norm_text(formation_place)
    combined = " ".join(x for x in [p, s, fp] if x)

    if not p or p == "substitute":
        return "UNKNOWN"
    if "goalkeeper" in combined or p in {"gk", "keeper"}:
        return "GK"

    # Explicit role labels first.
    if any(k in combined for k in ["centre back", "center back", "central defender"]):
        return "CB"
    if any(k in combined for k in ["full back", "wing back", "left back", "right back"]):
        return "FB"
    if "defensive midfielder" in combined or "holding midfielder" in combined:
        return "DM"
    if any(k in combined for k in ["attacking midfielder", "number 10", "number ten"]):
        return "AM"
    if any(k in combined for k in ["winger", "left wing", "right wing", "wide forward"]):
        return "W"
    if any(k in combined for k in ["striker", "centre forward", "center forward"]):
        return "ST"

    # Provider broad labels refined by side.
    if "defender" in p:
        if any(k in s for k in ["left", "right", "wide"]):
            return "FB"
        return "CB"
    if "midfielder" in p:
        if any(k in s for k in ["left", "right", "wide"]):
            return "W"
        if "defensive" in combined:
            return "DM"
        if "attacking" in combined:
            return "AM"
        return "CM"
    if "forward" in p:
        if any(k in s for k in ["left", "right", "wide"]):
            return "W"
        return "ST"

    return "UNKNOWN"


def safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    n = pd.to_numeric(num, errors="coerce")
    d = pd.to_numeric(den, errors="coerce")
    out = n / d.where(d > 0)
    return out.clip(lower=0.0, upper=1.0)


def add_derived_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    mins = pd.to_numeric(out["minutes_played"], errors="coerce")
    factor = 90.0 / mins.where(mins > 0)

    count_cols = list(SOURCE_FEATURES.keys())
    for col in count_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        out[f"{col}_p90"] = out[col] * factor

    out["pass_accuracy"] = safe_ratio(out["passes_completed"], out["passes_total"])
    out["dribble_success"] = safe_ratio(out["dribbles_won"], out["dribbles_total"])
    out["tackle_success"] = safe_ratio(out["tackles_won"], out["tackles_total"])
    return out


def load_matrix(input_dir: Path, min_minutes: float) -> pd.DataFrame:
    stats = input_dir / "opta_player_stats.parquet"
    lineups = input_dir / "opta_lineups.parquet"
    select_stats = ", ".join(
        ["CAST(s.match_id AS VARCHAR) AS match_id", "CAST(s.team_id AS VARCHAR) AS team_id", "CAST(s.player_id AS VARCHAR) AS player_id", "TRY_CAST(s.minsPlayed AS DOUBLE) AS minutes_played"]
        + [f'TRY_CAST(s."{src}" AS DOUBLE) AS {logical}' for logical, src in SOURCE_FEATURES.items()]
    )
    q = f'''
        SELECT
            {select_stats},
            l.position,
            l.position_side,
            l.formation_place
        FROM read_parquet('{sql_path(stats)}') s
        LEFT JOIN read_parquet('{sql_path(lineups)}') l
          ON CAST(l.match_id AS VARCHAR)=CAST(s.match_id AS VARCHAR)
         AND CAST(l.team_id AS VARCHAR)=CAST(s.team_id AS VARCHAR)
         AND CAST(l.player_id AS VARCHAR)=CAST(s.player_id AS VARCHAR)
        WHERE TRY_CAST(s.minsPlayed AS DOUBLE) >= {float(min_minutes)}
    '''
    with duckdb.connect() as con:
        frame = con.execute(q).df()
    frame = frame.drop_duplicates(["match_id", "team_id", "player_id"], keep="first")
    frame["position_group"] = [
        map_position(p, s, fp)
        for p, s, fp in zip(frame["position"], frame["position_side"], frame["formation_place"])
    ]
    return add_derived_features(frame)


def signed_dimension_matrix(frame: pd.DataFrame, dimension: str) -> tuple[pd.DataFrame, dict[str, float]]:
    mapping = DIMENSION_FEATURES[dimension]
    cols = [c for c in mapping if c in frame.columns]
    if not cols:
        return pd.DataFrame(index=frame.index), {}
    x = frame[cols].copy()
    for col in cols:
        x[col] = pd.to_numeric(x[col], errors="coerce") * float(mapping[col])
    return x, {c: float(mapping[c]) for c in cols}


def fit_dimension_pca(frame: pd.DataFrame, dimension: str, max_rows: int) -> dict[str, Any] | None:
    x, signs = signed_dimension_matrix(frame, dimension)
    if x.empty or x.shape[1] == 0:
        return None

    # Keep features with meaningful coverage and variability.
    coverage = x.notna().mean()
    keep = [c for c in x.columns if coverage[c] >= 0.20 and x[c].nunique(dropna=True) > 1]
    if not keep:
        return None
    x = x[keep]

    medians = x.median(numeric_only=True)
    x = x.fillna(medians)
    if len(x) > max_rows:
        x = x.sample(n=max_rows, random_state=18)

    scaler = StandardScaler()
    z = scaler.fit_transform(x)
    pca = PCA(n_components=1, random_state=18)
    pc = pca.fit_transform(z).reshape(-1)

    # Orient PC1 so higher means align with the mean of already signed z-features.
    signed_mean = np.nanmean(z, axis=1)
    corr = np.corrcoef(pc, signed_mean)[0, 1] if len(pc) > 2 else 1.0
    if np.isfinite(corr) and corr < 0:
        pca.components_[0] *= -1.0
        pc *= -1.0

    return {
        "dimension": dimension,
        "features": keep,
        "coverage": {c: float(coverage[c]) for c in keep},
        "medians": {c: float(medians[c]) for c in keep},
        "scaler_mean": {c: float(v) for c, v in zip(keep, scaler.mean_)},
        "scaler_scale": {c: float(v) for c, v in zip(keep, scaler.scale_)},
        "loadings": {c: float(v) for c, v in zip(keep, pca.components_[0])},
        "explained_variance_ratio": float(pca.explained_variance_ratio_[0]),
        "orientation_corr": None if not np.isfinite(corr) else float(abs(corr)),
        "fit_rows": int(len(x)),
    }


def main() -> None:
    args = parse_args()
    input_dir = discover_input_dir(args.input_dir)
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    frame = load_matrix(input_dir, args.min_minutes)
    counts = frame["position_group"].value_counts(dropna=False).to_dict()
    mapped = frame[frame["position_group"].isin(ALL_POSITIONS)].copy()

    print("PERF-18 POSITION PCA MATRIX: READY")
    print(f"input_dir={input_dir}")
    print(f"rows_min_{args.min_minutes:g}m={len(frame)}")
    print(f"mapped_rows={len(mapped)}")
    print(f"position_counts={counts}")

    results: dict[str, Any] = {
        "input_dir": str(input_dir),
        "min_minutes": float(args.min_minutes),
        "rows": int(len(frame)),
        "mapped_rows": int(len(mapped)),
        "position_counts": {str(k): int(v) for k, v in counts.items()},
        "positions": {},
        "method": "position_specific_signed_zscore_plus_PCA",
        "target": None,
        "production_status": "EXPERIMENT_ONLY",
    }

    for position in ALL_POSITIONS:
        pos = mapped[mapped["position_group"] == position].copy()
        if len(pos) < 500:
            print(f"{position}: SKIP rows={len(pos)}")
            continue

        applicable = ["goalkeeping"] if position == "GK" else ["shooting", "passing", "possession", "defending", "attacking"]
        pos_result: dict[str, Any] = {"rows": int(len(pos)), "dimensions": {}}
        print(f"\nPOSITION={position} rows={len(pos)}")
        for dim in applicable:
            fitted = fit_dimension_pca(pos, dim, args.max_fit_rows_per_position)
            if fitted is None:
                print(f"  {dim}: unavailable")
                continue
            pos_result["dimensions"][dim] = fitted
            print(
                f"  {dim}: features={len(fitted['features'])} "
                f"EV1={fitted['explained_variance_ratio']:.3f} "
                f"orientation={fitted['orientation_corr']:.3f}"
            )
            top = sorted(fitted["loadings"].items(), key=lambda kv: abs(kv[1]), reverse=True)[:4]
            print("    top_loadings=" + ", ".join(f"{k}:{v:+.3f}" for k, v in top))
        results["positions"][position] = pos_result

    out = output_dir / "position_pca_reference.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    unknown_share = 1.0 - (len(mapped) / len(frame) if len(frame) else 0.0)
    print("\nPERF-18 POSITION PCA EXPERIMENT: COMPLETE")
    print(f"mapped_share={1.0-unknown_share:.4f}")
    print(f"unknown_share={unknown_share:.4f}")
    print(f"artifact={out}")
    print("No external target or pseudo-target was used. No production rating was changed.")


if __name__ == "__main__":
    main()
