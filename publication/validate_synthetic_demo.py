"""Validate the redistributable synthetic public product demo.

The gate checks that the database is generated from scratch, contains no professional
source rows, exposes the current product contracts, and can feed the real read-only
app/report access layers. It does not claim to revalidate the calibrated Match Rating
or Performance Index research models: those two layers are explicit compatibility
fixtures in the synthetic demo.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance_synthetic_demo.duckdb"
TEAM_ID = "SYN_TEAM_001"
DEMO_VERSION = "synthetic_public_demo_v0.1.0"
MATCH_RATING_VERSION = "match_rating_v0.5-candidate"
SCORE_VERSION = "performance_score_v0.2-experimental"
EXPERT_VERSION = "expert_0.7.0"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate the synthetic public FPS demo DB")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--rebuild", action="store_true", help="Rebuild the DB from scratch before validation")
    return p.parse_args()


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    args = parse_args()
    db = args.db.expanduser().resolve()

    if args.rebuild:
        from publication.build_synthetic_demo import build
        build(db, 20261003, True)

    if not db.exists():
        raise FileNotFoundError(f"Synthetic demo DB not found: {db}. Run with --rebuild.")

    os.environ["FPS_DEMO_MODE"] = "1"
    os.environ.setdefault("FPS_ACCESS_ROLE", "SUPERADMIN")

    with duckdb.connect(str(db), read_only=True) as con:
        meta = con.execute(
            """
            SELECT demo_version, data_origin, seed, contains_professional_source_rows,
                   redistribution_status, match_rating_fixture_notice, performance_index_fixture_notice
            FROM public_demo_metadata
            LIMIT 1
            """
        ).fetchone()
        _check(meta is not None, "public_demo_metadata missing")
        _check(meta[0] == DEMO_VERSION, f"unexpected demo_version: {meta[0]}")
        _check(meta[1] == "SYNTHETIC_GENERATED_FROM_SCRATCH", f"unexpected data_origin: {meta[1]}")
        _check(meta[3] is False, "contains_professional_source_rows must be FALSE")
        _check(meta[4] == "REDISTRIBUTABLE_SYNTHETIC_DEMO", f"unexpected redistribution status: {meta[4]}")

        source_types = {str(r[0]) for r in con.execute("SELECT DISTINCT source_type FROM matches").fetchall()}
        _check(source_types == {"synthetic_public_demo"}, f"unexpected match source types: {source_types}")
        raw_sources = {str(r[0]) for r in con.execute("SELECT DISTINCT source_type FROM player_match_raw_stats").fetchall()}
        _check(raw_sources == {"synthetic_public_demo"}, f"unexpected raw source types: {raw_sources}")

        match_count = int(con.execute("SELECT COUNT(*) FROM matches").fetchone()[0])
        player_count = int(con.execute("SELECT COUNT(*) FROM players").fetchone()[0])
        player_match_count = int(con.execute("SELECT COUNT(*) FROM player_match").fetchone()[0])
        played_count = int(con.execute("SELECT COUNT(*) FROM player_match WHERE minutes_played>0").fetchone()[0])
        feature01 = int(con.execute("SELECT COUNT(*) FROM player_match_features WHERE feature_version='0.1.0'").fetchone()[0])
        feature02 = int(con.execute("SELECT COUNT(*) FROM player_match_features WHERE feature_version='0.2.0'").fetchone()[0])
        feature03 = int(con.execute("SELECT COUNT(*) FROM player_match_features WHERE feature_version='0.3.0'").fetchone()[0])
        analytics_rows = int(con.execute("SELECT COUNT(*) FROM analytics_evidence WHERE analytics_version='analytics_0.1.0'").fetchone()[0])
        expert_rows = int(con.execute("SELECT COUNT(*) FROM decision_results WHERE engine_version=?", [EXPERT_VERSION]).fetchone()[0])
        n13000_rows = int(con.execute("SELECT COUNT(*) FROM decision_results WHERE engine_version=? AND node_id LIKE 'N13000.%'", [EXPERT_VERSION]).fetchone()[0])
        rating_rows = int(con.execute("SELECT COUNT(*) FROM player_match_rating WHERE match_rating_version=?", [MATCH_RATING_VERSION]).fetchone()[0])
        score_rows = int(con.execute("SELECT COUNT(*) FROM player_match_performance_score WHERE score_version=?", [SCORE_VERSION]).fetchone()[0])
        gps_rows = int(con.execute("SELECT COUNT(*) FROM player_match_gps_summary WHERE summary_version='gps_physical_summary_v0.1-descriptive' AND import_rank=1").fetchone()[0])

        _check(match_count == 12, f"expected 12 synthetic matches, got {match_count}")
        _check(player_count == 18, f"expected 18 synthetic players, got {player_count}")
        _check(player_match_count == 216, f"expected 216 player_match rows, got {player_match_count}")
        _check(played_count > 0, "no played appearances")
        _check(feature01 == player_match_count * 28, f"FEATURE-01 row mismatch: {feature01}")
        _check(feature02 > 0 and feature03 > 0, "temporal feature layers missing")
        _check(analytics_rows > 0, "ANALYTICS-01 rows missing")
        _check(expert_rows > 0 and n13000_rows == player_match_count * 3, "final expert engine incomplete")
        _check(rating_rows == played_count, f"synthetic rating coverage mismatch: {rating_rows}/{played_count}")
        _check(score_rows == played_count, f"synthetic Performance Index fixture mismatch: {score_rows}/{played_count}")
        _check(gps_rows == played_count, f"GPS summary coverage mismatch: {gps_rows}/{played_count}")

        leaked = con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT display_name AS txt FROM teams
                UNION ALL SELECT display_name FROM players
                UNION ALL SELECT COALESCE(source_name,'') FROM teams
                UNION ALL SELECT COALESCE(source_name,'') FROM players
            )
            WHERE lower(txt) LIKE '%alav%'
               OR lower(txt) LIKE '%deportivo%'
               OR lower(txt) LIKE '%opta%'
               OR lower(txt) LIKE '%pannadata%'
            """
        ).fetchone()[0]
        _check(int(leaked) == 0, f"professional-source text leaked into synthetic demo: {leaked}")

    from app.attention_access import get_attention_summary
    from app.data_access import (
        get_engine_status,
        get_latest_player_gate,
        get_match_lineup,
        get_squad_summary,
        get_team_matches,
        get_team_overview,
        list_base_features,
        list_teams,
    )
    from app.gps_physical_access import get_gps_summary_status, get_team_gps_match_coverage
    from app.match_rating_access import get_match_ratings, get_team_player_rating_snapshot
    from app.performance_score_access import get_team_score_snapshot
    from reports.data_builder import build_match_report_data, build_player_report_data, build_team_report_data

    teams = list_teams(db)
    _check(not teams.empty and TEAM_ID in teams["team_id"].astype(str).tolist(), "app list_teams cannot see synthetic team")
    overview = get_team_overview(db, TEAM_ID)
    matches = get_team_matches(db, TEAM_ID)
    squad = get_squad_summary(db, TEAM_ID)
    features = list_base_features(db)
    engine = get_engine_status(db)
    gps_status = get_gps_summary_status(db)
    gps_coverage = get_team_gps_match_coverage(db, TEAM_ID)
    attention = get_attention_summary(db, TEAM_ID)

    _check(int(overview["matches"]) == 12, "app team overview mismatch")
    _check(len(squad) == 18, "app squad mismatch")
    _check(len(features) == 28, f"app base feature count mismatch: {len(features)}")
    _check(int(engine["unsafe_final_states"]) == 0, "unsafe N13000 state found")
    _check(int(gps_status["rows"]) == played_count, "app GPS status mismatch")
    _check(len(gps_coverage) == 12, "app GPS match coverage mismatch")
    _check(attention is not None, "attention access failed")

    latest_match = str(matches.iloc[0]["match_id"])
    player_id = str(squad.iloc[0]["player_id"])
    lineup = get_match_lineup(db, TEAM_ID, latest_match)
    ratings = get_match_ratings(db, TEAM_ID, latest_match)
    rating_snapshot = get_team_player_rating_snapshot(db, TEAM_ID)
    score_snapshot = get_team_score_snapshot(db, TEAM_ID)
    gate = get_latest_player_gate(db, TEAM_ID, player_id)
    _check(not lineup.empty and not ratings.empty, "Match Mode read-only access failed")
    _check(not rating_snapshot.empty, "team Match Rating snapshot missing")
    _check(not score_snapshot.empty, "Performance Index snapshot missing")
    _check(gate is not None and str(gate.get("final_status", "")).startswith("RECOMMENDATION_NOT_ISSUED_"), "N13000 safety gate unavailable")

    team_payload = build_team_report_data(db, TEAM_ID)
    player_payload = build_player_report_data(db, TEAM_ID, player_id)
    match_payload = build_match_report_data(db, TEAM_ID, latest_match)
    _check(team_payload.get("language") == "es", "team report payload language mismatch")
    _check(player_payload.get("language") == "es", "player report payload language mismatch")
    _check(match_payload.get("language") == "es", "match report payload language mismatch")
    _check(bool(team_payload.get("gps", {}).get("contains_synthetic_demo")), "team report does not identify synthetic GPS")

    print("SYNTHETIC PUBLIC DEMO CONTRACT: PASS")
    print(f"demo_version={DEMO_VERSION}")
    print(f"db={db}")
    print(f"matches={match_count} players={player_count} player_match={player_match_count} played={played_count}")
    print(f"FEATURE-01={feature01} FEATURE-02={feature02} FEATURE-03={feature03}")
    print(f"analytics_rows={analytics_rows} expert_rows={expert_rows} N13000={n13000_rows}")
    print(f"ratings={rating_rows} performance_index={score_rows} gps={gps_rows}")
    print("app_read_layer=PASS")
    print("report_payloads=PASS")
    print("professional_source_rows=0")
    print("redistribution_status=REDISTRIBUTABLE_SYNTHETIC_DEMO")
    print("rating_index_notice=UI compatibility fixtures; not calibrated-model revalidation")


if __name__ == "__main__":
    main()
