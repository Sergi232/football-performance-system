"""PERF-18 — dedicated goalkeeper Match Rating experiment.

Goalkeepers are NOT treated as another outfield position. This script builds an
independent goalkeeper reference model using only collector-compatible variables.
It does not modify the production rating.

Conceptual dimensions:
- shot_stopping: saves vs goals conceded;
- distribution: passing and long-ball execution;
- discipline: cards/fouls/penalties conceded when observed.

The final production GK rating may share the 3–10 display scale with outfield
players, but its internal feature space, normalization and weighting remain separate.
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
DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_gk"

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

DIMENSIONS = {
    "shot_stopping": {
        "saves_p90": +1.0,
        "goals_conceded_p90": -1.0,
    },
    "distribution": {
        "pass_accuracy": +1.0,
        "passes_completed_p90": +1.0,
        "long_ball_accuracy": +1.0,
        "long_balls_completed_p90": +1.0,
    },
    "discipline_context": {
        "clearances_p90": +1.0,
        "fouls_committed_p90": -1.0,
        "yellow_cards_p90": -1.0,
        "red_cards_p90": -1.0,
        "penalties_conceded_p90": -1.0,
    },
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PERF-18 dedicated goalkeeper rating experiment")
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
    return (n / d.where(d > 0)).clip(0.0, 1.0)


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
    df["pass_accuracy"] = safe_ratio(df["passes_completed"], df["passes_total"])
    df["long_ball_accuracy"] = safe_ratio(df["long_balls_completed"], df["long_balls_total"])
    return df


def fit_dimension(df: pd.DataFrame, name: str, max_rows: int) -> dict | None:
    mapping = DIMENSIONS[name]
    cols = [c for c in mapping if c in df.columns]
    if not cols:
        return None
    x = pd.DataFrame(index=df.index)
    coverage = {}
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce") * float(mapping[c])
        coverage[c] = float(s.notna().mean())
        if coverage[c] >= 0.20 and s.nunique(dropna=True) > 1:
            x[c] = s
    if x.empty:
        return None
    med = x.median(numeric_only=True)
    x = x.fillna(med)
    if len(x) > max_rows:
        x = x.sample(max_rows, random_state=18)
    scaler = StandardScaler()
    z = scaler.fit_transform(x)
    pca = PCA(n_components=1, random_state=18)
    pc = pca.fit_transform(z).reshape(-1)
    signed_mean = np.mean(z, axis=1)
    corr = np.corrcoef(pc, signed_mean)[0, 1] if len(pc) > 2 else 1.0
    if np.isfinite(corr) and corr < 0:
        pca.components_[0] *= -1
        pc *= -1
    return {
        "features": list(x.columns),
        "coverage": {c: coverage[c] for c in x.columns},
        "medians": {c: float(med[c]) for c in x.columns},
        "scaler_mean": {c: float(v) for c, v in zip(x.columns, scaler.mean_)},
        "scaler_scale": {c: float(v) for c, v in zip(x.columns, scaler.scale_)},
        "loadings": {c: float(v) for c, v in zip(x.columns, pca.components_[0])},
        "explained_variance_ratio": float(pca.explained_variance_ratio_[0]),
        "orientation_corr": None if not np.isfinite(corr) else float(abs(corr)),
        "fit_rows": int(len(x)),
    }


def main() -> None:
    args = parse_args()
    input_dir = discover_input_dir(args.input_dir)
    out = args.output_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    df = load_goalkeepers(input_dir, args.min_minutes)
    print("PERF-18 GOALKEEPER MATRIX: READY")
    print(f"input_dir={input_dir}")
    print(f"rows_min_{args.min_minutes:g}m={len(df)}")

    result = {
        "rows": int(len(df)),
        "min_minutes": float(args.min_minutes),
        "method": "separate_goalkeeper_reference",
        "production_status": "EXPERIMENT_ONLY",
        "dimensions": {},
    }
    for dim in DIMENSIONS:
        fitted = fit_dimension(df, dim, args.max_fit_rows)
        result["dimensions"][dim] = fitted
        if fitted is None:
            print(f"{dim}: unavailable")
            continue
        loads = sorted(fitted["loadings"].items(), key=lambda kv: abs(kv[1]), reverse=True)
        print(
            f"{dim}: features={len(fitted['features'])} "
            f"EV1={fitted['explained_variance_ratio']:.3f} "
            f"orientation={fitted['orientation_corr']:.3f}"
        )
        print("  top_loadings=" + ", ".join(f"{k}:{v:+.3f}" for k, v in loads[:5]))

    artifact = out / "goalkeeper_reference.json"
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PERF-18 GOALKEEPER EXPERIMENT: COMPLETE")
    print(f"artifact={artifact}")
    print("Goalkeepers remain methodologically separate from outfield players.")


if __name__ == "__main__":
    main()
