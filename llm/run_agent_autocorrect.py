"""Continuous controlled auto-correction for the local Coach Copilot.

Scope:
- router rules in llm/coach_agent_router_v2.py
- match-query resolution and SYSTEM_PROMPT in llm/coach_agent_hybrid.py
- bounded runtime profile selection

Never edits football analytics, ratings, features, expert decisions, database content
or model weights.

Loop:
baseline -> diagnose -> candidate patch -> fresh-process Golden Set -> accept/rollback
-> repeat until no safe candidate remains or wall-clock budget expires.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "llm" / "coach_agent_router_v2.py"
HYBRID = ROOT / "llm" / "coach_agent_hybrid.py"
WHITELIST = (ROUTER, HYBRID)
PROFILES = ("tiny", "compact", "fast", "balanced")

ROUTER_REPAIRS = [
    {
        "name": "router_gps_exclusive_profile",
        "trigger": {"ROUTER_EXTRA_TOOL"},
        "file": ROUTER,
        "ops": [
            (
                'if players and not any(name == "compare_players" for name, _ in plan):',
                'if players and not any(name in {"compare_players", "get_player_gps"} for name, _ in plan):',
            )
        ],
        "reason": "A named-player GPS request should not add the generic player profile.",
    },
    {
        "name": "router_profile_scope_recent",
        "trigger": {"ROUTER_EXTRA_TOOL"},
        "file": ROUTER,
        "ops": [
            (
                '"accions", "acciones", "estad", "rendiment recent", "rendimiento reciente",',
                '"accions", "acciones", "estad",',
            ),
            (
                '"nota", "rating", "match rating", "performance index", "motor expert",\n'
                '    "motor experto",',
                '"nota", "rating", "match rating",',
            ),
        ],
        "reason": "A generic recent profile or component summary should not automatically add player-match stats.",
    },
    {
        "name": "router_team_form_precision",
        "trigger": {"ROUTER_EXTRA_TOOL"},
        "file": ROUTER,
        "ops": [
            (
                '"equip", "equipo", "forma", "millorant", "mejorando", "empitjorant", "empeorando",',
                '"equip", "equipo", "forma de l\'equip", "forma del equipo", "millorant", "mejorando", "empitjorant", "empeorando",',
            )
        ],
        "reason": 'The bare substring "forma" collides with neutral wording such as "de forma breve".',
    },
    {
        "name": "match_resolver_spanish_last_match",
        "trigger": {"ROUTER_MISSING_TOOL"},
        "file": HYBRID,
        "ops": [
            (
                '("ultim partit", "darrer partit", "last match")',
                '("ultim partit", "darrer partit", "ultimo partido", "ultimo encuentro", "last match")',
            )
        ],
        "reason": "Spanish last-match wording must resolve the latest match like Catalan and English.",
    },
]

BASE_PROMPT = """You are Coach Copilot for football staff.
Answer ONLY from the compact EVIDENCE supplied.
Never invent values, metrics, thresholds, causes or recommendations.
Do not recalculate Match Rating, Performance Index or expert-system outputs.
If evidence is insufficient, say what is missing.
Answer in the user's language in at most 6 short sentences.
"""

PROMPT_STRATEGIES = [
    {
        "name": "prompt_numeric_verbatim",
        "trigger": {"NUMERIC_UNGROUNDED"},
        "text": BASE_PROMPT.replace(
            "Never invent values, metrics, thresholds, causes or recommendations.\n",
            "Never invent values, metrics, thresholds, causes or recommendations.\n"
            "Use a numeric value only when that exact value is explicitly present in EVIDENCE; do not calculate, round, convert or infer numbers.\n",
        ),
    },
    {
        "name": "prompt_numeric_minimal",
        "trigger": {"NUMERIC_UNGROUNDED"},
        "text": BASE_PROMPT.replace(
            "If evidence is insufficient, say what is missing.\n",
            "If evidence is insufficient, say what is missing.\n"
            "Prefer qualitative wording over numbers; when a number is not essential, omit it.\n",
        ),
    },
    {
        "name": "prompt_subject_first",
        "trigger": {"SUBJECT_OMISSION"},
        "text": BASE_PROMPT.replace(
            "If evidence is insufficient, say what is missing.\n",
            "If evidence is insufficient, say what is missing.\n"
            "When QUESTION explicitly names a player, opponent or team, name that subject in the first sentence.\n",
        ),
    },
    {
        "name": "prompt_short_2_4",
        "trigger": {"SENTENCE_LIMIT"},
        "text": BASE_PROMPT.replace(
            "Answer in the user's language in at most 6 short sentences.\n",
            "Answer in exactly 2 to 4 short sentences in the user's language.\n",
        ),
    },
    {
        "name": "prompt_language_exact",
        "trigger": {"LANGUAGE"},
        "text": BASE_PROMPT.replace(
            "Answer in the user's language in at most 6 short sentences.\n",
            "Answer strictly in the language used in QUESTION, not the language of EVIDENCE, in at most 6 short sentences.\n",
        ),
    },
    {
        "name": "prompt_grounded_compact",
        "trigger": {"NUMERIC_UNGROUNDED", "SUBJECT_OMISSION", "SENTENCE_LIMIT", "LANGUAGE"},
        "text": """You are Coach Copilot for football staff.
Use only facts explicitly present in EVIDENCE.
Do not invent, infer or recalculate metrics, values, causes, thresholds or recommendations.
Copy numeric values only when necessary and exactly as supported by EVIDENCE.
If QUESTION names a player, opponent or team, mention that subject immediately.
If evidence is insufficient, state the missing information instead of guessing.
Reply strictly in the language of QUESTION using 2 to 4 short sentences.
""",
    },
    {
        "name": "prompt_grounded_conservative",
        "trigger": {"NUMERIC_UNGROUNDED", "SUBJECT_OMISSION", "SENTENCE_LIMIT", "LANGUAGE"},
        "text": """You are Coach Copilot.
Answer only what EVIDENCE directly supports.
Never compute, extrapolate, diagnose or recommend beyond validated outputs.
Avoid numbers unless they are essential and explicitly shown in EVIDENCE.
Keep the requested player, opponent or team explicit in the answer.
If evidence is incomplete, say so.
Use the same language as QUESTION and no more than 4 short sentences.
""",
    },
]

PROMPT_RE = re.compile(r'SYSTEM_PROMPT = """(.*?)"""', re.S)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def current_prompt() -> str:
    text = HYBRID.read_text(encoding="utf-8")
    match = PROMPT_RE.search(text)
    if not match:
        raise RuntimeError("SYSTEM_PROMPT block not found")
    return match.group(1)


def set_prompt(prompt: str) -> None:
    text = HYBRID.read_text(encoding="utf-8")
    if not PROMPT_RE.search(text):
        raise RuntimeError("SYSTEM_PROMPT block not found")
    replacement = 'SYSTEM_PROMPT = """' + prompt.rstrip() + '\n"""'
    HYBRID.write_text(PROMPT_RE.sub(lambda _: replacement, text, count=1), encoding="utf-8")


def apply_ops(path: Path, ops: list[tuple[str, str]]) -> tuple[bool, list[str]]:
    text = path.read_text(encoding="utf-8")
    changed = False
    notes: list[str] = []
    for old, new in ops:
        if new in text:
            notes.append("already_present")
            continue
        if old not in text:
            notes.append("anchor_missing")
            return False, notes
        text = text.replace(old, new, 1)
        changed = True
        notes.append("applied")
    if changed:
        path.write_text(text, encoding="utf-8")
    return changed, notes


def syntax_ok(path: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0, (result.stderr or result.stdout)[-1200:]


def rows_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(r["id"]): r for r in payload.get("rows", [])}


def compare_case_changes(before: dict[str, Any], after: dict[str, Any]) -> tuple[list[str], list[str]]:
    b = rows_by_id(before)
    a = rows_by_id(after)
    improved: list[str] = []
    regressed: list[str] = []
    for case_id in sorted(set(b) & set(a)):
        bp = bool(b[case_id].get("pass"))
        ap = bool(a[case_id].get("pass"))
        if not bp and ap:
            improved.append(case_id)
        elif bp and not ap:
            regressed.append(case_id)
    return improved, regressed


def run_eval(
    *,
    db: Path,
    model: str,
    mode: str,
    profile: str,
    out: Path,
    team_id: str | None,
    seed: int = 20260930,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "llm.eval_agent_autocorrect_candidate",
        "--db", str(db),
        "--model", model,
        "--mode", mode,
        "--profile", profile,
        "--seed", str(seed),
        "--output", str(out),
    ]
    if team_id:
        cmd.extend(["--team-id", team_id])
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
    with (out.parent / "subprocess.log").open("a", encoding="utf-8") as fh:
        fh.write(f"\n[{now_iso()}] {' '.join(cmd)}\n")
        fh.write(result.stdout)
        fh.write(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Evaluator failed ({result.returncode}): {result.stderr[-1200:]}")
    return load_json(out)


def router_accept(before: dict[str, Any], after: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    improved, regressed = compare_case_changes(before, after)
    ok = (
        int(after.get("safety_failures", 0)) == 0
        and int(after.get("passes", 0)) > int(before.get("passes", 0))
        and not regressed
    )
    return ok, {"improved": improved, "regressed": regressed}


def full_accept(before: dict[str, Any], after: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    improved, regressed = compare_case_changes(before, after)
    net = len(improved) - len(regressed)
    ok = (
        int(after.get("safety_failures", 0)) == 0
        and int(after.get("passes", 0)) > int(before.get("passes", 0))
        and int(after.get("runtime_failures", 0)) <= int(before.get("runtime_failures", 0))
        and net > 0
    )
    return ok, {"improved": improved, "regressed": regressed, "net": net}


def profile_rank(payload: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        -float(payload.get("safety_failures", 0)),
        float(payload.get("passes", 0)),
        -float(payload.get("runtime_failures", 0)),
        -float(payload.get("avg_case_s", 9999.0)),
    )


def classification_set(payload: dict[str, Any]) -> set[str]:
    return {str(k) for k, v in (payload.get("classifications") or {}).items() if int(v or 0) > 0}


def snapshot_sources() -> dict[Path, str]:
    return {p: p.read_text(encoding="utf-8") for p in WHITELIST}


def restore_sources(snapshot: dict[Path, str]) -> None:
    for path, text in snapshot.items():
        path.write_text(text, encoding="utf-8")


def diff_text() -> str:
    return subprocess.run(
        ["git", "diff", "--", "llm/coach_agent_router_v2.py", "llm/coach_agent_hybrid.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    ).stdout


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("FPS_DB_PATH"))
    ap.add_argument("--model", default=os.environ.get("FPS_LOCAL_LLM_MODEL", "qwen3:1.7b"))
    ap.add_argument("--team-id", default=None)
    ap.add_argument("--hours", type=float, default=10.0)
    ap.add_argument("--output", default="outputs/agent_eval/autocorrect_continuous")
    args = ap.parse_args()

    if not args.db:
        raise SystemExit("Set FPS_DB_PATH or pass --db")
    db = Path(args.db).expanduser().resolve()
    if not db.exists():
        raise SystemExit(f"Database not found: {db}")

    deadline = time.monotonic() + max(0.1, args.hours) * 3600.0
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = (ROOT / args.output / run_id).resolve()
    out.mkdir(parents=True, exist_ok=True)
    backup_dir = out / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    original = snapshot_sources()
    for path in WHITELIST:
        shutil.copy2(path, backup_dir / path.name)

    events: list[dict[str, Any]] = []
    accepted: list[str] = []
    rejected: list[str] = []
    tested: set[str] = set()
    cycle = 0
    hard_rollback = False

    print("=" * 108)
    print("COACH COPILOT CONTINUOUS AUTO-CORRECT")
    print("detect -> patch -> fresh Golden Set -> accept/rollback -> repeat")
    print(f"model={args.model} hours={args.hours} db={db}")
    print("Editable whitelist: router rules + match resolver + synthesis prompt")
    print("Protected: data, analytics, ratings, features, expert engine, model weights")
    print("=" * 108)

    try:
        router_baseline = run_eval(
            db=db, model=args.model, mode="router", profile="balanced",
            out=out / "router_baseline.json", team_id=args.team_id,
        )
        print(f"ROUTER BASELINE {router_baseline['passes']}/{router_baseline['cases']}")

        while time.monotonic() < deadline:
            cycle += 1
            failures = classification_set(router_baseline)
            candidate = next(
                (
                    c for c in ROUTER_REPAIRS
                    if c["name"] not in tested and (not c["trigger"] or c["trigger"] & failures)
                ),
                None,
            )
            if candidate is None:
                break
            tested.add(candidate["name"])
            before = snapshot_sources()
            changed, notes = apply_ops(candidate["file"], candidate["ops"])
            if not changed:
                events.append({
                    "cycle": cycle, "candidate": candidate["name"], "kind": "router",
                    "accepted": False, "status": "not_applicable", "notes": notes,
                    "timestamp": now_iso(),
                })
                print(f"SKIP {candidate['name']}: {','.join(notes)}")
                continue

            ok_syntax, syntax_msg = syntax_ok(candidate["file"])
            if not ok_syntax:
                restore_sources(before)
                rejected.append(candidate["name"])
                print(f"ROLLBACK {candidate['name']}: syntax error")
                events.append({
                    "cycle": cycle, "candidate": candidate["name"], "accepted": False,
                    "status": "syntax_error", "error": syntax_msg, "timestamp": now_iso(),
                })
                continue

            result = run_eval(
                db=db, model=args.model, mode="router", profile="balanced",
                out=out / f"cycle_{cycle:03d}_{candidate['name']}.json", team_id=args.team_id,
            )
            ok, detail = router_accept(router_baseline, result)
            event = {
                "cycle": cycle, "candidate": candidate["name"], "kind": "router",
                "reason": candidate["reason"], "accepted": ok,
                "before_passes": router_baseline["passes"], "after_passes": result["passes"],
                **detail, "timestamp": now_iso(),
            }
            events.append(event)
            if ok:
                accepted.append(candidate["name"])
                print(f"ACCEPT {candidate['name']}: {router_baseline['passes']} -> {result['passes']}")
                router_baseline = result
            else:
                restore_sources(before)
                rejected.append(candidate["name"])
                print(f"ROLLBACK {candidate['name']}: no safe router improvement")

            write_json(out / "progress.json", {
                "cycle": cycle,
                "router_passes": router_baseline["passes"],
                "accepted": accepted,
                "rejected": rejected,
                "events": events,
                "updated_at": now_iso(),
            })

        profile_results: dict[str, dict[str, Any]] = {}
        for profile in PROFILES:
            if time.monotonic() >= deadline:
                break
            print(f"PROFILE TEST {profile} ...")
            payload = run_eval(
                db=db, model=args.model, mode="full", profile=profile,
                out=out / f"profile_{profile}.json", team_id=args.team_id,
            )
            profile_results[profile] = payload
            print(
                f"PROFILE {profile}: {payload['passes']}/{payload['cases']} "
                f"runtime={payload['runtime_failures']} safety={payload['safety_failures']} "
                f"avg={payload['avg_case_s']}s"
            )

        if not profile_results:
            raise RuntimeError("No runtime profile could be evaluated")
        best_profile = max(profile_results, key=lambda p: profile_rank(profile_results[p]))
        full_baseline = profile_results[best_profile]
        print(f"BEST PROFILE = {best_profile} ({full_baseline['passes']}/{full_baseline['cases']})")

        while time.monotonic() < deadline:
            failures = classification_set(full_baseline)
            relevant = [
                p for p in PROMPT_STRATEGIES
                if p["name"] not in tested and p["trigger"] & failures
            ]
            if not relevant:
                break

            strategy = relevant[0]
            tested.add(strategy["name"])
            cycle += 1
            before = snapshot_sources()
            previous_prompt = current_prompt()
            set_prompt(strategy["text"])

            ok_syntax, syntax_msg = syntax_ok(HYBRID)
            if not ok_syntax:
                restore_sources(before)
                rejected.append(strategy["name"])
                events.append({
                    "cycle": cycle, "candidate": strategy["name"], "kind": "synthesis",
                    "accepted": False, "status": "syntax_error", "error": syntax_msg,
                    "timestamp": now_iso(),
                })
                print(f"ROLLBACK {strategy['name']}: syntax error")
                continue

            result = run_eval(
                db=db, model=args.model, mode="full", profile=best_profile,
                out=out / f"cycle_{cycle:03d}_{strategy['name']}.json", team_id=args.team_id,
            )
            ok, detail = full_accept(full_baseline, result)
            event = {
                "cycle": cycle, "candidate": strategy["name"], "kind": "synthesis",
                "accepted": ok,
                "before_passes": full_baseline["passes"], "after_passes": result["passes"],
                "before_runtime_failures": full_baseline["runtime_failures"],
                "after_runtime_failures": result["runtime_failures"],
                **detail, "timestamp": now_iso(),
            }
            events.append(event)
            if ok:
                accepted.append(strategy["name"])
                full_baseline = result
                print(f"ACCEPT {strategy['name']}: {event['before_passes']} -> {event['after_passes']}")
            else:
                set_prompt(previous_prompt)
                rejected.append(strategy["name"])
                print(f"ROLLBACK {strategy['name']}: no safe net improvement")

            write_json(out / "progress.json", {
                "cycle": cycle,
                "router_passes": router_baseline["passes"],
                "full_passes": full_baseline["passes"],
                "best_profile": best_profile,
                "accepted": accepted,
                "rejected": rejected,
                "remaining_failures": full_baseline.get("classifications", {}),
                "events": events,
                "updated_at": now_iso(),
            })

        challenge_results: list[dict[str, Any]] = []
        for seed in (20261001, 20261002, 20261003):
            if time.monotonic() >= deadline:
                break
            challenge = run_eval(
                db=db, model=args.model, mode="full", profile=best_profile,
                out=out / f"challenge_{seed}.json", team_id=args.team_id, seed=seed,
            )
            challenge_results.append({
                "seed": seed,
                "passes": challenge["passes"],
                "cases": challenge["cases"],
                "safety_failures": challenge["safety_failures"],
                "runtime_failures": challenge["runtime_failures"],
                "classifications": challenge["classifications"],
            })
            print(
                f"CHALLENGE {seed}: {challenge['passes']}/{challenge['cases']} "
                f"safety={challenge['safety_failures']} runtime={challenge['runtime_failures']}"
            )
            if int(challenge.get("safety_failures", 0)) > 0:
                hard_rollback = True
                break

        if hard_rollback:
            restore_sources(original)
            accepted = []
            print("HARD ROLLBACK: unseen-seed safety/language regression detected.")

        diff_path = out / "accepted_source.diff"
        diff_path.write_text(diff_text(), encoding="utf-8")

        summary = {
            "run_id": run_id,
            "model": args.model,
            "duration_target_hours": args.hours,
            "cycles": cycle,
            "best_profile": best_profile,
            "accepted_candidates": accepted,
            "rejected_candidates": rejected,
            "hard_rollback": hard_rollback,
            "router_final": {k: v for k, v in router_baseline.items() if k != "rows"},
            "full_final": {k: v for k, v in full_baseline.items() if k != "rows"},
            "challenge_results": challenge_results,
            "events": events,
            "whitelist": [str(p.relative_to(ROOT)) for p in WHITELIST],
            "auto_push": False,
            "analytics_mutation": False,
            "decision_engine_mutation": False,
            "model_weight_training": False,
            "backup_dir": str(backup_dir),
            "diff_file": str(diff_path),
            "converged": time.monotonic() < deadline,
            "finished_at": now_iso(),
        }
        write_json(out / "autocorrect_summary.json", summary)
        write_json((ROOT / args.output / "autocorrect_summary_latest.json").resolve(), summary)
        write_json(out / "recommended_profile.json", {
            "profile": best_profile,
            "metrics": {k: v for k, v in full_baseline.items() if k != "rows"},
            "selected_at": now_iso(),
        })

        print("=" * 108)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"summary={out / 'autocorrect_summary.json'}")
        print(f"diff={diff_path}")
        print("=" * 108)

    except KeyboardInterrupt:
        print("Interrupted by user; accepted patches remain auditable and already regression-tested.")
        raise
    except Exception:
        restore_sources(original)
        raise


if __name__ == "__main__":
    main()
