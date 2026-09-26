"""Validate the auditable attention-flags contract."""
from __future__ import annotations

import os
from pathlib import Path
import duckdb

ATTENTION_VERSION = "attention_flags_v0.1-auditable"
DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "football_performance.duckdb"
APPROVED_CODES = {
    "ROLE_CONTEXT_UNAVAILABLE",
    "INSUFFICIENT_RATING_EVIDENCE",
    "GPS_QUALITY_FLAGS_PRESENT",
}


def main() -> None:
    db = Path(os.environ.get("FPS_DB_PATH", DEFAULT_DB)).expanduser().resolve()
    if not db.exists():
        raise FileNotFoundError(db)

    with duckdb.connect(str(db), read_only=True) as con:
        actual = dict(con.execute(
            """
            SELECT attention_code, COUNT(*)
            FROM attention_flags
            WHERE attention_version=?
            GROUP BY attention_code
            """,
            [ATTENTION_VERSION],
        ).fetchall())

        role_expected = con.execute(
            "SELECT COUNT(*) FROM player_match_rating WHERE match_rating_context='GENERIC_ROLE_UNAVAILABLE'"
        ).fetchone()[0]
        evidence_expected = con.execute(
            "SELECT COUNT(*) FROM player_match_rating WHERE match_rating_status LIKE 'NEUTRAL_%'"
        ).fetchone()[0]
        gps_expected = con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT match_id, player_id
                FROM gps_observations
                WHERE quality_flags IS NOT NULL
                  AND lower(trim(CAST(quality_flags AS VARCHAR))) NOT IN ('', 'null', '[]', '{}')
                GROUP BY match_id, player_id
            ) q
            """
        ).fetchone()[0]
        codes = {r[0] for r in con.execute(
            "SELECT DISTINCT attention_code FROM attention_flags WHERE attention_version=?",
            [ATTENTION_VERSION],
        ).fetchall()}

    expected = {
        "ROLE_CONTEXT_UNAVAILABLE": role_expected,
        "INSUFFICIENT_RATING_EVIDENCE": evidence_expected,
        "GPS_QUALITY_FLAGS_PRESENT": gps_expected,
    }
    for code, n in expected.items():
        if actual.get(code, 0) != n:
            raise RuntimeError(f"{code}: expected={n} actual={actual.get(code, 0)}")
    if not codes <= APPROVED_CODES:
        raise RuntimeError(f"Unexpected attention codes: {sorted(codes - APPROVED_CODES)}")

    print("ATTENTION FLAGS CONTRACT: PASS")
    print(f"attention_version={ATTENTION_VERSION}")
    for code in sorted(APPROVED_CODES):
        print(f"{code}={actual.get(code, 0)}")
    print("No performance/fatigue/injury-risk threshold is part of this contract.")


if __name__ == "__main__":
    main()
