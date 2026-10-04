"""Validate the unified PERF-18 Match Rating V5 candidate.

This is the last pre-promotion contract. It validates route coverage and lineage but does
not change the active app/access version.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
DEFAULT_METADATA = ROOT / "dsai" / "output" / "perf18_v5_candidate" / "match_rating_v5_candidate_metadata.json"
V2_VERSION = "match_rating_v0.2-candidate"
OUTFIELD_VERSION = "match_rating_v0.4.1-experimental-onpitch"
FINAL_VERSION = "match_rating_v0.5-candidate"

OUTFIELD_PATHS = {"OUTFIELD_PERF18_ANCHORED"}
GK_PATH = "GOALKEEPER_PERF18_SHOT90_DIST10"
FALLBACK_PATH = "OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate unified PERF-18 Match Rating V5 candidate")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    p.add_argument("--outfield-player", default="", help="Optional private local sample; omitted in public validation output")
    p.add_argument("--goalkeeper", default="", help="Optional private local sample; omitted in public validation output")
    return p.parse_args()


def spearman(a: pd.Series, b: pd.Series) -> float | None:
    aa = pd.to_numeric(a, errors="coerce")
    bb = pd.to_numeric(b, errors="coerce")
    valid = aa.notna() & bb.notna()
    if int(valid.sum()) < 3:
        return None
    return float(aa[valid].rank(method="average").corr(bb[valid].rank(method="average")))


def sample_player(frame: pd.DataFrame, needle: str, title: str) -> None:
    key = str(needle).strip().lower()
    x = frame.loc[frame["display_name"].astype(str).str.lower().str.contains(key, regex=False)].copy()
    if x.empty:
        print(f"\n{title}: no rows matched {needle!r}")
        return
    cols = [
        "match_date", "display_name", "position_group", "rating_path", "minutes_played",
        "score_for", "score_against", "match_rating_10", "match_rating_confidence",
        "attacking_threat", "creation_progression", "defensive_contribution",
        "finishing", "discipline",
    ]
    print(f"\n{title}: {needle}")
    print(x[cols].to_string(index=False))


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    meta_path = args.metadata.expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)
    if not meta_path.exists():
        raise FileNotFoundError(meta_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    with duckdb.connect(str(db), read_only=True) as con:
        final = con.execute(
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
            [FINAL_VERSION],
        ).df()
        expected_played = int(con.execute(
            "SELECT COUNT(*) FROM player_match WHERE minutes_played>0"
        ).fetchone()[0])
        expected_matches = int(con.execute(
            "SELECT COUNT(DISTINCT match_id) FROM player_match WHERE minutes_played>0"
        ).fetchone()[0])
        expected_outfield = int(con.execute(
            "SELECT COUNT(*) FROM player_match_rating WHERE match_rating_version=?",
            [OUTFIELD_VERSION],
        ).fetchone()[0])
        expected_gk = int(con.execute(
            "SELECT COUNT(*) FROM player_match_rating WHERE match_rating_version=? AND position_group='GK'",
            [V2_VERSION],
        ).fetchone()[0])
        expected_fallback = int(con.execute(
            "SELECT COUNT(*) FROM player_match_rating WHERE match_rating_version=? AND position_group='OTHER_OUTFIELD'",
            [V2_VERSION],
        ).fetchone()[0])
        joined = con.execute(
            """
            SELECT v5.match_id, v5.player_id, v5.rating_path,
                   v5.match_rating_10 AS v5_rating, v2.match_rating_10 AS v2_rating
            FROM player_match_rating v5
            JOIN player_match_rating v2
              ON v2.match_id=v5.match_id AND v2.team_id=v5.team_id AND v2.player_id=v5.player_id
             AND v2.match_rating_version=?
            WHERE v5.match_rating_version=?
            """,
            [V2_VERSION, FINAL_VERSION],
        ).df()
        first_date = con.execute(
            "SELECT MIN(match_date) FROM player_match_rating WHERE match_rating_version=?",
            [FINAL_VERSION],
        ).fetchone()[0]
        first_expected = int(con.execute(
            """
            SELECT COUNT(*)
            FROM player_match pm JOIN matches m ON m.match_id=pm.match_id
            WHERE pm.minutes_played>0 AND m.match_date=?
            """,
            [first_date],
        ).fetchone()[0]) if first_date is not None else 0

    if final.empty:
        raise RuntimeError("V5 candidate not materialized")

    rows = len(final)
    matches = int(final["match_id"].nunique())
    nulls = int(final["match_rating_10"].isna().sum())
    duplicates = int(final.duplicated(["match_id", "player_id"]).sum())
    out_of_range = int((~final["match_rating_10"].between(3.0, 10.0)).sum())
    route_counts = final["rating_path"].value_counts().to_dict()
    outfield_rows = int(final["rating_path"].isin(OUTFIELD_PATHS).sum())
    gk_rows = int((final["rating_path"] == GK_PATH).sum())
    fallback_rows = int((final["rating_path"] == FALLBACK_PATH).sum())
    unknown_routes = sorted(set(final["rating_path"].astype(str)) - OUTFIELD_PATHS - {GK_PATH, FALLBACK_PATH})

    fallback = final.loc[final["rating_path"] == FALLBACK_PATH].copy()
    fallback_bad_role = int((fallback["position_group"] != "OTHER_OUTFIELD").sum())
    fallback_bad_context = int((fallback["match_rating_context"] != "ROLE_UNAVAILABLE_V2_FALLBACK").sum())
    fallback_join = joined.loc[joined["rating_path"] == FALLBACK_PATH]
    fallback_max_error = (
        float((fallback_join["v5_rating"] - fallback_join["v2_rating"]).abs().max())
        if not fallback_join.empty else None
    )

    gk = final.loc[final["rating_path"] == GK_PATH].copy()
    gk_bad_role = int((gk["position_group"] != "GK").sum())
    gk_bad_context = int((gk["match_rating_context"] != "GOALKEEPER_SEPARATE_PRO_REFERENCE_SHOT90_DIST10").sum())

    first_rows = int((pd.to_datetime(final["match_date"]) == pd.Timestamp(first_date)).sum()) if first_date is not None else 0
    gk_meta = meta.get("goalkeeper", {})
    gate_meta = meta.get("goalkeeper_final_gate", {})
    gk_weight_gate = bool(
        abs(float(gk_meta.get("shot_weight", -1)) - 0.90) <= 1e-12
        and abs(float(gk_meta.get("distribution_weight", -1)) - 0.10) <= 1e-12
        and bool(gate_meta.get("overall_gate"))
        and bool(gate_meta.get("monotonicity_gate"))
        and bool(gate_meta.get("local_weight_sensitivity_gate"))
    )

    route_gate = bool(
        outfield_rows == expected_outfield
        and gk_rows == expected_gk
        and fallback_rows == expected_fallback
        and not unknown_routes
    )
    fallback_gate = bool(
        fallback_bad_role == 0
        and fallback_bad_context == 0
        and fallback_max_error is not None
        and fallback_max_error <= 1e-12
    )
    coverage_gate = bool(rows == expected_played and matches == expected_matches and first_rows == first_expected)
    integrity_gate = bool(nulls == 0 and duplicates == 0 and out_of_range == 0)

    print("PERF-18 UNIFIED MATCH RATING V5 CANDIDATE VALIDATION")
    print(f"version={FINAL_VERSION}")
    print(f"coverage={rows}/{expected_played} matches={matches}/{expected_matches}")
    print(f"first_match_coverage={first_rows}/{first_expected}")
    print(f"null_ratings={nulls} duplicates={duplicates} out_of_range={out_of_range}")
    print("route_counts=" + str(route_counts))
    print(
        "expected_routes="
        + str({"outfield": expected_outfield, "goalkeeper": expected_gk, "fallback": expected_fallback})
    )
    print(f"coverage_gate={'PASS' if coverage_gate else 'FAIL'}")
    print(f"route_gate={'PASS' if route_gate else 'FAIL'} unknown_routes={unknown_routes}")
    print(f"fallback_gate={'PASS' if fallback_gate else 'FAIL'} max_error_vs_v2={fallback_max_error}")
    print(f"gk_weight_gate={'PASS' if gk_weight_gate else 'FAIL'}")

    print(
        "distribution_v5="
        + str({
            "mean": float(final["match_rating_10"].mean()),
            "median": float(final["match_rating_10"].median()),
            "q10": float(final["match_rating_10"].quantile(0.10)),
            "q90": float(final["match_rating_10"].quantile(0.90)),
            "min": float(final["match_rating_10"].min()),
            "max": float(final["match_rating_10"].max()),
        })
    )

    if not joined.empty:
        diff = joined["v5_rating"] - joined["v2_rating"]
        print(
            "V5_VS_V2="
            + str({
                "n": int(len(joined)),
                "pearson": float(joined["v5_rating"].corr(joined["v2_rating"])),
                "spearman": spearman(joined["v5_rating"], joined["v2_rating"]),
                "mean_delta": float(diff.mean()),
                "median_abs_delta": float(diff.abs().median()),
            })
        )

    print("\nBY RESULT")
    print(final.groupby("result")["match_rating_10"].agg(["count", "mean", "median"]).reset_index().to_string(index=False))

    heavy = final.loc[(final["score_against"] - final["score_for"]) >= 2].copy()
    if not heavy.empty:
        heavy_summary = (
            heavy.groupby(["match_date", "score_for", "score_against"])["match_rating_10"]
            .agg(players="count", mean="mean", median="median")
            .reset_index().sort_values("match_date")
        )
        print("\nHEAVY LOSSES — FULL TEAM")
        print(heavy_summary.to_string(index=False))

    if args.outfield_player:
        sample_player(final, args.outfield_player, "OUTFIELD SAMPLE")
    if args.goalkeeper:
        sample_player(final, args.goalkeeper, "GOALKEEPER SAMPLE")

    contract = bool(
        coverage_gate and integrity_gate and route_gate and fallback_gate and gk_weight_gate
        and gk_bad_role == 0 and gk_bad_context == 0
        and str(meta.get("version")) == FINAL_VERSION
    )
    print("\nFINAL_CANDIDATE_CONTRACT=" + ("PASS" if contract else "FAIL"))
    print("Promotion status: BLOCKED until this contract passes; active V2 has not been changed.")
    if not contract:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
