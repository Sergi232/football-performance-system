"""Validate EXPERT-02 N1000-N7000 domain evidence layer."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "football_performance.duckdb"
BASE_CATALOG = ROOT / "features" / "catalog.json"
STAGE1_CATALOG = ROOT / "decision_tree" / "catalog.json"
DOMAIN_CATALOG = Path(__file__).with_name("domain_catalog.json")

FORBIDDEN_TOKENS = (
    "GOOD", "BAD", "IMPROVING", "DECLINING", "RECOMMEND", "BEST", "WORST",
    "HIGH_PERFORMANCE", "LOW_PERFORMANCE",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    base_catalog = load_json(BASE_CATALOG)
    stage1_catalog = load_json(STAGE1_CATALOG)
    domain_catalog = load_json(DOMAIN_CATALOG)

    engine_version = domain_catalog["engine_version"]
    parent_version = domain_catalog["parent_engine_version"]
    domain_nodes = domain_catalog["domain_nodes"]
    base_features = [x["name"] for x in base_catalog["ratio_features"] + base_catalog["per90_features"]]

    if stage1_catalog["engine_version"] != parent_version:
        raise RuntimeError("Parent engine version mismatch")

    family_node_counts: dict[str, int] = {}
    for node in domain_nodes:
        family_node_counts[node["family"]] = family_node_counts.get(node["family"], 0) + 1

    with duckdb.connect(str(DB), read_only=True) as con:
        pm_count = con.execute("SELECT COUNT(*) FROM player_match").fetchone()[0]
        expected_parent = pm_count * (2 + 2 * len(base_features))
        expected_total = expected_parent + pm_count * len(domain_nodes)

        total = con.execute(
            "SELECT COUNT(*) FROM decision_results WHERE engine_version = ?",
            [engine_version],
        ).fetchone()[0]
        if total != expected_total:
            raise RuntimeError(f"decision rows mismatch: {total}/{expected_total}")

        duplicate_count = con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT match_id, player_id, node_id, COUNT(*) AS n
                FROM decision_results
                WHERE engine_version = ?
                GROUP BY 1,2,3
                HAVING COUNT(*) > 1
            )
            """,
            [engine_version],
        ).fetchone()[0]
        if duplicate_count:
            raise RuntimeError(f"duplicate node outputs: {duplicate_count}")

        confidence_bad = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND (confidence IS NULL OR confidence <> 1.0)
            """,
            [engine_version],
        ).fetchone()[0]
        if confidence_bad:
            raise RuntimeError(f"deterministic confidence violations: {confidence_bad}")

        families = dict(
            con.execute(
                """
                SELECT regexp_extract(node_id, '^(N[0-9]+)', 1) AS family, COUNT(*)
                FROM decision_results
                WHERE engine_version = ?
                GROUP BY 1
                """,
                [engine_version],
            ).fetchall()
        )

        expected_families = {
            "N1000": pm_count,
            "N2000": pm_count,
            "N3000": pm_count * 2 * len(base_features),
            **{family: pm_count * n for family, n in family_node_counts.items()},
        }
        if families != expected_families:
            raise RuntimeError(f"family coverage mismatch: actual={families} expected={expected_families}")

        # N1000-N3000 must be carried forward unchanged, apart from decision_id and engine_version.
        parent_diff = con.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT match_id, player_id, node_id, result_type, result_value, confidence, justification
                FROM decision_results WHERE engine_version = ? AND (
                    node_id LIKE 'N1000.%' OR node_id LIKE 'N2000.%' OR node_id LIKE 'N3000.%'
                )
                EXCEPT
                SELECT match_id, player_id, node_id, result_type, result_value, confidence, justification
                FROM decision_results WHERE engine_version = ?
            )
            """,
            [engine_version, parent_version],
        ).fetchone()[0]
        if parent_diff:
            raise RuntimeError(f"N1000-N3000 carry-forward differs from parent: {parent_diff} rows")

        domain_count = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ? AND result_type = 'domain_relative_signal'
            """,
            [engine_version],
        ).fetchone()[0]
        expected_domain = pm_count * len(domain_nodes)
        if domain_count != expected_domain:
            raise RuntimeError(f"domain rows mismatch: {domain_count}/{expected_domain}")

        bad_domain_justification = con.execute(
            """
            SELECT COUNT(*) FROM decision_results
            WHERE engine_version = ?
              AND result_type = 'domain_relative_signal'
              AND (justification NOT LIKE '%feature=%' OR justification NOT LIKE '%strict_past_history_n=%')
            """,
            [engine_version],
        ).fetchone()[0]
        if bad_domain_justification:
            raise RuntimeError(f"domain justification contract violations: {bad_domain_justification}")

        values = [
            str(row[0]).upper()
            for row in con.execute(
                "SELECT result_value FROM decision_results WHERE engine_version = ?",
                [engine_version],
            ).fetchall()
        ]
        forbidden_hits = sorted({token for token in FORBIDDEN_TOKENS if any(token in value for value in values)})
        if forbidden_hits:
            raise RuntimeError(f"premature evaluative labels found: {forbidden_hits}")

    print("EXPERT-02 VALIDATION: PASS")
    print(f"engine_version: {engine_version}")
    print(f"parent_engine_version: {parent_version}")
    print(f"player_match rows: {pm_count}")
    print(f"domain nodes per player-match: {len(domain_nodes)}")
    print(f"decision rows: {total}/{expected_total}")
    print("family coverage: " + ", ".join(f"{k}={families[k]}" for k in sorted(families)))
    print("N1000-N3000 exact carry-forward: PASS")
    print("deterministic confidence contract: PASS")
    print("no premature evaluative/recommendation labels: PASS")
    print("No scores, weights, percentiles or practical-significance thresholds were validated or created.")


if __name__ == "__main__":
    main()
