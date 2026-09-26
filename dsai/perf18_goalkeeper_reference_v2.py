"""PERF-18 goalkeeper reference v2.

Goalkeepers are modelled independently from outfield players.

Key methodological choices:
- shot-stopping quality is based on save rate, not saves per 90;
- per-match save rate is empirically shrunk toward the professional-population
  prior to reduce extreme small-sample ratings;
- saves per 90 / shots faced proxy are evidence-volume descriptors only;
- distribution is represented by a position-specific PCA because the previous
  experiment showed a coherent direction for passing execution;
- sparse discipline events are kept as explicit penalties, not forced into PCA;
- no production rating is changed by this experiment.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_gk_v2"

SOURCE = {
    "passes_total": "totalPass",
    "passes_completed": "accuratePass",
    "long_balls_total": "totalLongBalls",
    "long_balls_completed": "accurateLongBalls",
    "clearances": "totalClearance",
    "fouls_committed": "fouls",
    "yellow_cards": "yellowCard",
    "red_cards": "redCard",
    "penalties_conceded": "penaltyConceded",
    "saves": "saves",
    "goals_conceded": "goalsConceded",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-18 goalkeeper reference v2")
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--min-minutes", type=float, default=30.0)
    p.add_argument("--max-fit-rows", type=int, default=200000)
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
    for p in candidates:
        q = p.expanduser().resolve()
        if (q / "opta_player_stats.parquet").exists() and (q / "opta_lineups.parquet").exists():
            return q
    raise FileNotFoundError("PannaData player_stats + lineups not found")


def sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    n = pd.to_numeric(num, errors="coerce")
    d = pd.to_numeric(den, errors="coerce")
    return n / d.where(d > 0)


def load_goalkeepers(input_dir: Path, min_minutes: float) -> pd.DataFrame:
    stats = input_dir / "opta_player_stats.parquet"
    lineups = input_dir / "opta_lineups.parquet"
    select_stats = ", ".join(
        [
            "CAST(s.match_id AS VARCHAR) AS match_id",
            "CAST(s.team_id AS VARCHAR) AS team_id",
            "CAST(s.player_id AS VARCHAR) AS player_id",
            "TRY_CAST(s.minsPlayed AS DOUBLE) AS minutes_played",
        ]
        + [f'TRY_CAST(s."{src}" AS DOUBLE) AS {logical}' for logical, src in SOURCE.items()]
    )
    q = f'''
        SELECT {select_stats}, l.position
        FROM read_parquet('{sql_path(stats)}') s
        LEFT JOIN read_parquet('{sql_path(lineups)}') l
          ON CAST(l.match_id AS VARCHAR)=CAST(s.match_id AS VARCHAR)
         AND CAST(l.team_id AS VARCHAR)=CAST(s.team_id AS VARCHAR)
         AND CAST(l.player_id AS VARCHAR)=CAST(s.player_id AS VARCHAR)
        WHERE TRY_CAST(s.minsPlayed AS DOUBLE) >= {float(min_minutes)}
    '''
    with duckdb.connect() as con:
        df = con.execute(q).df()
    df = df.drop_duplicates(["match_id", "team_id", "player_id"], keep="first")
    pos = df["position"].fillna("").astype(str).str.lower()
    df = df[pos.str.contains("goalkeeper|keeper") | pos.eq("gk")].copy()

    mins = pd.to_numeric(df["minutes_played"], errors="coerce")
    factor = 90.0 / mins.where(mins > 0)
    for c in SOURCE:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df[f"{c}_p90"] = df[c] * factor

    df["shots_on_target_faced_proxy"] = df["saves"].fillna(0) + df["goals_conceded"].fillna(0)
    df["raw_save_rate"] = safe_ratio(df["saves"], df["shots_on_target_faced_proxy"])
    df["pass_accuracy"] = safe_ratio(df["passes_completed"], df["passes_total"]).clip(0, 1)
    df["long_ball_accuracy"] = safe_ratio(df["long_balls_completed"], df["long_balls_total"]).clip(0, 1)
    return df


def robust_reference(series: pd.Series) -> dict[str, float | None]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {"median": None, "q25": None, "q75": None, "iqr": None}
    q25, med, q75 = np.quantile(s, [0.25, 0.50, 0.75])
    return {
        "median": float(med),
        "q25": float(q25),
        "q75": float(q75),
        "iqr": float(q75 - q25),
    }


def fit_distribution_pca(df: pd.DataFrame, max_rows: int) -> dict:
    cols = ["pass_accuracy", "long_ball_accuracy", "passes_completed_p90", "long_balls_completed_p90"]
    x = df[cols].copy()
    coverage = {c: float(x[c].notna().mean()) for c in cols}
    keep = [c for c in cols if coverage[c] >= 0.20 and x[c].nunique(dropna=True) > 1]
    x = x[keep]
    med = x.median(numeric_only=True)
    x = x.fillna(med)
    if len(x) > max_rows:
        x = x.sample(max_rows, random_state=18)

    scaler = StandardScaler()
    z = scaler.fit_transform(x)
    pca = PCA(n_components=1, random_state=18)
    pc = pca.fit_transform(z).reshape(-1)
    desirability = np.nanmean(z, axis=1)
    corr = np.corrcoef(pc, desirability)[0, 1]
    if np.isfinite(corr) and corr < 0:
        pca.components_[0] *= -1.0
        pc *= -1.0
        corr = -corr
    return {
        "features": keep,
        "coverage": {c: coverage[c] for c in keep},
        "medians": {c: float(med[c]) for c in keep},
        "scaler_mean": {c: float(v) for c, v in zip(keep, scaler.mean_)},
        "scaler_scale": {c: float(v) for c, v in zip(keep, scaler.scale_)},
        "loadings": {c: float(v) for c, v in zip(keep, pca.components_[0])},
        "explained_variance_ratio": float(pca.explained_variance_ratio_[0]),
        "orientation_corr": float(corr) if np.isfinite(corr) else None,
        "fit_rows": int(len(x)),
    }


def main() -> None:
    args = parse_args()
    input_dir = discover_input_dir(args.input_dir)
    out = args.output_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    df = load_goalkeepers(input_dir, args.min_minutes)
    faced = df["shots_on_target_faced_proxy"]
    observed = df.loc[faced > 0].copy()
    if observed.empty:
        raise RuntimeError("No goalkeeper rows with saves/goals-conceded evidence")

    total_saves = float(observed["saves"].fillna(0).sum())
    total_faced = float(observed["shots_on_target_faced_proxy"].sum())
    prior_save_rate = total_saves / total_faced if total_faced > 0 else 0.0
    prior_strength = float(max(1.0, observed["shots_on_target_faced_proxy"].median()))

    # Empirical shrinkage: the professional population determines both the prior
    # save rate and the equivalent prior sample size.
    df["shrunk_save_rate"] = (
        df["saves"].fillna(0) + prior_save_rate * prior_strength
    ) / (df["shots_on_target_faced_proxy"].fillna(0) + prior_strength)

    distribution = fit_distribution_pca(df, args.max_fit_rows)

    discipline_coverage = {
        c: float(df[c].notna().mean())
        for c in ["fouls_committed", "yellow_cards", "red_cards", "penalties_conceded", "clearances"]
    }
    discipline_positive_share = {
        c: float((pd.to_numeric(df[c], errors="coerce").fillna(0) > 0).mean())
        for c in discipline_coverage
    }

    result = {
        "rows": int(len(df)),
        "rows_with_shot_stopping_evidence": int((faced > 0).sum()),
        "min_minutes": float(args.min_minutes),
        "method": "independent_goalkeeper_empirical_shrinkage_plus_distribution_pca",
        "production_status": "EXPERIMENT_ONLY",
        "shot_stopping": {
            "prior_save_rate": float(prior_save_rate),
            "prior_strength_shots": float(prior_strength),
            "raw_save_rate_reference": robust_reference(df["raw_save_rate"]),
            "shrunk_save_rate_reference": robust_reference(df["shrunk_save_rate"]),
            "shots_faced_proxy_reference": robust_reference(df["shots_on_target_faced_proxy"]),
            "interpretation": "shrunk_save_rate is quality; shots_faced/saves_p90 are evidence/workload only",
        },
        "distribution": distribution,
        "discipline_context": {
            "coverage": discipline_coverage,
            "positive_event_share": discipline_positive_share,
            "method": "explicit_event_penalties_only; no PCA unless coverage/variance support it",
        },
        "display_scale": "not_calibrated_yet",
    }

    artifact = out / "goalkeeper_reference_v2.json"
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("PERF-18 GOALKEEPER REFERENCE V2: COMPLETE")
    print(f"input_dir={input_dir}")
    print(f"rows={len(df)}")
    print(f"rows_with_shot_stopping_evidence={(faced > 0).sum()}")
    print(f"prior_save_rate={prior_save_rate:.4f}")
    print(f"prior_strength_shots={prior_strength:.2f}")
    shot = result["shot_stopping"]
    print(f"raw_save_rate_median={shot['raw_save_rate_reference']['median']}")
    print(f"shrunk_save_rate_median={shot['shrunk_save_rate_reference']['median']}")
    print(
        "distribution="
        f"EV1={distribution['explained_variance_ratio']:.3f} "
        f"orientation={distribution['orientation_corr']:.3f}"
    )
    print("discipline_positive_event_share=" + str(discipline_positive_share))
    print(f"artifact={artifact}")
    print("No production rating was changed.")


if __name__ == "__main__":
    main()
