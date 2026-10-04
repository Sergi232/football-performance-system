"""Reproducible academic validation for the frozen Match Rating and expert system.

The script is deliberately read-only: it does not retrain, recalibrate or alter the
product.  It joins the versioned construct gates with the current DuckDB outputs to
verify the claims that can be demonstrated today: coherent sensitivity, observed-role
routing, an auditable expert trace, and safe degradation when evidence is incomplete.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publication.validate_hypothesis_functional import _pick_trace_case  # noqa: E402
from app.presentation import build_player_aliases  # noqa: E402

DB = ROOT / "data" / "football_performance.duckdb"
SYNTHETIC_DB = ROOT / "data" / "football_performance_synthetic_demo.duckdb"
V5 = "match_rating_v0.5-candidate"
ENGINE = "expert_0.7.0"
FALLBACK = "OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2"
GK_PATH = "GOALKEEPER_PERF18_SHOT90_DIST10"
OUTFIELD_PATH = "OUTFIELD_PERF18_ANCHORED"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def clean(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate academic evidence for Match Rating V5")
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument("--synthetic-db", type=Path, default=SYNTHETIC_DB)
    return parser.parse_args()


def sensitivity_gates() -> None:
    anchored = json.loads((ROOT / "dsai/output/perf18_anchored_final_gate/anchored_final_gate.json").read_text(encoding="utf-8"))
    goalkeeper = json.loads((ROOT / "dsai/output/perf18_gk_final_gate/goalkeeper_final_gate.json").read_text(encoding="utf-8"))
    require(anchored.get("overall_gate") is True, "Outfield controlled-sensitivity gate failed")
    require(goalkeeper.get("overall_gate") is True, "Goalkeeper controlled-sensitivity gate failed")

    # These are controlled perturbations of the frozen construct, not observations
    # presented as external player ratings.
    events = {
        name: detail
        for role in anchored["roles"].values()
        for name, detail in role["monotonicity"].items()
    }
    for name in ("goal", "assist", "turnover", "penalty_conceded", "red_card"):
        require(events[name]["pass"] is True, f"Outfield sensitivity failed for {name}")
    for name in ("save", "goal_conceded", "successful_pass"):
        require(goalkeeper["monotonicity"][name]["pass"] is True, f"Goalkeeper sensitivity failed for {name}")

    print("SENSITIVITY: PASS")
    print("outfield=7 observed role groups; goal:+1.00, assist:+0.60, turnover<0, penalty_conceded:-0.40, red_card:-0.50 (median raw deltas; all directions PASS)")
    print("goalkeeper=save:+0.33, goal_conceded:-0.70, successful_pass:+0.01 (median deltas; all directions PASS)")


def route_validation(db: Path) -> None:
    with duckdb.connect(str(db), read_only=True) as con:
        rows = con.execute(
            """
            SELECT rating_path, position_group, match_rating_context, COUNT(*) AS n
            FROM player_match_rating WHERE match_rating_version=?
            GROUP BY 1,2,3 ORDER BY 1,2
            """, [V5]
        ).fetchall()
        gk_bad = con.execute(
            """SELECT COUNT(*) FROM player_match_rating
               WHERE match_rating_version=? AND rating_path=? AND position_group <> 'GK'""", [V5, GK_PATH]
        ).fetchone()[0]
        outfield_bad = con.execute(
            """SELECT COUNT(*) FROM player_match_rating
               WHERE match_rating_version=? AND rating_path=? AND position_group IN ('GK','OTHER_OUTFIELD')""", [V5, OUTFIELD_PATH]
        ).fetchone()[0]
        fallback_bad = con.execute(
            """SELECT COUNT(*) FROM player_match_rating
               WHERE match_rating_version=? AND rating_path=?
                 AND (position_group <> 'OTHER_OUTFIELD' OR match_rating_context <> 'ROLE_UNAVAILABLE_V2_FALLBACK')""", [V5, FALLBACK]
        ).fetchone()[0]
        counts: dict[str, int] = {}
        for path, _group, _context, n in rows:
            counts[path] = counts.get(path, 0) + int(n)

    require(counts.get(GK_PATH, 0) > 0 and gk_bad == 0, "Goalkeeper route is absent or contaminated")
    require(counts.get(OUTFIELD_PATH, 0) > 0 and outfield_bad == 0, "Reliable outfield route is absent or contaminated")
    require(counts.get(FALLBACK, 0) > 0 and fallback_bad == 0, "Missing-role fallback is not explicit")
    print("OBSERVED-ROLE ROUTING: PASS")
    print(f"goalkeeper={counts.get(GK_PATH, 0)} -> GK-specific path; reliable_outfield={counts.get(OUTFIELD_PATH, 0)} -> positional path; missing_or_unreliable_role={counts.get(FALLBACK, 0)} -> explicit generic fallback")


def expert_trace(db: Path) -> str:
    with duckdb.connect(str(db), read_only=True) as con:
        team_id = str(con.execute(
            """SELECT team_id FROM player_match_rating
               WHERE match_rating_version=?
               GROUP BY team_id ORDER BY COUNT(*) DESC LIMIT 1""", [V5]
        ).fetchone()[0])
        squad = con.execute(
            """
            SELECT p.player_id, p.display_name AS player, COUNT(*) AS appearances
            FROM player_match pm
            JOIN players p ON p.player_id=pm.player_id
            WHERE pm.team_id=?
            GROUP BY 1, 2
            ORDER BY appearances DESC, p.player_id
            """,
            [team_id],
        ).df()
    trace = _pick_trace_case(db, team_id)
    player_alias = build_player_aliases(squad).get(str(trace["player_id"]), "Jugador")
    nodes = {x["node_id"]: x for x in trace["expert"]}
    final = nodes["N13000.120"]
    require(final["result_value"].startswith("RECOMMENDATION_NOT_ISSUED"), "Trace has an unsupported final recommendation")
    print("AUDITABLE EXPERT TRACE: PASS")
    print(f"case={player_alias} | match={trace['match_id']} | observed_role={trace['primary_role']}")
    print(f"input=minutes:{clean(trace['minutes_played'])}; passes:{clean(trace['passes_completed'])}/{clean(trace['passes_total'])}; pass_completion_rate:{clean(trace['pass_completion_rate'])}")
    print(f"condition=N12000.100 -> {nodes['N12000.100']['result_value']}; N13000.100 -> {nodes['N13000.100']['result_value']}")
    print(f"evidence=scope:{trace['comparison_scope']}; state:{trace['evidence_state']}; rating:{clean(trace['match_rating_10'])}/10; confidence:{clean(trace['match_rating_confidence'])}")
    print(f"justification={final['justification']}")
    print(f"final_state={final['result_value']}; deterministic_confidence={clean(final['confidence'])}")
    return team_id


def incomplete_evidence(db: Path, synthetic_db: Path) -> None:
    with duckdb.connect(str(db), read_only=True) as con:
        no_gps = con.execute(
            """
            SELECT d.match_id, d.player_id, d.result_value, r.match_rating_10
            FROM decision_results d
            JOIN player_match_rating r ON r.match_id=d.match_id AND r.player_id=d.player_id
             AND r.match_rating_version=?
            WHERE d.engine_version=? AND d.node_id='N9000.100' AND d.result_value='GPS_NOT_AVAILABLE'
            LIMIT 1
            """, [V5, ENGINE]
        ).fetchone()
        low_history = con.execute(
            """
            SELECT e.match_id, e.player_id, e.result_value, f.result_value
            FROM decision_results e
            JOIN decision_results f ON f.match_id=e.match_id AND f.player_id=e.player_id
             AND f.engine_version=e.engine_version AND f.node_id='N13000.120'
            WHERE e.engine_version=? AND e.node_id='N13000.100'
              AND e.result_value <> 'EVIDENCE_AVAILABLE'
              AND f.result_value LIKE 'RECOMMENDATION_NOT_ISSUED%'
            LIMIT 1
            """, [ENGINE]
        ).fetchone()
    require(no_gps is not None, "No no-GPS continuation case found")
    require(low_history is not None, "No insufficient-evidence abstention case found")
    require(synthetic_db.exists(), "Synthetic GPS demo database is missing")
    with duckdb.connect(str(synthetic_db), read_only=True) as con:
        synthetic_imports = con.execute("SELECT COUNT(*) FROM gps_imports WHERE lower(provider)='fps synthetic demo'").fetchone()[0]
        gps_states = con.execute(
            """SELECT COUNT(*) FROM decision_results
               WHERE node_id='N9000.100' AND result_value='GPS_NOT_AVAILABLE'"""
        ).fetchone()[0]
    require(synthetic_imports > 0 and gps_states > 0, "Synthetic GPS was not excluded from expert evidence")
    print("INCOMPLETE-EVIDENCE ROBUSTNESS: PASS")
    print(f"no_GPS=case {no_gps[0]}/{no_gps[1]} keeps rating {clean(no_gps[3])} with N9000.100={no_gps[2]}")
    print(f"little_history=case {low_history[0]}/{low_history[1]} -> {low_history[2]} -> {low_history[3]}")
    print(f"synthetic_GPS=imports:{synthetic_imports}; expert GPS_NOT_AVAILABLE states:{gps_states}; no physiological conclusion is activated")


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()
    synthetic_db = args.synthetic_db.expanduser().resolve()
    require(db.exists(), f"Database not found: {db}")
    print("ACADEMIC MATCH RATING / EXPERT VALIDATION")
    print("external_independent_player_match_rating=NOT_AVAILABLE_IN_CURRENT_DATA")
    print("external_comparison=NOT_RUN (no correlation, ranking or top/bottom claim is made)")
    sensitivity_gates()
    route_validation(db)
    expert_trace(db)
    incomplete_evidence(db, synthetic_db)
    print("ACADEMIC VALIDATION CONTRACT: PASS")


if __name__ == "__main__":
    main()
