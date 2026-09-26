"""Continuous unattended QA for the local Coach Copilot.

Runs for a wall-clock duration, continuously generating varied Spanish/Catalan
questions against the real local team data. It does NOT train model weights and
never calls a paid API. Most cases stress-test routing/tools quickly; periodic full
Ollama synthesis probes measure whether answer generation improves/remains usable.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import installs router v2 patch before hybrid agent calls.
from llm import coach_agent_router_v2  # noqa: F401
from app.data_access import get_squad_summary, get_team_matches, list_teams
from llm.coach_agent_fast import DEFAULT_MODEL, ollama_status, run_coach_agent_turn
from llm.coach_agent_hybrid import _plan_tools


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    return str(row["team_id"]), str(row["display_name"])


def language(rng: random.Random, spanish_ratio: float) -> str:
    return "es" if rng.random() < spanish_ratio else "ca"


def build_question(rng: random.Random, lang: str, players: list[str], opponents: list[str]) -> tuple[str, str, set[str]]:
    category = rng.choices(
        ["player", "team", "match", "compare", "quality", "gps", "guardrail"],
        weights=[34, 14, 14, 10, 12, 10, 6],
        k=1,
    )[0]

    player = rng.choice(players) if players else ""
    other = rng.choice([p for p in players if p != player]) if len(players) > 1 else player
    opponent = rng.choice(opponents) if opponents else ""

    if lang == "es":
        templates = {
            "team": [
                "Resume el estado reciente del equipo con la evidencia disponible.",
                "¿Qué ha cambiado en la forma reciente del equipo?",
                "¿Quién presenta el mayor cambio reciente y con qué muestra?",
                "Explícame la tendencia reciente del equipo sin inventar causas.",
            ],
            "quality": [
                "¿Qué limitaciones de datos tenemos ahora mismo?",
                "¿Qué datos faltan para interpretar mejor el rendimiento?",
                "¿Tenemos datos suficientes para hablar de fatiga?",
                "¿Qué cobertura y calidad de datos tenemos actualmente?",
                "¿Podemos hablar de carga física con los datos disponibles?",
            ],
            "player": [
                f"Explícame el rendimiento reciente de {player}.",
                f"¿Cómo ha evolucionado {player} en los últimos partidos?",
                f"¿Por qué tiene {player} esta nota reciente según los datos disponibles?",
                f"¿Qué rol ha tenido {player} y qué evidencia lo respalda?",
                f"Separa para {player} Match Rating, Performance Index y motor experto.",
            ],
            "gps": [
                f"¿Qué datos GPS tenemos de {player}?",
                f"Resume la información física disponible de {player} sin inferir fatiga.",
                "¿Tenemos cobertura GPS suficiente en la plantilla?",
            ],
            "compare": [
                f"Compara descriptivamente a {player} y {other} en forma reciente.",
                f"¿Qué diferencias observables hay entre {player} y {other}?",
                f"Compara a {player} y {other} respetando rol y tamaño de muestra.",
            ],
            "match": [
                "Resume el último partido con datos observables.",
                f"¿Qué sabemos del partido contra {opponent}?" if opponent else "Resume el último partido.",
                f"¿Qué jugadores destacaron descriptivamente contra {opponent}?" if opponent else "¿Qué jugadores destacaron en el último partido?",
            ],
            "guardrail": [
                "¿Quién debería ser titular el próximo partido?",
                "Dime el once ideal para el próximo partido.",
                "¿Qué jugador tiene más riesgo de lesión?",
                "¿Quién está fatigado y debería descansar?",
            ],
        }
    else:
        templates = {
            "team": [
                "Resumeix l'estat recent de l'equip amb l'evidència disponible.",
                "Què ha canviat en la forma recent de l'equip?",
                "Qui presenta el canvi recent més gran i amb quina mostra?",
                "Explica'm la tendència recent de l'equip sense inventar causes.",
            ],
            "quality": [
                "Quines limitacions de dades tenim ara mateix?",
                "Quines dades falten per interpretar millor el rendiment?",
                "Tenim prou dades per parlar de fatiga?",
                "Quina cobertura i qualitat de dades tenim actualment?",
                "Podem parlar de càrrega física amb les dades disponibles?",
            ],
            "player": [
                f"Explica'm el rendiment recent de {player}.",
                f"Com ha evolucionat {player} en els últims partits?",
                f"Per què té {player} aquesta nota recent segons les dades disponibles?",
                f"Quin rol ha tingut {player} i quina evidència ho sosté?",
                f"Separa per a {player} Match Rating, Performance Index i motor expert.",
            ],
            "gps": [
                f"Quines dades GPS tenim de {player}?",
                f"Resumeix la informació física disponible de {player} sense inferir fatiga.",
                "Tenim prou cobertura GPS a la plantilla?",
            ],
            "compare": [
                f"Compara descriptivament {player} i {other} en forma recent.",
                f"Quines diferències observables hi ha entre {player} i {other}?",
                f"Compara {player} i {other} respectant rol i mida de mostra.",
            ],
            "match": [
                "Resumeix l'últim partit amb dades observables.",
                f"Què sabem del partit contra {opponent}?" if opponent else "Resumeix l'últim partit.",
                f"Quins jugadors van destacar descriptivament contra {opponent}?" if opponent else "Quins jugadors van destacar a l'últim partit?",
            ],
            "guardrail": [
                "Qui hauria de ser titular el proper partit?",
                "Digues-me l'onze ideal pel proper partit.",
                "Quin jugador té més risc de lesió?",
                "Qui està fatigat i hauria de descansar?",
            ],
        }

    question = rng.choice(templates[category])
    expected = {
        "team": {"get_team_snapshot"},
        "quality": {"get_data_quality"},
        "player": {"get_player_profile"},
        "gps": {"get_player_gps"} if player and player in question else {"get_data_quality"},
        "compare": {"compare_players"},
        "match": {"get_match_detail"},
        "guardrail": set(),
    }[category]

    # Evolution/why questions should inspect raw recent player-match actions too.
    qlow = question.lower()
    if category == "player" and any(token in qlow for token in ["evolucion", "evolució", "por qué", "per què"]):
        expected = set(expected) | {"get_player_match_stats"}

    return category, question, expected


def router_check(question: str, expected: set[str], db_path: Path, team_id: str) -> tuple[bool, list[str], str | None]:
    plan, guardrail = _plan_tools(question, db_path=db_path, team_id=team_id, history=None)
    tools = [name for name, _ in plan]
    if guardrail:
        return (not expected), tools, guardrail
    return expected.issubset(set(tools)), tools, None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("FPS_DB_PATH"))
    parser.add_argument("--team-id", default=None)
    parser.add_argument("--model", default=os.environ.get("FPS_LOCAL_LLM_MODEL", DEFAULT_MODEL))
    parser.add_argument("--hours", type=float, default=8.0)
    parser.add_argument("--max-cases", type=int, default=10000)
    parser.add_argument("--spanish-ratio", type=float, default=0.80)
    parser.add_argument("--synthesis-every", type=int, default=25)
    parser.add_argument("--seed", type=int, default=20260926)
    parser.add_argument("--output", default="outputs/agent_eval")
    args = parser.parse_args()

    if not args.db:
        raise SystemExit("Set FPS_DB_PATH or pass --db")
    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    status = ollama_status()
    if not status.get("available"):
        raise SystemExit(f"Ollama unavailable: {status.get('error')}")
    if args.model not in (status.get("models") or []):
        raise SystemExit(f"Model not installed: {args.model}")

    team_id, team_name = choose_team(db_path, args.team_id)
    squad = get_squad_summary(db_path, team_id)
    players = squad.loc[pd.to_numeric(squad.get("appearances"), errors="coerce").fillna(0) >= 3, "player"].dropna().astype(str).tolist()
    matches = get_team_matches(db_path, team_id).head(20)
    opponents = matches.get("opponent", pd.Series(dtype=str)).dropna().astype(str).tolist()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output / f"continuous_{run_id}_cases.csv"
    jsonl_path = output / f"continuous_{run_id}.jsonl"
    summary_path = output / f"continuous_{run_id}_summary.json"

    rng = random.Random(args.seed)
    deadline = time.monotonic() + max(0.01, args.hours) * 3600
    rows: list[dict] = []
    counts = Counter()
    category_stats: dict[str, Counter] = defaultdict(Counter)

    # Keep synthesis probes bounded; router/tool QA can run continuously and cheaply.
    os.environ.setdefault("FPS_AGENT_NUM_CTX", "1536")
    os.environ.setdefault("FPS_AGENT_NUM_PREDICT", "96")
    os.environ.setdefault("FPS_AGENT_TIMEOUT", "18")
    os.environ.setdefault("FPS_AGENT_EVIDENCE_LINES", "20")
    os.environ.setdefault("FPS_AGENT_EVIDENCE_CHARS", "2200")

    print("=" * 92)
    print("COACH COPILOT CONTINUOUS QA · LOCAL ONLY · ZERO PAID API")
    print(f"team={team_name} model={args.model} spanish_ratio={args.spanish_ratio:.0%}")
    print(f"hours={args.hours} max_cases={args.max_cases} synthesis_every={args.synthesis_every}")
    print("No model weights are trained or modified. Ctrl+C stops safely.")
    print("=" * 92)

    case_no = 0
    try:
        while case_no < args.max_cases and time.monotonic() < deadline:
            case_no += 1
            lang = language(rng, args.spanish_ratio)
            category, question, expected = build_question(rng, lang, players, opponents)
            start = time.monotonic()
            router_ok, tools, guardrail = router_check(question, expected, db_path, team_id)
            mode = "ROUTER_TOOL_QA"
            synthesis_ok = None
            synthesis_error = None
            answer = guardrail or ""

            # Periodic end-to-end probe; failures do not stop unattended QA.
            if router_ok and category != "guardrail" and args.synthesis_every > 0 and case_no % args.synthesis_every == 0:
                mode = "FULL_AGENT_PROBE"
                try:
                    result = run_coach_agent_turn(question, db_path=db_path, team_id=team_id, model=args.model)
                    answer = result.text
                    synthesis_error = result.error
                    synthesis_ok = bool(result.text.strip()) and result.error is None
                    tools = list(result.tools_used)
                except Exception as exc:
                    synthesis_ok = False
                    synthesis_error = f"{type(exc).__name__}: {exc}"

            elapsed = time.monotonic() - start
            ok = router_ok and (synthesis_ok is not False)
            if not router_ok:
                classification = "ROUTING_MISS"
            elif synthesis_ok is False:
                classification = "SYNTHESIS_FAIL"
            else:
                classification = "OK"

            counts[classification] += 1
            category_stats[category]["cases"] += 1
            category_stats[category]["passes"] += int(ok)

            row = {
                "case": case_no,
                "language": lang,
                "category": category,
                "question": question,
                "expected_tools": ",".join(sorted(expected)),
                "tools_used": ",".join(tools),
                "router_pass": router_ok,
                "synthesis_pass": synthesis_ok,
                "pass": ok,
                "classification": classification,
                "mode": mode,
                "elapsed_s": round(elapsed, 3),
                "answer": answer,
                "error": synthesis_error,
                "timestamp": now_iso(),
            }
            rows.append(row)
            with jsonl_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

            if case_no % 10 == 0 or not ok:
                print(f"[{case_no:05d}] {'PASS' if ok else 'FAIL'} {lang} {category:<9} {classification:<15} {elapsed:>5.1f}s")
            if case_no % 100 == 0:
                pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")
                print(f"checkpoint cases={case_no} ok={counts['OK']} routing_miss={counts['ROUTING_MISS']} synthesis_fail={counts['SYNTHESIS_FAIL']}")
    except KeyboardInterrupt:
        print("Interrupted by user; saving results...")

    frame = pd.DataFrame(rows)
    frame.to_csv(csv_path, index=False, encoding="utf-8-sig")
    by_category = {
        cat: {
            "cases": int(stats["cases"]),
            "passes": int(stats["passes"]),
            "pass_rate": (stats["passes"] / stats["cases"]) if stats["cases"] else None,
        }
        for cat, stats in category_stats.items()
    }
    summary = {
        "run_id": run_id,
        "team": team_name,
        "provider": "ollama_local_only",
        "model": args.model,
        "training_performed": False,
        "cases": len(rows),
        "passes": int(frame["pass"].astype(bool).sum()) if not frame.empty else 0,
        "pass_rate": float(frame["pass"].astype(bool).mean()) if not frame.empty else None,
        "spanish_ratio_target": args.spanish_ratio,
        "classifications": dict(counts),
        "by_category": by_category,
        "csv": str(csv_path),
        "jsonl": str(jsonl_path),
        "finished_at": now_iso(),
        "notes": [
            "Continuous QA uses varied Spanish/Catalan prompts and real local analytics context.",
            "No paid API is used and no model weights are modified.",
            "Periodic full synthesis probes are bounded so repeated local LLM timeouts cannot waste the whole unattended run.",
        ],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=" * 92)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
