"""Validate the minimum data contract required by DASHBOARD-01."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_access import (  # noqa: E402
    FINAL_ENGINE_VERSION,
    get_engine_status,
    get_squad_summary,
    get_team_matches,
    get_team_overview,
    list_base_features,
    list_teams,
)

DB = ROOT / "data" / "football_performance.duckdb"


def main() -> None:
    teams = list_teams(DB)
    if teams.empty:
        raise RuntimeError("DASHBOARD-01 requires at least one team with player_match data")

    team_id = str(teams.iloc[0]["team_id"])
    overview = get_team_overview(DB, team_id)
    matches = get_team_matches(DB, team_id)
    squad = get_squad_summary(DB, team_id)
    features = list_base_features(DB)
    engine = get_engine_status(DB)

    if int(overview["matches"]) <= 0:
        raise RuntimeError("Dashboard team overview has no matches")
    if len(matches) != int(overview["matches"]):
        raise RuntimeError(f"Match-list mismatch: {len(matches)} != {overview['matches']}")
    if int(overview["players"]) <= 0 or squad.empty:
        raise RuntimeError("Dashboard squad query returned no players")
    if len(features) != 28:
        raise RuntimeError(f"Expected 28 FEATURE-01 metrics, found {len(features)}")
    if engine["player_match_rows"] <= 0:
        raise RuntimeError("No player_match rows found")
    if engine["engine_rows"] <= 0:
        raise RuntimeError(f"No {FINAL_ENGINE_VERSION} decision rows found")
    if engine["n13000_rows"] != engine["player_match_rows"] * 3:
        raise RuntimeError(
            f"N13000 coverage mismatch: {engine['n13000_rows']} != {engine['player_match_rows'] * 3}"
        )
    if engine["unsafe_final_states"] != 0:
        raise RuntimeError(f"Unsafe N13000 final states found: {engine['unsafe_final_states']}")

    print("DASHBOARD-01 DATA CONTRACT: PASS")
    print(f"team: {teams.iloc[0]['display_name']}")
    print(f"matches: {overview['matches']}")
    print(f"players: {overview['players']}")
    print(f"FEATURE-01 metrics available: {len(features)}")
    print(f"final engine: {FINAL_ENGINE_VERSION}")
    print(f"decision rows: {engine['engine_rows']}")
    print(f"N13000 rows: {engine['n13000_rows']}")
    print("Final recommendation gate safety: PASS")


if __name__ == "__main__":
    main()
