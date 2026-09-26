"""Structural improvement spiral for the Coach Command Center.

Unlike the old CSS tuner, this optimizer changes real dashboard decisions:
- quick navigation on/off;
- operational strip on/off;
- match/summary proportions;
- Coach Brief 4-column vs 2x2 layout;
- trend/context proportions;
- squad tabs vs side-by-side;
- quality cards vs compact panel;
- order of the main analytical sections.

It mutates only app/dashboard_config.py. Analytics, Match Rating, expert rules, LLM,
GPS logic and database contents are never modified. Candidates must compile, pass the
UI compatibility validator and improve browser/layout + hierarchy/usability scoring.
Accepted candidates are committed locally on a product-spiral-* branch. Nothing is
pushed automatically and no browser/model/data download is performed.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import random
import re
import subprocess
import sys
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG_PATH = ROOT / "app" / "dashboard_config.py"
OUTPUT_ROOT = ROOT / "outputs" / "product_spiral"

BASE_CONFIG: dict[str, Any] = {
    "show_quick_nav": True,
    "show_command_strip": True,
    "hero_ratio": [1.45, 1.0],
    "brief_columns": 4,
    "trend_ratio": [1.65, 0.75],
    "squad_mode": "tabs",
    "quality_mode": "cards",
    "section_order": ["coach_brief", "trend", "squad", "quality"],
}

SPACES: dict[str, list[Any]] = {
    "show_quick_nav": [True, False],
    "show_command_strip": [True, False],
    "hero_ratio": [[1.60, 1.0], [1.45, 1.0], [1.30, 1.0]],
    "brief_columns": [4, 2],
    "trend_ratio": [[1.80, 0.75], [1.65, 0.75], [1.45, 0.90]],
    "squad_mode": ["tabs", "split"],
    "quality_mode": ["cards", "compact"],
    "section_order": [
        ["coach_brief", "trend", "squad", "quality"],
        ["trend", "coach_brief", "squad", "quality"],
        ["coach_brief", "squad", "trend", "quality"],
        ["trend", "squad", "coach_brief", "quality"],
    ],
}


def _run(cmd: list[str], timeout: int = 120) -> tuple[bool, float, str]:
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
        return proc.returncode == 0, elapsed, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        return False, time.perf_counter() - started, f"TIMEOUT: {exc}"


def _ensure_git_identity() -> None:
    ok, _, out = _run(["git", "config", "--local", "user.name"], 20)
    if not ok or not out.strip():
        _run(["git", "config", "--local", "user.name", "Dashboard Spiral"], 20)
    ok, _, out = _run(["git", "config", "--local", "user.email"], 20)
    if not ok or not out.strip():
        _run(["git", "config", "--local", "user.email", "dashboard-spiral@local.invalid"], 20)


def _ensure_branch(run_id: str) -> str:
    ok, _, current = _run(["git", "branch", "--show-current"], 20)
    current = current.strip() if ok else ""
    if current.startswith("product-spiral-"):
        return current
    branch = f"product-spiral-dashboard-{run_id.lower()}"
    ok, _, out = _run(["git", "switch", "-c", branch], 30)
    if not ok:
        raise RuntimeError(f"No s'ha pogut crear la branca local: {out}")
    return branch


def _config_text(cfg: dict[str, Any]) -> str:
    return (
        '"""Presentation-only configuration for the Coach Command Center.\n\n'
        'Automatically tuned by product/run_dashboard_spiral.py. Analytics must never\n'
        'depend on these values.\n"""\nfrom __future__ import annotations\n\n'
        + "DASHBOARD_CONFIG = "
        + json.dumps(cfg, ensure_ascii=False, indent=4)
        .replace("true", "True")
        .replace("false", "False")
        .replace("null", "None")
        + "\n"
    )


def _write_config(cfg: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(_config_text(cfg), encoding="utf-8")


def _key(cfg: dict[str, Any]) -> str:
    return json.dumps(cfg, sort_keys=True, ensure_ascii=False)


def _find_browser() -> Path | None:
    for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = os.environ.get(env)
        if not root:
            continue
        r = Path(root)
        for candidate in (
            r / "Google/Chrome/Application/chrome.exe",
            r / "Microsoft/Edge/Application/msedge.exe",
        ):
            if candidate.exists():
                return candidate
    return None


def _section_html(name: str, cfg: dict[str, Any]) -> str:
    if name == "coach_brief":
        cols = int(cfg["brief_columns"])
        return f'''<section data-section="coach_brief"><h2>Coach Brief</h2>
        <div class="brief brief-{cols}">
          <article>Destacats<br><strong>7.8 · 7.4 · 7.2</strong></article>
          <article>Millora recent<br><strong>+0.62 · +0.41</strong></article>
          <article>Descens recent<br><strong>-0.38 · -0.29</strong></article>
          <article>Qualitat de dades<br><strong>Context auditable</strong></article>
        </div></section>'''
    if name == "trend":
        a, b = cfg["trend_ratio"]
        return f'''<section data-section="trend"><h2>Evolució de rendiment</h2>
        <div class="trend" style="grid-template-columns:{a}fr {b}fr">
          <article class="chart"><div class="line"></div></article>
          <article class="context"><b>38 partits</b><span>36 jugadors</span><span>GPS opcional</span></article>
        </div></section>'''
    if name == "squad":
        if cfg["squad_mode"] == "split":
            return '''<section data-section="squad"><h2>Plantilla</h2><div class="squad split"><article class="chart dots">Mapa</article><article class="chart bars">Ratings</article></div></section>'''
        return '''<section data-section="squad"><h2>Plantilla</h2><div class="tabs"><b>Mapa de plantilla</b><span>Ratings · últim partit</span></div><article class="chart dots">Mapa de plantilla</article></section>'''
    if name == "quality":
        if cfg["quality_mode"] == "compact":
            return '''<section data-section="quality"><h2>Qualitat i revisió</h2><article class="quality compact">Context de rol · GPS · Cobertura</article></section>'''
        return '''<section data-section="quality"><h2>Qualitat i revisió</h2><div class="quality cards"><article>Context de rol</article><article>GPS</article><article>Cobertura</article></div></section>'''
    return ""


def _preview_html(cfg: dict[str, Any]) -> str:
    hero_a, hero_b = cfg["hero_ratio"]
    nav = '''<div class="quick"><b>Equip</b><b>Partit</b><b>Jugador</b><b>Assistent IA</b></div>''' if cfg["show_quick_nav"] else ""
    strip = '''<div class="strip"><span>Últim partit · 2026-09-20</span><span>Forma L5 · 3-1-1</span><span>Plantilla · 36</span><span>Partits · 38</span></div>''' if cfg["show_command_strip"] else ""
    sections = "".join(_section_html(name, cfg) for name in cfg["section_order"])
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
    *{{box-sizing:border-box}}body{{margin:0;background:#F5F8FA;color:#102A43;font-family:Arial,sans-serif}}
    .shell{{display:grid;grid-template-columns:225px 1fr;min-height:100vh}}.side{{background:#0B1F33;color:white;padding:22px 16px}}
    .main{{padding:20px 28px;max-width:1500px;width:100%;margin:auto}}h1{{font-size:30px;margin:0 0 4px}}h2{{font-size:18px;margin:26px 0 10px}}
    .sub{{color:#607D8B;margin-bottom:14px}}.quick{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:12px 0}}
    .quick b,.strip span,.metric,.brief article,.quality article,.context,.chart,.tabs{{background:white;border:1px solid #DDE5EB;border-radius:12px;padding:12px}}
    .strip{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 14px}}.strip span{{padding:7px 10px;font-size:12px}}
    .hero{{display:grid;grid-template-columns:{hero_a}fr {hero_b}fr;gap:18px}}.score{{background:#0B1F33;color:white;border-radius:16px;padding:24px;min-height:210px}}
    .score strong{{font-size:52px;display:block;margin:18px 0}}.metrics{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}.metric strong{{font-size:24px;display:block}}
    .brief{{display:grid;gap:10px}}.brief-4{{grid-template-columns:repeat(4,1fr)}}.brief-2{{grid-template-columns:repeat(2,1fr)}}.brief article{{min-height:92px}}
    .trend{{display:grid;gap:14px}}.chart{{height:270px;overflow:hidden}}.line{{height:3px;background:#13A37F;width:80%;margin:130px auto 0;transform:rotate(-8deg)}}
    .context{{display:flex;flex-direction:column;gap:18px;justify-content:center}}.squad.split{{display:grid;grid-template-columns:1.15fr 1fr;gap:14px}}.tabs{{display:flex;gap:24px;margin-bottom:8px}}.quality.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.quality.compact{{min-height:80px}}
    @media(max-width:700px){{.shell{{grid-template-columns:1fr}}.side{{display:none}}.main{{padding:14px}}.quick{{grid-template-columns:repeat(2,1fr)}}.hero,.trend,.squad.split{{grid-template-columns:1fr!important}}.brief-4,.brief-2,.quality.cards{{grid-template-columns:repeat(2,1fr)}}.score{{min-height:175px}}.chart{{height:220px}}}}
    </style></head><body><div class="shell"><aside class="side"><b>FOOTBALL PERFORMANCE</b><p>Command Center</p><p>Equip</p><p>Partit</p><p>Jugador</p></aside><main class="main">
    <h1>Coach Command Center</h1><div class="sub">Visió executiva del rendiment, evolució i context de l'equip.</div>{nav}{strip}
    <div class="hero" data-section="hero"><article class="score">Últim partit<strong>2 — 1</strong>Local · 4-2-3-1</article><div class="metrics"><article class="metric">Match Rating<strong>6.9</strong></article><article class="metric">Confiança<strong>82%</strong></article><article class="metric">Forma L5<strong>3-1-1</strong></article><article class="metric">Context rol<strong>17</strong></article></div></div>
    {sections}</main></div><pre id="metrics" style="display:none"></pre><script>
    const all=[...document.querySelectorAll('article,.quick b,.strip span,.tabs')];
    const overflow=all.filter(e=>e.scrollWidth>e.clientWidth+1).length;
    const secs=[...document.querySelectorAll('[data-section]')];
    const above=secs.filter(e=>e.getBoundingClientRect().top<window.innerHeight).length;
    const brief=[...document.querySelectorAll('.brief article')].map(e=>e.getBoundingClientRect().height);
    const spread=brief.length?Math.max(...brief)-Math.min(...brief):0;
    const m={{innerWidth:window.innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow,aboveFold:above,briefSpread:spread,bodyHeight:document.body.scrollHeight}};
    document.getElementById('metrics').textContent=JSON.stringify(m);
    </script></body></html>'''


def _browser_probe(browser: Path | None, run_dir: Path, cfg: dict[str, Any], width: int, height: int, screenshot: str | None = None) -> dict[str, Any]:
    if browser is None:
        return {"available": False, "probe_ok": False, "horizontal": 0, "overflow": 0, "aboveFold": 0, "briefSpread": 0}
    preview = run_dir / "dashboard_preview.html"
    preview.write_text(_preview_html(cfg), encoding="utf-8")
    profile = run_dir / f"chrome_profile_{width}"
    base = [str(browser), "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars", f"--user-data-dir={profile}", f"--window-size={width},{height}"]
    ok, _, out = _run(base + ["--dump-dom", preview.resolve().as_uri()], 45)
    if not ok:
        return {"available": True, "probe_ok": False, "error": out[-800:]}
    match = re.search(r'<pre id="metrics"[^>]*>(.*?)</pre>', out, flags=re.S | re.I)
    if not match:
        return {"available": True, "probe_ok": False, "error": "metrics_not_found"}
    try:
        metrics = json.loads(html.unescape(match.group(1)))
    except Exception as exc:
        return {"available": True, "probe_ok": False, "error": repr(exc)}
    metrics["available"] = True
    metrics["probe_ok"] = True
    metrics["horizontal"] = max(0, int(metrics.get("scrollWidth", width)) - int(metrics.get("innerWidth", width)))
    if screenshot:
        shot = run_dir / f"{screenshot}_{width}x{height}.png"
        _run(base + [f"--screenshot={shot}", preview.resolve().as_uri()], 45)
    return metrics


def _contracts() -> dict[str, Any]:
    checks = []
    for name, cmd in (
        ("compile", [sys.executable, "-m", "compileall", "-q", "app", "product"]),
        ("ui", [sys.executable, "app/validate_ui_compatibility.py"]),
    ):
        ok, elapsed, out = _run(cmd, 120)
        checks.append({"name": name, "pass": ok, "elapsed_s": round(elapsed, 3), "tail": out[-1000:]})
    return {"all_pass": all(c["pass"] for c in checks), "checks": checks}


def _score(cfg: dict[str, Any], contracts: dict[str, Any], desktop: dict[str, Any], mobile: dict[str, Any]) -> tuple[float, dict[str, float]]:
    if not contracts["all_pass"]:
        return -999.0, {"contracts": 0.0}
    contracts_score = 35.0
    browser_score = 22.0
    if desktop.get("probe_ok") and mobile.get("probe_ok"):
        horizontal = float(desktop.get("horizontal", 0)) + float(mobile.get("horizontal", 0))
        overflow = float(desktop.get("overflow", 0)) + float(mobile.get("overflow", 0))
        spread = float(desktop.get("briefSpread", 0)) + float(mobile.get("briefSpread", 0))
        browser_score = 30.0 - min(14.0, horizontal * 0.3) - min(10.0, overflow * 2.5) - min(6.0, spread * 0.20)
        browser_score = max(0.0, browser_score)

    hierarchy = 0.0
    order = cfg["section_order"]
    hierarchy += 8.0 if order[-1] == "quality" else 2.0
    hierarchy += 5.0 if order[0] in {"coach_brief", "trend"} else 2.0
    above = float(desktop.get("aboveFold", 2)) if desktop.get("probe_ok") else 2.0
    hierarchy += max(0.0, 7.0 - abs(above - 2.5) * 2.0)
    hierarchy = min(20.0, hierarchy)

    usability = 0.0
    usability += 4.0 if cfg["show_quick_nav"] else 1.0
    usability += 3.0 if cfg["show_command_strip"] else 1.0
    usability += 3.0 if cfg["brief_columns"] == 4 else 2.5
    usability += 2.5 if cfg["squad_mode"] == "tabs" else 2.0
    usability += 2.5 if cfg["quality_mode"] == "compact" else 2.0
    usability = min(15.0, usability)

    parts = {"contracts": contracts_score, "browser": round(browser_score, 3), "hierarchy": round(hierarchy, 3), "usability": round(usability, 3)}
    return round(sum(parts.values()), 4), parts


def _evaluate(cfg: dict[str, Any], browser: Path | None, run_dir: Path, screenshot: str | None = None) -> dict[str, Any]:
    _write_config(cfg)
    contracts = _contracts()
    desktop = _browser_probe(browser, run_dir, cfg, 1440, 900, screenshot)
    mobile = _browser_probe(browser, run_dir, cfg, 390, 844, screenshot)
    score, parts = _score(cfg, contracts, desktop, mobile)
    return {"score": score, "parts": parts, "contracts": contracts, "desktop": desktop, "mobile": mobile}


def _mutate(best: dict[str, Any], rng: random.Random, iteration: int) -> dict[str, Any]:
    candidate = deepcopy(best)
    keys = list(SPACES)
    n = 2 if iteration % 17 == 0 else rng.choice([1, 1, 1, 2])
    for key in rng.sample(keys, k=n):
        choices = [deepcopy(v) for v in SPACES[key] if v != candidate[key]]
        if choices:
            candidate[key] = rng.choice(choices)
    return candidate


def _append_csv(path: Path, row: dict[str, Any]) -> None:
    flat = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()}
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(flat.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(flat)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=10.0)
    parser.add_argument("--max-cases", type=int, default=100000)
    parser.add_argument("--max-iterations", type=int, default=1200)
    parser.add_argument("--stagnation", type=int, default=180)
    parser.add_argument("--seed", type=int, default=26092026)
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUT_ROOT / f"dashboard_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    protected = []
    ok, _, status = _run(["git", "status", "--porcelain"], 20)
    if ok:
        for line in status.splitlines():
            path = line[3:].replace("\\", "/") if len(line) > 3 else ""
            if path.startswith(("analytics/", "features/", "decision_tree/", "models/", "llm/", "gps/", "data/")):
                protected.append(path)
    if protected:
        raise SystemExit("Fitxers protegits modificats localment: " + ", ".join(protected))

    _ensure_git_identity()
    branch = _ensure_branch(run_id)
    browser = _find_browser()

    print("=" * 100)
    print("FOOTBALL PERFORMANCE SYSTEM · DASHBOARD STRUCTURAL SPIRAL")
    print(f"branch={branch} hours={args.hours:g} browser={browser or 'static-fallback'}")
    print("Loop: structural dashboard mutation -> Chrome desktop/mobile -> contracts -> keep best -> repeat")
    print("Only app/dashboard_config.py may be changed. No DB/model/browser download. Nothing is pushed.")
    print("=" * 100)

    best = deepcopy(BASE_CONFIG)
    best_eval = _evaluate(best, browser, run_dir, "baseline")
    if best_eval["score"] < 0:
        _write_json(run_dir / "bootstrap_failure.json", best_eval)
        raise SystemExit("El baseline no supera els contractes; consulta bootstrap_failure.json")

    _run(["git", "add", "app/dashboard_config.py"], 20)
    _run(["git", "commit", "-m", f"Dashboard spiral baseline {best_eval['score']:.2f}"], 40)

    best_score = float(best_eval["score"])
    accepted = 0
    attempted = 0
    since_improvement = 0
    seen = {_key(best)}
    deadline = time.monotonic() + max(0.0, args.hours) * 3600.0
    leaderboard = run_dir / "leaderboard.csv"

    _write_json(run_dir / "best_config.json", {"config": best, "evaluation": best_eval})
    print(f"BASELINE score={best_score:.2f}/100 config={best}")

    max_attempts = min(args.max_iterations, args.max_cases)
    while attempted < max_attempts and time.monotonic() < deadline and since_improvement < args.stagnation:
        candidate = _mutate(best, rng, attempted + 1)
        key = _key(candidate)
        if key in seen:
            since_improvement += 1
            continue
        seen.add(key)
        attempted += 1
        snapshot = CONFIG_PATH.read_text(encoding="utf-8")
        try:
            ev = _evaluate(candidate, browser, run_dir)
        except Exception as exc:
            ev = {"score": -999.0, "error": repr(exc)}

        improved = float(ev.get("score", -999.0)) > best_score + 0.01
        if improved:
            ok, _, out = _run(["git", "add", "app/dashboard_config.py"], 20)
            if ok:
                ok, _, out = _run(["git", "commit", "-m", f"Dashboard spiral: iter {attempted} score {ev['score']:.2f}"], 40)
            if ok:
                best = deepcopy(candidate)
                best_score = float(ev["score"])
                best_eval = _evaluate(best, browser, run_dir, f"best_{attempted:04d}")
                accepted += 1
                since_improvement = 0
                _write_json(run_dir / "best_config.json", {"config": best, "evaluation": best_eval, "iteration": attempted})
                print(f"[{attempted:04d}] ACCEPT score={best_score:.2f} accepted={accepted} config={best}")
            else:
                CONFIG_PATH.write_text(snapshot, encoding="utf-8")
                _run(["git", "reset"], 20)
                since_improvement += 1
        else:
            CONFIG_PATH.write_text(snapshot, encoding="utf-8")
            since_improvement += 1

        _append_csv(leaderboard, {
            "iteration": attempted,
            "accepted": improved,
            "score": ev.get("score"),
            "best_score": best_score,
            "since_improvement": since_improvement,
            "config": candidate,
            "parts": ev.get("parts", {}),
            "desktop": ev.get("desktop", {}),
            "mobile": ev.get("mobile", {}),
            "error": ev.get("error", ""),
        })
        if attempted % 25 == 0:
            print(f"[{attempted:04d}] search best={best_score:.2f} accepted={accepted} stagnation={since_improvement}/{args.stagnation}")

    _write_config(best)
    final_contracts = _contracts()
    final_desktop = _browser_probe(browser, run_dir, best, 1440, 900, "final")
    final_mobile = _browser_probe(browser, run_dir, best, 390, 844, "final")
    final_score, final_parts = _score(best, final_contracts, final_desktop, final_mobile)
    reason = "CONVERGED" if since_improvement >= args.stagnation else ("TIME_LIMIT" if time.monotonic() >= deadline else "ITERATION_LIMIT")
    final = {
        "run_id": run_id,
        "branch": branch,
        "reason": reason,
        "attempted_candidates": attempted,
        "accepted_improvements": accepted,
        "best_score": final_score,
        "best_config": best,
        "score_parts": final_parts,
        "desktop": final_desktop,
        "mobile": final_mobile,
        "contracts": final_contracts,
        "browser": str(browser) if browser else None,
        "private_db_downloaded": False,
        "model_downloaded": False,
        "browser_downloaded": False,
        "product_changes_pushed": False,
    }
    _write_json(run_dir / "final_summary.json", final)

    print("=" * 100)
    print(f"DASHBOARD STRUCTURAL SPIRAL COMPLETE · {reason}")
    print(f"attempted={attempted} accepted={accepted} best_score={final_score:.2f}/100")
    print(f"best_config={best}")
    print(f"contracts={'PASS' if final_contracts['all_pass'] else 'FAIL'}")
    print(f"summary={run_dir / 'final_summary.json'}")
    print("Accepted changes are local only. Nothing was pushed automatically.")


if __name__ == "__main__":
    main()
