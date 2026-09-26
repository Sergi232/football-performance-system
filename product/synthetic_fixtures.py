"""Deterministic synthetic fixtures for product/UI/PDF QA without the private DuckDB.

These fixtures reproduce the public product contracts and field shapes used by the
Streamlit/report layers. They are explicitly synthetic: they are not a substitute for
final validation on the real Deportivo Alaves demonstrator database.
"""
from __future__ import annotations

import random
from copy import deepcopy

MATCH_RATING_VERSION = "match_rating_v0.5-candidate"
ENGINE_VERSION = "expert_0.7.0"

GUARDRAILS = {
    "recommendation_policy_validated": False,
    "cross_player_ranking_allowed": False,
    "report_may_recalculate_critical_metrics": False,
    "report_may_issue_tactical_recommendation": False,
}

ROLES = ["GK", "CB", "FB_WB", "DM_CM", "AM_W", "ST"]
FIRST_NAMES = ["Alex", "Bruno", "Carlos", "Dani", "Eric", "Ferran", "Guillem", "Hugo", "Ivan", "Jan"]
LAST_NAMES = ["Garcia", "Martinez", "Lopez", "Sanchez", "Fernandez", "Rodriguez", "Perez", "Ruiz", "Torres", "Romero"]


def _player_name(i: int, long_text: bool = False) -> str:
    first = FIRST_NAMES[i % len(FIRST_NAMES)]
    last = LAST_NAMES[(i * 3) % len(LAST_NAMES)]
    if long_text and i % 5 == 0:
        return f"{first} {last} de la Fuente-Montserrat"
    return f"{first} {last}"


def _base(kind: str) -> dict:
    return {
        "report_type": kind,
        "team": {"display_name": "Club Demo FPS"},
        "match_rating_version": MATCH_RATING_VERSION,
        "engine_version": ENGINE_VERSION,
        "guardrails": dict(GUARDRAILS),
    }


def team_payload(seed: int = 1, *, sparse: bool = False, long_text: bool = False, dense: bool = False) -> dict:
    rng = random.Random(seed)
    payload = _base("team")
    n_players = 36 if dense else 24
    snapshot = []
    squad = []
    for i in range(n_players):
        name = _player_name(i, long_text=long_text)
        role = ROLES[i % len(ROLES)]
        rating = None if sparse and i % 4 == 0 else round(5.4 + rng.random() * 2.5, 2)
        conf = None if sparse and i % 4 == 0 else int(55 + rng.random() * 42)
        snapshot.append({
            "player": name,
            "latest_position_group": role,
            "latest_match_rating": rating,
            "latest_confidence": conf,
            "avg_last5": None if rating is None else round(rating + rng.uniform(-0.35, 0.35), 2),
            "trend_delta_5v5": None if sparse and i % 3 == 0 else round(rng.uniform(-0.8, 0.8), 2),
        })
        squad.append({
            "player": name,
            "appearances": max(1, 38 - (i % 17)),
            "starts": max(0, 30 - (i % 19)),
            "minutes": max(90, 2900 - i * 63),
            "goals": i % 8,
            "assists": (i * 2) % 7,
            "observed_roles": role if not long_text else f"{role} · secundari {ROLES[(i + 1) % len(ROLES)]}",
        })
    matches = []
    opponents = [
        "Racing del Nord", "Atletic Mediterrani", "Union Esportiva Central", "Sporting del Litoral",
        "Real Montanya", "Club Metropolita", "Academia Futbolistica de la Vall amb Nom Especialment Llarg",
    ]
    for i in range(12):
        matches.append({
            "match_date": f"2026-{((i + 1) % 9) + 1:02d}-{(i * 2 + 3):02d}",
            "venue": "Local" if i % 2 == 0 else "Visitant",
            "opponent": opponents[i % len(opponents)] if long_text else opponents[i % 6],
            "score_for": None if sparse and i % 5 == 0 else i % 4,
            "score_against": None if sparse and i % 5 == 0 else (i + 1) % 3,
            "starting_formation": None if sparse and i % 4 == 0 else ["4-3-3", "4-2-3-1", "3-4-2-1"][i % 3],
        })
    payload.update({
        "overview": {"matches": 38, "players": n_players, "goals": 47},
        "rating_snapshot": snapshot,
        "matches": matches,
        "squad": squad,
    })
    return payload


def player_payload(seed: int = 2, *, sparse: bool = False, long_text: bool = False, dense: bool = False) -> dict:
    rng = random.Random(seed)
    payload = _base("player")
    player = "Alejandro Fernandez de la Fuente-Montserrat" if long_text else "Alejandro Fernandez"
    ratings = []
    match_history = []
    n_matches = 18 if dense else 10
    for i in range(n_matches):
        rating = None if sparse and i % 3 == 0 else round(5.6 + rng.random() * 2.3, 2)
        ratings.append({
            "match_date": f"2026-{((i + 1) % 9) + 1:02d}-{(i * 2 + 2):02d}",
            "opponent": ("Academia Futbolistica de la Vall amb Nom Especialment Llarg" if long_text and i % 4 == 0 else f"Rival {i + 1}"),
            "minutes_played": 90 if i % 4 else 64,
            "primary_role": ROLES[(i + 2) % len(ROLES)],
            "match_rating_10": rating,
            "match_rating_confidence": None if rating is None else int(60 + rng.random() * 35),
        })
        match_history.append({
            "match_date": ratings[-1]["match_date"],
            "opponent": ratings[-1]["opponent"],
            "minutes": ratings[-1]["minutes_played"],
            "primary_role": ratings[-1]["primary_role"],
            "passes_total": 25 + i * 2,
            "passes_completed": 18 + i * 2,
            "shots_total": i % 5,
            "goals": 1 if i in {2, 7} else 0,
            "tackles_total": (i + 1) % 4,
            "interceptions": i % 3,
        })
    perf = {} if sparse else {
        "position_group": "DM_CM",
        "performance_score": 68.4,
        "score_evidence_confidence": 82,
        "attacking_threat": 54.0,
        "creation_progression": 72.0,
        "defensive_contribution": 69.0,
        "finishing": 45.0,
        "discipline": 78.0,
        "attacking_threat_evidence": "DIRECT_SIGNED",
        "creation_progression_evidence": "DIRECT_SIGNED",
        "defensive_contribution_evidence": "CONTRIBUTION_FALLBACK",
        "finishing_evidence": "DIRECT_SIGNED",
        "discipline_evidence": "DIRECT_SIGNED",
    }
    payload.update({
        "summary": {
            "player": player,
            "appearances": 31,
            "starts": 24,
            "minutes": 2314,
            "goals": 4,
            "assists": 6,
            "observed_roles": "DM_CM · AM_W" if long_text else "DM_CM",
        },
        "match_ratings": ratings,
        "performance_index": perf,
        "latest_role_fit_gate": None if sparse else {
            "observed_role": "DM_CM",
            "same_role_history": 17,
            "evaluable_signals": 8,
            "evidence_coverage": "82%",
            "final_status": "RECOMMENDATION_NOT_ISSUED_POLICY_GUARDRAIL",
        },
        "match_history": match_history,
    })
    return payload


def match_payload(seed: int = 3, *, sparse: bool = False, long_text: bool = False, dense: bool = False) -> dict:
    rng = random.Random(seed)
    payload = _base("match")
    n_players = 18 if dense else 16
    lineup = []
    for i in range(n_players):
        rating = None if sparse and i % 5 == 0 else round(5.3 + rng.random() * 2.8, 2)
        lineup.append({
            "player": _player_name(i, long_text=long_text),
            "started": i < 11,
            "minutes": 90 if i < 8 else 60 + (i % 4) * 10,
            "primary_role": ROLES[i % len(ROLES)],
            "match_rating_10": rating,
            "match_rating_confidence": None if rating is None else int(58 + rng.random() * 40),
            "passes_total": 18 + i * 3,
            "passes_completed": 13 + i * 2,
            "shots_total": i % 5,
            "goals": 1 if i in {8, 11} else 0,
            "tackles_total": (i + 2) % 5,
            "interceptions": i % 4,
        })
    payload.update({
        "match": {
            "opponent": "Academia Futbolistica de la Vall amb Nom Especialment Llarg" if long_text else "Racing del Nord",
            "score_for": None if sparse else 2,
            "score_against": None if sparse else 1,
            "venue": "Local",
            "match_date": "2026-09-20",
            "starting_formation": None if sparse else "4-2-3-1",
        },
        "lineup": lineup,
        "observations": {
            "goal_scorers": [] if sparse else [{"player": lineup[8]["player"], "goals": 1}, {"player": lineup[11]["player"], "goals": 1}],
            "assist_providers": [] if sparse else [{"player": lineup[4]["player"], "assists": 1}],
            "leaders": {
                "shots_total": {"players": [lineup[8]["player"]], "value": 4},
                "passes_completed": {"players": [lineup[5]["player"]], "value": 58},
                "tackles_won": {"players": [lineup[2]["player"]], "value": 5},
                "interceptions": {"players": [lineup[3]["player"]], "value": 4},
            },
        },
    })
    return payload


def scenario_payloads(seed: int = 26092026) -> list[tuple[str, dict]]:
    """Return realistic plus stress-test report payloads with the same production schema."""
    scenarios: list[tuple[str, dict]] = []
    builders = [("team", team_payload), ("player", player_payload), ("match", match_payload)]
    variants = [
        ("normal", {}),
        ("sparse", {"sparse": True}),
        ("long_text", {"long_text": True}),
        ("dense", {"dense": True}),
        ("dense_long", {"dense": True, "long_text": True}),
    ]
    for k, (kind, builder) in enumerate(builders):
        for j, (variant, kwargs) in enumerate(variants):
            scenarios.append((f"{kind}:{variant}", builder(seed + k * 100 + j, **kwargs)))
    return scenarios


def mutated_payload(label: str, payload: dict, seed: int) -> tuple[str, dict]:
    """Create bounded text/missingness variation without changing metric semantics."""
    rng = random.Random(seed)
    out = deepcopy(payload)
    if rng.random() < 0.35:
        out["team"]["display_name"] = "Club Demo FPS amb denominacio institucional llarga"
    if out["report_type"] == "match" and rng.random() < 0.30:
        out["match"]["opponent"] = "Union Esportiva Experimental Metropolitana de la Costa"
    if out["report_type"] == "player" and rng.random() < 0.30:
        out["summary"]["observed_roles"] = "DM_CM · AM_W · FB_WB"
    return f"{label}:m{seed % 1000}", out
