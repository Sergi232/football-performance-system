"""Unattended self-improvement loop for the local Coach Copilot.

This process improves the agent safely without changing football analytics, model
weights, ratings, expert decisions or source code during the run.

It combines:
- a functional Golden Set built from real squad/match entities;
- strict router contracts (missing AND extra tools);
- A/B isolation of mutation-triggered routing failures;
- grounded synthesis checks (numeric support, language, safety, length);
- adaptive replay of weak/failing cases;
- bounded Ollama runtime-profile search;
- checkpointing, root-cause clustering and a recommended runtime profile.

The process does not claim complete semantic correctness. Representative responses
still require human review before LLM-02 can be closed.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm import coach_agent_router_v2  # noqa: F401,E402
from app.data_access import get_squad_summary, get_team_matches, list_teams  # noqa: E402
from llm import coach_agent as _core  # noqa: E402
from llm.coach_agent_fast import DEFAULT_MODEL, ollama_status, run_coach_agent_turn  # noqa: E402
from llm.coach_agent_hybrid import _compact_payload, _plan_tools  # noqa: E402
from llm.run_synthesis_grounding_qa import (  # noqa: E402
    fallback_present,
    guardrail_contract,
    language_contract,
    policy_safe,
    sentence_contract,
)
from llm.run_synthesis_grounding_qa_safe import numeric_grounding_safe  # noqa: E402


PROFILES = [
    {"name": "tiny", "ctx": 1280, "predict": 72, "timeout": 18, "lines": 12, "chars": 1350},
    {"name": "compact", "ctx": 1408, "predict": 88, "timeout": 21, "lines": 15, "chars": 1600},
    {"name": "fast", "ctx": 1536, "predict": 96, "timeout": 23, "lines": 16, "chars": 1750},
    {"name": "balanced", "ctx": 1536, "predict": 112, "timeout": 25, "lines": 18, "chars": 1900},
]

CAPABILITY_GAPS = [
    {
        "capability": "role_ranking",
        "example_es": "¿Quién rinde mejor como interior?",
        "example_ca": "Qui rendeix millor com a interior?",
        "reason": "Needs a validated role-conditioned analytics/tool layer before LLM synthesis.",
    },
    {
        "capability": "player_similarity",
        "example_es": "¿Qué jugadores tienen perfiles similares?",
        "example_ca": "Quins jugadors tenen perfils similars?",
        "reason": "Needs a validated similarity feature space/model before LLM synthesis.",
    },
    {
        "capability": "future_prediction",
        "example_es": "¿Quién rendirá mejor el próximo partido?",
        "example_ca": "Qui rendirà millor el proper partit?",
        "reason": "No validated predictive target/model is available.",
    },
]

MUTATIONS = {
    "es": [
        ("none", "", ""),
        ("evidence_prefix", "Según la evidencia disponible, ", ""),
        ("current_data_prefix", "Con los datos actuales, ", ""),
        ("coach_prefix", "Para el cuerpo técnico: ", ""),
        ("concise_prefix", "De forma breve, ", ""),
        ("limitations_suffix", "", " Indica las limitaciones."),
        ("data_only_suffix", "", " Usa solo datos disponibles."),
        ("precise_suffix", "", " Sé preciso."),
    ],
    "ca": [
        ("none", "", ""),
        ("evidence_prefix", "Segons l'evidència disponible, ", ""),
        ("current_data_prefix", "Amb les dades actuals, ", ""),
        ("coach_prefix", "Per al cos tècnic: ", ""),
        ("concise_prefix", "De forma breu, ", ""),
        ("limitations_suffix", "", " Indica les limitacions."),
        ("data_only_suffix", "", " Usa només dades disponibles."),
        ("precise_suffix", "", " Sigues precís."),
    ],
}

FAILURE_PRIORITY = [
    "ROUTER_WRONG_GUARDRAIL",
    "ROUTER_MISSING_TOOL",
    "ROUTER_EXTRA_TOOL",
    "RUNTIME_ERROR",
    "FALLBACK",
    "SYNTHESIS_TOOL_MISSING",
    "SYNTHESIS_TOOL_EXTRA",
    "NUMERIC_UNGROUNDED",
    "POLICY_SAFETY",
    "LANGUAGE",
    "SENTENCE_LIMIT",
    "SUBJECT_OMISSION",
    "EMPTY_ANSWER",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(text: object) -> str:
    raw = unicodedata.normalize("NFKD", str(text or ""))
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    return " ".join(raw.casefold().strip().split())


def choose_team(db_path: Path, explicit: str | None) -> tuple[str, str]:
    teams = list_teams(db_path)
    if teams.empty:
        raise RuntimeError("No teams available")
    if explicit:
        row = teams.loc[teams["team_id"].astype(str) == str(explicit)]
        if row.empty:
            raise RuntimeError(f"Unknown team_id: {explicit}")
        return str(row.iloc[0]["team_id"]), str(row.iloc[0]["display_name"])
    row = teams.iloc[0]
    return str(row["team_id"]), str(row.iloc[0]["display_name"])


def anchor_tokens(name: str) -> list[str]:
    tokens = [t for t in re.split(r"\W+", norm(name)) if len(t) >= 4]
    return tokens[-2:] if len(tokens) >= 2 else tokens


def case(*, case_id: str, category: str, language: str, question: str, required: set[str], allowed: set[str], history: list[dict[str, str]] | None = None, anchors: list[str] | None = None, anchor_mode: str = "any", guardrail: bool = False) -> dict[str, Any]:
    return {
        "id": case_id,
        "category": category,
        "language": language,
        "question": question,
        "required_tools": sorted(required),
        "allowed_tools": sorted(allowed),
        "history": history,
        "anchors": anchors or [],
        "anchor_mode": anchor_mode,
        "guardrail": guardrail,
    }


def build_golden_set(players: list[str], opponents: list[str], seed: int) -> list[dict[str, Any]]:
    if len(players) < 2:
        raise RuntimeError("Golden Set needs at least two players with >=3 appearances")
    rng = random.Random(seed)
    pool = list(dict.fromkeys(players))
    rng.shuffle(pool)
    p1, p2 = pool[:2]
    p3 = pool[2] if len(pool) >= 3 else p1
    opponent = opponents[0] if opponents else ""
    opponent2 = opponents[1] if len(opponents) >= 2 else opponent
    out: list[dict[str, Any]] = []

    for lang in ("es", "ca"):
        if lang == "es":
            texts = {
                "team_state": "Resume el estado reciente del equipo.",
                "team_change": "¿Qué ha cambiado en la forma reciente del equipo sin inventar causas?",
                "team_mover": "¿Quién presenta el mayor cambio reciente y con qué muestra?",
                "player_profile": f"Explícame el rendimiento reciente de {p1}.",
                "player_evolution": f"¿Cómo ha evolucionado {p2} en los últimos partidos?",
                "player_rating": f"¿Por qué tiene {p1} esta nota reciente?",
                "player_components": f"Separa para {p3} Match Rating, Performance Index y motor experto.",
                "compare_form": f"Compara descriptivamente a {p1} y {p2} en forma reciente.",
                "compare_diff": f"¿Qué diferencias observables hay entre {p1} y {p2} respetando rol y muestra?",
                "match_last": "Resume el último partido con datos observables.",
                "match_named": f"¿Qué sabemos del partido contra {opponent}?" if opponent else "Resume el último partido.",
                "match_standouts": f"¿Qué jugadores destacaron descriptivamente contra {opponent2}?" if opponent2 else "¿Qué jugadores destacaron en el último partido?",
                "quality": "¿Qué limitaciones de datos tenemos ahora mismo?",
                "gps": f"Resume la información GPS disponible de {p1} sin inferir fatiga.",
                "guardrail_xi": "¿Quién debería ser titular el próximo partido?",
                "guardrail_fatigue": "¿Quién está fatigado y debería descansar?",
                "followup_seed": f"Explícame el rendimiento reciente de {p2}.",
                "followup": "¿Y cómo ha evolucionado en los últimos partidos?",
            }
        else:
            texts = {
                "team_state": "Resumeix l'estat recent de l'equip.",
                "team_change": "Què ha canviat en la forma recent de l'equip sense inventar causes?",
                "team_mover": "Qui presenta el canvi recent més gran i amb quina mostra?",
                "player_profile": f"Explica'm el rendiment recent de {p1}.",
                "player_evolution": f"Com ha evolucionat {p2} en els últims partits?",
                "player_rating": f"Per què té {p1} aquesta nota recent?",
                "player_components": f"Separa per a {p3} Match Rating, Performance Index i motor expert.",
                "compare_form": f"Compara descriptivament {p1} i {p2} en forma recent.",
                "compare_diff": f"Quines diferències observables hi ha entre {p1} i {p2} respectant rol i mostra?",
                "match_last": "Resumeix l'últim partit amb dades observables.",
                "match_named": f"Què sabem del partit contra {opponent}?" if opponent else "Resumeix l'últim partit.",
                "match_standouts": f"Quins jugadors van destacar descriptivament contra {opponent2}?" if opponent2 else "Quins jugadors van destacar a l'últim partit?",
                "quality": "Quines limitacions de dades tenim ara mateix?",
                "gps": f"Resumeix la informació GPS disponible de {p1} sense inferir fatiga.",
                "guardrail_xi": "Qui hauria de ser titular el proper partit?",
                "guardrail_fatigue": "Qui està fatigat i hauria de descansar?",
                "followup_seed": f"Explica'm el rendiment recent de {p2}.",
                "followup": "I com ha evolucionat en els últims partits?",
            }

        prefix = f"{lang}_"
        out.extend([
            case(case_id=prefix+"team_state", category="team", language=lang, question=texts["team_state"], required={"get_team_snapshot"}, allowed={"get_team_snapshot"}),
            case(case_id=prefix+"team_change", category="team", language=lang, question=texts["team_change"], required={"get_team_snapshot"}, allowed={"get_team_snapshot"}),
            case(case_id=prefix+"team_mover", category="team", language=lang, question=texts["team_mover"], required={"get_team_snapshot"}, allowed={"get_team_snapshot"}),
            case(case_id=prefix+"player_profile", category="player", language=lang, question=texts["player_profile"], required={"get_player_profile"}, allowed={"get_player_profile"}, anchors=anchor_tokens(p1)),
            case(case_id=prefix+"player_evolution", category="player", language=lang, question=texts["player_evolution"], required={"get_player_profile", "get_player_match_stats"}, allowed={"get_player_profile", "get_player_match_stats"}, anchors=anchor_tokens(p2)),
            case(case_id=prefix+"player_rating", category="player", language=lang, question=texts["player_rating"], required={"get_player_profile", "get_player_match_stats"}, allowed={"get_player_profile", "get_player_match_stats"}, anchors=anchor_tokens(p1)),
            case(case_id=prefix+"player_components", category="player", language=lang, question=texts["player_components"], required={"get_player_profile"}, allowed={"get_player_profile"}, anchors=anchor_tokens(p3)),
            case(case_id=prefix+"compare_form", category="compare", language=lang, question=texts["compare_form"], required={"compare_players"}, allowed={"compare_players"}, anchors=anchor_tokens(p1)+anchor_tokens(p2), anchor_mode="all"),
            case(case_id=prefix+"compare_diff", category="compare", language=lang, question=texts["compare_diff"], required={"compare_players"}, allowed={"compare_players"}, anchors=anchor_tokens(p1)+anchor_tokens(p2), anchor_mode="all"),
            case(case_id=prefix+"match_last", category="match", language=lang, question=texts["match_last"], required={"get_match_detail"}, allowed={"get_match_detail"}),
            case(case_id=prefix+"match_named", category="match", language=lang, question=texts["match_named"], required={"get_match_detail"}, allowed={"get_match_detail"}, anchors=anchor_tokens(opponent) if opponent else []),
            case(case_id=prefix+"match_standouts", category="match", language=lang, question=texts["match_standouts"], required={"get_match_detail"}, allowed={"get_match_detail"}, anchors=anchor_tokens(opponent2) if opponent2 else []),
            case(case_id=prefix+"quality", category="quality", language=lang, question=texts["quality"], required={"get_data_quality"}, allowed={"get_data_quality"}),
            case(case_id=prefix+"gps", category="gps", language=lang, question=texts["gps"], required={"get_player_gps"}, allowed={"get_player_gps"}, anchors=anchor_tokens(p1)),
            case(case_id=prefix+"guardrail_xi", category="guardrail", language=lang, question=texts["guardrail_xi"], required=set(), allowed=set(), guardrail=True),
            case(case_id=prefix+"guardrail_fatigue", category="guardrail", language=lang, question=texts["guardrail_fatigue"], required=set(), allowed=set(), guardrail=True),
            case(case_id=prefix+"followup", category="followup", language=lang, question=texts["followup"], required={"get_player_profile", "get_player_match_stats"}, allowed={"get_player_profile", "get_player_match_stats"}, history=[{"role": "user", "content": texts["followup_seed"]}, {"role": "assistant", "content": f"Resum previ sobre {p2}." if lang == "ca" else f"Resumen previo sobre {p2}."}], anchors=anchor_tokens(p2)),
        ])
    return out


def mutate_case(rng: random.Random, base: dict[str, Any]) -> tuple[str, str]:
    tag, prefix, suffix = rng.choice(MUTATIONS[base["language"]])
    q = str(base["question"]).strip()
    if tag == "none":
        return q, tag
    return (prefix + q.rstrip("?.") + suffix).strip(), tag


def router_contract(question: str, spec: dict[str, Any], db_path: Path, team_id: str) -> dict[str, Any]:
    required = set(spec["required_tools"])
    allowed = set(spec["allowed_tools"])
    plan, guardrail = _plan_tools(question, db_path=db_path, team_id=team_id, history=spec.get("history"))
    tools = [name for name, _ in plan]
    actual = set(tools)
    missing = sorted(required - actual)
    extra = sorted(actual - allowed)
    if spec["guardrail"]:
        passed = bool(guardrail) and not tools
        wrong_guardrail = not bool(guardrail) or bool(tools)
    else:
        passed = guardrail is None and not missing and not extra
        wrong_guardrail = guardrail is not None
    return {"pass": passed, "tools": tools, "missing_tools": missing, "extra_tools": extra, "guardrail": guardrail, "wrong_guardrail": wrong_guardrail}


def capture_evidence(question: str, spec: dict[str, Any], db_path: Path, team_id: str) -> tuple[dict[str, Any], list[str]]:
    plan, guardrail = _plan_tools(question, db_path=db_path, team_id=team_id, history=spec.get("history"))
    if guardrail:
        return {}, []
    runtime = _core.CoachAgentRuntime(db_path, team_id)
    evidence: dict[str, Any] = {}
    tools: list[str] = []
    for name, args in plan:
        fn = _core.TOOL_FUNCTIONS.get(name)
        if fn is None:
            continue
        tools.append(name)
        try:
            payload = fn(runtime, args)
        except Exception as exc:
            payload = {"error": f"{type(exc).__name__}: {exc}"}
        evidence[name] = _compact_payload(name, payload)
    return evidence, tools


def subject_contract(answer: str, spec: dict[str, Any]) -> bool:
    anchors = [norm(x) for x in spec.get("anchors", []) if norm(x)]
    if not anchors:
        return True
    text = norm(answer)
    hits = [a in text for a in anchors]
    if spec.get("anchor_mode") == "all":
        return sum(hits) >= min(2, len(anchors))
    return any(hits)


def set_profile(profile: dict[str, Any]) -> None:
    os.environ["FPS_AGENT_NUM_CTX"] = str(profile["ctx"])
    os.environ["FPS_AGENT_NUM_PREDICT"] = str(profile["predict"])
    os.environ["FPS_AGENT_TIMEOUT"] = str(profile["timeout"])
    os.environ["FPS_AGENT_EVIDENCE_LINES"] = str(profile["lines"])
    os.environ["FPS_AGENT_EVIDENCE_CHARS"] = str(profile["chars"])


def profile_score(stats: Counter) -> float:
    attempts = stats["attempts"]
    if not attempts:
        return -1e9
    pass_rate = stats["passes"] / attempts
    avg_s = stats["elapsed_ms"] / attempts / 1000.0
    timeout_rate = stats["runtime_fail"] / attempts
    return (pass_rate * 100.0) - (avg_s * 0.8) - (timeout_rate * 18.0)


def select_profile(rng: random.Random, stats: dict[str, Counter]) -> dict[str, Any]:
    for profile in PROFILES:
        if stats[profile["name"]]["attempts"] < 4:
            return profile
    if rng.random() < 0.18:
        return rng.choice(PROFILES)
    return max(PROFILES, key=lambda p: profile_score(stats[p["name"]]))


def evaluate_synthesis(*, question: str, spec: dict[str, Any], db_path: Path, team_id: str, model: str) -> dict[str, Any]:
    evidence, planned_tools = capture_evidence(question, spec, db_path, team_id)
    started = time.monotonic()
    try:
        result = run_coach_agent_turn(question, db_path=db_path, team_id=team_id, history=spec.get("history"), model=model)
        answer = str(result.text or "")
        runtime_error = result.error
        tools_used = list(result.tools_used)
    except Exception as exc:
        answer = ""
        runtime_error = f"{type(exc).__name__}: {exc}"
        tools_used = []
    elapsed = time.monotonic() - started
    required = set(spec["required_tools"])
    allowed = set(spec["allowed_tools"])
    actual = set(tools_used)
    tool_missing = sorted(required - actual)
    tool_extra = sorted(actual - allowed)

    if spec["guardrail"]:
        guardrail_ok = guardrail_contract(answer, spec["language"], tuple(tools_used))
        numeric_ok, unsupported_numbers = True, []
        safety_ok, unsafe_patterns = True, []
        no_fallback = True
        tool_ok = not tools_used
    else:
        guardrail_ok = True
        numeric_ok, unsupported_numbers = numeric_grounding_safe(answer, question, evidence)
        safety_ok, unsafe_patterns = policy_safe(answer, spec["category"])
        no_fallback = not fallback_present(answer)
        tool_ok = not tool_missing and not tool_extra

    lang_ok, detected_lang = language_contract(answer, spec["language"])
    length_ok, sentence_count = sentence_contract(answer)
    subject_ok = subject_contract(answer, spec)
    nonempty = bool(answer.strip())
    passed = runtime_error is None and nonempty and tool_ok and guardrail_ok and numeric_ok and safety_ok and lang_ok and length_ok and no_fallback and subject_ok

    failures: list[str] = []
    if runtime_error is not None: failures.append("RUNTIME_ERROR")
    if not no_fallback: failures.append("FALLBACK")
    if tool_missing: failures.append("SYNTHESIS_TOOL_MISSING")
    if tool_extra: failures.append("SYNTHESIS_TOOL_EXTRA")
    if not numeric_ok: failures.append("NUMERIC_UNGROUNDED")
    if not safety_ok or not guardrail_ok: failures.append("POLICY_SAFETY")
    if not lang_ok: failures.append("LANGUAGE")
    if not length_ok: failures.append("SENTENCE_LIMIT")
    if not subject_ok: failures.append("SUBJECT_OMISSION")
    if not nonempty: failures.append("EMPTY_ANSWER")

    return {"pass": passed, "failures": failures, "answer": answer, "runtime_error": runtime_error or "", "tools_used": tools_used, "planned_tools": planned_tools, "tool_missing": tool_missing, "tool_extra": tool_extra, "numeric_grounding_pass": numeric_ok, "unsupported_numbers": unsupported_numbers, "policy_safety_pass": safety_ok and guardrail_ok, "unsafe_patterns": unsafe_patterns, "language_pass": lang_ok, "detected_language": detected_lang or "UNKNOWN", "sentence_limit_pass": length_ok, "sentence_count": sentence_count, "subject_pass": subject_ok, "fallback_absent": no_fallback, "elapsed_s": round(elapsed, 3)}


def failure_classification(router: dict[str, Any], synth: dict[str, Any] | None) -> str:
    if router["wrong_guardrail"]: return "ROUTER_WRONG_GUARDRAIL"
    if router["missing_tools"]: return "ROUTER_MISSING_TOOL"
    if router["extra_tools"]: return "ROUTER_EXTRA_TOOL"
    if synth is None: return "ROUTER_PASS"
    if synth["pass"]: return "FULL_PASS"
    for name in FAILURE_PRIORITY:
        if name in synth["failures"]: return name
    return "SYNTHESIS_FAIL"


def weighted_case(rng: random.Random, golden: list[dict[str, Any]], recent: deque[tuple[str, bool]]) -> dict[str, Any]:
    by_id = {c["id"]: c for c in golden}
    stats: dict[str, list[bool]] = defaultdict(list)
    for case_id, ok in recent: stats[case_id].append(ok)
    weights: list[float] = []
    for spec in golden:
        vals = stats.get(spec["id"], [])
        if not vals:
            weights.append(1.8)
            continue
        fail_rate = sum(1 for x in vals if not x) / len(vals)
        weights.append(1.0 + 4.0 * fail_rate)
    return by_id[rng.choices([c["id"] for c in golden], weights=weights, k=1)[0]]


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh: fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows: return
    flat_rows: list[dict[str, Any]] = []
    keys: list[str] = []
    for row in rows:
        copied = dict(row)
        for key, value in list(copied.items()):
            if isinstance(value, (dict, list, tuple, set)): copied[key] = json.dumps(value, ensure_ascii=False, default=str)
        flat_rows.append(copied)
        for key in copied:
            if key not in keys: keys.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys); writer.writeheader(); writer.writerows(flat_rows)


def recommended_profile_payload(profile_stats: dict[str, Counter]) -> dict[str, Any]:
    tested = [p for p in PROFILES if profile_stats[p["name"]]["attempts"]]
    best = max(tested, key=lambda p: profile_score(profile_stats[p["name"]])) if tested else PROFILES[-1]
    st = profile_stats[best["name"]]
    return {"profile": best, "attempts": int(st["attempts"]), "passes": int(st["passes"]), "pass_rate": (st["passes"] / st["attempts"]) if st["attempts"] else None, "avg_elapsed_s": (st["elapsed_ms"] / st["attempts"] / 1000.0) if st["attempts"] else None, "score": profile_score(st) if st["attempts"] else None, "env": {"FPS_AGENT_NUM_CTX": str(best["ctx"]), "FPS_AGENT_NUM_PREDICT": str(best["predict"]), "FPS_AGENT_TIMEOUT": str(best["timeout"]), "FPS_AGENT_EVIDENCE_LINES": str(best["lines"]), "FPS_AGENT_EVIDENCE_CHARS": str(best["chars"])}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("FPS_DB_PATH"))
    parser.add_argument("--team-id", default=None)
    parser.add_argument("--model", default=os.environ.get("FPS_LOCAL_LLM_MODEL", DEFAULT_MODEL))
    parser.add_argument("--hours", type=float, default=10.0)
    parser.add_argument("--max-cases", type=int, default=100000)
    parser.add_argument("--synthesis-rate", type=float, default=0.72)
    parser.add_argument("--seed", type=int, default=20260930)
    parser.add_argument("--output", default="outputs/agent_eval/self_improve")
    args = parser.parse_args()
    if not args.db: raise SystemExit("Set FPS_DB_PATH or pass --db")
    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists(): raise SystemExit(f"Database not found: {db_path}")
    status = ollama_status()
    if not status.get("available"): raise SystemExit(f"Ollama unavailable: {status.get('error')}")
    installed = set(status.get("models") or [])
    if args.model not in installed: raise SystemExit(f"Model not installed: {args.model}")

    team_id, team_name = choose_team(db_path, args.team_id)
    squad = get_squad_summary(db_path, team_id)
    players = squad.loc[pd.to_numeric(squad.get("appearances"), errors="coerce").fillna(0) >= 3, "player"].dropna().astype(str).tolist()
    matches = get_team_matches(db_path, team_id).head(24)
    opponents = matches.get("opponent", pd.Series(dtype=str)).dropna().astype(str).tolist()
    golden = build_golden_set(players, opponents, args.seed)

    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    rows_path = output / f"agent_self_improve_{run_id}_cases.jsonl"
    failures_path = output / f"agent_self_improve_{run_id}_failures.csv"
    checkpoints_path = output / f"agent_self_improve_{run_id}_checkpoints.jsonl"
    summary_path = output / f"agent_self_improve_{run_id}_summary.json"
    recommended_path = output / "recommended_profile.json"
    env_path = output / "recommended_profile.env"
    root_causes_path = output / f"agent_self_improve_{run_id}_root_causes.json"
    golden_path = output / f"agent_self_improve_{run_id}_golden_set.json"
    write_json(golden_path, {"team": team_name, "team_id": team_id, "cases": golden, "capability_gaps": CAPABILITY_GAPS})

    rng = random.Random(args.seed)
    deadline = time.monotonic() + max(0.01, args.hours) * 3600.0
    recent: deque[tuple[str, bool]] = deque(maxlen=800)
    replay: deque[dict[str, Any]] = deque(maxlen=600)
    profile_stats: dict[str, Counter] = {p["name"]: Counter() for p in PROFILES}
    counters = Counter(); category_stats: dict[str, Counter] = defaultdict(Counter); language_stats: dict[str, Counter] = defaultdict(Counter)
    mutation_failures: Counter = Counter(); extra_tool_clusters: Counter = Counter(); missing_tool_clusters: Counter = Counter(); failure_rows: list[dict[str, Any]] = []

    print("=" * 100)
    print("COACH COPILOT SELF-IMPROVE · GOLDEN SET + ROOT-CAUSE QA · LOCAL ONLY")
    print(f"team={team_name} model={args.model} golden_cases={len(golden)} hours={args.hours}")
    print("Safe scope: no source-code rewrite, no model-weight training, no analytics/decision changes.")
    print("Adaptive scope: case replay + weak-case oversampling + bounded Ollama profile search.")
    print("=" * 100)

    case_no = 0
    try:
        while case_no < args.max_cases and time.monotonic() < deadline:
            case_no += 1
            if replay and rng.random() < 0.38:
                item = replay.popleft(); spec = item["spec"]; forced_tag = item.get("mutation_tag")
                choices = [m for m in MUTATIONS[spec["language"]] if m[0] == forced_tag] if forced_tag else []
                if choices:
                    tag, prefix, suffix = choices[0]; question = (prefix + str(spec["question"]).rstrip("?.") + suffix).strip(); mutation_tag = tag
                else: question, mutation_tag = mutate_case(rng, spec)
                source = "failure_replay"
            else:
                spec = weighted_case(rng, golden, recent); question, mutation_tag = mutate_case(rng, spec); source = "adaptive"

            started = time.monotonic(); router = router_contract(question, spec, db_path, team_id)
            ab_base_pass: bool | None = None; mutation_trigger = False
            if not router["pass"] and question != spec["question"]:
                base_router = router_contract(spec["question"], spec, db_path, team_id); ab_base_pass = bool(base_router["pass"]); mutation_trigger = bool(base_router["pass"])
                if mutation_trigger: mutation_failures[f"{mutation_tag}|{failure_classification(router, None)}"] += 1

            do_synthesis = router["pass"] and (spec["guardrail"] or rng.random() < max(0.05, min(float(args.synthesis_rate), 1.0)))
            synth: dict[str, Any] | None = None; profile_name = ""
            if do_synthesis:
                profile = select_profile(rng, profile_stats); profile_name = profile["name"]; set_profile(profile)
                synth = evaluate_synthesis(question=question, spec=spec, db_path=db_path, team_id=team_id, model=args.model)
                ps = profile_stats[profile_name]; ps["attempts"] += 1; ps["passes"] += int(bool(synth["pass"])); ps["fails"] += int(not bool(synth["pass"])); ps["elapsed_ms"] += int(float(synth["elapsed_s"]) * 1000); ps["runtime_fail"] += int("RUNTIME_ERROR" in synth["failures"] or "FALLBACK" in synth["failures"])

            classification = failure_classification(router, synth); passed = router["pass"] and (synth is None or synth["pass"]); elapsed = time.monotonic() - started
            if router["extra_tools"]: extra_tool_clusters[f"{spec['category']}|{mutation_tag}|{','.join(router['extra_tools'])}"] += 1
            if router["missing_tools"]: missing_tool_clusters[f"{spec['category']}|{mutation_tag}|{','.join(router['missing_tools'])}"] += 1
            recent.append((spec["id"], passed)); counters[classification] += 1; category_stats[spec["category"]]["cases"] += 1; category_stats[spec["category"]]["passes"] += int(passed); language_stats[spec["language"]]["cases"] += 1; language_stats[spec["language"]]["passes"] += int(passed)

            row = {"case_no": case_no, "golden_id": spec["id"], "category": spec["category"], "language": spec["language"], "source": source, "mutation_tag": mutation_tag, "question": question, "required_tools": spec["required_tools"], "allowed_tools": spec["allowed_tools"], "router_pass": router["pass"], "router_tools": router["tools"], "router_missing": router["missing_tools"], "router_extra": router["extra_tools"], "mutation_trigger": mutation_trigger, "ab_base_pass": ab_base_pass, "synthesis_attempted": do_synthesis, "synthesis_profile": profile_name, "synthesis_pass": None if synth is None else synth["pass"], "classification": classification, "pass": passed, "elapsed_total_s": round(elapsed, 3), "runtime_error": "" if synth is None else synth["runtime_error"], "synthesis_failures": [] if synth is None else synth["failures"], "tools_used": [] if synth is None else synth["tools_used"], "numeric_grounding_pass": None if synth is None else synth["numeric_grounding_pass"], "unsupported_numbers": [] if synth is None else synth["unsupported_numbers"], "policy_safety_pass": None if synth is None else synth["policy_safety_pass"], "language_pass": None if synth is None else synth["language_pass"], "sentence_limit_pass": None if synth is None else synth["sentence_limit_pass"], "subject_pass": None if synth is None else synth["subject_pass"], "fallback_absent": None if synth is None else synth["fallback_absent"], "answer_preview": "" if synth is None else str(synth["answer"]).replace("\r", " ").replace("\n", " ")[:900], "timestamp": now_iso()}
            write_jsonl(rows_path, row)
            if not passed:
                failure_rows.append(row)
                for _ in range(3): replay.append({"spec": spec, "mutation_tag": mutation_tag})
            if case_no % 20 == 0 or not passed:
                print(f"[{case_no:06d}] {'PASS' if passed else 'FAIL'} {spec['language']} {spec['category']:<9} {classification:<24} {elapsed:>5.1f}s profile={profile_name or '-':<8} replay={len(replay)}")
            if case_no % 100 == 0:
                rec = recommended_profile_payload(profile_stats); write_json(recommended_path, rec); env_path.write_text("\n".join(f"{k}={v}" for k, v in rec["env"].items()) + "\n", encoding="utf-8")
                checkpoint = {"case": case_no, "elapsed_hours": round(args.hours - max(0.0, deadline - time.monotonic()) / 3600.0, 3), "classifications": dict(counters), "recommended_profile": rec, "top_mutation_triggers": mutation_failures.most_common(12), "top_extra_tool_clusters": extra_tool_clusters.most_common(12), "top_missing_tool_clusters": missing_tool_clusters.most_common(12), "timestamp": now_iso()}; write_jsonl(checkpoints_path, checkpoint)
    except KeyboardInterrupt:
        print("Interrupted by user; writing final artifacts...")

    write_csv(failures_path, failure_rows)
    rec = recommended_profile_payload(profile_stats); write_json(recommended_path, rec); env_path.write_text("\n".join(f"{k}={v}" for k, v in rec["env"].items()) + "\n", encoding="utf-8")
    root_causes = {"mutation_trigger_failures": mutation_failures.most_common(), "extra_tool_clusters": extra_tool_clusters.most_common(), "missing_tool_clusters": missing_tool_clusters.most_common(), "interpretation": "A mutation_trigger means the base Golden Set question passed routing but a controlled wording mutation failed. This is evidence for a routing trigger, not a synthesis failure."}; write_json(root_causes_path, root_causes)
    by_category = {category: {"cases": int(st["cases"]), "passes": int(st["passes"]), "pass_rate": (st["passes"] / st["cases"]) if st["cases"] else None} for category, st in sorted(category_stats.items())}
    by_language = {language: {"cases": int(st["cases"]), "passes": int(st["passes"]), "pass_rate": (st["passes"] / st["cases"]) if st["cases"] else None} for language, st in sorted(language_stats.items())}
    profiles = {name: {"attempts": int(st["attempts"]), "passes": int(st["passes"]), "pass_rate": (st["passes"] / st["attempts"]) if st["attempts"] else None, "avg_elapsed_s": (st["elapsed_ms"] / st["attempts"] / 1000.0) if st["attempts"] else None, "runtime_failures": int(st["runtime_fail"]), "score": profile_score(st) if st["attempts"] else None} for name, st in profile_stats.items()}
    total = max(1, sum(counters.values()))
    summary = {"run_id": run_id, "team": team_name, "team_id": team_id, "model": args.model, "duration_target_hours": args.hours, "cases": case_no, "golden_cases": len(golden), "classifications": dict(counters), "overall_iteration_pass_rate": (counters["ROUTER_PASS"] + counters["FULL_PASS"]) / total, "full_synthesis_passes": int(counters["FULL_PASS"]), "by_category": by_category, "by_language": by_language, "profiles": profiles, "recommended_profile": rec, "root_cause_file": str(root_causes_path), "golden_set_file": str(golden_path), "failures_csv": str(failures_path), "cases_jsonl": str(rows_path), "capability_gaps": CAPABILITY_GAPS, "safety_scope": {"source_code_auto_rewrite": False, "model_weight_training": False, "analytics_mutation": False, "decision_engine_mutation": False, "runtime_profile_search": True, "adaptive_case_replay": True, "router_root_cause_ablation": True}, "semantic_scope": {"deterministic_checks": ["strict required/allowed tool routing", "mutation A/B root-cause isolation", "runtime/fallback", "numeric grounding", "policy safety", "language", "six-sentence limit", "subject mention when applicable"], "human_review_required": True, "not_claimed": ["complete coaching usefulness", "complete semantic correctness"]}, "finished_at": now_iso()}
    write_json(summary_path, summary)
    print("=" * 100); print(json.dumps(summary, ensure_ascii=False, indent=2)); print(f"summary={summary_path}"); print(f"recommended_profile={recommended_path}"); print(f"root_causes={root_causes_path}"); print(f"failures={failures_path}")


if __name__ == "__main__":
    main()
