"""DSAI-08: audit source-derived tactical-role granularity before a second baseline.

DATA-02 stores starter roles as `position | position_side` when side exists, or as
`position` otherwise. This audit deterministically recovers the source `position`
component and evaluates whether that parent target is structurally more suitable
for supervised modelling. No model is trained and no intuitive class merge is used.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "football_performance.duckdb"
OUTPUT_DIR = Path(__file__).with_name("output")
VERSION = "dsai_role_granularity_0.1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit source-position target granularity")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def clean(value):
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def records(df: pd.DataFrame) -> list[dict]:
    return [{k: clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def load_clean_target(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    frame = con.execute(
        """
        SELECT
            pm.match_id,
            pm.player_id,
            m.match_date,
            TRIM(pm.primary_role) AS detailed_role
        FROM player_match pm
        JOIN matches m ON m.match_id = pm.match_id
        WHERE pm.started IS TRUE
          AND pm.primary_role IS NOT NULL
          AND TRIM(pm.primary_role) <> ''
          AND LOWER(TRIM(pm.primary_role)) <> 'substitute'
        ORDER BY m.match_date, pm.match_id, pm.player_id
        """
    ).fetchdf()
    if frame.empty:
        return frame

    frame["source_position"] = (
        frame["detailed_role"].astype(str).str.split(" | ", n=1, regex=False).str[0].str.strip()
    )
    frame["source_side"] = frame["detailed_role"].astype(str).apply(
        lambda x: x.split(" | ", 1)[1].strip() if " | " in x else None
    )
    return frame


def add_strict_past_flags(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["position_seen_strict_past"] = False
    result["same_position_other_player_strict_past"] = False

    seen_positions: set[str] = set()
    position_players: dict[str, set[str]] = defaultdict(set)

    for _, idx in result.groupby("match_date", sort=True).groups.items():
        indices = list(idx)
        for i in indices:
            position = str(result.at[i, "source_position"])
            player = str(result.at[i, "player_id"])
            result.at[i, "position_seen_strict_past"] = position in seen_positions
            result.at[i, "same_position_other_player_strict_past"] = any(
                prior_player != player
                for prior_player in position_players.get(position, set())
            )
        for i in indices:
            position = str(result.at[i, "source_position"])
            player = str(result.at[i, "player_id"])
            seen_positions.add(position)
            position_players[position].add(player)
    return result


def summarize(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {
            "version": VERSION,
            "status": "GRANULARITY_AUDIT_ONLY",
            "summary": {
                "target_rows": 0,
                "detailed_labels": 0,
                "source_positions": 0,
                "players": 0,
                "matches": 0,
                "single_player_positions": 0,
                "positions_without_any_strict_past": 0,
                "positions_without_other_player_strict_past": 0,
                "parsing_anomalies": 0,
                "conclusion": "NO_GO_SOURCE_POSITION",
            },
            "position_distribution": [],
            "mapping": [],
            "rules": [],
        }

    frame = add_strict_past_flags(frame)
    anomalies = frame[
        frame["source_position"].isna()
        | frame["source_position"].astype(str).str.strip().eq("")
        | frame["source_position"].astype(str).str.lower().eq("substitute")
    ]

    distribution = (
        frame.groupby("source_position")
        .agg(
            rows=("match_id", "size"),
            players=("player_id", "nunique"),
            matches=("match_id", "nunique"),
            strict_past_rows=("position_seen_strict_past", "sum"),
            other_player_strict_past_rows=("same_position_other_player_strict_past", "sum"),
        )
        .reset_index()
        .sort_values(["rows", "source_position"], ascending=[False, True])
    )

    mapping = (
        frame.groupby(["detailed_role", "source_position"], dropna=False)
        .size()
        .rename("rows")
        .reset_index()
        .sort_values(["source_position", "detailed_role"])
    )

    single_player_positions = distribution.loc[
        distribution["players"].eq(1), "source_position"
    ].astype(str).tolist()
    no_any_strict = distribution.loc[
        distribution["strict_past_rows"].eq(0), "source_position"
    ].astype(str).tolist()
    no_other_player = distribution.loc[
        distribution["other_player_strict_past_rows"].eq(0), "source_position"
    ].astype(str).tolist()

    if len(anomalies) > 0:
        conclusion = "NO_GO_SOURCE_POSITION"
    elif no_any_strict:
        conclusion = "NO_GO_SOURCE_POSITION"
    elif single_player_positions or no_other_player:
        conclusion = "LIMITED_SOURCE_POSITION_BASELINE"
    else:
        conclusion = "GO_SOURCE_POSITION_BASELINE"

    summary = {
        "target_rows": int(len(frame)),
        "detailed_labels": int(frame["detailed_role"].nunique()),
        "source_positions": int(frame["source_position"].nunique()),
        "players": int(frame["player_id"].nunique()),
        "matches": int(frame["match_id"].nunique()),
        "strict_past_position_seen_rows": int(frame["position_seen_strict_past"].sum()),
        "identity_independent_strict_past_rows": int(
            frame["same_position_other_player_strict_past"].sum()
        ),
        "single_player_positions": int(len(single_player_positions)),
        "positions_without_any_strict_past": int(len(no_any_strict)),
        "positions_without_other_player_strict_past": int(len(no_other_player)),
        "parsing_anomalies": int(len(anomalies)),
        "conclusion": conclusion,
    }

    return {
        "version": VERSION,
        "status": "GRANULARITY_AUDIT_ONLY",
        "summary": summary,
        "single_player_position_names": single_player_positions,
        "positions_without_any_strict_past_names": no_any_strict,
        "positions_without_other_player_strict_past_names": no_other_player,
        "position_distribution": records(distribution),
        "mapping": records(mapping),
        "rules": [
            "source_position is obtained only by reversing DATA-02's `position | position_side` representation.",
            "No football-semantic grouping is invented by this audit.",
            "No model is trained.",
            "No rows or classes are removed for modelling convenience.",
            "No rating, player fit, ranking or recommendation is created.",
        ],
    }


def render_markdown(result: dict) -> str:
    s = result["summary"]
    lines = [
        "# DSAI-08 — Source-position granularity audit",
        "",
        f"Version: `{result['version']}`",
        f"Status: **{result['status']}**",
        "",
        "## Summary",
    ]
    for key, value in s.items():
        lines.append(f"- {key}: {value}")

    lines.extend([
        "",
        "## Position distribution",
        "",
        "| Source position | Rows | Players | Matches | Strict-past rows | Other-player prior rows |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for row in result["position_distribution"]:
        lines.append(
            f"| {row['source_position']} | {row['rows']} | {row['players']} | {row['matches']} | "
            f"{row['strict_past_rows']} | {row['other_player_strict_past_rows']} |"
        )

    lines.extend([
        "",
        "## Detailed-role mapping",
        "",
        "| Detailed role | Source position | Rows |",
        "|---|---|---:|",
    ])
    for row in result["mapping"]:
        lines.append(f"| {row['detailed_role']} | {row['source_position']} | {row['rows']} |")

    lines.extend(["", "## Rules"])
    for rule in result["rules"]:
        lines.append(f"- {rule}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with duckdb.connect(str(db_path), read_only=True) as con:
        frame = load_clean_target(con)

    result = summarize(frame)
    s = result["summary"]

    print("DSAI-08 ROLE GRANULARITY AUDIT: COMPLETE")
    print(f"db: {db_path}")
    print(
        f"rows={s['target_rows']} detailed_labels={s['detailed_labels']} "
        f"source_positions={s['source_positions']} players={s['players']} matches={s['matches']}"
    )
    print(
        f"strict_past_position_seen={s.get('strict_past_position_seen_rows', 0)}/{s['target_rows']} "
        f"identity_independent_strict_past={s.get('identity_independent_strict_past_rows', 0)}/{s['target_rows']}"
    )
    print(
        f"single_player_positions={s['single_player_positions']} "
        f"positions_without_any_strict_past={s['positions_without_any_strict_past']} "
        f"positions_without_other_player_strict_past={s['positions_without_other_player_strict_past']} "
        f"parsing_anomalies={s['parsing_anomalies']}"
    )
    print(f"conclusion={s['conclusion']}")
    print("No model or intuitive class merge was created.")

    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "role_granularity_audit.json"
        md_path = OUTPUT_DIR / "role_granularity_audit.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(result), encoding="utf-8")
        print(f"json: {json_path}")
        print(f"markdown: {md_path}")


if __name__ == "__main__":
    main()
