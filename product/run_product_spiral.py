"""Autonomous, bounded product-quality spiral for the Streamlit UI and PDF exports.

The loop is deliberately downstream of analytics. It may only mutate a tiny allowlist
of presentation files, validates every accepted change, and never pushes by itself.

Typical use:
    python product/run_product_spiral.py --hours 10

Safety model:
- analytics, ratings, expert thresholds, DB contents and LLM logic are protected;
- each recipe is deterministic, idempotent and presentation-only;
- a recipe is accepted only when contracts pass and product-quality score does not fall;
- failures are rolled back immediately;
- long-run time is used for real-data PDF/report scenario probing and failure replay.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUTPUT_ROOT = ROOT / "outputs" / "product_spiral"

ALLOWED_MUTATION_PATHS = {
    Path("app/ui_theme.py"),
    Path("app/coach_ui.py"),
    Path("reports/pdf_engine.py"),
}

PROTECTED_PREFIXES = (
    "analytics/",
    "data/",
    "features/",
    "decision_tree/",
    "models/",
    "llm/",
    "gps/",
)


@dataclass(frozen=True)
class Recipe:
    name: str
    path: Path
    marker: str
    apply: Callable[[str], str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str], timeout: int = 180) -> tuple[bool, float, str]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        elapsed = time.perf_counter() - started
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, elapsed, output[-12000:]
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - started
        return False, elapsed, f"TIMEOUT after {timeout}s: {exc}"


def _git_status_paths() -> list[str]:
    ok, _, out = _run(["git", "status", "--porcelain"], timeout=30)
    if not ok:
        return []
    paths: list[str] = []
    for line in out.splitlines():
        if len(line) >= 4:
            paths.append(line[3:].strip().replace("\\", "/"))
    return paths


def _protected_dirty_paths() -> list[str]:
    return [p for p in _git_status_paths() if p.startswith(PROTECTED_PREFIXES)]


def _ensure_local_branch(run_id: str) -> str:
    ok, _, current = _run(["git", "branch", "--show-current"], timeout=30)
    current = current.strip() if ok else ""
    branch = f"product-spiral-{run_id.lower()}"
    if current.startswith("product-spiral-"):
        return current
    ok, _, out = _run(["git", "switch", "-c", branch], timeout=30)
    if not ok:
        raise RuntimeError(f"Could not create local product branch: {out}")
    return branch


def _read(rel: Path) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _write(rel: Path, text: str) -> None:
    if rel not in ALLOWED_MUTATION_PATHS:
        raise RuntimeError(f"Mutation blocked outside allowlist: {rel}")
    (ROOT / rel).write_text(text, encoding="utf-8")


def _insert_before(text: str, needle: str, block: str) -> str:
    if needle not in text:
        raise ValueError(f"Insertion anchor not found: {needle}")
    return text.replace(needle, block + "\n" + needle, 1)


def _recipe_interaction_pack(text: str) -> str:
    block = r'''
        /* PRODUCT-SPIRAL:INTERACTION-PACK */
        [data-testid="stSidebar"] a[aria-current="page"] {
            background: rgba(19,163,127,.16);
            box-shadow: inset 3px 0 0 var(--fps-accent);
        }
        .stButton > button, [data-testid="stDownloadButton"] button {
            min-height: 2.5rem;
            border: 1px solid #D6E0E7;
            font-weight: 750;
            transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease;
        }
        .stButton > button:hover, [data-testid="stDownloadButton"] button:hover {
            border-color: #AFC5D2;
            box-shadow: 0 4px 12px rgba(11,31,51,.08);
            transform: translateY(-1px);
        }
        .stButton > button:focus-visible, [data-testid="stDownloadButton"] button:focus-visible,
        a:focus-visible, input:focus-visible, textarea:focus-visible {
            outline: 3px solid rgba(19,163,127,.22) !important;
            outline-offset: 2px;
        }
        [data-testid="stDownloadButton"] button {
            background: #0B1F33;
            color: #FFFFFF;
            border-color: #0B1F33;
        }
'''
    return _insert_before(text, "        @media (max-width: 900px) {", block)


def _recipe_surface_pack(text: str) -> str:
    block = r'''
        /* PRODUCT-SPIRAL:SURFACE-PACK */
        [data-testid="stPlotlyChart"] {
            background: #FFFFFF;
            border: 1px solid var(--fps-border);
            border-radius: 13px;
            padding: .35rem .45rem .2rem .45rem;
            box-shadow: 0 2px 8px rgba(11,31,51,.03);
        }
        [data-testid="stExpander"] {
            background: #FFFFFF;
            border: 1px solid var(--fps-border);
            border-radius: 11px;
            overflow: hidden;
        }
        [data-testid="stAlert"] {
            border-radius: 11px;
            border-width: 1px;
        }
        [data-testid="stDataFrame"] {
            box-shadow: 0 2px 8px rgba(11,31,51,.025);
        }
        [data-testid="stCaptionContainer"] { color: var(--fps-muted); }
'''
    return _insert_before(text, "        @media (max-width: 900px) {", block)


def _recipe_mobile_pack(text: str) -> str:
    block = r'''
        /* PRODUCT-SPIRAL:MOBILE-PACK */
        @media (max-width: 700px) {
            .block-container { padding-top:.75rem; padding-left:.72rem; padding-right:.72rem; }
            .coach-page-header { margin-bottom:.8rem; padding-bottom:.75rem; }
            .coach-title { font-size:1.48rem; }
            .coach-subtitle { font-size:.86rem; }
            .coach-metric-card, .fps-score-card { min-height:0; padding:.78rem .82rem; }
            .coach-metric-value, .fps-score-value { font-size:1.48rem; }
            .coach-scoreboard { padding:1rem; min-height:0; }
            .coach-score { width:max-content; }
            [data-testid="stPlotlyChart"] { padding:.15rem; border-radius:10px; }
            [data-testid="stDataFrame"] { font-size:.82rem; }
        }
'''
    return _insert_before(text, "        </style>", block)


def _recipe_empty_state_helper(text: str) -> str:
    block = r'''

# PRODUCT-SPIRAL:EMPTY-STATE-HELPER
def empty_state(title: str, body: str, hint: str = "") -> None:
    """Render a calm, explicit empty state without implying missing analytics are zero."""
    hint_html = "" if not hint else f"<div class='coach-empty-hint'>{html.escape(hint)}</div>"
    st.markdown(
        f"""
        <div class="coach-empty-state">
          <div class="coach-empty-title">{html.escape(title)}</div>
          <div class="coach-empty-body">{html.escape(body)}</div>
          {hint_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# PRODUCT-SPIRAL:CONTEXT-BANNER-HELPER
def context_banner(title: str, body: str, tone: str = "neutral") -> None:
    """Render context/evidence notes consistently; no analytical interpretation is added."""
    safe_tone = tone if tone in {"neutral", "warning", "positive", "negative"} else "neutral"
    st.markdown(
        f"""
        <div class="coach-context coach-context-{safe_tone}">
          <div class="coach-context-title">{html.escape(title)}</div>
          <div class="coach-context-body">{html.escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
'''
    return text.rstrip() + block + "\n"


def _recipe_empty_state_css(text: str) -> str:
    block = r'''
        /* PRODUCT-SPIRAL:EMPTY-STATE-CSS */
        .coach-empty-state {
            background:#FFFFFF;
            border:1px dashed #CBD7DF;
            border-radius:12px;
            padding:1rem 1.05rem;
            color:var(--fps-text);
        }
        .coach-empty-title { font-size:.9rem; font-weight:850; }
        .coach-empty-body { margin-top:.2rem; color:var(--fps-muted); font-size:.84rem; line-height:1.4; }
        .coach-empty-hint { margin-top:.45rem; color:#486173; font-size:.77rem; font-weight:650; }
        .coach-context {
            background:#FFFFFF;
            border:1px solid var(--fps-border);
            border-left:4px solid #8A9AA8;
            border-radius:10px;
            padding:.72rem .85rem;
            margin:.45rem 0 .7rem 0;
        }
        .coach-context-warning { border-left-color:var(--fps-warn); }
        .coach-context-positive { border-left-color:var(--fps-good); }
        .coach-context-negative { border-left-color:var(--fps-bad); }
        .coach-context-title { font-size:.78rem; font-weight:850; color:var(--fps-text); }
        .coach-context-body { margin-top:.16rem; font-size:.8rem; line-height:1.38; color:var(--fps-muted); }
'''
    return _insert_before(text, "        @media (max-width: 900px) {", block)


def _recipe_pdf_heading_flow(text: str) -> str:
    if "# PRODUCT-SPIRAL:PDF-FLOW" in text:
        return text
    old_h2 = '            leading=15, textColor=NAVY, spaceBefore=10, spaceAfter=6,\n'
    new_h2 = '            leading=15, textColor=NAVY, spaceBefore=10, spaceAfter=6, keepWithNext=True,\n'
    old_h3 = '            leading=12, textColor=TEXT, spaceBefore=6, spaceAfter=4,\n'
    new_h3 = '            leading=12, textColor=TEXT, spaceBefore=6, spaceAfter=4, keepWithNext=True,\n'
    if old_h2 not in text or old_h3 not in text:
        raise ValueError("PDF heading style anchors not found")
    text = text.replace(old_h2, new_h2, 1).replace(old_h3, new_h3, 1)
    return text.replace('def _styles() -> dict[str, ParagraphStyle]:\n', 'def _styles() -> dict[str, ParagraphStyle]:\n    # PRODUCT-SPIRAL:PDF-FLOW\n', 1)


def _recipe_pdf_table_flow(text: str) -> str:
    if "# PRODUCT-SPIRAL:PDF-TABLE-FLOW" in text:
        return text
    old = '    table = Table(cooked, colWidths=widths, repeatRows=1, hAlign="LEFT")\n'
    new = '    # PRODUCT-SPIRAL:PDF-TABLE-FLOW\n    table = Table(cooked, colWidths=widths, repeatRows=1, hAlign="LEFT", splitByRow=1)\n'
    if old not in text:
        raise ValueError("PDF table constructor anchor not found")
    return text.replace(old, new, 1)


RECIPES = [
    Recipe("ui_interaction_pack", Path("app/ui_theme.py"), "PRODUCT-SPIRAL:INTERACTION-PACK", _recipe_interaction_pack),
    Recipe("ui_surface_pack", Path("app/ui_theme.py"), "PRODUCT-SPIRAL:SURFACE-PACK", _recipe_surface_pack),
    Recipe("ui_mobile_pack", Path("app/ui_theme.py"), "PRODUCT-SPIRAL:MOBILE-PACK", _recipe_mobile_pack),
    Recipe("coach_empty_context_helpers", Path("app/coach_ui.py"), "PRODUCT-SPIRAL:EMPTY-STATE-HELPER", _recipe_empty_state_helper),
    Recipe("ui_empty_context_styles", Path("app/ui_theme.py"), "PRODUCT-SPIRAL:EMPTY-STATE-CSS", _recipe_empty_state_css),
    Recipe("pdf_heading_flow", Path("reports/pdf_engine.py"), "PRODUCT-SPIRAL:PDF-FLOW", _recipe_pdf_heading_flow),
    Recipe("pdf_table_flow", Path("reports/pdf_engine.py"), "PRODUCT-SPIRAL:PDF-TABLE-FLOW", _recipe_pdf_table_flow),
]


def audit_repository() -> dict:
    ui = _read(Path("app/ui_theme.py"))
    coach = _read(Path("app/coach_ui.py"))
    pdf = _read(Path("reports/pdf_engine.py"))
    pages = list((ROOT / "app" / "pages").glob("*.py"))

    checks: list[tuple[str, bool, int]] = [
        ("shared_professional_theme", "def apply_professional_theme" in ui, 7),
        ("shared_sidebar_navigation", "def sidebar_navigation" in ui, 5),
        ("responsive_breakpoint", "@media (max-width: 900px)" in ui, 5),
        ("active_navigation_state", "PRODUCT-SPIRAL:INTERACTION-PACK" in ui, 5),
        ("keyboard_focus_state", ":focus-visible" in ui, 5),
        ("download_button_identity", "stDownloadButton" in ui, 4),
        ("chart_surface", "PRODUCT-SPIRAL:SURFACE-PACK" in ui, 4),
        ("mobile_density_pack", "PRODUCT-SPIRAL:MOBILE-PACK" in ui, 5),
        ("empty_state_component", "def empty_state" in coach, 4),
        ("context_banner_component", "def context_banner" in coach, 4),
        ("page_header_component", "def page_header" in coach, 4),
        ("metric_card_component", "def metric_card" in coach, 4),
        ("insight_component", "def insight_card" in coach, 4),
        ("shared_chart_language", "def _base_layout" in coach, 4),
        ("pdf_header", "def _header" in pdf, 4),
        ("pdf_footer_page_number", "Pàgina {doc.page}" in pdf, 4),
        ("pdf_repeat_table_header", "repeatRows=1" in pdf, 4),
        ("pdf_heading_orphan_control", "PRODUCT-SPIRAL:PDF-FLOW" in pdf, 4),
        ("pdf_table_split_control", "PRODUCT-SPIRAL:PDF-TABLE-FLOW" in pdf, 3),
        ("pdf_guardrail_note", "def _guardrail_note" in pdf, 4),
        ("pdf_kpi_strip", "def _kpi_strip" in pdf, 4),
        ("full_navigation_pages", len(pages) >= 7, 4),
        ("ui_compatibility_validator", (ROOT / "app" / "validate_ui_compatibility.py").exists(), 3),
        ("dashboard_validator", (ROOT / "app" / "validate_dashboard.py").exists(), 3),
        ("report_validator", (ROOT / "reports" / "validate_reports.py").exists(), 3),
    ]
    total = sum(weight for _, _, weight in checks)
    earned = sum(weight for _, passed, weight in checks if passed)
    score = round(100.0 * earned / total, 2) if total else 0.0
    return {
        "score": score,
        "earned": earned,
        "possible": total,
        "checks": [{"name": name, "pass": passed, "weight": weight} for name, passed, weight in checks],
    }


def run_contract_gates(db_available: bool) -> dict:
    commands: list[tuple[str, list[str], int]] = [
        ("compile", [sys.executable, "-m", "compileall", "-q", "app", "reports", "product"], 120),
        ("ui_compatibility", [sys.executable, "app/validate_ui_compatibility.py"], 120),
    ]
    if db_available:
        commands.extend([
            ("dashboard", [sys.executable, "app/validate_dashboard.py"], 180),
            ("match_mode", [sys.executable, "app/validate_match_mode.py"], 180),
            ("reports", [sys.executable, "reports/validate_reports.py"], 240),
        ])
    results = {}
    all_ok = True
    for name, cmd, timeout in commands:
        ok, elapsed, out = _run(cmd, timeout=timeout)
        results[name] = {"pass": ok, "elapsed_s": round(elapsed, 3), "tail": out[-3000:]}
        all_ok = all_ok and ok
    results["all_pass"] = all_ok
    results["db_dependent_gates_run"] = db_available
    return results


def _snapshot_allowed() -> dict[Path, str]:
    return {path: _read(path) for path in ALLOWED_MUTATION_PATHS}


def _restore(snapshot: dict[Path, str]) -> None:
    for path, text in snapshot.items():
        _write(path, text)


def _commit_recipe(recipe: Recipe, score: float) -> tuple[bool, str]:
    ok, _, out = _run(["git", "add", str(recipe.path)], timeout=30)
    if not ok:
        return False, out
    msg = f"Product spiral: {recipe.name} (quality {score:.2f})"
    ok, _, out = _run(["git", "commit", "-m", msg], timeout=60)
    return ok, out


def apply_recipe(recipe: Recipe, db_available: bool) -> dict:
    before_audit = audit_repository()
    current = _read(recipe.path)
    if recipe.marker in current:
        return {"recipe": recipe.name, "status": "ALREADY_APPLIED", "before_score": before_audit["score"]}

    snapshot = _snapshot_allowed()
    try:
        updated = recipe.apply(current)
        if updated == current:
            return {"recipe": recipe.name, "status": "NO_CHANGE", "before_score": before_audit["score"]}
        _write(recipe.path, updated)
        protected = _protected_dirty_paths()
        if protected:
            _restore(snapshot)
            return {"recipe": recipe.name, "status": "BLOCKED_PROTECTED_DIRTY", "paths": protected}
        gates = run_contract_gates(db_available)
        after_audit = audit_repository()
        accepted = bool(gates["all_pass"] and after_audit["score"] >= before_audit["score"])
        if not accepted:
            _restore(snapshot)
            return {
                "recipe": recipe.name,
                "status": "ROLLED_BACK",
                "before_score": before_audit["score"],
                "after_score": after_audit["score"],
                "gates": gates,
            }
        committed, commit_out = _commit_recipe(recipe, after_audit["score"])
        if not committed:
            _restore(snapshot)
            _run(["git", "reset"], timeout=30)
            return {
                "recipe": recipe.name,
                "status": "ROLLED_BACK_COMMIT_FAILURE",
                "before_score": before_audit["score"],
                "after_score": after_audit["score"],
                "commit_tail": commit_out[-2000:],
            }
        return {
            "recipe": recipe.name,
            "status": "ACCEPTED",
            "before_score": before_audit["score"],
            "after_score": after_audit["score"],
            "gates": gates,
        }
    except Exception as exc:
        _restore(snapshot)
        return {"recipe": recipe.name, "status": "EXCEPTION_ROLLBACK", "error": repr(exc)}


def _report_cases(db_path: Path) -> list[tuple[str, str, str, str]]:
    """Return (kind, team_id, entity_id, label) report scenarios."""
    from app.data_access import get_squad_summary, get_team_matches, list_teams

    cases: list[tuple[str, str, str, str]] = []
    teams = list_teams(db_path)
    for team in teams.itertuples(index=False):
        team_id = str(team.team_id)
        team_name = str(team.display_name)
        cases.append(("team", team_id, team_id, team_name))
        squad = get_squad_summary(db_path, team_id)
        if not squad.empty:
            for row in squad.loc[squad["appearances"] > 0].itertuples(index=False):
                cases.append(("player", team_id, str(row.player_id), str(row.player)))
        matches = get_team_matches(db_path, team_id)
        if not matches.empty:
            for row in matches.itertuples(index=False):
                cases.append(("match", team_id, str(row.match_id), str(row.opponent)))
    return cases


def probe_report_case(db_path: Path, case: tuple[str, str, str, str]) -> dict:
    from reports.data_builder import build_match_report_data, build_player_report_data, build_team_report_data
    from reports.pdf_engine import render_pdf_bytes

    kind, team_id, entity_id, label = case
    started = time.perf_counter()
    if kind == "team":
        payload = build_team_report_data(db_path, team_id)
    elif kind == "player":
        payload = build_player_report_data(db_path, team_id, entity_id)
    else:
        payload = build_match_report_data(db_path, team_id, entity_id)

    guardrails = payload.get("guardrails") or {}
    unsafe = any(
        guardrails.get(key) is not False
        for key in (
            "recommendation_policy_validated",
            "cross_player_ranking_allowed",
            "report_may_recalculate_critical_metrics",
            "report_may_issue_tactical_recommendation",
        )
    )
    pdf = render_pdf_bytes(payload)
    pdf_ok = pdf.startswith(b"%PDF-") and len(pdf) >= 1000
    approx_pages = max(1, len(re.findall(rb"/Type\s*/Page\b", pdf))) if pdf_ok else 0
    elapsed = time.perf_counter() - started
    return {
        "timestamp": _utc_now(),
        "kind": kind,
        "team_id": team_id,
        "entity_id": entity_id,
        "label": label,
        "pass": bool(pdf_ok and not unsafe),
        "classification": "OK" if pdf_ok and not unsafe else "PDF_OR_GUARDRAIL_FAIL",
        "pdf_bytes": len(pdf),
        "approx_pages": approx_pages,
        "elapsed_s": round(elapsed, 3),
        "unsafe_guardrail": unsafe,
        "match_rating_version": payload.get("match_rating_version"),
        "engine_version": payload.get("engine_version"),
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _append_csv(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=10.0)
    parser.add_argument("--max-cases", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=26092026)
    parser.add_argument("--no-branch", action="store_true", help="Do not create a dedicated local branch")
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUT_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    protected_dirty = _protected_dirty_paths()
    if protected_dirty:
        raise SystemExit(
            "Protected analytics/data/LLM files are already modified locally; refusing autonomous product run:\n- "
            + "\n- ".join(protected_dirty)
        )

    branch = "UNCHANGED"
    if not args.no_branch:
        branch = _ensure_local_branch(run_id)

    db_default = ROOT / "data" / "football_performance.duckdb"
    db_path = Path(os.environ.get("FPS_DB_PATH", db_default)).expanduser().resolve()
    db_available = db_path.exists()

    baseline = audit_repository()
    bootstrap_gates = run_contract_gates(db_available)
    if not bootstrap_gates["all_pass"]:
        _write_json(run_dir / "bootstrap_failure.json", bootstrap_gates)
        raise SystemExit(f"Bootstrap contracts failed. See {run_dir / 'bootstrap_failure.json'}")

    print("=" * 96)
    print("FOOTBALL PERFORMANCE SYSTEM · PRODUCT SPIRAL LAB")
    print(f"branch={branch}")
    print(f"hours={args.hours:g} db_available={db_available} db={db_path}")
    print(f"baseline_product_quality={baseline['score']:.2f}/100")
    print("Scope: UI/PDF presentation only. Analytics, ratings, expert thresholds and DB are protected.")
    print("Accepted changes are committed LOCALLY on the product-spiral branch; nothing is pushed automatically.")
    print("=" * 96)

    recipe_log: list[dict] = []
    for recipe in RECIPES:
        result = apply_recipe(recipe, db_available)
        recipe_log.append(result)
        print(f"RECIPE {recipe.name}: {result.get('status')} score={result.get('after_score', result.get('before_score', '—'))}")
        _write_json(run_dir / "recipes.json", recipe_log)

    post_recipes = audit_repository()
    print(f"PRODUCT QUALITY AFTER SAFE RECIPES: {post_recipes['score']:.2f}/100")

    deadline = time.monotonic() + max(0.0, args.hours) * 3600.0
    cases_done = 0
    passes = 0
    failures = Counter()
    replay: deque[tuple[str, str, str, str]] = deque(maxlen=1000)
    report_cases: list[tuple[str, str, str, str]] = []
    if db_available:
        try:
            report_cases = _report_cases(db_path)
            rng.shuffle(report_cases)
        except Exception as exc:
            _write_json(run_dir / "case_discovery_error.json", {"error": repr(exc)})

    if not report_cases:
        print("No DB-backed report scenarios available. Remaining run is audit/regression-only.")

    case_csv = run_dir / "cases.csv"
    next_full_gate = time.monotonic()
    next_checkpoint = time.monotonic()

    while cases_done < args.max_cases and time.monotonic() < deadline:
        if db_available and report_cases:
            case = replay.popleft() if replay and rng.random() < 0.60 else report_cases[cases_done % len(report_cases)]
            try:
                row = probe_report_case(db_path, case)
            except Exception as exc:
                kind, team_id, entity_id, label = case
                row = {
                    "timestamp": _utc_now(), "kind": kind, "team_id": team_id, "entity_id": entity_id,
                    "label": label, "pass": False, "classification": "EXCEPTION", "pdf_bytes": 0,
                    "approx_pages": 0, "elapsed_s": 0.0, "unsafe_guardrail": False,
                    "match_rating_version": "", "engine_version": "", "error": repr(exc),
                }
            cases_done += 1
            if row["pass"]:
                passes += 1
            else:
                failures[row["classification"]] += 1
                replay.extend([case, case, case])
            _append_csv(case_csv, row)
            if (not row["pass"]) or cases_done % 25 == 0:
                print(
                    f"[{cases_done:06d}] {'PASS' if row['pass'] else 'FAIL'} {row['kind']:<6} "
                    f"{row['classification']:<24} {row['elapsed_s']:.2f}s replay={len(replay)}"
                )
        else:
            cases_done += 1
            time.sleep(1.0)

        now = time.monotonic()
        if now >= next_full_gate:
            gates = run_contract_gates(db_available)
            _write_json(run_dir / "latest_gates.json", gates)
            if not gates["all_pass"]:
                failures["REGRESSION_GATE_FAIL"] += 1
                print("REGRESSION GATE FAIL — autonomous mutations stop; diagnostics saved.")
                break
            next_full_gate = now + 15 * 60

        if now >= next_checkpoint:
            summary = {
                "run_id": run_id,
                "updated_at": _utc_now(),
                "branch": branch,
                "db_available": db_available,
                "baseline_quality": baseline,
                "current_quality": audit_repository(),
                "recipes": recipe_log,
                "cases": cases_done,
                "passes": passes,
                "pass_rate": (passes / cases_done) if cases_done else None,
                "failures": dict(failures),
                "replay_queue": len(replay),
                "notes": [
                    "No analytics/rating/threshold/DB mutation is permitted by this runner.",
                    "Accepted recipe commits remain local; the runner never pushes.",
                    "DB-backed cases exercise real TEAM/PLAYER/MATCH PDF payloads and guardrails.",
                ],
            }
            _write_json(run_dir / "checkpoint.json", summary)
            next_checkpoint = now + 5 * 60

    final_gates = run_contract_gates(db_available)
    final = {
        "run_id": run_id,
        "finished_at": _utc_now(),
        "branch": branch,
        "db": str(db_path),
        "db_available": db_available,
        "baseline_quality": baseline,
        "final_quality": audit_repository(),
        "recipes": recipe_log,
        "cases": cases_done,
        "passes": passes,
        "pass_rate": (passes / cases_done) if cases_done else None,
        "failures": dict(failures),
        "final_gates": final_gates,
        "case_csv": str(case_csv),
        "product_changes_pushed": False,
    }
    _write_json(run_dir / "final_summary.json", final)

    print("=" * 96)
    print("PRODUCT SPIRAL COMPLETE")
    print(f"quality: {baseline['score']:.2f} -> {final['final_quality']['score']:.2f}")
    print(f"cases={cases_done} passes={passes} pass_rate={(passes / cases_done):.3f}" if cases_done else "cases=0")
    print(f"final_contracts={'PASS' if final_gates['all_pass'] else 'FAIL'}")
    print(f"summary={run_dir / 'final_summary.json'}")
    print("Nothing was pushed automatically. Review/merge the local product-spiral branch after the run.")


if __name__ == "__main__":
    main()
