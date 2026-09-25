"""ANALYTICS-01: build structured self-role and peer-role evidence.

The analytics layer consumes validated FEATURE-01 and FEATURE-03 outputs and writes
read-only evidence for upper layers. It does not create rankings, scores, tactical
recommendations or minimum-sample policies.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
CONTRACT_PATH = Path(__file__).with_name("contract.json")
FEATURE_CATALOG = ROOT / "features" / "catalog.json"

SELF_SCOPE = "SELF_ROLE_PRIOR"
PEER_SCOPE = "PEER_ROLE_PRIOR"
ROLE_OPERATORS = (
    "role_history_n",
    "role_prior_mean",
    "role_prior_std",
    "role_delta_prior_mean",
    "role_prior_slope",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ANALYTICS-01 evidence")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_role(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def finite_or_none(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def direction(delta: float | None) -> str | None:
    if delta is None:
        return None
    if delta > 0:
        return "ABOVE_MEAN"
    if delta < 0:
        return "BELOW_MEAN"
    return "EQUAL_MEAN"


def base_feature_names() -> list[str]:
    catalog = load_json(FEATURE_CATALOG)
    return [row["name"] for row in catalog["ratio_features"] + catalog["per90_features"]]


def role_feature_wide(role_rows: pd.DataFrame, base_names: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for operator in ROLE_OPERATORS:
        suffix = f"__{operator}"
        mask = role_rows["feature_name"].astype(str).str.endswith(suffix)
        part = role_rows.loc[mask, ["match_id", "player_id", "feature_name", "feature_value"]].copy()
        part["base_feature"] = part["feature_name"].str.slice(stop=-len(suffix))
        part = part[part["base_feature"].isin(base_names)]
        part = part.rename(columns={"feature_value": operator})
        frames.append(part[["match_id", "player_id", "base_feature", operator]])

    if not frames:
        return pd.DataFrame(columns=["match_id", "player_id", "base_feature", *ROLE_OPERATORS])

    wide = frames[0]
    for part in frames[1:]:
        wide = wide.merge(part, on=["match_id", "player_id", "base_feature"], how="outer", validate="one_to_one")
    return wide


def self_evidence(base: pd.DataFrame, role_wide: pd.DataFrame, version: str) -> pd.DataFrame:
    frame = base.merge(
        role_wide,
        left_on=["match_id", "player_id", "feature_name"],
        right_on=["match_id", "player_id", "base_feature"],
        how="left",
        validate="one_to_one",
    )

    rows: list[dict] = []
    for row in frame.itertuples(index=False):
        role = clean_role(row.primary_role)
        current = finite_or_none(row.feature_value)
        history_n_value = finite_or_none(row.role_history_n)
        history_n = 0 if history_n_value is None else int(history_n_value)
        baseline_mean = finite_or_none(row.role_prior_mean)
        baseline_std = finite_or_none(row.role_prior_std)
        baseline_slope = finite_or_none(row.role_prior_slope)
        delta = finite_or_none(row.role_delta_prior_mean)

        if role is None:
            state = "ROLE_UNKNOWN"
        elif current is None:
            state = "CURRENT_VALUE_MISSING"
        elif history_n <= 0 or baseline_mean is None:
            state = "NO_PRIOR_EVIDENCE"
        else:
            state = "EVIDENCE_AVAILABLE"

        rows.append(
            {
                "match_id": row.match_id,
                "team_id": row.team_id,
                "player_id": row.player_id,
                "primary_role": role,
                "feature_name": row.feature_name,
                "comparison_scope": SELF_SCOPE,
                "current_value": current,
                "baseline_observations_n": history_n,
                "baseline_players_n": 1 if history_n > 0 else 0,
                "baseline_mean": baseline_mean,
                "baseline_median": None,
                "baseline_std": baseline_std,
                "baseline_slope": baseline_slope,
                "delta_from_mean": delta,
                "comparison_direction": direction(delta),
                "evidence_state": state,
                "baseline_definition": "SELF_SAME_ROLE_STRICT_PAST",
                "analytics_version": version,
            }
        )
    return pd.DataFrame(rows)


def peer_evidence(base: pd.DataFrame, version: str) -> pd.DataFrame:
    rows: list[dict] = []
    frame = base.copy()
    frame["primary_role"] = frame["primary_role"].map(clean_role)

    unknown = frame[frame["primary_role"].isna()]
    for row in unknown.itertuples(index=False):
        rows.append(
            {
                "match_id": row.match_id,
                "team_id": row.team_id,
                "player_id": row.player_id,
                "primary_role": None,
                "feature_name": row.feature_name,
                "comparison_scope": PEER_SCOPE,
                "current_value": finite_or_none(row.feature_value),
                "baseline_observations_n": 0,
                "baseline_players_n": 0,
                "baseline_mean": None,
                "baseline_median": None,
                "baseline_std": None,
                "baseline_slope": None,
                "delta_from_mean": None,
                "comparison_direction": None,
                "evidence_state": "ROLE_UNKNOWN",
                "baseline_definition": "TEAM_PEERS_SAME_ROLE_STRICT_PAST_EQUAL_PLAYER_WEIGHT",
                "analytics_version": version,
            }
        )

    known = frame[frame["primary_role"].notna()].copy()
    known = known.sort_values(["team_id", "primary_role", "feature_name", "match_date", "match_id", "player_id"])

    for (team_id, role, feature_name), group in known.groupby(
        ["team_id", "primary_role", "feature_name"], sort=False
    ):
        history: dict[str, list[float]] = {}
        for _, same_date in group.groupby("match_date", sort=True):
            same_date = same_date.sort_values(["match_id", "player_id"])
            for row in same_date.itertuples(index=False):
                current = finite_or_none(row.feature_value)
                peer_histories = {
                    player_id: values
                    for player_id, values in history.items()
                    if player_id != row.player_id and values
                }
                peer_means = [sum(values) / len(values) for values in peer_histories.values()]
                observations_n = sum(len(values) for values in peer_histories.values())
                players_n = len(peer_means)

                baseline_mean = None
                baseline_median = None
                baseline_std = None
                delta = None
                if peer_means:
                    baseline_mean = sum(peer_means) / players_n
                    baseline_median = float(statistics.median(peer_means))
                    if players_n >= 2:
                        variance = sum((value - baseline_mean) ** 2 for value in peer_means) / players_n
                        baseline_std = math.sqrt(variance)
                    if current is not None:
                        delta = current - baseline_mean

                if current is None:
                    state = "CURRENT_VALUE_MISSING"
                elif players_n == 0:
                    state = "NO_PRIOR_EVIDENCE"
                else:
                    state = "EVIDENCE_AVAILABLE"

                rows.append(
                    {
                        "match_id": row.match_id,
                        "team_id": team_id,
                        "player_id": row.player_id,
                        "primary_role": role,
                        "feature_name": feature_name,
                        "comparison_scope": PEER_SCOPE,
                        "current_value": current,
                        "baseline_observations_n": observations_n,
                        "baseline_players_n": players_n,
                        "baseline_mean": baseline_mean,
                        "baseline_median": baseline_median,
                        "baseline_std": baseline_std,
                        "baseline_slope": None,
                        "delta_from_mean": delta,
                        "comparison_direction": direction(delta),
                        "evidence_state": state,
                        "baseline_definition": "TEAM_PEERS_SAME_ROLE_STRICT_PAST_EQUAL_PLAYER_WEIGHT",
                        "analytics_version": version,
                    }
                )

            # Same-date values enter history only after all comparisons for that date.
            for row in same_date.itertuples(index=False):
                value = finite_or_none(row.feature_value)
                if value is not None:
                    history.setdefault(row.player_id, []).append(value)

    return pd.DataFrame(rows)


def build_frame(con: duckdb.DuckDBPyConnection, contract: dict) -> pd.DataFrame:
    base_version = contract["source_feature_version"]
    role_version = contract["source_role_feature_version"]
    version = contract["analytics_version"]
    names = base_feature_names()

    base = con.execute(
        """
        SELECT f.match_id, pm.team_id, f.player_id, pm.primary_role,
               m.match_date, f.feature_name, f.feature_value
        FROM player_match_features f
        JOIN player_match pm
          ON pm.match_id = f.match_id AND pm.player_id = f.player_id
        JOIN matches m ON m.match_id = f.match_id
        WHERE f.feature_version = ?
        ORDER BY pm.team_id, f.player_id, m.match_date, f.match_id, f.feature_name
        """,
        [base_version],
    ).fetchdf()
    if base.empty:
        raise RuntimeError("FEATURE-01 rows not found")
    if base["match_date"].isna().any():
        raise RuntimeError("ANALYTICS-01 requires non-null match_date")
    if set(base["feature_name"].unique()) != set(names):
        raise RuntimeError("FEATURE-01 catalog/database mismatch")

    role_rows = con.execute(
        """
        SELECT match_id, player_id, feature_name, feature_value
        FROM player_match_features
        WHERE feature_version = ?
        """,
        [role_version],
    ).fetchdf()
    if role_rows.empty:
        raise RuntimeError("FEATURE-03 rows not found")

    role_wide = role_feature_wide(role_rows, names)
    self_frame = self_evidence(base, role_wide, version)
    peer_frame = peer_evidence(base, version)
    combined = pd.concat([self_frame, peer_frame], ignore_index=True)

    expected = len(base) * 2
    if len(combined) != expected:
        raise RuntimeError(f"Expected {expected} analytics rows, built {len(combined)}")
    return combined


def ensure_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_evidence (
            match_id VARCHAR NOT NULL,
            team_id VARCHAR NOT NULL,
            player_id VARCHAR NOT NULL,
            primary_role VARCHAR,
            feature_name VARCHAR NOT NULL,
            comparison_scope VARCHAR NOT NULL,
            current_value DOUBLE,
            baseline_observations_n BIGINT NOT NULL,
            baseline_players_n BIGINT NOT NULL,
            baseline_mean DOUBLE,
            baseline_median DOUBLE,
            baseline_std DOUBLE,
            baseline_slope DOUBLE,
            delta_from_mean DOUBLE,
            comparison_direction VARCHAR,
            evidence_state VARCHAR NOT NULL,
            baseline_definition VARCHAR NOT NULL,
            analytics_version VARCHAR NOT NULL,
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (match_id, player_id, feature_name, comparison_scope, analytics_version)
        )
        """
    )


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    contract = load_json(CONTRACT_PATH)
    version = contract["analytics_version"]

    with duckdb.connect(str(db_path)) as con:
        combined = build_frame(con, contract)
        ensure_table(con)
        con.execute("DELETE FROM analytics_evidence WHERE analytics_version = ?", [version])
        con.register("analytics_df", combined)
        con.execute(
            """
            INSERT INTO analytics_evidence (
                match_id, team_id, player_id, primary_role, feature_name,
                comparison_scope, current_value, baseline_observations_n,
                baseline_players_n, baseline_mean, baseline_median, baseline_std,
                baseline_slope, delta_from_mean, comparison_direction,
                evidence_state, baseline_definition, analytics_version
            )
            SELECT
                match_id, team_id, player_id, primary_role, feature_name,
                comparison_scope, current_value, baseline_observations_n,
                baseline_players_n, baseline_mean, baseline_median, baseline_std,
                baseline_slope, delta_from_mean, comparison_direction,
                evidence_state, baseline_definition, analytics_version
            FROM analytics_df
            """
        )
        con.unregister("analytics_df")

        written = con.execute(
            "SELECT COUNT(*) FROM analytics_evidence WHERE analytics_version = ?", [version]
        ).fetchone()[0]
        states = con.execute(
            """
            SELECT comparison_scope, evidence_state, COUNT(*)
            FROM analytics_evidence
            WHERE analytics_version = ?
            GROUP BY comparison_scope, evidence_state
            ORDER BY comparison_scope, evidence_state
            """,
            [version],
        ).fetchall()

    print("ANALYTICS-01 build complete")
    print(f"analytics_version: {version}")
    print(f"rows written: {written}")
    for scope, state, count in states:
        print(f"{scope} / {state}: {count}")
    print("DG-AN-01 C applied: self-role and peer-role evidence remain separate.")
    print("No score, ranking, recommendation, minimum-sample threshold or good/bad label was created.")


if __name__ == "__main__":
    main()
