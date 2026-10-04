"""Compare original and frozen-artifact V5 rows with strict numeric tolerance."""
from __future__ import annotations
import argparse
import numpy as np
import duckdb

COLUMNS = ["match_rating_10", "attacking_threat", "creation_progression", "defensive_contribution", "finishing", "discipline", "match_rating_confidence"]

def load(db: str):
    with duckdb.connect(db, read_only=True) as con:
        return con.execute("""SELECT match_id, player_id, match_rating_10, attacking_threat,
        creation_progression, defensive_contribution, finishing, discipline, rating_path,
        match_rating_confidence, match_rating_dimensions_used
        FROM player_match_rating WHERE match_rating_version='match_rating_v0.5-candidate'
        ORDER BY match_id, player_id""").df()

def main():
    p=argparse.ArgumentParser(); p.add_argument("--original",required=True); p.add_argument("--frozen",required=True); p.add_argument("--tolerance",type=float,default=1e-12); a=p.parse_args()
    original, frozen = load(a.original), load(a.frozen)
    merged=original.merge(frozen,on=["match_id","player_id"],suffixes=("_original","_frozen"),validate="one_to_one")
    if len(original)!=len(frozen) or len(merged)!=len(original): raise SystemExit("FAIL row coverage")
    max_error=0.0
    for col in COLUMNS:
        left=merged[col+"_original"].to_numpy(dtype=float); right=merged[col+"_frozen"].to_numpy(dtype=float)
        if not np.array_equal(np.isnan(left),np.isnan(right)): raise SystemExit(f"FAIL null coverage {col}")
        error=float(np.nanmax(np.abs(left-right))) if len(left) else 0.0
        max_error=max(max_error,error)
    if not (merged.rating_path_original==merged.rating_path_frozen).all(): raise SystemExit("FAIL rating_path")
    if not (merged.match_rating_dimensions_used_original==merged.match_rating_dimensions_used_frozen).all(): raise SystemExit("FAIL dimensions")
    if max_error>a.tolerance: raise SystemExit(f"FAIL max_abs_error={max_error}")
    print(f"FROZEN_EQUIVALENCE: PASS rows={len(merged)} max_abs_error={max_error:.17g} tolerance={a.tolerance:.1e}")
if __name__=="__main__": main()
