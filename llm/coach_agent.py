"""Tool-using coaching agent over validated Football Performance System analytics.

Architecture:
DATA -> ANALYTICS -> DECISION ENGINE -> LOCAL PRIVACY -> AGENT -> COACH

The model never receives the DuckDB file. It receives only pseudonymized outputs
from read-only tools. Critical ratings/features remain calculated outside the LLM.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.attention_access import get_attention_summary, get_team_attention_flags
from app.data_access import (
    get_latest_player_gate,
    get_player_match_history,
    get_squad_summary,
    get_team_matches,
    get_team_overview,
    list_teams,
)
from app.gps_physical_access import get_gps_summary_status, get_player_gps_history
from app.match_insights import get_match_observations
from app.match_rating_access import (
    MATCH_RATING_VERSION,
    get_match_ratings,
    get_player_match_ratings,
    get_team_match_rating_history,
    get_team_player_rating_snapshot,
)
from app.performance_score_access import get_latest_player_score
from llm.privacy import AliasBook, assert_no_known_entities

try:
    from agents import Agent, ModelSettings, RunContextWrapper, Runner, SQLiteSession, set_tracing_disabled
    from agents.decorators import tool
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Install the agent runtime with: pip install -r requirements.txt") from exc


DEFAULT_MODEL = os.environ.get("FPS_AGENT_MODEL", "gpt-5.6-luna")

AGENT_INSTRUCTIONS = """You are Coach Copilot, the explanation and exploration layer of a football performance system.

You answer open-ended coaching questions by selecting and combining the available read-only tools.
The tool loop may use several calls before answering.

NON-NEGOTIABLE RULES
1. Use only values returned by tools. Never invent observations, metrics, thresholds, weights or model outputs.
2. Match Rating, Performance Index, features and expert-system outputs are already calculated outside the LLM. Never recalculate them.
3. You may sort or compare an explicitly materialized descriptive field returned by a tool, e.g. trend_delta_5v5, but call it a descriptive comparison and report sample size when available.
4. Do not turn descriptive changes into causal claims.
5. Do not issue tactical recommendations, ideal line-ups, injury-risk, fatigue or readiness conclusions unless a validated decision-engine output explicitly authorizes them. Current recommendation policy is not validated.
6. If evidence is missing, say exactly what is unavailable.
7. Preserve role/context. Avoid comparing unlike roles as if they were equivalent unless the user explicitly asks for a descriptive comparison and you state the limitation.
8. Entity identifiers are pseudonyms. Use them exactly as returned by tools; the application restores real names locally after your response.
9. Be concise, coach-oriented and answer in the language of the user.
10. When useful, end with a short 'Evidència consultada' summary naming the tool outputs used, not hidden reasoning.
"""


@dataclass
class CoachAgentRuntime:
    db_path: Path
    team_id: str
    aliases: AliasBook


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _records(frame: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if limit is not None:
        frame = frame.head(limit)
    return [{str(k): _clean(v) for k, v in row.items()} for row in frame.to_dict(orient="records")]


def _external_json(ctx: RunContextWrapper[CoachAgentRuntime], payload: Any) -> str:
    anonymized = ctx.context.aliases.anonymize_obj(payload)
    text = json.dumps(anonymized, ensure_ascii=False, separators=(",", ":"), default=str)
    leaks = assert_no_known_entities(text, ctx.context.aliases)
    if leaks:
        raise RuntimeError(f"Privacy gate blocked tool output: {len(leaks)} known entity leak(s).")
    return text


def build_alias_book(db_path: Path, team_id: str) -> AliasBook:
    aliases = AliasBook()
    teams = list_teams(db_path)
    for row in teams.itertuples(index=False):
        aliases.add("TEAM", row.display_name, entity_id=row.team_id)

    squad = get_squad_summary(db_path, team_id)
    for row in squad.itertuples(index=False):
        aliases.add("PLAYER", row.player, entity_id=row.player_id)

    matches = get_team_matches(db_path, team_id)
    for row in matches.itertuples(index=False):
        aliases.add("MATCH", row.match_id, entity_id=row.match_id)
        if row.opponent:
            aliases.add("OPPONENT", row.opponent)
    return aliases


@tool
def get_team_snapshot(ctx: RunContextWrapper[CoachAgentRuntime]) -> str:
    """Get team overview, recent match-rating history and per-player recent descriptive trends."""
    runtime = ctx.context
    overview = get_team_overview(runtime.db_path, runtime.team_id)
    history = get_team_match_rating_history(runtime.db_path, runtime.team_id).tail(12)
    trends = get_team_player_rating_snapshot(runtime.db_path, runtime.team_id).copy()
    if not trends.empty:
        for col in ["latest_match_rating", "avg_last5", "avg_previous5", "trend_delta_5v5", "latest_confidence"]:
            trends[col] = pd.to_numeric(trends[col], errors="coerce")
        trends = trends.sort_values("trend_delta_5v5", ascending=False, na_position="last")
    payload = {
        "overview": overview,
        "match_rating_version": MATCH_RATING_VERSION,
        "recent_team_rating_history": _records(history),
        "player_recent_form": _records(trends),
        "interpretation": "trend_delta_5v5 is descriptive: mean latest 5 minus mean previous 5; use n_last5/n_previous5.",
    }
    return _external_json(ctx, payload)


@tool
def get_player_profile(ctx: RunContextWrapper[CoachAgentRuntime], player_alias: str) -> str:
    """Get one player's participation, roles, ratings, Performance Index and latest expert gate. Use PLAYER_* aliases."""
    runtime = ctx.context
    player_id = runtime.aliases.resolve_player(player_alias)
    if player_id is None:
        return json.dumps({"error": "Unknown player alias. Use aliases returned by get_team_snapshot."})

    squad = get_squad_summary(runtime.db_path, runtime.team_id)
    selected = squad.loc[squad["player_id"].astype(str) == str(player_id)]
    ratings = get_player_match_ratings(runtime.db_path, runtime.team_id, player_id)
    gate = get_latest_player_gate(runtime.db_path, runtime.team_id, player_id)
    index = get_latest_player_score(runtime.db_path, runtime.team_id, player_id)
    payload = {
        "summary": None if selected.empty else _records(selected, 1)[0],
        "ratings": _records(ratings.tail(12)),
        "latest_performance_index": index,
        "latest_expert_gate": gate,
    }
    return _external_json(ctx, payload)


@tool
def get_player_match_stats(ctx: RunContextWrapper[CoachAgentRuntime], player_alias: str, last_n: int = 10) -> str:
    """Get raw observed player-match statistics for recent matches. This does not calculate new metrics."""
    runtime = ctx.context
    player_id = runtime.aliases.resolve_player(player_alias)
    if player_id is None:
        return json.dumps({"error": "Unknown player alias."})
    last_n = max(1, min(int(last_n), 30))
    frame = get_player_match_history(runtime.db_path, runtime.team_id, player_id).head(last_n)
    return _external_json(ctx, {"rows": _records(frame), "limit": last_n})


@tool
def list_recent_matches(ctx: RunContextWrapper[CoachAgentRuntime], last_n: int = 10) -> str:
    """List recent matches so the agent can select a MATCH_* alias for deeper inspection."""
    runtime = ctx.context
    last_n = max(1, min(int(last_n), 20))
    frame = get_team_matches(runtime.db_path, runtime.team_id).head(last_n)
    return _external_json(ctx, {"matches": _records(frame)})


@tool
def get_match_detail(ctx: RunContextWrapper[CoachAgentRuntime], match_alias: str) -> str:
    """Get one match's ratings and deterministic post-match observations. Use MATCH_* aliases."""
    runtime = ctx.context
    match_id = runtime.aliases.resolve_match(match_alias)
    if match_id is None:
        return json.dumps({"error": "Unknown match alias. Use list_recent_matches first."})
    matches = get_team_matches(runtime.db_path, runtime.team_id)
    selected = matches.loc[matches["match_id"].astype(str) == str(match_id)]
    ratings = get_match_ratings(runtime.db_path, runtime.team_id, match_id)
    observations = get_match_observations(runtime.db_path, runtime.team_id, match_id)
    payload = {
        "match": None if selected.empty else _records(selected, 1)[0],
        "ratings": _records(ratings),
        "observations": observations,
    }
    return _external_json(ctx, payload)


@tool
def get_data_quality(ctx: RunContextWrapper[CoachAgentRuntime]) -> str:
    """Get auditable data/context/evidence limitations and GPS availability for this team."""
    runtime = ctx.context
    summary = get_attention_summary(runtime.db_path, runtime.team_id)
    flags = get_team_attention_flags(runtime.db_path, runtime.team_id)
    gps = get_gps_summary_status(runtime.db_path)
    return _external_json(ctx, {"attention_summary": _records(summary), "recent_flags": _records(flags.head(30)), "gps_status": gps})


@tool
def get_player_gps(ctx: RunContextWrapper[CoachAgentRuntime], player_alias: str) -> str:
    """Get available normalized GPS history for one player. No fatigue/readiness inference is allowed."""
    runtime = ctx.context
    player_id = runtime.aliases.resolve_player(player_alias)
    if player_id is None:
        return json.dumps({"error": "Unknown player alias."})
    try:
        frame = get_player_gps_history(runtime.db_path, runtime.team_id, player_id)
    except Exception as exc:
        return json.dumps({"error": f"GPS unavailable: {type(exc).__name__}"})
    return _external_json(ctx, {"gps_history": _records(frame.tail(12)), "interpretation": "descriptive normalized GPS only; no fatigue/readiness model"})


def create_agent(model: str | None = None) -> Agent[CoachAgentRuntime]:
    # Tracing can contain tool I/O; keep it off by default for this privacy-sensitive workflow.
    set_tracing_disabled(True)
    return Agent[CoachAgentRuntime](
        name="Coach Copilot",
        instructions=AGENT_INSTRUCTIONS,
        model=model or DEFAULT_MODEL,
        model_settings=ModelSettings(store=False, truncation="auto"),
        tools=[
            get_team_snapshot,
            get_player_profile,
            get_player_match_stats,
            list_recent_matches,
            get_match_detail,
            get_data_quality,
            get_player_gps,
        ],
    )


def run_coach_agent(
    question: str,
    *,
    db_path: Path,
    team_id: str,
    session_id: str = "coach-default",
    session_db: Path | None = None,
    model: str | None = None,
) -> str:
    """Run one conversational turn and restore real entity names locally afterwards."""
    aliases = build_alias_book(db_path, team_id)
    runtime = CoachAgentRuntime(Path(db_path), str(team_id), aliases)
    anonymized_question = aliases.anonymize_text(question)
    leaks = assert_no_known_entities(anonymized_question, aliases)
    if leaks:
        raise RuntimeError("Privacy gate blocked the user question before external model call.")

    if session_db is None:
        session_db = Path(db_path).parent / "coach_agent_sessions.sqlite"
    session = SQLiteSession(session_id, db_path=session_db)
    result = Runner.run_sync(
        create_agent(model),
        anonymized_question,
        context=runtime,
        session=session,
    )
    return aliases.deanonymize_text(str(result.final_output))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ask an open question to the anonymized coaching agent.")
    parser.add_argument("question")
    parser.add_argument("--db", default=os.environ.get("FPS_DB_PATH"))
    parser.add_argument("--team-id", required=True)
    parser.add_argument("--session-id", default="coach-cli")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()
    if not args.db:
        raise SystemExit("Set FPS_DB_PATH or pass --db.")
    print(run_coach_agent(args.question, db_path=Path(args.db), team_id=args.team_id, session_id=args.session_id, model=args.model))
