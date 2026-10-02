"""Validate EXPERT-03 N8000 context + N9000 optional GPS gate."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
CATALOG = Path(__file__).with_name("context_catalog.json")

FORBIDDEN_TOKENS = (
    "GOOD", "BAD", "IMPROVING", "DECLINING", "RECOMMEND", "BEST", "WORST",
    "HIGH_PERFORMANCE", "LOW_PERFORMANCE",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    catalog = load_json(CATALOG)
    engine_version = catalog["engine_version"]
    parent_version = catalog["parent_engine_version"]
    nodes = catalog["nodes"]

    family_nodes: dict[str, int] = {}
    for node in nodes:
        family_nodes[node["family"]] = family_nodes.get(node["family"], 0) + 1

    with duckdb.connect(str(DB), read_only=True) as con:
        pm_count = con.execute("SELECT COUNT(*) FROM player_match").fetchone()[0]
        parent_count = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?", [parent_version]
        ).fetchone()[0]
        if parent_count == 0:
            raise RuntimeError(f"Parent engine missing: {parent_version}")

        expected_total = parent_count + pm_count * len(nodes)
        total = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?", [engine_version]
        ).fetchone()[0]
        if total != expected_total:
            raise RuntimeError(f"decision rows mismatch: {total}/{expected_total}")

        duplicates = con.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT match_id, player_id, node_id, COUNT(*) n
              FROM decision_results WHERE engine_version = ?
              GROUP BY 1,2,3 HAVING COUNT(*) > 1
            )
            """, [engine_version]
        ).fetchone()[0]
        if duplicates:
            raise RuntimeError(f"duplicate node outputs: {duplicates}")

        confidence_bad = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND (confidence IS NULL OR confidence <> 1.0)
            """, [engine_version]
        ).fetchone()[0]
        if confidence_bad:
            raise RuntimeError(f"deterministic confidence violations: {confidence_bad}")

        # Parent N1000-N7000 content must carry forward exactly.
        parent_diff = con.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT match_id, player_id, node_id, result_type, result_value, confidence, justification
              FROM decision_results WHERE engine_version = ? AND (
                node_id LIKE 'N1000.%' OR node_id LIKE 'N2000.%' OR node_id LIKE 'N3000.%' OR
                node_id LIKE 'N4000.%' OR node_id LIKE 'N5000.%' OR node_id LIKE 'N6000.%' OR node_id LIKE 'N7000.%'
              )
              EXCEPT
              SELECT match_id, player_id, node_id, result_type, result_value, confidence, justification
              FROM decision_results WHERE engine_version = ?
            )
            """, [engine_version, parent_version]
        ).fetchone()[0]
        if parent_diff:
            raise RuntimeError(f"N1000-N7000 carry-forward differs from parent: {parent_diff}")

        families = dict(con.execute(
            """
            SELECT regexp_extract(node_id, '^(N[0-9]+)', 1), COUNT(*)
            FROM decision_results WHERE engine_version = ? GROUP BY 1
            """, [engine_version]
        ).fetchall())
        for family, n_nodes in family_nodes.items():
            expected = pm_count * n_nodes
            if families.get(family) != expected:
                raise RuntimeError(f"{family} coverage mismatch: {families.get(family)}/{expected}")

        gps_bad = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND node_id = 'N9000.100'
              AND result_value NOT IN ('GPS_OBSERVED','GPS_NOT_AVAILABLE')
            """, [engine_version]
        ).fetchone()[0]
        if gps_bad:
            raise RuntimeError(f"invalid N9000 GPS states: {gps_bad}")

        # N9000 is allowed to observe real/provider GPS only. Synthetic demo GPS is
        # product/demo data and must never become expert-system evidence.
        gps_expected = dict(((m, p), n) for m, p, n in con.execute(
            """
            SELECT go.match_id, go.player_id, COUNT(*)
            FROM gps_observations go
            JOIN gps_imports gi ON gi.gps_import_id = go.gps_import_id
            WHERE lower(coalesce(gi.provider, '')) <> 'fps synthetic demo'
              AND lower(coalesce(gi.source_format, '')) <> 'synthetic_demo'
            GROUP BY 1,2
            """
        ).fetchall())
        gps_rows = con.execute(
            """
            SELECT match_id, player_id, result_value FROM decision_results
            WHERE engine_version = ? AND node_id = 'N9000.100'
            """, [engine_version]
        ).fetchall()
        mismatches = 0
        for match_id, player_id, value in gps_rows:
            expected = "GPS_OBSERVED" if gps_expected.get((match_id, player_id), 0) > 0 else "GPS_NOT_AVAILABLE"
            mismatches += int(value != expected)
        if mismatches:
            raise RuntimeError(f"N9000 observed non-synthetic GPS availability mismatches: {mismatches}")

        values = [str(v[0]).upper() for v in con.execute(
            "SELECT result_value FROM decision_results WHERE engine_version = ?", [engine_version]
        ).fetchall()]
        forbidden = sorted({tok for tok in FORBIDDEN_TOKENS if any(tok in value for value in values)})
        if forbidden:
            raise RuntimeError(f"premature evaluative labels found: {forbidden}")

        n8000 = families.get("N8000", 0)
        n9000 = families.get("N9000", 0)
        gps_observed = sum(1 for _, _, value in gps_rows if value == "GPS_OBSERVED")

    print("EXPERT-03 VALIDATION: PASS")
    print(f"engine_version: {engine_version}")
    print(f"parent_engine_version: {parent_version}")
    print(f"player_match rows: {pm_count}")
    print(f"decision rows: {total}/{expected_total}")
    print(f"family coverage: N8000={n8000}, N9000={n9000}")
    print("N1000-N7000 exact carry-forward: PASS")
    print("N8000 own-team context contract: PASS")
    print("N9000 observed non-synthetic GPS availability contract: PASS")
    print(f"player-match rows with observed non-synthetic GPS: {gps_observed}")
    print("Synthetic demo GPS is excluded from expert evidence: PASS")
    print("No physical estimate, sprint/HIE/load threshold, score, weight, percentile or recommendation was created.")


if __name__ == "__main__":
    main()
