"""Validate the local PERF-18 Match Rating V4 experimental outfield candidate.

The validator checks data/contract integrity and reports football sanity cases. It
DOES NOT promote V4. Goalkeeper validation and on-pitch goal context remain separate
requirements before any production switch.
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
DEFAULT_METADATA = ROOT / "dsai" / "output" / "perf18_v4_local" / "match_rating_v4_local_metadata.json"
V2_VERSION = "match_rating_v0.2-candidate"
V4_VERSION = "match_rating_v0.4-experimental-outfield"
VALID_ROLES = {"CB", "FB", "DM", "CM", "AM", "W", "ST"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate PERF-18 Match Rating V4 experimental outfield")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    p.add_argument("--player", default="Ale")
    return p.parse_args()


def spearman(a: pd.Series, b: pd.Series) -> float | None:
    aa = pd.to_numeric(a, errors="coerce")
    bb = pd.to_numeric(b, errors="coerce")
    valid = aa.notna() & bb.notna()
    if int(valid.sum()) < 3:
        return None
    return float(aa[valid].rank(method="average").corr(bb[valid].rank(method="average")))


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    metadata_path = args.metadata.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"V4 metadata not found: {metadata_path}. Run V4 builder first.")
    meta = json.loads(metadata_path.read_text(encoding="utf-8"))

    with duckdb.connect(str(db_path), read_only=True) as con:
        v4 = con.execute(
            """
            SELECT r.*, p.display_name, tm.score_for, tm.score_against,
                   CASE
                     WHEN tm.score_for > tm.score_against THEN 'WIN'
                     WHEN tm.score_for < tm.score_against THEN 'LOSS'
                     ELSE 'DRAW'
                   END AS result
            FROM player_match_rating r
            JOIN players p ON p.player_id=r.player_id
            JOIN team_match tm ON tm.match_id=r.match_id AND tm.team_id=r.team_id
            WHERE r.match_rating_version=?
            ORDER BY r.match_date, p.display_name
            """,
            [V4_VERSION],
        ).df()
        expected = int(con.execute(
            "SELECT COUNT(*) FROM player_match_rating WHERE match_rating_version=? AND rating_path='OUTFIELD'",
            [V2_VERSION],
        ).fetchone()[0])
        joined = con.execute(
            """
            SELECT
                v4.match_id, v4.player_id, v4.match_date, v4.position_group,
                v4.match_rating_10 AS v4_rating,
                v2.match_rating_10 AS v2_rating,
                p.display_name, tm.score_for, tm.score_against
            FROM player_match_rating v4
            JOIN player_match_rating v2
              ON v2.match_id=v4.match_id AND v2.team_id=v4.team_id AND v2.player_id=v4.player_id
             AND v2.match_rating_version=?
            JOIN players p ON p.player_id=v4.player_id
            JOIN team_match tm ON tm.match_id=v4.match_id AND tm.team_id=v4.team_id
            WHERE v4.match_rating_version=?
            ORDER BY v4.match_date, p.display_name
            """,
            [V2_VERSION, V4_VERSION],
        ).df()

    if v4.empty:
        raise RuntimeError("V4 candidate not materialized")

    rows = len(v4)
    nulls = int(v4["match_rating_10"].isna().sum())
    duplicates = int(v4.duplicated(["match_id", "player_id"]).sum())
    out_of_range = int((~v4["match_rating_10"].between(3.0, 10.0)).sum())
    bad_roles = sorted(set(v4["position_group"].dropna().astype(str)) - VALID_ROLES)
    goalkeeper_rows = int(v4["rating_path"].astype(str).str.contains("GOALKEEPER", case=False, na=False).sum())

    print("PERF-18 MATCH RATING V4 EXPERIMENTAL VALIDATION")
    print(f"version={V4_VERSION}")
    print(f"coverage={rows}/{expected} expected_v2_outfield_rows")
    print(f"null_ratings={nulls} duplicates={duplicates} out_of_range={out_of_range}")
    print(f"bad_roles={bad_roles} goalkeeper_rows={goalkeeper_rows}")
    print("mapping_status=" + str(v4["position_mapping_status"].value_counts().to_dict()))
    print(
        "distribution_v4="
        + str({
            "mean": float(v4["match_rating_10"].mean()),
            "median": float(v4["match_rating_10"].median()),
            "q10": float(v4["match_rating_10"].quantile(0.10)),
            "q90": float(v4["match_rating_10"].quantile(0.90)),
            "min": float(v4["match_rating_10"].min()),
            "max": float(v4["match_rating_10"].max()),
        })
    )

    if not joined.empty:
        pearson = float(joined["v4_rating"].corr(joined["v2_rating"]))
        rho = spearman(joined["v4_rating"], joined["v2_rating"])
        diff = joined["v4_rating"] - joined["v2_rating"]
        print(
            "V4_VS_V2="
            + str({
                "n": int(len(joined)),
                "pearson": pearson,
                "spearman": rho,
                "mean_delta": float(diff.mean()),
                "median_abs_delta": float(diff.abs().median()),
            })
        )

    by_result = (
        v4.groupby("result", dropna=False)["match_rating_10"]
        .agg(["count", "mean", "median"])
        .reset_index()
    )
    print("\nBY RESULT")
    print(by_result.to_string(index=False))

    by_role = (
        v4.groupby("position_group", dropna=False)["match_rating_10"]
        .agg(["count", "mean", "median"])
        .reset_index()
        .sort_values("position_group")
    )
    print("\nBY ROLE")
    print(by_role.to_string(index=False))

    heavy = v4.loc[(v4["score_against"] - v4["score_for"]) >= 2].copy()
    if not heavy.empty:
        heavy_summary = (
            heavy.groupby(["match_date", "match_id", "score_for", "score_against"])["match_rating_10"]
            .agg(players="count", mean="mean", median="median")
            .reset_index()
            .sort_values("match_date")
        )
        print("\nHEAVY LOSSES")
        print(heavy_summary.to_string(index=False))

    needle = str(args.player).strip().lower()
    player_rows = v4.loc[v4["display_name"].astype(str).str.lower().str.contains(needle, regex=False)].copy()
    if not player_rows.empty:
        cols = [
            "match_date", "display_name", "position_group", "minutes_played",
            "score_for", "score_against", "match_rating_10", "match_rating_confidence",
            "attacking_threat", "creation_progression", "defensive_contribution", "finishing", "discipline",
        ]
        print(f"\nPLAYER SAMPLE: {args.player}")
        print(player_rows[cols].to_string(index=False))

    cutoff = pd.Timestamp(meta["local_first_match_date"])
    local_first = pd.Timestamp(v4["match_date"].min())
    chronology_pass = bool(cutoff.normalize() == local_first.normalize())
    contract_pass = bool(
        rows == expected
        and nulls == 0
        and duplicates == 0
        and out_of_range == 0
        and not bad_roles
        and goalkeeper_rows == 0
        and chronology_pass
    )

    print("\nREFERENCE")
    print("professional_reference_rows_by_role=" + str(meta.get("professional_reference_rows_by_role")))
    print(f"reference_policy={meta.get('professional_reference_policy')}")
    print(f"chronology_metadata_gate={'PASS' if chronology_pass else 'FAIL'}")
    print(f"V4_OUTFIELD_CONTRACT={'PASS' if contract_pass else 'FAIL'}")
    print("Promotion status: BLOCKED pending football sanity review, separate goalkeeper model, and on-pitch context decision.")

    if not contract_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
