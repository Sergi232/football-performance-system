"""PERF-18 — Match Rating V4.1 experimental on-pitch context anchor.

Starts from the validated V4 outfield candidate and adds only one contextual anchor:
-0.10 per goal conceded while the player was actually on the pitch.

The -0.10 value is the transparent public Opta Points outfield goals-conceded weight;
it is not inferred from the proprietary Opta Player Rating. The purpose is to restore
an auditable match-context penalty without using final team result as a blanket proxy.

No production access layer is changed.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
BASE_VERSION = "match_rating_v0.4-experimental-outfield"
NEW_VERSION = "match_rating_v0.4.1-experimental-onpitch"
CONTEXT_VERSION = "on_pitch_goal_context_v0.2"
SOURCE_VERSION = "perf18_v4_plus_public_opta_points_onpitch_ga_anchor"
GOALS_AGAINST_WEIGHT = -0.10


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build PERF-18 V4.1 on-pitch context experiment")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)

    with duckdb.connect(str(db)) as con:
        base = con.execute(
            """
            SELECT b.*, c.goals_against_on_pitch, c.goals_for_on_pitch,
                   c.timing_precision, c.boundary_ambiguity_goals
            FROM player_match_rating b
            JOIN player_match_on_pitch_context c
              ON c.match_id=b.match_id AND c.team_id=b.team_id AND c.player_id=b.player_id
             AND c.context_version=?
            WHERE b.match_rating_version=?
            ORDER BY b.match_date, b.match_id, b.player_id
            """,
            [CONTEXT_VERSION, BASE_VERSION],
        ).df()

        expected = int(con.execute(
            "SELECT COUNT(*) FROM player_match_rating WHERE match_rating_version=?",
            [BASE_VERSION],
        ).fetchone()[0])
        if len(base) != expected:
            raise RuntimeError(f"V4.1 context coverage mismatch: {len(base)}/{expected}")
        if base.empty:
            raise RuntimeError("V4 base candidate not materialized")

        out = base[[
            "match_id", "match_date", "team_id", "player_id", "minutes_played", "started",
            "primary_role", "position_group", "position_mapping_status",
            "attacking_threat", "creation_progression", "defensive_contribution",
            "finishing", "discipline", "fallback_dimension_count", "rating_path",
            "match_rating_100", "match_rating_10", "match_rating_confidence",
            "match_rating_dimensions_used", "match_rating_context", "match_rating_status",
            "match_rating_version", "source_score_version",
        ]].copy()

        ga = pd.to_numeric(base["goals_against_on_pitch"], errors="raise").astype(float)
        new_rating = (pd.to_numeric(base["match_rating_10"], errors="raise") + GOALS_AGAINST_WEIGHT * ga).clip(3.0, 10.0)
        out["match_rating_10"] = new_rating
        out["match_rating_100"] = ((new_rating - 3.0) * (100.0 / 7.0)).clip(0.0, 100.0)
        out["match_rating_context"] = "POSITION_PRO_REFERENCE_PLUS_ON_PITCH_GA_PUBLIC_ANCHOR"
        out["match_rating_status"] = "V4_1_EXPERIMENTAL_ON_PITCH_RATED"
        out["match_rating_version"] = NEW_VERSION
        out["source_score_version"] = SOURCE_VERSION

        con.execute("DELETE FROM player_match_rating WHERE match_rating_version=?", [NEW_VERSION])
        con.register("v41_df", out)
        cols = list(out.columns)
        con.execute(
            f"INSERT INTO player_match_rating ({', '.join(cols)}) SELECT {', '.join(cols)} FROM v41_df"
        )
        con.unregister("v41_df")

    delta = new_rating - pd.to_numeric(base["match_rating_10"], errors="coerce")
    print("PERF-18 MATCH RATING V4.1 EXPERIMENTAL ON-PITCH: MATERIALIZED")
    print(f"version={NEW_VERSION}")
    print(f"rows={len(out)} matches={out['match_id'].nunique()}")
    print(f"goals_against_weight={GOALS_AGAINST_WEIGHT:+.2f}")
    print(f"mean={out['match_rating_10'].mean():.3f} median={out['match_rating_10'].median():.3f}")
    print(f"mean_delta_vs_v4={delta.mean():+.3f} min_delta={delta.min():+.3f}")
    print("timing_precision=" + str(base["timing_precision"].value_counts().to_dict()))
    print(f"boundary_ambiguity_rows={(base['boundary_ambiguity_goals'] > 0).sum()}")
    print("V4 remains experimental; no production access layer was changed.")


if __name__ == "__main__":
    main()
