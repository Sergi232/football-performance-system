"""PERF-18 — audited Opta Points benchmark reconstruction.

Purpose
-------
Reconstruct the public Opta Points formula from PannaData aggregates when the
required provider columns are available. This benchmark is external and
transparent; it is NOT the proprietary Opta Player Rating.

The script never changes the production rating. If required source columns are
missing, status is PARTIAL_PROXY and the result must not be called Opta Points.

Official public scoring reference (Stats Perform / Opta Points):
base 5.5, capped 3.0–10.0; goals +1.0; shots on target +0.4;
shots off target +0.2; blocked shots +0.2; own goals -0.5; assists +0.6;
successful passes +0.02; crosses +0.02; tackles +0.2; interceptions +0.2;
fouls won +0.1; fouls committed -0.1; offsides -0.1; yellow -0.2;
red -0.5; penalties won +0.4; goals conceded -0.1 outfield/-0.6 GK;
saves +0.5 GK; penalty saves +0.5 GK.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dsai" / "output" / "perf18_opta_points"

# Candidate provider names observed across Opta exports. First present alias wins.
ALIASES: dict[str, list[str]] = {
    "goals": ["goals"],
    "shots_on_target": ["ontargetScoringAtt", "onTargetScoringAtt", "shotsOnTarget", "shots_on_target"],
    "shots_off_target": ["shotOffTarget", "shotsOffTarget", "shots_off_target"],
    "blocked_shots": ["blockedScoringAtt", "blockedShots", "blocked_shots"],
    "own_goals": ["ownGoals", "ownGoal", "own_goals"],
    "assists": ["goalAssist", "assists"],
    # Opta Points explainer explicitly describes a successful pass.
    "successful_passes": ["accuratePass", "successfulPasses", "completedPasses"],
    "crosses": ["totalCross", "crosses", "accurateCross"],
    "tackles": ["wonTackle", "tacklesWon", "totalTackle"],
    "interceptions": ["interception", "interceptions"],
    "fouls_won": ["wasFouled", "foulsWon"],
    "fouls_committed": ["fouls", "foulsCommitted"],
    "offsides": ["totalOffside", "offsides", "offside"],
    "yellow_cards": ["yellowCard", "yellowCards"],
    "red_cards": ["redCard", "redCards"],
    "goals_conceded": ["goalsConceded", "goals_conceded"],
    "penalties_won": ["penaltyWon", "penaltiesWon"],
    "saves": ["saves", "totalSaves"],
    "penalty_saves": ["penaltySave", "penaltySaves", "penaltiesSaved"],
}

WEIGHTS_OUTFIELD = {
    "goals": 1.0,
    "shots_on_target": 0.4,
    "shots_off_target": 0.2,
    "blocked_shots": 0.2,
    "own_goals": -0.5,
    "assists": 0.6,
    "successful_passes": 0.02,
    "crosses": 0.02,
    "tackles": 0.2,
    "interceptions": 0.2,
    "fouls_won": 0.1,
    "fouls_committed": -0.1,
    "offsides": -0.1,
    "yellow_cards": -0.2,
    "red_cards": -0.5,
    "goals_conceded": -0.1,
    "penalties_won": 0.4,
    "saves": 0.0,
    "penalty_saves": 0.0,
}
WEIGHTS_GK = dict(WEIGHTS_OUTFIELD)
WEIGHTS_GK.update({"goals_conceded": -0.6, "saves": 0.5, "penalty_saves": 0.5})


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit/reconstruct public Opta Points benchmark")
    p.add_argument("--input-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--min-minutes", type=float, default=1.0)
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


def choose_aliases(available: Iterable[str]) -> tuple[dict[str, str], list[str]]:
    available_set = set(available)
    mapping: dict[str, str] = {}
    missing: list[str] = []
    for logical, aliases in ALIASES.items():
        chosen = next((a for a in aliases if a in available_set), None)
        if chosen is None:
            missing.append(logical)
        else:
            mapping[logical] = chosen
    return mapping, missing


def is_goalkeeper(position: object) -> bool:
    if position is None or pd.isna(position):
        return False
    text = str(position).strip().lower()
    return text == "gk" or "goalkeeper" in text or text == "keeper"


def quantiles(s: pd.Series) -> dict[str, float | None]:
    x = pd.to_numeric(s, errors="coerce").dropna()
    if x.empty:
        return {"mean": None, "median": None, "q10": None, "q90": None, "min": None, "max": None}
    return {
        "mean": float(x.mean()),
        "median": float(x.median()),
        "q10": float(x.quantile(0.10)),
        "q90": float(x.quantile(0.90)),
        "min": float(x.min()),
        "max": float(x.max()),
    }


def main() -> None:
    args = parse_args()
    input_dir = discover_input_dir(args.input_dir)
    out = args.output_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    stats = input_dir / "opta_player_stats.parquet"
    lineups = input_dir / "opta_lineups.parquet"

    with duckdb.connect() as con:
        schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{sql_path(stats)}')").df()
        available = schema["column_name"].astype(str).tolist()
        mapping, missing = choose_aliases(available)

        selected = [
            "CAST(s.match_id AS VARCHAR) AS match_id",
            "CAST(s.team_id AS VARCHAR) AS team_id",
            "CAST(s.player_id AS VARCHAR) AS player_id",
            "TRY_CAST(s.minsPlayed AS DOUBLE) AS minutes_played",
        ]
        for logical, source in mapping.items():
            selected.append(f'TRY_CAST(s."{source}" AS DOUBLE) AS {logical}')
        query = f'''
            SELECT {", ".join(selected)}, l.position
            FROM read_parquet('{sql_path(stats)}') s
            LEFT JOIN read_parquet('{sql_path(lineups)}') l
              ON CAST(l.match_id AS VARCHAR)=CAST(s.match_id AS VARCHAR)
             AND CAST(l.team_id AS VARCHAR)=CAST(s.team_id AS VARCHAR)
             AND CAST(l.player_id AS VARCHAR)=CAST(s.player_id AS VARCHAR)
            WHERE TRY_CAST(s.minsPlayed AS DOUBLE) >= {float(args.min_minutes)}
        '''
        df = con.execute(query).df()

    df = df.drop_duplicates(["match_id", "team_id", "player_id"], keep="first")
    df["is_gk"] = df["position"].map(is_goalkeeper)

    # Missing benchmark variables contribute zero only for the PARTIAL_PROXY audit;
    # status prevents this proxy from being mislabeled as complete Opta Points.
    for logical in ALIASES:
        if logical not in df.columns:
            df[logical] = 0.0
        df[logical] = pd.to_numeric(df[logical], errors="coerce").fillna(0.0)

    def score_row(row: pd.Series) -> float:
        weights = WEIGHTS_GK if bool(row["is_gk"]) else WEIGHTS_OUTFIELD
        raw = 5.5 + sum(float(row[k]) * float(w) for k, w in weights.items())
        return float(np.clip(raw, 3.0, 10.0))

    df["benchmark_score"] = df.apply(score_row, axis=1)
    status = "COMPLETE_RECONSTRUCTION" if not missing else "PARTIAL_PROXY"

    result = {
        "status": status,
        "source": str(stats),
        "rows": int(len(df)),
        "goalkeeper_rows": int(df["is_gk"].sum()),
        "outfield_rows": int((~df["is_gk"]).sum()),
        "mapped_columns": mapping,
        "missing_logical_variables": missing,
        "coverage": {
            logical: float(pd.to_numeric(df[logical], errors="coerce").notna().mean())
            for logical in ALIASES
        },
        "overall": quantiles(df["benchmark_score"]),
        "goalkeeper": quantiles(df.loc[df["is_gk"], "benchmark_score"]),
        "outfield": quantiles(df.loc[~df["is_gk"], "benchmark_score"]),
        "formula": {
            "base": 5.5,
            "min": 3.0,
            "max": 10.0,
            "outfield": WEIGHTS_OUTFIELD,
            "goalkeeper": WEIGHTS_GK,
        },
        "guardrail": "Only COMPLETE_RECONSTRUCTION may be described as reconstructed public Opta Points. PARTIAL_PROXY is benchmark research only.",
        "production_status": "EXPERIMENT_ONLY",
    }

    artifact = out / "opta_points_benchmark_audit.json"
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("PERF-18 OPTA POINTS BENCHMARK AUDIT")
    print(f"input_dir={input_dir}")
    print(f"rows={len(df)} gk_rows={int(df['is_gk'].sum())} outfield_rows={int((~df['is_gk']).sum())}")
    print(f"status={status}")
    print("mapped_columns=" + str(mapping))
    print("missing_logical_variables=" + str(missing))
    print("overall=" + str(result["overall"]))
    print("goalkeeper=" + str(result["goalkeeper"]))
    print("outfield=" + str(result["outfield"]))
    print(f"artifact={artifact}")
    print("No production rating was changed.")


if __name__ == "__main__":
    main()
