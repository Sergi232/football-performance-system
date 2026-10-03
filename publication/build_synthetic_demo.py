"""Build a deterministic, redistributable synthetic DuckDB for the public product demo.

This dataset is generated from scratch and contains no rows copied from the private
professional demonstrator. It exists to make the Streamlit product reproducible from
a clean Git clone when source-data redistribution rights are unavailable.

The script intentionally distinguishes two kinds of outputs:
- FEATURE-01/02/03, ANALYTICS-01, EXPERT-01..07, GPS summary and attention flags are
  built by the project's real deterministic code over synthetic raw inputs;
- Match Rating V5 and Performance Index rows are compatibility fixtures with explicit
  synthetic provenance, because the validated research calibration assets used by the
  professional demonstrator are not redistributable inputs to this public demo.

The synthetic rating/index values demonstrate UI/data contracts only. They are NOT a
revalidation or reproduction of the calibrated sports models.
"""
from __future__ import annotations

import argparse
import importlib
import json
import random
import subprocess
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "football_performance_synthetic_demo.duckdb"
DEMO_VERSION = "synthetic_public_demo_v0.1.0"
RAW_SOURCE_TYPE = "synthetic_public_demo"
TEAM_ID = "SYN_TEAM_001"
RNG_SEED = 20261003
MATCH_RATING_VERSION = "match_rating_v0.5-candidate"
SCORE_VERSION = "performance_score_v0.2-experimental"
EXPERT_VERSION = "expert_0.7.0"

PLAYER_SPECS = [
    ("SYN_P01", "Portero Demo", 1, "Goalkeeper", "GK"),
    ("SYN_P02", "Central Demo A", 4, "Defender | Centre", "CB"),
    ("SYN_P03", "Central Demo B", 5, "Defender | Centre", "CB"),
    ("SYN_P04", "Lateral Demo I", 3, "Defender | Left", "FB_WB"),
    ("SYN_P05", "Lateral Demo D", 2, "Defender | Right", "FB_WB"),
    ("SYN_P06", "Medio Demo A", 6, "Defensive Midfielder | Centre", "DM_CM"),
    ("SYN_P07", "Medio Demo B", 8, "Midfielder | Centre", "DM_CM"),
    ("SYN_P08", "Interior Demo", 14, "Midfielder | Centre", "DM_CM"),
    ("SYN_P09", "Extremo Demo I", 11, "Attacking Midfielder | Left", "AM_W"),
    ("SYN_P10", "Extremo Demo D", 7, "Attacking Midfielder | Right", "AM_W"),
    ("SYN_P11", "Delantero Demo", 9, "Striker | Centre", "ST"),
    ("SYN_P12", "Portero Demo B", 13, "Goalkeeper", "GK"),
    ("SYN_P13", "Defensa Demo C", 15, "Defender | Centre", "CB"),
    ("SYN_P14", "Carrilero Demo", 17, "Defender | Right", "FB_WB"),
    ("SYN_P15", "Medio Demo C", 18, "Midfielder | Centre", "DM_CM"),
    ("SYN_P16", "Mediapunta Demo", 10, "Attacking Midfielder | Centre", "AM_W"),
    ("SYN_P17", "Atacante Demo A", 19, "Striker | Centre", "ST"),
    ("SYN_P18", "Atacante Demo B", 20, "Attacking Midfielder | Left", "AM_W"),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build the fully synthetic public product demo DB")
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--seed", type=int, default=RNG_SEED)
    p.add_argument("--force", action="store_true", help="Replace an existing output DB")
    return p.parse_args()


def _run(*args: str) -> None:
    print("$ " + " ".join(args))
    subprocess.run(list(args), cwd=ROOT, check=True)


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _formation(match_index: int) -> str:
    return ("4-3-3", "4-2-3-1", "3-4-2-1")[match_index % 3]


def _played_ids(match_index: int) -> list[str]:
    """Return 16 played players; rotate two bench-only rows without role invention."""
    all_ids = [row[0] for row in PLAYER_SPECS]
    omitted = {all_ids[(match_index + 12) % len(all_ids)], all_ids[(match_index + 15) % len(all_ids)]}
    # Always keep one goalkeeper among the played rows.
    omitted.discard("SYN_P01" if match_index % 3 else "SYN_P12")
    while len(omitted) < 2:
        candidate = all_ids[(match_index + len(omitted) + 10) % len(all_ids)]
        if candidate not in {"SYN_P01", "SYN_P12"}:
            omitted.add(candidate)
    return [pid for pid in all_ids if pid not in omitted]


def _starting_ids(played: list[str], match_index: int) -> list[str]:
    goalkeeper = "SYN_P01" if match_index % 3 else "SYN_P12"
    outfield = [pid for pid in played if pid not in {"SYN_P01", "SYN_P12"}]
    return [goalkeeper] + outfield[:10]


def _raw_stats(rng: random.Random, role_group: str, minutes: float) -> dict[str, int | None]:
    if minutes <= 0:
        return {key: None for key in (
            "passes_total", "passes_completed", "assists", "long_balls_total", "long_balls_completed",
            "crosses_total", "crosses_completed", "dribbles_total", "dribbles_won", "turnovers",
            "dispossessed", "shots_total", "shots_blocked", "goals", "tackles_total", "tackles_won",
            "interceptions", "blocked_passes", "clearances", "fouls_committed", "fouls_received",
            "yellow_cards", "red_cards", "penalties_conceded", "penalties_won", "saves", "goals_conceded",
        )}

    scale = minutes / 90.0
    if role_group == "GK":
        passes = max(6, round((24 + rng.randint(-5, 6)) * scale))
        completed = min(passes, max(0, round(passes * rng.uniform(0.65, 0.90))))
        return {
            "passes_total": passes, "passes_completed": completed, "assists": 0,
            "long_balls_total": max(0, round((9 + rng.randint(-3, 4)) * scale)),
            "long_balls_completed": max(0, round((5 + rng.randint(-2, 3)) * scale)),
            "crosses_total": 0, "crosses_completed": 0, "dribbles_total": 0, "dribbles_won": 0,
            "turnovers": rng.randint(0, 1), "dispossessed": 0, "shots_total": 0, "shots_blocked": 0,
            "goals": 0, "tackles_total": 0, "tackles_won": 0, "interceptions": 0,
            "blocked_passes": 0, "clearances": rng.randint(0, 2), "fouls_committed": 0,
            "fouls_received": 0, "yellow_cards": 0, "red_cards": 0, "penalties_conceded": 0,
            "penalties_won": 0, "saves": rng.randint(1, 6), "goals_conceded": rng.randint(0, 2),
        }

    role_pass = {"CB": 48, "FB_WB": 39, "DM_CM": 51, "AM_W": 34, "ST": 22}.get(role_group, 30)
    passes = max(3, round((role_pass + rng.randint(-9, 10)) * scale))
    completed = min(passes, max(0, round(passes * rng.uniform(0.70, 0.91))))
    long_total = max(0, round(({"CB": 6, "FB_WB": 4, "DM_CM": 5, "AM_W": 2, "ST": 1}.get(role_group, 2) + rng.randint(0, 3)) * scale))
    long_completed = min(long_total, max(0, round(long_total * rng.uniform(0.45, 0.78))))
    cross_total = max(0, round(({"FB_WB": 4, "AM_W": 4}.get(role_group, 1) + rng.randint(0, 2)) * scale))
    cross_completed = min(cross_total, max(0, round(cross_total * rng.uniform(0.20, 0.55))))
    dribbles = max(0, round(({"AM_W": 4, "ST": 2, "FB_WB": 2}.get(role_group, 1) + rng.randint(0, 2)) * scale))
    dribbles_won = min(dribbles, max(0, round(dribbles * rng.uniform(0.35, 0.75))))
    shots = max(0, round(({"ST": 3, "AM_W": 2, "DM_CM": 1}.get(role_group, 0) + rng.randint(0, 2)) * scale))
    tackles = max(0, round(({"CB": 3, "FB_WB": 3, "DM_CM": 3, "AM_W": 1, "ST": 1}.get(role_group, 1) + rng.randint(0, 2)) * scale))
    tackles_won = min(tackles, max(0, round(tackles * rng.uniform(0.50, 0.90))))
    return {
        "passes_total": passes,
        "passes_completed": completed,
        "assists": 0,
        "long_balls_total": long_total,
        "long_balls_completed": long_completed,
        "crosses_total": cross_total,
        "crosses_completed": cross_completed,
        "dribbles_total": dribbles,
        "dribbles_won": dribbles_won,
        "turnovers": rng.randint(0, max(1, round(2 * scale))),
        "dispossessed": rng.randint(0, max(1, round(2 * scale))),
        "shots_total": shots,
        "shots_blocked": min(shots, rng.randint(0, 1) if shots else 0),
        "goals": 0,
        "tackles_total": tackles,
        "tackles_won": tackles_won,
        "interceptions": max(0, round(({"CB": 2, "DM_CM": 2}.get(role_group, 1) + rng.randint(0, 2)) * scale)),
        "blocked_passes": max(0, round(rng.randint(0, 2) * scale)),
        "clearances": max(0, round(({"CB": 4, "FB_WB": 2}.get(role_group, 0) + rng.randint(0, 2)) * scale)),
        "fouls_committed": max(0, round(rng.randint(0, 2) * scale)),
        "fouls_received": max(0, round(rng.randint(0, 3) * scale)),
        "yellow_cards": 1 if rng.random() < 0.08 * scale else 0,
        "red_cards": 0,
        "penalties_conceded": 1 if role_group in {"CB", "FB_WB"} and rng.random() < 0.015 else 0,
        "penalties_won": 1 if role_group in {"AM_W", "ST"} and rng.random() < 0.025 else 0,
        "saves": None,
        "goals_conceded": None,
    }


def _seed_base(db: Path, seed: int) -> None:
    rng = random.Random(seed)
    player_by_id = {row[0]: row for row in PLAYER_SPECS}
    start = date(2026, 1, 10)

    with duckdb.connect(str(db)) as con:
        con.execute("INSERT INTO teams (team_id, display_name, source_name, source_team_id, is_anonymized) VALUES (?, ?, ?, ?, TRUE)",
                    [TEAM_ID, "Club Demo FPS", "SYNTHETIC_GENERATED", TEAM_ID])
        for i in range(12):
            oid = f"SYN_OPP_{i + 1:02d}"
            con.execute("INSERT INTO teams (team_id, display_name, source_name, source_team_id, is_anonymized) VALUES (?, ?, ?, ?, TRUE)",
                        [oid, f"Rival Demo {i + 1:02d}", "SYNTHETIC_GENERATED", oid])

        for pid, name, shirt, role, _group in PLAYER_SPECS:
            con.execute(
                "INSERT INTO players (player_id, display_name, source_name, source_player_id, default_position, is_anonymized) VALUES (?, ?, ?, ?, ?, TRUE)",
                [pid, name, "SYNTHETIC_GENERATED", pid, role],
            )

        for i in range(12):
            match_id = f"SYN_MATCH_{i + 1:02d}"
            opp_id = f"SYN_OPP_{i + 1:02d}"
            is_home = i % 2 == 0
            match_date = start + timedelta(days=7 * i)
            score_for = (i * 2 + 1) % 4
            score_against = (i + 1) % 3
            home_id, away_id = (TEAM_ID, opp_id) if is_home else (opp_id, TEAM_ID)
            home_score, away_score = (score_for, score_against) if is_home else (score_against, score_for)
            con.execute(
                """
                INSERT INTO matches
                (match_id, competition, season, match_date, home_team_id, away_team_id, home_score, away_score, source_match_id, source_type)
                VALUES (?, 'Liga Demo Sintética', '2025-26', ?, ?, ?, ?, ?, ?, ?)
                """,
                [match_id, match_date.isoformat(), home_id, away_id, home_score, away_score, match_id, RAW_SOURCE_TYPE],
            )
            con.execute(
                """
                INSERT INTO team_match
                (match_id, team_id, opponent_team_id, is_home, starting_formation, score_for, score_against)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [match_id, TEAM_ID, opp_id, is_home, _formation(i), score_for, score_against],
            )

            played = _played_ids(i)
            starters = set(_starting_ids(played, i))
            scorer_candidates: list[str] = []
            for p_index, (pid, _name, shirt, role, group) in enumerate(PLAYER_SPECS):
                if pid not in played:
                    minutes = 0.0
                    started = False
                elif pid in starters:
                    minutes = float(90 - (10 if (p_index + i) % 7 == 0 else 0))
                    started = True
                else:
                    minutes = float(20 + 5 * ((p_index + i) % 7))
                    started = False

                con.execute(
                    "INSERT INTO player_match (match_id, team_id, player_id, started, minutes_played, primary_role, shirt_number) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [match_id, TEAM_ID, pid, started, minutes, role, shirt],
                )
                if minutes > 0:
                    stint_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"synthetic:{match_id}:{pid}:stint"))
                    con.execute(
                        """
                        INSERT INTO player_role_stints
                        (stint_id, match_id, team_id, player_id, start_second, end_second, role, position, side, formation, source_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                        """,
                        [stint_id, match_id, TEAM_ID, pid, 0 if started else 3600, int(minutes * 60), role, role, _formation(i), RAW_SOURCE_TYPE],
                    )

                stats = _raw_stats(rng, group, minutes)
                columns = [
                    "passes_total", "passes_completed", "assists", "long_balls_total", "long_balls_completed",
                    "crosses_total", "crosses_completed", "dribbles_total", "dribbles_won", "turnovers",
                    "dispossessed", "shots_total", "shots_blocked", "goals", "tackles_total", "interceptions",
                    "blocked_passes", "clearances", "fouls_committed", "fouls_received", "yellow_cards", "red_cards",
                    "penalties_conceded", "penalties_won", "saves", "tackles_won", "goals_conceded",
                ]
                values = [stats.get(c) for c in columns]
                placeholders = ",".join("?" for _ in columns)
                con.execute(
                    f"""
                    INSERT INTO player_match_raw_stats
                    (match_id, team_id, player_id, source_type, source_match_id, source_player_id, source_minutes, {', '.join(columns)})
                    VALUES (?, ?, ?, ?, ?, ?, ?, {placeholders})
                    """,
                    [match_id, TEAM_ID, pid, RAW_SOURCE_TYPE, match_id, pid, minutes, *values],
                )
                if minutes > 0 and group in {"ST", "AM_W", "DM_CM"}:
                    scorer_candidates.append(pid)

            # Make raw goal/assist totals coherent with the synthetic team score.
            for g in range(score_for):
                if not scorer_candidates:
                    break
                scorer = scorer_candidates[(i + g) % len(scorer_candidates)]
                con.execute(
                    "UPDATE player_match_raw_stats SET goals=COALESCE(goals,0)+1, shots_total=GREATEST(COALESCE(shots_total,0),1) WHERE match_id=? AND player_id=? AND source_type=?",
                    [match_id, scorer, RAW_SOURCE_TYPE],
                )
                assister = scorer_candidates[(i + g + 1) % len(scorer_candidates)]
                if assister != scorer:
                    con.execute(
                        "UPDATE player_match_raw_stats SET assists=COALESCE(assists,0)+1 WHERE match_id=? AND player_id=? AND source_type=?",
                        [match_id, assister, RAW_SOURCE_TYPE],
                    )


def _build_features_analytics_expert(db: Path) -> None:
    py = sys.executable
    _run(py, str(ROOT / "features" / "build_player_match_features.py"), "--db", str(db), "--raw-source-type", RAW_SOURCE_TYPE)
    _run(py, str(ROOT / "features" / "build_temporal_features.py"), "--db", str(db))
    _run(py, str(ROOT / "features" / "build_role_temporal_features.py"), "--db", str(db))
    _run(py, str(ROOT / "analytics" / "build_stage1.py"), "--db", str(db))

    # Expert stage scripts currently expose DB as a module-level path. Rebinding it
    # here keeps the public builder isolated from the private/default DuckDB and uses
    # the production decision logic without copying it.
    for stage in range(1, 8):
        module = importlib.import_module(f"decision_tree.build_stage{stage}")
        if not hasattr(module, "DB"):
            raise RuntimeError(f"decision_tree.build_stage{stage} does not expose DB")
        module.DB = db
        print(f"EXPERT-{stage:02d} synthetic build -> {db}")
        module.main()


def _materialize_rating_fixture(db: Path, seed: int) -> None:
    rng = random.Random(seed + 101)
    group_by_player = {pid: group for pid, _name, _shirt, _role, group in PLAYER_SPECS}
    with duckdb.connect(str(db)) as con:
        con.execute("DROP TABLE IF EXISTS player_match_rating")
        con.execute(
            """
            CREATE TABLE player_match_rating (
                match_id VARCHAR NOT NULL, match_date DATE, team_id VARCHAR NOT NULL, player_id VARCHAR NOT NULL,
                minutes_played DOUBLE, started BOOLEAN, primary_role VARCHAR, position_group VARCHAR,
                position_mapping_status VARCHAR, attacking_threat DOUBLE, creation_progression DOUBLE,
                defensive_contribution DOUBLE, finishing DOUBLE, discipline DOUBLE, fallback_dimension_count BIGINT,
                rating_path VARCHAR NOT NULL, match_rating_100 DOUBLE NOT NULL, match_rating_10 DOUBLE NOT NULL,
                match_rating_confidence DOUBLE NOT NULL, match_rating_dimensions_used BIGINT NOT NULL,
                match_rating_context VARCHAR NOT NULL, match_rating_status VARCHAR NOT NULL,
                match_rating_version VARCHAR NOT NULL, source_score_version VARCHAR NOT NULL,
                computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (match_id, player_id, match_rating_version)
            )
            """
        )
        rows = con.execute(
            """
            SELECT pm.match_id, CAST(m.match_date AS DATE), pm.team_id, pm.player_id,
                   pm.minutes_played, pm.started, pm.primary_role,
                   rs.passes_total, rs.passes_completed, rs.assists, rs.shots_total, rs.goals,
                   rs.tackles_won, rs.interceptions, rs.turnovers, rs.dispossessed,
                   rs.saves, rs.goals_conceded
            FROM player_match pm
            JOIN matches m ON m.match_id=pm.match_id
            JOIN player_match_raw_stats rs
              ON rs.match_id=pm.match_id AND rs.player_id=pm.player_id AND rs.team_id=pm.team_id
             AND rs.source_type=?
            WHERE pm.minutes_played>0
            ORDER BY m.match_date, pm.player_id
            """,
            [RAW_SOURCE_TYPE],
        ).fetchall()
        for row in rows:
            (match_id, match_date, team_id, player_id, minutes, started, role, passes, completed, assists,
             shots, goals, tackles_won, interceptions, turnovers, dispossessed, saves, conceded) = row
            group = group_by_player[str(player_id)]
            if group == "GK":
                faced = float((saves or 0) + (conceded or 0))
                save_rate = (float(saves or 0) / faced) if faced > 0 else 0.5
                rating10 = _clip(5.4 + 2.6 * save_rate - 0.20 * float(conceded or 0), 4.5, 9.2)
                dims = [None, None, None, None, None]
                dimensions_used = 1
            else:
                pass_acc = float(completed or 0) / max(1.0, float(passes or 0))
                rating10 = _clip(
                    5.45 + 0.55 * pass_acc + 0.65 * float(goals or 0) + 0.35 * float(assists or 0)
                    + 0.07 * float(tackles_won or 0) + 0.06 * float(interceptions or 0)
                    - 0.05 * float(turnovers or 0) - 0.05 * float(dispossessed or 0)
                    + rng.uniform(-0.18, 0.18),
                    4.5, 9.2,
                )
                dims = [
                    _clip(50 + 8 * float(shots or 0) + rng.uniform(-6, 6), 20, 95),
                    _clip(45 + 40 * pass_acc + 5 * float(assists or 0) + rng.uniform(-5, 5), 20, 95),
                    _clip(45 + 6 * float(tackles_won or 0) + 5 * float(interceptions or 0) + rng.uniform(-5, 5), 20, 95),
                    _clip(40 + 18 * float(goals or 0) + 4 * float(shots or 0) + rng.uniform(-5, 5), 20, 95),
                    _clip(78 - 4 * float(turnovers or 0) + rng.uniform(-4, 4), 20, 95),
                ]
                dimensions_used = 5
            rating100 = (rating10 - 4.0) / 0.06
            confidence = _clip(60 + 35 * min(1.0, float(minutes) / 90.0), 0, 100)
            con.execute(
                """
                INSERT INTO player_match_rating VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, 'SYNTHETIC_PUBLIC_DEMO_MAPPING', ?, ?, ?, ?, ?, 0,
                 'SYNTHETIC_FIXTURE', ?, ?, ?, ?, 'SYNTHETIC_PUBLIC_DEMO_FIXTURE',
                 'SYNTHETIC_DEMO_COMPATIBLE_OUTPUT', ?, 'synthetic_public_demo_fixture_v0.1', CURRENT_TIMESTAMP)
                """,
                [match_id, match_date, team_id, player_id, minutes, started, role, group,
                 *dims, rating100, rating10, confidence, dimensions_used, MATCH_RATING_VERSION],
            )


def _materialize_performance_index_fixture(db: Path) -> None:
    with duckdb.connect(str(db)) as con:
        con.execute("DROP TABLE IF EXISTS player_match_performance_score")
        con.execute(
            """
            CREATE TABLE player_match_performance_score (
                match_id VARCHAR NOT NULL, team_id VARCHAR NOT NULL, player_id VARCHAR NOT NULL,
                primary_role VARCHAR, raw_source_position VARCHAR, position_group VARCHAR NOT NULL,
                position_mapping_status VARCHAR NOT NULL, dimension_coverage_count BIGINT NOT NULL,
                attacking_threat DOUBLE, creation_progression DOUBLE, defensive_contribution DOUBLE,
                finishing DOUBLE, discipline DOUBLE, performance_score DOUBLE, score_evidence_confidence DOUBLE,
                score_status VARCHAR NOT NULL, score_method VARCHAR NOT NULL, score_version VARCHAR NOT NULL,
                source_experiment_version VARCHAR NOT NULL, computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fallback_dimension_count BIGINT,
                attacking_threat_evidence VARCHAR, creation_progression_evidence VARCHAR,
                defensive_contribution_evidence VARCHAR, finishing_evidence VARCHAR, discipline_evidence VARCHAR,
                PRIMARY KEY (match_id, player_id, score_version)
            )
            """
        )
        ratings = con.execute(
            """
            SELECT match_id, team_id, player_id, primary_role, position_group,
                   attacking_threat, creation_progression, defensive_contribution, finishing, discipline,
                   match_rating_100, match_rating_confidence
            FROM player_match_rating WHERE match_rating_version=?
            """,
            [MATCH_RATING_VERSION],
        ).fetchall()
        for row in ratings:
            match_id, team_id, player_id, role, group, a, c, d, f, disc, rating100, conf = row
            is_gk = str(group) == "GK"
            dims = [a, c, d, f, disc]
            coverage = sum(v is not None for v in dims)
            score = None if is_gk else _clip(float(rating100) * 0.82 + 9.0, 0, 100)
            con.execute(
                """
                INSERT INTO player_match_performance_score
                (match_id, team_id, player_id, primary_role, raw_source_position, position_group,
                 position_mapping_status, dimension_coverage_count, attacking_threat, creation_progression,
                 defensive_contribution, finishing, discipline, performance_score, score_evidence_confidence,
                 score_status, score_method, score_version, source_experiment_version, fallback_dimension_count,
                 attacking_threat_evidence, creation_progression_evidence, defensive_contribution_evidence,
                 finishing_evidence, discipline_evidence)
                VALUES (?, ?, ?, ?, ?, ?, 'SYNTHETIC_PUBLIC_DEMO_MAPPING', ?, ?, ?, ?, ?, ?, ?, ?,
                        'SYNTHETIC_DEMO_COMPATIBLE_OUTPUT', 'SYNTHETIC_FIXTURE_NOT_MODEL_REVALIDATION', ?,
                        'synthetic_public_demo_fixture_v0.1', 0, ?, ?, ?, ?, ?)
                """,
                [match_id, team_id, player_id, role, role, group, coverage, a, c, d, f, disc, score, conf,
                 SCORE_VERSION, *(["SYNTHETIC_FIXTURE"] * 5)],
            )


def _seed_gps_and_build_summary(db: Path, seed: int) -> None:
    rng = random.Random(seed + 202)
    with duckdb.connect(str(db)) as con:
        matches = con.execute("SELECT match_id FROM matches WHERE source_type=? ORDER BY match_date", [RAW_SOURCE_TYPE]).fetchall()
        for (match_id,) in matches:
            import_id = f"SYN_GPS_{match_id}"
            con.execute(
                """
                INSERT INTO gps_imports
                (gps_import_id, match_id, provider, source_filename, mapping_version, source_format,
                 sample_rate_hz, time_basis, coordinate_system, distance_mode, source_units, mapping_config, notes)
                VALUES (?, ?, 'FPS Synthetic Demo', ?, 'synthetic_public_demo_v0.1', 'synthetic_demo',
                        0.0166667, 'MATCH_RELATIVE', 'LOCAL_METRES', 'incremental', ?, ?, ?)
                """,
                [import_id, match_id, f"{match_id}_synthetic_gps.csv",
                 json.dumps({"distance": "m", "speed": "m/s", "acceleration": "m/s2"}),
                 json.dumps({"synthetic_demo": True, "generator": DEMO_VERSION}),
                 "Generated from scratch for public reproducibility; not observed GPS."],
            )
            played = con.execute(
                "SELECT player_id, minutes_played FROM player_match WHERE match_id=? AND minutes_played>0 ORDER BY player_id",
                [match_id],
            ).fetchall()
            for player_id, minutes in played:
                con.execute(
                    "INSERT INTO gps_player_map VALUES (?, ?, ?, ?, 'SYNTHETIC_EXPLICIT_MAP', 1.0, CURRENT_TIMESTAMP)",
                    [import_id, player_id, player_id, player_id],
                )
                total_distance = float(minutes) * rng.uniform(85.0, 118.0)
                samples = 6
                for s in range(samples):
                    timestamp_ms = int((float(minutes) * 60_000) * s / (samples - 1)) if samples > 1 else 0
                    distance = total_distance / samples
                    speed = rng.uniform(2.2, 6.6)
                    acceleration = rng.uniform(-2.8, 2.8)
                    con.execute(
                        """
                        INSERT INTO gps_observations
                        (gps_import_id, match_id, player_id, timestamp_ms, x, y, distance_m, speed_m_s,
                         acceleration_m_s2, source_row_number, quality_flags)
                        VALUES (?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, NULL)
                        """,
                        [import_id, match_id, player_id, timestamp_ms, distance, speed, acceleration, s + 1],
                    )

    from analytics.build_gps_physical_summary import materialize
    materialize(db)


def _build_attention(db: Path) -> None:
    _run(sys.executable, str(ROOT / "analytics" / "build_attention_flags.py"), "--db", str(db))


def _write_metadata(db: Path, seed: int) -> None:
    with duckdb.connect(str(db)) as con:
        con.execute("DROP TABLE IF EXISTS public_demo_metadata")
        con.execute(
            """
            CREATE TABLE public_demo_metadata (
                demo_version VARCHAR,
                data_origin VARCHAR,
                seed BIGINT,
                contains_professional_source_rows BOOLEAN,
                redistribution_status VARCHAR,
                match_rating_fixture_notice VARCHAR,
                performance_index_fixture_notice VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        con.execute(
            """
            INSERT INTO public_demo_metadata VALUES
            (?, 'SYNTHETIC_GENERATED_FROM_SCRATCH', ?, FALSE, 'REDISTRIBUTABLE_SYNTHETIC_DEMO',
             'UI-compatible synthetic fixture values; not Match Rating V5 model revalidation.',
             'UI-compatible synthetic fixture values; not Performance Index model revalidation.',
             CURRENT_TIMESTAMP)
            """,
            [DEMO_VERSION, seed],
        )


def build(output: Path, seed: int, force: bool) -> Path:
    output = output.expanduser().resolve()
    if output.exists():
        if not force:
            raise FileExistsError(f"Output already exists: {output}. Use --force to replace it.")
        output.unlink()
    output.parent.mkdir(parents=True, exist_ok=True)

    from data.init_database import initialize_database
    initialize_database(output)
    _seed_base(output, seed)
    _build_features_analytics_expert(output)
    _materialize_rating_fixture(output, seed)
    _materialize_performance_index_fixture(output)
    _seed_gps_and_build_summary(output, seed)
    _build_attention(output)
    _write_metadata(output, seed)

    with duckdb.connect(str(output), read_only=True) as con:
        matches = con.execute("SELECT COUNT(*) FROM matches WHERE source_type=?", [RAW_SOURCE_TYPE]).fetchone()[0]
        players = con.execute("SELECT COUNT(*) FROM players").fetchone()[0]
        appearances = con.execute("SELECT COUNT(*) FROM player_match WHERE minutes_played>0").fetchone()[0]
        ratings = con.execute("SELECT COUNT(*) FROM player_match_rating WHERE match_rating_version=?", [MATCH_RATING_VERSION]).fetchone()[0]
        decisions = con.execute("SELECT COUNT(*) FROM decision_results WHERE engine_version=?", [EXPERT_VERSION]).fetchone()[0]
        gps = con.execute("SELECT COUNT(*) FROM player_match_gps_summary WHERE summary_version='gps_physical_summary_v0.1-descriptive' AND import_rank=1").fetchone()[0]

    print("SYNTHETIC PUBLIC PRODUCT DEMO: BUILT")
    print(f"output={output}")
    print(f"demo_version={DEMO_VERSION}")
    print(f"matches={matches} players={players} played_appearances={appearances}")
    print(f"ratings={ratings} expert_rows={decisions} gps_latest_rows={gps}")
    print("contains_professional_source_rows=False")
    print("redistribution_status=REDISTRIBUTABLE_SYNTHETIC_DEMO")
    print("Match Rating / Performance Index values are explicit UI compatibility fixtures, not model revalidation.")
    return output


def main() -> None:
    args = parse_args()
    build(args.output, args.seed, args.force)


if __name__ == "__main__":
    main()
