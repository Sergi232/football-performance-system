"""Import the official Collector V1.1 JSON export into DuckDB.

The importer only normalizes Collector context, roster, role stints, atomic events
and direct event counts. It never calculates features, ratings or recommendations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "collector" / "event_catalog.json"
SOURCE_TYPE = "collector_html_v1.1"
CATALOG_VERSION = "0.3.0"


def stable_id(kind: str, value: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fps:{kind}:{value}"))


def load_export(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {"collector_version", "catalog_version", "meta", "players", "events", "player_summary"}
    missing = required - set(payload)
    if missing:
        raise ValueError(f"Collector JSON missing required keys: {sorted(missing)}")
    if payload["collector_version"] != "1.1.0":
        raise ValueError(f"Unsupported collector_version: {payload['collector_version']!r}")
    if payload["catalog_version"] != CATALOG_VERSION:
        raise ValueError(f"Unsupported catalog_version: {payload['catalog_version']!r}; expected {CATALOG_VERSION}")
    if not isinstance(payload["meta"], dict) or not isinstance(payload["players"], list) or not isinstance(payload["events"], list):
        raise ValueError("Collector JSON meta/players/events have invalid types")
    for field in ("teamName", "opponentName", "matchDate"):
        if not str(payload["meta"].get(field) or "").strip():
            raise ValueError(f"Collector JSON meta.{field} is required")
    try:
        datetime.fromisoformat(str(payload["meta"]["matchDate"]))
    except ValueError as exc:
        raise ValueError("Collector JSON meta.matchDate must use ISO YYYY-MM-DD") from exc
    return payload


def allowed_events() -> dict[tuple[str, str | None], set[str | None]]:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if catalog.get("catalog_version") != CATALOG_VERSION:
        raise RuntimeError("Local Collector catalog version mismatch")
    return {
        (row["action_type"], row.get("subtype")): set(row.get("outcomes", [])) or {None}
        for row in catalog["events"]
    }


def validate_payload(payload: dict[str, Any]) -> None:
    players = {str(p.get("id")): p for p in payload["players"] if str(p.get("id") or "").strip()}
    if not players:
        raise ValueError("Collector JSON has no players")
    if len(players) != len(payload["players"]):
        raise ValueError("Collector JSON contains missing or duplicate player ids")
    allowed = allowed_events()
    event_ids: set[str] = set()
    for event in payload["events"]:
        event_id = str(event.get("event_id") or "")
        if not event_id or event_id in event_ids:
            raise ValueError("Collector JSON contains missing or duplicate event_id")
        event_ids.add(event_id)
        key = (event.get("action_type"), event.get("subtype"))
        if key not in allowed or event.get("outcome") not in allowed[key]:
            raise ValueError(f"Event {event_id} is outside event_catalog v{CATALOG_VERSION}: {key}/{event.get('outcome')}")
        player_id = event.get("player_id")
        if player_id is not None and str(player_id) not in players:
            raise ValueError(f"Event {event_id} references unknown player_id {player_id!r}")
        if event.get("linked_event_id") and str(event["linked_event_id"]) not in event_ids and str(event["linked_event_id"]) not in {str(e.get("event_id")) for e in payload["events"]}:
            raise ValueError(f"Event {event_id} references unknown linked_event_id")


def event_counts(events: list[dict[str, Any]], player_key: str) -> dict[str, int | None]:
    ev = [e for e in events if str(e.get("player_id")) == player_key]
    count = lambda action, subtype=None, outcome=None: sum(
        e.get("action_type") == action and (subtype is None or e.get("subtype") == subtype) and (outcome is None or e.get("outcome") == outcome)
        for e in ev
    )
    passes = lambda subtype=None, outcome=None: count("PASS", subtype, outcome)
    return {
        "passes_total": passes(), "passes_completed": passes(outcome="SUCCESS"),
        "assists": sum(bool((e.get("qualifiers") or {}).get("assist")) for e in ev if e.get("action_type") == "PASS"),
        "long_balls_total": passes("LONG"), "long_balls_completed": passes("LONG", "SUCCESS"),
        "crosses_total": passes("CROSS"), "crosses_completed": passes("CROSS", "SUCCESS"),
        "dribbles_total": count("DRIBBLE"), "dribbles_won": count("DRIBBLE", outcome="SUCCESS"),
        "turnovers": passes(outcome="FAIL") + count("DRIBBLE", outcome="FAIL") + count("LOSS"),
        "dispossessed": None, "shots_total": count("SHOT"), "shots_blocked": count("SHOT", outcome="BLOCKED"),
        "shots_on_target": count("SHOT", outcome="GOAL") + count("SHOT", outcome="ON_TARGET"),
        "goals": count("SHOT", outcome="GOAL"), "tackles_total": count("TACKLE"), "tackles_won": count("TACKLE", outcome="SUCCESS"),
        "interceptions": count("INTERCEPTION"), "blocked_passes": None, "clearances": count("CLEARANCE"),
        "fouls_committed": count("FOUL", "COMMITTED"), "fouls_received": count("FOUL", "RECEIVED"),
        "yellow_cards": count("CARD", "YELLOW") + sum(e.get("action_type") == "CARD" and e.get("subtype") == "RED" and bool((e.get("qualifiers") or {}).get("second_yellow")) for e in ev),
        "red_cards": count("CARD", "RED"), "penalties_conceded": count("PENALTY", "CONCEDED"), "penalties_won": count("PENALTY", "WON"),
        "saves": count("GK", "SAVE"), "goals_conceded": count("GK", "GOAL_CONCEDED"),
    }


def import_collector_export(export_path: Path, db_path: Path) -> dict[str, str | int]:
    payload = load_export(export_path)
    validate_payload(payload)
    meta, players, events = payload["meta"], payload["players"], payload["events"]
    team_name, opponent_name, date = (str(meta[k]).strip() for k in ("teamName", "opponentName", "matchDate"))
    match_source = f"collector:{date}:{team_name}:{opponent_name}:{str(meta.get('matchName') or '').strip()}"
    team_id, opponent_id, match_id = stable_id("team", team_name), stable_id("team", opponent_name), stable_id("match", match_source)
    session_id = stable_id("collector_session", hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest())
    db_path = db_path.expanduser().resolve()
    with duckdb.connect(str(db_path)) as con:
        con.execute("BEGIN")
        try:
            con.execute("INSERT INTO teams (team_id, display_name, source_name, source_team_id) VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING", [team_id, team_name, "collector", team_name])
            con.execute("INSERT INTO teams (team_id, display_name, source_name, source_team_id) VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING", [opponent_id, opponent_name, "collector", opponent_name])
            con.execute("INSERT INTO matches (match_id, match_date, home_team_id, away_team_id, source_match_id, source_type) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING", [match_id, date, team_id, opponent_id, match_source, SOURCE_TYPE])
            con.execute("INSERT INTO team_match (match_id, team_id, opponent_team_id, is_home, starting_formation) VALUES (?, ?, ?, NULL, ?) ON CONFLICT DO NOTHING", [match_id, team_id, opponent_id, meta.get("formation") or None])
            con.execute("INSERT INTO collector_sessions (collector_session_id, match_id, collector_version, notes) VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING", [session_id, match_id, payload["collector_version"], f"catalog_version={payload['catalog_version']}"])
            con.execute("DELETE FROM player_role_stints WHERE match_id=? AND source_type=?", [match_id, SOURCE_TYPE])
            con.execute("DELETE FROM match_events WHERE match_id=? AND source_type=?", [match_id, SOURCE_TYPE])
            con.execute("DELETE FROM player_match_raw_stats WHERE match_id=? AND source_type=?", [match_id, SOURCE_TYPE])
            for player in players:
                key, name = str(player["id"]), str(player.get("name") or player["id"])
                player_id = stable_id("player", f"{team_name}:{key}")
                minutes = max(0.0, float(player.get("minuteOut", 90) or 0) - float(player.get("minuteIn", 0) or 0))
                con.execute("INSERT INTO players (player_id, display_name, source_name, source_player_id, default_position) VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING", [player_id, name, "collector", key, player.get("role") or None])
                con.execute("INSERT OR REPLACE INTO player_match (match_id, team_id, player_id, started, minutes_played, primary_role, shirt_number) VALUES (?, ?, ?, ?, ?, ?, ?)", [match_id, team_id, player_id, bool(player.get("starter")), minutes, player.get("role") or None, player.get("shirtNumber")])
                changes = sorted(player.get("roleChanges") or [], key=lambda x: x.get("match_second", 0))
                stints = [{"match_second": int(float(player.get("minuteIn", 0) or 0) * 60), "role": player.get("role"), "side": player.get("side"), "formation": meta.get("formation")} , *changes]
                for index, stint in enumerate(stints):
                    if not stint.get("role"):
                        continue
                    end = changes[index].get("match_second") if index < len(changes) else int(float(player.get("minuteOut", 0) or 0) * 60)
                    con.execute("INSERT INTO player_role_stints VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [stable_id("stint", f"{match_id}:{key}:{index}"), match_id, team_id, player_id, stint["match_second"], end, stint.get("role"), None, stint.get("side"), stint.get("formation"), SOURCE_TYPE])
                counts = event_counts(events, key)
                cols = ["match_id", "team_id", "player_id", "source_type", "source_match_id", "source_player_id", "source_minutes", *counts]
                con.execute(f"INSERT INTO player_match_raw_stats ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})", [match_id, team_id, player_id, SOURCE_TYPE, match_source, key, minutes, *counts.values()])
            player_lookup = {str(p["id"]): stable_id("player", f"{team_name}:{p['id']}") for p in players}
            for event in events:
                con.execute("INSERT INTO match_events (event_id, match_id, team_id, player_id, action_type, subtype, outcome, period, match_second, video_second, x, y, qualifiers, linked_event_id, source_type, source_event_id, collector_session_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [stable_id("event", f"{match_id}:{event['event_id']}"), match_id, team_id, player_lookup.get(str(event.get("player_id"))), event["action_type"], event.get("subtype"), event.get("outcome"), event.get("period"), event.get("match_second"), event.get("video_second"), event.get("x"), event.get("y"), json.dumps(event.get("qualifiers") or {}), stable_id("event", f"{match_id}:{event['linked_event_id']}") if event.get("linked_event_id") else None, SOURCE_TYPE, event["event_id"], session_id])
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    return {"match_id": match_id, "team_id": team_id, "players": len(players), "events": len(events), "session_id": session_id}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import official Collector V1.1 JSON export")
    parser.add_argument("export", type=Path)
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    result = import_collector_export(args.export, args.db)
    print("COLLECTOR IMPORT: PASS")
    print(" ".join(f"{key}={value}" for key, value in result.items()))


if __name__ == "__main__":
    main()
