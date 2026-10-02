"""Generate clearly-labelled synthetic GPS demo data into the canonical DuckDB layer.

This module exists only to demonstrate the optional GPS product flow when no approved
real GPS file is available. It never writes directly to dashboard/report tables.
Instead it writes the same normalized GPS tables used by a real provider:

    gps_imports -> gps_player_map -> gps_observations
        -> analytics/build_gps_physical_summary.py
        -> app / reports

Synthetic values are deterministic for a given seed, match and player. The priors below
are presentation/demo priors, not scientific thresholds, normative references or
validated performance targets. They must never be used to infer fatigue, readiness,
injury risk or player quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.build_gps_physical_summary import materialize  # noqa: E402

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
MIGRATION = ROOT / "data" / "migrations" / "004_gps_normalization.sql"
GENERATOR_VERSION = "gps_synthetic_demo_v1.1"
PROVIDER = "FPS Synthetic Demo"
SOURCE_FORMAT = "synthetic_demo"

# Demo-generation priors only. Units: distance m/90, peak km/h, |acceleration| m/s².
ROLE_PRIORS = {
    "GK": {"distance90": 5200.0, "peak_kmh": 26.0, "accel": 3.0, "decel": 3.2},
    "CB": {"distance90": 9600.0, "peak_kmh": 30.5, "accel": 3.2, "decel": 3.5},
    "FB": {"distance90": 10500.0, "peak_kmh": 32.5, "accel": 3.6, "decel": 3.9},
    "CM": {"distance90": 10800.0, "peak_kmh": 31.0, "accel": 3.5, "decel": 3.8},
    "AM_W": {"distance90": 10300.0, "peak_kmh": 33.5, "accel": 3.8, "decel": 4.0},
    "ST": {"distance90": 9800.0, "peak_kmh": 32.5, "accel": 3.7, "decel": 3.9},
    "OTHER": {"distance90": 10000.0, "peak_kmh": 31.5, "accel": 3.5, "decel": 3.8},
}


def _stable_seed(seed: int, match_id: str, player_id: str) -> int:
    raw = f"{seed}|{match_id}|{player_id}".encode("utf-8")
    return int.from_bytes(hashlib.blake2b(raw, digest_size=8).digest(), "big")


def _import_id(match_id: str) -> str:
    digest = hashlib.sha1(f"{GENERATOR_VERSION}|{match_id}".encode("utf-8")).hexdigest()[:20]
    return f"gps_demo_{digest}"


def _role_group(value: object) -> str:
    text = str(value or "").strip().upper().replace("-", "_").replace("/", "_")
    if any(token in text for token in ("GOALKEEPER", "PORTERO", "KEEPER")) or text == "GK":
        return "GK"
    if any(token in text for token in ("CENTRE_BACK", "CENTER_BACK", "CENTRAL")) or text in {"CB", "DC"}:
        return "CB"
    if any(token in text for token in ("FULL_BACK", "WING_BACK", "LATERAL")) or text in {"LB", "RB", "LWB", "RWB", "FB", "WB"}:
        return "FB"
    if any(token in text for token in ("MIDFIELDER", "MEDIOCENTRO", "DEFENSIVE_MID", "CENTRAL_MID")) or text in {"CM", "DM", "CDM"}:
        return "CM"
    if any(token in text for token in ("WINGER", "EXTREMO", "ATTACKING_MID", "INTERIOR")) or text in {"AM", "LW", "RW", "LM", "RM"}:
        return "AM_W"
    if any(token in text for token in ("FORWARD", "STRIKER", "DELANTERO", "CENTRE_FORWARD")) or text in {"ST", "CF", "FW"}:
        return "ST"
    return "OTHER"


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _targets(minutes: float, role: str, rng: random.Random) -> dict[str, float]:
    prior = ROLE_PRIORS[role]
    exposure = _clip(minutes / 90.0, 0.01, 1.25)
    intensity = _clip(rng.normalvariate(1.0, 0.06), 0.84, 1.16)
    distance_m = prior["distance90"] * exposure * intensity

    # Peak speed depends less on minutes than volume, but shorter appearances have
    # fewer opportunities to reach a maximum.
    opportunity = 0.86 + 0.14 * min(1.0, minutes / 60.0)
    peak_kmh = prior["peak_kmh"] * opportunity * _clip(rng.normalvariate(1.0, 0.035), 0.91, 1.09)
    peak_kmh = _clip(peak_kmh, 20.0 if role == "GK" else 24.0, 36.5)

    max_accel = prior["accel"] * _clip(rng.normalvariate(1.0, 0.08), 0.80, 1.20)
    max_decel = prior["decel"] * _clip(rng.normalvariate(1.0, 0.08), 0.80, 1.20)
    return {
        "distance_m": distance_m,
        "peak_speed_m_s": peak_kmh / 3.6,
        "max_acceleration_m_s2": max_accel,
        "min_acceleration_m_s2": -max_decel,
    }


def _samples(
    *,
    match_id: str,
    player_id: str,
    minutes: float,
    role: str,
    seed: int,
    sample_seconds: int,
) -> list[tuple[int, float, float, float, int]]:
    rng = random.Random(_stable_seed(seed, match_id, player_id))
    targets = _targets(minutes, role, rng)

    # Work in milliseconds so even very short appearances can contain separate
    # positive- and negative-acceleration observations.
    duration_ms = max(1, int(round(minutes * 60.0 * 1000.0)))
    step_ms = sample_seconds * 1000
    n_intervals = max(1, math.ceil(duration_ms / step_ms))
    timestamps = [min(i * step_ms, duration_ms) for i in range(n_intervals + 1)]
    if timestamps[-1] != duration_ms:
        timestamps.append(duration_ms)
    if len(timestamps) == 2 and duration_ms > 1:
        midpoint = max(1, duration_ms // 2)
        if midpoint < duration_ms:
            timestamps.insert(1, midpoint)

    interval_count = len(timestamps) - 1
    weights = [max(0.05, rng.lognormvariate(0.0, 0.55)) for _ in range(interval_count)]
    weight_sum = sum(weights)
    distances = [targets["distance_m"] * w / weight_sum for w in weights]

    candidate_indices = list(range(1, len(timestamps)))
    peak_idx = rng.choice(candidate_indices)
    accel_idx = rng.choice(candidate_indices)
    decel_candidates = [idx for idx in candidate_indices if idx != accel_idx]
    decel_idx = rng.choice(decel_candidates) if decel_candidates else accel_idx

    out: list[tuple[int, float, float, float, int]] = [(0, 0.0, 0.0, 0.0, 1)]
    for idx in range(1, len(timestamps)):
        dt = max(0.001, (timestamps[idx] - timestamps[idx - 1]) / 1000.0)
        distance = distances[idx - 1]
        mean_speed = distance / dt
        speed = _clip(mean_speed * rng.uniform(0.65, 1.65), 0.0, targets["peak_speed_m_s"] * 0.90)
        acceleration = _clip(rng.normalvariate(0.0, 0.70), -2.4, 2.4)
        if idx == peak_idx:
            speed = targets["peak_speed_m_s"]
        if idx == accel_idx:
            acceleration = targets["max_acceleration_m_s2"]
        if idx == decel_idx:
            acceleration = targets["min_acceleration_m_s2"]
        out.append((int(timestamps[idx]), distance, speed, acceleration, idx + 1))
    return out


def _apply_gps_contract(con: duckdb.DuckDBPyConnection) -> None:
    if not MIGRATION.exists():
        raise FileNotFoundError(f"GPS migration not found: {MIGRATION}")
    con.execute(MIGRATION.read_text(encoding="utf-8"))


def _appearance_rows(con: duckdb.DuckDBPyConnection, team_id: str | None) -> list[tuple]:
    where_team = "AND pm.team_id=?" if team_id else ""
    params = [team_id] if team_id else []
    return con.execute(
        f"""
        SELECT
            pm.match_id,
            pm.team_id,
            pm.player_id,
            pm.minutes_played,
            COALESCE(pm.primary_role, p.default_position, 'UNKNOWN') AS role,
            p.display_name,
            m.match_date
        FROM player_match pm
        JOIN players p ON p.player_id=pm.player_id
        JOIN matches m ON m.match_id=pm.match_id
        WHERE pm.minutes_played > 0
          {where_team}
        ORDER BY m.match_date, pm.match_id, pm.player_id
        """,
        params,
    ).fetchall()


def generate(
    db_path: Path,
    *,
    team_id: str | None = None,
    seed: int = 20261002,
    sample_seconds: int = 15,
) -> dict[str, int]:
    db_path = Path(db_path).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    if sample_seconds < 5 or sample_seconds > 60:
        raise ValueError("sample_seconds must be between 5 and 60")

    with duckdb.connect(str(db_path)) as con:
        _apply_gps_contract(con)
        appearances = _appearance_rows(con, team_id)
        if not appearances:
            raise RuntimeError("No player-match appearances with minutes_played > 0")

        by_match: dict[str, list[tuple]] = {}
        for row in appearances:
            by_match.setdefault(str(row[0]), []).append(row)

        import_rows = []
        for match_id in by_match:
            import_rows.append((
                _import_id(match_id),
                match_id,
                PROVIDER,
                f"synthetic_demo_{match_id}.generated",
                GENERATOR_VERSION,
                SOURCE_FORMAT,
                1.0 / sample_seconds,
                "PLAYER_EXPOSURE_ZERO_SYNTHETIC",
                "NONE",
                "delta",
                json.dumps({"distance": "m", "speed": "m/s", "acceleration": "m/s2"}),
                json.dumps({
                    "synthetic_demo": True,
                    "generator_version": GENERATOR_VERSION,
                    "seed": seed,
                    "sample_seconds": sample_seconds,
                    "rule": "role_and_minutes_conditioned_demo_priors",
                }),
                "SYNTHETIC DEMO ONLY. Not observed athlete data; generated to exercise the canonical GPS pipeline.",
            ))

        map_rows: list[tuple] = []
        all_observations: list[tuple] = []
        for match_id, rows in by_match.items():
            gps_import_id = _import_id(match_id)
            for _, _, player_id, minutes, role_raw, player_name, _ in rows:
                role = _role_group(role_raw)
                source_key = f"synthetic:{player_id}"
                map_rows.append((gps_import_id, source_key, player_name, player_id, "SYNTHETIC_DEMO_EXACT", 1.0))
                for timestamp_ms, distance_m, speed_m_s, acceleration_m_s2, source_row_number in _samples(
                    match_id=match_id,
                    player_id=str(player_id),
                    minutes=float(minutes),
                    role=role,
                    seed=seed,
                    sample_seconds=sample_seconds,
                ):
                    all_observations.append((
                        gps_import_id,
                        match_id,
                        player_id,
                        timestamp_ms,
                        None,
                        None,
                        distance_m,
                        speed_m_s,
                        acceleration_m_s2,
                        source_row_number,
                        None,
                    ))

        con.execute("BEGIN TRANSACTION")
        try:
            # Idempotent and safe: remove only rows from this synthetic demo provider.
            old_ids = [r[0] for r in con.execute(
                "SELECT gps_import_id FROM gps_imports WHERE provider=? AND source_format=?",
                [PROVIDER, SOURCE_FORMAT],
            ).fetchall()]
            if old_ids:
                placeholders = ",".join("?" for _ in old_ids)
                con.execute(f"DELETE FROM gps_observations WHERE gps_import_id IN ({placeholders})", old_ids)
                con.execute(f"DELETE FROM gps_player_map WHERE gps_import_id IN ({placeholders})", old_ids)
                con.execute(f"DELETE FROM gps_imports WHERE gps_import_id IN ({placeholders})", old_ids)

            # Parent rows must exist before mappings and observations because both
            # canonical child tables reference gps_imports.
            con.executemany(
                """
                INSERT INTO gps_imports(
                    gps_import_id, match_id, provider, source_filename, mapping_version,
                    source_format, sample_rate_hz, time_basis, coordinate_system,
                    distance_mode, source_units, mapping_config, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                import_rows,
            )
            con.executemany(
                """
                INSERT INTO gps_player_map(
                    gps_import_id, source_player_key, source_player_name,
                    player_id, mapping_method, mapping_confidence
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                map_rows,
            )
            con.executemany(
                """
                INSERT INTO gps_observations(
                    gps_import_id, match_id, player_id, timestamp_ms,
                    x, y, distance_m, speed_m_s, acceleration_m_s2,
                    source_row_number, quality_flags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                all_observations,
            )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

    physical = materialize(db_path)
    return {
        "appearances": len(appearances),
        "imports": len(import_rows),
        "player_maps": len(map_rows),
        "observations": len(all_observations),
        "summary_rows": int(physical["summary_rows"]),
        "latest_rows": int(physical["latest_rows"]),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate synthetic GPS demo data into the canonical DuckDB flow")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--team-id", default=None)
    p.add_argument("--seed", type=int, default=20261002)
    p.add_argument("--sample-seconds", type=int, default=15)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    result = generate(
        args.db,
        team_id=args.team_id,
        seed=args.seed,
        sample_seconds=args.sample_seconds,
    )
    print("GPS SYNTHETIC DEMO GENERATION: COMPLETE")
    print(f"generator_version={GENERATOR_VERSION}")
    print(f"provider={PROVIDER}")
    print("source=SYNTHETIC_DEMO_NOT_OBSERVED")
    for key, value in result.items():
        print(f"{key}={value}")
    print("FLOW: gps_imports -> gps_player_map -> gps_observations -> player_match_gps_summary")
    print("No Match Rating, Performance Index or expert decision was modified.")


if __name__ == "__main__":
    main()
