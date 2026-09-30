"""Controlled source-code auto-correction for the local Coach Copilot.

This is intentionally narrower than a generic coding agent. It may edit only:
- llm/coach_agent_router_v2.py
- the synthesis SYSTEM_PROMPT in llm/coach_agent_hybrid.py

It never edits football analytics, ratings, features, expert decisions, database
content or model weights. Every candidate follows:

    backup -> patch -> fresh-process Golden Set -> accept OR rollback

Accepted source changes remain in the local working tree for review. They are never
pushed to GitHub automatically. A final safety regression gate restores the original
sources if policy/language/guardrail contracts regress.
"""
from __future__ import annotations

import argparse
import json
import os
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

CANDIDATES = [
    {
        "name": "router_gps_exclusive_profile",
        "kind": "router",
        "file": ROUTER,
        "old": 'if players and not any(name == "compare_players" for name, _ in plan):',
        "new": 'if players and not any(name in {"compare_players", "get_player_gps"} for name, _ in plan):',
        "reason": "A named-player GPS request should not automatically add the generic player profile unless the question separately asks for player-detail analysis.",
    },
    {
        "name": "prompt_numeric_grounding",
        "kind": "synthesis",
        "file": HYBRID,
        "old": "Never invent values, metrics, thresholds, causes or recommendations.\n",
        "new": "Never invent values, metrics, thresholds, causes or recommendations.\nAny numeric value in the answer must be directly supported by EVIDENCE; otherwise omit it.\n",
        "reason": "Reduce numeric hallucination/unsupported-number failures.",
    },
    {
        "name": "prompt_subject_explicit",
        "kind": "synthesis",
        "file": HYBRID,
        "old": "If evidence is insufficient, say what is missing.\n",
        "new": "If evidence is insufficient, say what is missing.\nExplicitly name the player, opponent or team asked about when it is identifiable from QUESTION or EVIDENCE.\n",
        "reason": "Reduce subject-omission failures in match/player answers.",
    },
    {
        "name": "prompt_sentence_hard_cap",
        "kind": "synthesis",
        "file": HYBRID,
        "old": "Answer in the user's language in at most 6 short sentences.\n",
        "new": "Answer in the user's language in at most 6 short sentences. Never exceed 6 sentences; prefer 3 to 5.\n",
        "reason": "Reduce sentence-limit failures without changing football content.",
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_exact(path: Path, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    if old not in text:
        raise RuntimeError(f"Candidate anchor not found in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


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
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "llm.eval_agent_autocorrect_candidate",
        "--db",
        str(db),
        "--model",
        model,
        "--mode",
        mode,
        "--profile",
        profile,
        "--output",
        str(out),
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
        raise RuntimeError(f"Candidate evaluator failed ({result.returncode}): {result.stderr[-1200:]}")
    return load_json(out)


def candidate_accept_router(before: dict[str, Any], after: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    improved, regressed = compare_case_changes(before, after)
    accepted = (
        after.get("safety_failures", 0) == 0
        and int(after.get("passes", 0)) > int(before.get("passes", 0))
        and not regressed
    )
    return accepted, {"improved": improved, "regressed": regressed}


def candidate_accept_synthesis(before: dict[str, Any], after: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    improved, regressed = compare_case_changes(before, after)
    net = len(improved) - len(regressed)
    accepted = (
        int(after.get("safety_failures", 0)) == 0
        and int(after.get("passes", 0)) > int(before.get("passes", 0))
        and int(after.get("runtime_failures", 0)) <= int(before.get("runtime_failures", 0))
        and net > 0
    )
    return accepted, {"improved": improved, "regressed": regressed, "net": net}


def profile_rank(payload: dict[str, Any]) -> tuple[float, float, float, float]:
    # Safety dominates. Then correctness, runtime reliability and latency.
    return (
        -float(payload.get("safety_failures", 0)),
        float(payload.get("passes", 0)),
        -float(payload.get("runtime_failures", 0)),
        -float(payload.get("avg_case_s", 9999.0)),
    )


def run_stress_chunk(*, db: Path, model: str, hours: float, output_root: Path, team_id: str | None) -> None:
    if hours <= 0.01:
        return
    cmd = [
        sys.executable,
        "-m",
        "llm.run_agent_self_improve_entry",
        "--db",
        str(db),
        "--model",
        model,
        "--hours",
        str(hours),
        "--synthesis-rate",
        "0.35",
        "--output",
        str(output_root / "stress"),
    ]
    if team_id:
        cmd.extend(["--team-id", team_id])
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    subprocess.run(cmd, cwd=ROOT, env=env, check=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("FPS_DB_PATH"))
    ap.add_argument("--model", default=os.environ.get("FPS_LOCAL_LLM_MODEL", "qwen3:1.7b"))
    ap.add_argument("--team-id", default=None)
    ap.add_argument("--hours", type=float, default=10.0)
    ap.add_argument("--output", default="outputs/agent_eval/autocorrect")
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

    originals: dict[Path, str] = {}
    for path in WHITELIST:
        originals[path] = path.read_text(encoding="utf-8")
        shutil.copy2(path, backup_dir / path.name)

    events: list[dict[str, Any]] = []
    accepted: list[str] = []
    rejected: list[str] = []

    print("=" * 104)
    print("COACH COPILOT AUTO-CORRECT · SOURCE PATCH + GOLDEN REGRESSION + ROLLBACK")
    print(f"model={args.model} hours={args.hours} db={db}")
    print("Editable whitelist: router_v2 + synthesis SYSTEM_PROMPT only")
    print("Never edited: data, analytics, ratings, features, expert engine, model weights")
    print("=" * 104)

    try:
        # 1) Deterministic router baseline and structural router correction.
        router_baseline_path = out / "router_baseline.json"
        router_baseline = run_eval(db=db, model=args.model, mode="router", profile="balanced", out=router_baseline_path, team_id=args.team_id)
        print(f"ROUTER BASELINE {router_baseline['passes']}/{router_baseline['cases']}")

        for cand in [c for c in CANDIDATES if c["kind"] == "router"]:
            before_text = cand["file"].read_text(encoding="utf-8")
            try:
                changed = apply_exact(cand["file"], cand["old"], cand["new"])
                if not changed:
                    events.append({"candidate": cand["name"], "status": "already_present", "timestamp": now_iso()})
                    continue
                candidate_result = run_eval(
                    db=db, model=args.model, mode="router", profile="balanced",
                    out=out / f"candidate_{cand['name']}.json", team_id=args.team_id,
                )
                ok, detail = candidate_accept_router(router_baseline, candidate_result)
                event = {"candidate": cand["name"], "kind": cand["kind"], "reason": cand["reason"], "accepted": ok, "before_passes": router_baseline["passes"], "after_passes": candidate_result["passes"], **detail, "timestamp": now_iso()}
                events.append(event)
                if ok:
                    accepted.append(cand["name"])
                    router_baseline = candidate_result
                    print(f"ACCEPT {cand['name']}: {event['before_passes']} -> {event['after_passes']} router passes")
                else:
                    cand["file"].write_text(before_text, encoding="utf-8")
                    rejected.append(cand["name"])
                    print(f"ROLLBACK {cand['name']}: no safe router improvement")
            except Exception as exc:
                cand["file"].write_text(before_text, encoding="utf-8")
                rejected.append(cand["name"])
                events.append({"candidate": cand["name"], "accepted": False, "error": str(exc), "timestamp": now_iso()})
                print(f"ROLLBACK {cand['name']}: {exc}")

        # 2) Search the best bounded Ollama runtime profile on the corrected router.
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
            print(f"PROFILE {profile}: {payload['passes']}/{payload['cases']} runtime={payload['runtime_failures']} safety={payload['safety_failures']} avg={payload['avg_case_s']}s")

        if not profile_results:
            raise RuntimeError("No runtime profile could be evaluated")
        best_profile = max(profile_results, key=lambda name: profile_rank(profile_results[name]))
        full_baseline = profile_results[best_profile]
        write_json(out / "recommended_profile.json", {
            "profile": best_profile,
            "metrics": {k: v for k, v in full_baseline.items() if k != "rows"},
            "selected_at": now_iso(),
        })
        print(f"BEST PROFILE = {best_profile} ({full_baseline['passes']}/{full_baseline['cases']})")

        # 3) Prompt auto-correction. Every candidate is accepted or rolled back by
        # fresh-process full Golden Set regression.
        for cand in [c for c in CANDIDATES if c["kind"] == "synthesis"]:
            if time.monotonic() >= deadline:
                break
            before_text = cand["file"].read_text(encoding="utf-8")
            try:
                changed = apply_exact(cand["file"], cand["old"], cand["new"])
                if not changed:
                    events.append({"candidate": cand["name"], "status": "already_present", "timestamp": now_iso()})
                    continue
                candidate_result = run_eval(
                    db=db, model=args.model, mode="full", profile=best_profile,
                    out=out / f"candidate_{cand['name']}.json", team_id=args.team_id,
                )
                ok, detail = candidate_accept_synthesis(full_baseline, candidate_result)
                event = {"candidate": cand["name"], "kind": cand["kind"], "reason": cand["reason"], "accepted": ok, "before_passes": full_baseline["passes"], "after_passes": candidate_result["passes"], "before_runtime_failures": full_baseline["runtime_failures"], "after_runtime_failures": candidate_result["runtime_failures"], **detail, "timestamp": now_iso()}
                events.append(event)
                if ok:
                    accepted.append(cand["name"])
                    full_baseline = candidate_result
                    print(f"ACCEPT {cand['name']}: {event['before_passes']} -> {event['after_passes']} full passes")
                else:
                    cand["file"].write_text(before_text, encoding="utf-8")
                    rejected.append(cand["name"])
                    print(f"ROLLBACK {cand['name']}: no safe net improvement")
            except Exception as exc:
                cand["file"].write_text(before_text, encoding="utf-8")
                rejected.append(cand["name"])
                events.append({"candidate": cand["name"], "accepted": False, "error": str(exc), "timestamp": now_iso()})
                print(f"ROLLBACK {cand['name']}: {exc}")

        # 4) Final full regression gate. If a hard safety contract regresses, restore
        # all original whitelisted sources automatically.
        final_result = run_eval(
            db=db, model=args.model, mode="full", profile=best_profile,
            out=out / "final_verification.json", team_id=args.team_id,
        )
        hard_rollback = int(final_result.get("safety_failures", 0)) > 0
        if hard_rollback:
            for path, text in originals.items():
                path.write_text(text, encoding="utf-8")
            print("HARD ROLLBACK: final safety/language/guardrail regression detected; original sources restored.")
            accepted = []

        # Save the actual local source diff for review/audit.
        diff = subprocess.run(
            ["git", "diff", "--", "llm/coach_agent_router_v2.py", "llm/coach_agent_hybrid.py"],
            cwd=ROOT, text=True, capture_output=True,
        ).stdout
        (out / "accepted_source.diff").write_text(diff, encoding="utf-8")

        summary = {
            "run_id": run_id,
            "model": args.model,
            "duration_target_hours": args.hours,
            "best_profile": best_profile,
            "accepted_candidates": accepted,
            "rejected_candidates": rejected,
            "hard_rollback": hard_rollback,
            "router_final": {k: v for k, v in router_baseline.items() if k != "rows"},
            "full_final": {k: v for k, v in final_result.items() if k != "rows"},
            "events": events,
            "whitelist": [str(p.relative_to(ROOT)) for p in WHITELIST],
            "auto_push": False,
            "analytics_mutation": False,
            "decision_engine_mutation": False,
            "model_weight_training": False,
            "backup_dir": str(backup_dir),
            "diff_file": str(out / "accepted_source.diff"),
            "finished_correction_phase_at": now_iso(),
        }
        write_json(out / "autocorrect_summary.json", summary)
        write_json((ROOT / args.output / "autocorrect_summary_latest.json").resolve(), summary)

        # 5) Use any remaining wall-clock budget as adversarial stress/replay against
        # the corrected sources. This does not overwrite an accepted patch; it creates
        # evidence for the next correction cycle while keeping the run useful unattended.
        remaining_h = max(0.0, (deadline - time.monotonic()) / 3600.0)
        if remaining_h > 0.03:
            print(f"STRESS/REPLAY PHASE for remaining ~{remaining_h:.2f}h")
            run_stress_chunk(
                db=db,
                model=args.model,
                hours=remaining_h,
                output_root=out,
                team_id=args.team_id,
            )

        print("=" * 104)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"summary={out / 'autocorrect_summary.json'}")
        print(f"diff={out / 'accepted_source.diff'}")
        print("=" * 104)

    except KeyboardInterrupt:
        print("Interrupted by user. Existing accepted patches/backups remain auditable in the run folder.")
        raise
    except Exception:
        # Unexpected orchestration failure: restore originals rather than leave a
        # half-tested source candidate in place.
        for path, text in originals.items():
            path.write_text(text, encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
