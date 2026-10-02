"""Audit internal coherence of synthetic GPS demo data.

This is NOT a physiological validation. It checks that the generated demo GPS data
actually respects the generator contract: minutes exposure, role-conditioned priors,
explicit synthetic provenance, and plausible internal bounds defined by the generator.
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gps.generate_synthetic_demo import (  # noqa: E402
    GENERATOR_VERSION,
    PROVIDER,
    ROLE_PRIORS,
    SOURCE_FORMAT,
    _clip,
    _role_group,
)

DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"


def _corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    den = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    if den == 0:
        return None
    return sum(a * b for a, b in zip(dx, dy)) / den


def audit(db_path: Path) -> dict:
    db_path = Path(db_path).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with duckdb.connect(str(db_path), read_only=True) as con:
        rows = con.execute(
            """
            SELECT
                g.match_id,
                g.player_id,
                pm.minutes_played,
                CASE
                    WHEN UPPER(TRIM(COALESCE(pm.primary_role, ''))) IN ('SUBSTITUTE', 'SUB', 'BENCH')
                        THEN COALESCE(NULLIF(TRIM(p.default_position), ''), 'UNKNOWN')
                    ELSE COALESCE(NULLIF(TRIM(pm.primary_role), ''), NULLIF(TRIM(p.default_position), ''), 'UNKNOWN')
                END AS role_raw,
                g.total_distance_m,
                g.peak_speed_m_s,
                g.max_acceleration_m_s2,
                g.min_acceleration_m_s2,
                g.provider,
                gi.source_format,
                gi.mapping_version,
                gi.notes
            FROM player_match_gps_summary g
            JOIN player_match pm
              ON pm.match_id=g.match_id AND pm.player_id=g.player_id
            JOIN players p ON p.player_id=g.player_id
            JOIN gps_imports gi ON gi.gps_import_id=g.gps_import_id
            WHERE g.import_rank=1 AND g.provider=?
            ORDER BY g.match_id, g.player_id
            """,
            [PROVIDER],
        ).fetchall()

    if not rows:
        raise RuntimeError("No synthetic GPS summaries found. Run gps/generate_synthetic_demo.py first.")

    violations: list[str] = []
    minutes_all: list[float] = []
    distance_all: list[float] = []
    by_role: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
    ratio_values: list[float] = []

    for (
        match_id,
        player_id,
        minutes,
        role_raw,
        distance_m,
        peak_speed_m_s,
        max_accel,
        min_accel,
        provider,
        source_format,
        mapping_version,
        notes,
    ) in rows:
        minutes = float(minutes or 0.0)
        distance_m = float(distance_m or 0.0)
        peak_kmh = float(peak_speed_m_s or 0.0) * 3.6
        role = _role_group(role_raw)
        prior = ROLE_PRIORS[role]

        if provider != PROVIDER or source_format != SOURCE_FORMAT or mapping_version != GENERATOR_VERSION:
            violations.append(f"provenance:{match_id}:{player_id}")
        if "SYNTHETIC DEMO ONLY" not in str(notes or ""):
            violations.append(f"notes:{match_id}:{player_id}")
        if minutes <= 0:
            violations.append(f"minutes:{match_id}:{player_id}")
            continue

        exposure = _clip(minutes / 90.0, 0.01, 1.25)
        baseline_distance = prior["distance90"] * exposure
        ratio = distance_m / baseline_distance if baseline_distance > 0 else math.nan
        ratio_values.append(ratio)
        if not (0.8399 <= ratio <= 1.1601):
            violations.append(f"distance_contract:{match_id}:{player_id}:{ratio:.3f}")

        opportunity = 0.86 + 0.14 * min(1.0, minutes / 60.0)
        role_min = 20.0 if role == "GK" else 24.0
        expected_low = _clip(prior["peak_kmh"] * opportunity * 0.91, role_min, 36.5)
        expected_high = _clip(prior["peak_kmh"] * opportunity * 1.09, role_min, 36.5)
        if not (expected_low - 0.02 <= peak_kmh <= expected_high + 0.02):
            violations.append(f"speed_contract:{match_id}:{player_id}:{peak_kmh:.2f}")

        if max_accel is None or float(max_accel) <= 0:
            violations.append(f"accel:{match_id}:{player_id}")
        if min_accel is None or float(min_accel) >= 0:
            violations.append(f"decel:{match_id}:{player_id}")

        minutes_all.append(minutes)
        distance_all.append(distance_m)
        by_role[role].append((minutes, distance_m, peak_kmh))

    if violations:
        sample = ", ".join(violations[:10])
        raise AssertionError(f"Synthetic GPS coherence violations={len(violations)}; sample={sample}")

    role_summary = {}
    for role, values in sorted(by_role.items()):
        n = len(values)
        avg_minutes = sum(v[0] for v in values) / n
        avg_distance = sum(v[1] for v in values) / n
        avg_peak = sum(v[2] for v in values) / n
        fullish = [v for v in values if v[0] >= 75]
        avg_distance_75 = (sum(v[1] for v in fullish) / len(fullish)) if fullish else None
        role_summary[role] = {
            "n": n,
            "avg_minutes": avg_minutes,
            "avg_distance_m": avg_distance,
            "avg_peak_kmh": avg_peak,
            "n_75plus": len(fullish),
            "avg_distance_m_75plus": avg_distance_75,
        }

    return {
        "rows": len(rows),
        "minutes_distance_corr": _corr(minutes_all, distance_all),
        "min_distance_ratio": min(ratio_values),
        "max_distance_ratio": max(ratio_values),
        "roles": role_summary,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit internal coherence of synthetic GPS demo data")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    result = audit(args.db)

    print("GPS SYNTHETIC COHERENCE AUDIT: PASS")
    print("scope=INTERNAL_DEMO_COHERENCE_NOT_PHYSIOLOGICAL_VALIDATION")
    print(f"generator_version={GENERATOR_VERSION}")
    print(f"rows={result['rows']}")
    corr = result["minutes_distance_corr"]
    print(f"minutes_distance_corr={'NA' if corr is None else f'{corr:.4f}'}")
    print(f"distance_role_minutes_ratio_range={result['min_distance_ratio']:.3f}..{result['max_distance_ratio']:.3f}")
    print("ROLE SUMMARY")
    for role, info in result["roles"].items():
        full = info["avg_distance_m_75plus"]
        full_text = "NA" if full is None else f"{full / 1000.0:.2f}km"
        print(
            f"{role}: n={info['n']} avg_min={info['avg_minutes']:.1f} "
            f"avg_dist={info['avg_distance_m'] / 1000.0:.2f}km "
            f"avg_peak={info['avg_peak_kmh']:.1f}km/h "
            f"n_75plus={info['n_75plus']} avg_dist_75plus={full_text}"
        )
    print("minutes_conditioning=PASS")
    print("role_conditioning=PASS")
    print("synthetic_provenance=PASS")
    print("No fatigue/readiness/injury-risk or player-quality claim is validated by this audit.")


if __name__ == "__main__":
    main()
