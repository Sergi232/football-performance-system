"""Iterative product optimizer for the final Streamlit/PDF presentation layer.

This is a real bounded improvement loop, not only a stress test. It repeatedly:
1) mutates presentation parameters,
2) evaluates browser layout (using an already-installed Chrome/Edge when available),
3) renders contract-compatible synthetic TEAM/PLAYER/MATCH PDFs,
4) runs repository contracts,
5) keeps only candidates that improve the objective score,
6) reuses the accepted candidate as the next search baseline.

No private database, Ollama model, browser download or paid API is required.
Analytics, ratings, decision thresholds, LLM logic and production data are protected.
Accepted changes are committed only to a local product-spiral-* branch; nothing is pushed.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import run_product_spiral as spiral  # noqa: E402
from product.synthetic_fixtures import mutated_payload, scenario_payloads  # noqa: E402

UI_PATH = Path("app/ui_theme.py")
PDF_PATH = Path("reports/pdf_engine.py")
OPT_START = "/* PRODUCT-SPIRAL:OPTIMIZER-START */"
OPT_END = "/* PRODUCT-SPIRAL:OPTIMIZER-END */"
PDF_MARKER = "# PRODUCT-SPIRAL:PDF-OPTIMIZER-CONFIG"

UI_SPACE = {
    "max_width": [1360, 1400, 1440, 1480],
    "page_pad": [1.50, 1.70, 1.90, 2.00],
    "card_radius": [11, 12, 13, 14],
    "card_pad": [0.82, 0.90, 0.98, 1.04],
    "title_size": [1.88, 1.96, 2.05, 2.12],
    "section_gap": [0.95, 1.08, 1.20, 1.32],
    "chart_radius": [10, 11, 12, 13],
}
PDF_SPACE = {
    "pdf_title": [20.0, 20.5, 21.0, 21.5, 22.0],
    "pdf_subtitle": [8.2, 8.5, 8.8, 9.0],
    "pdf_h2": [11.5, 12.0, 12.5],
    "pdf_body": [8.3, 8.5, 8.7, 8.9],
    "pdf_table": [6.5, 6.8, 7.0],
    "pdf_kpi": [14.0, 15.0, 16.0],
}


@dataclass
class Config:
    max_width: int = 1440
    page_pad: float = 1.90
    card_radius: int = 13
    card_pad: float = 0.90
    title_size: float = 2.05
    section_gap: float = 1.20
    chart_radius: int = 12
    pdf_title: float = 21.0
    pdf_subtitle: float = 8.5
    pdf_h2: float = 12.0
    pdf_body: float = 8.5
    pdf_table: float = 6.8
    pdf_kpi: float = 15.0


def _ensure_git_identity() -> None:
    ok, _, name = spiral._run(["git", "config", "--local", "user.name"], timeout=20)
    if not ok or not name.strip():
        spiral._run(["git", "config", "--local", "user.name", "Product Spiral Lab"], timeout=20)
    ok, _, mail = spiral._run(["git", "config", "--local", "user.email"], timeout=20)
    if not ok or not mail.strip():
        spiral._run(["git", "config", "--local", "user.email", "product-spiral@local.invalid"], timeout=20)


def _replace_optimizer_block(text: str, block: str) -> str:
    pattern = re.compile(re.escape(OPT_START) + r".*?" + re.escape(OPT_END), re.S)
    if pattern.search(text):
        return pattern.sub(block, text, count=1)
    anchor = "        </style>"
    if anchor not in text:
        raise ValueError("UI style closing tag not found")
    return text.replace(anchor, block + "\n" + anchor, 1)


def _ui_block(cfg: Config) -> str:
    return f'''        {OPT_START}
        /* Iteratively tuned presentation overrides. Safe to remove as one block. */
        .block-container {{
            max-width: {cfg.max_width}px;
            padding-left: {cfg.page_pad:.2f}rem;
            padding-right: {cfg.page_pad:.2f}rem;
        }}
        .coach-title {{ font-size: {cfg.title_size:.2f}rem; }}
        .coach-section-head {{ margin-top: {cfg.section_gap:.2f}rem; }}
        .coach-metric-card, .fps-score-card {{
            border-radius: {cfg.card_radius}px;
            padding: {cfg.card_pad:.2f}rem {cfg.card_pad + 0.10:.2f}rem;
        }}
        [data-testid="stPlotlyChart"] {{ border-radius: {cfg.chart_radius}px; }}
        @media (max-width: 700px) {{
            .block-container {{ padding-left:.72rem; padding-right:.72rem; }}
            .coach-title {{ font-size:1.48rem; }}
            .coach-metric-card, .fps-score-card {{ padding:.78rem .82rem; }}
        }}
        {OPT_END}'''


def _instrument_pdf(text: str) -> str:
    if PDF_MARKER not in text:
        anchor = "WHITE = colors.white\n"
        if anchor not in text:
            raise ValueError("PDF color anchor not found")
        block = (
            anchor
            + "\n"
            + PDF_MARKER + "\n"
            + "PDF_OPT_TITLE = 21.0\n"
            + "PDF_OPT_SUBTITLE = 8.5\n"
            + "PDF_OPT_H2 = 12.0\n"
            + "PDF_OPT_BODY = 8.5\n"
            + "PDF_OPT_TABLE = 6.8\n"
            + "PDF_OPT_KPI = 15.0\n"
        )
        text = text.replace(anchor, block, 1)

        replacements = [
            ('"FPS_Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=21,',
             '"FPS_Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=PDF_OPT_TITLE,'),
            ('"FPS_Subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=8.5,',
             '"FPS_Subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=PDF_OPT_SUBTITLE,'),
            ('"FPS_H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12,',
             '"FPS_H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=PDF_OPT_H2,'),
            ('"FPS_Body", parent=base["BodyText"], fontName="Helvetica", fontSize=8.5,',
             '"FPS_Body", parent=base["BodyText"], fontName="Helvetica", fontSize=PDF_OPT_BODY,'),
            ('"FPS_TableHeader", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=6.8,',
             '"FPS_TableHeader", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=PDF_OPT_TABLE,'),
            ('"FPS_TableCell", parent=base["Normal"], fontName="Helvetica", fontSize=6.8,',
             '"FPS_TableCell", parent=base["Normal"], fontName="Helvetica", fontSize=PDF_OPT_TABLE,'),
            ('"FPS_KpiValue", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=15,',
             '"FPS_KpiValue", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=PDF_OPT_KPI,'),
        ]
        for old, new in replacements:
            if old not in text:
                raise ValueError(f"PDF instrumentation anchor missing: {old[:45]}")
            text = text.replace(old, new, 1)
    return text


def _set_pdf_config(text: str, cfg: Config) -> str:
    text = _instrument_pdf(text)
    values = {
        "PDF_OPT_TITLE": cfg.pdf_title,
        "PDF_OPT_SUBTITLE": cfg.pdf_subtitle,
        "PDF_OPT_H2": cfg.pdf_h2,
        "PDF_OPT_BODY": cfg.pdf_body,
        "PDF_OPT_TABLE": cfg.pdf_table,
        "PDF_OPT_KPI": cfg.pdf_kpi,
    }
    for key, value in values.items():
        text, n = re.subn(rf"^{key}\s*=\s*[-0-9.]+\s*$", f"{key} = {value:.2f}", text, count=1, flags=re.M)
        if n != 1:
            raise ValueError(f"Unable to set {key}")
    return text


def _apply_config(cfg: Config) -> None:
    ui = spiral._read(UI_PATH)
    pdf = spiral._read(PDF_PATH)
    spiral._write(UI_PATH, _replace_optimizer_block(ui, _ui_block(cfg)))
    spiral._write(PDF_PATH, _set_pdf_config(pdf, cfg))


def _find_browser() -> Path | None:
    candidates: list[Path] = []
    for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = os.environ.get(env)
        if not root:
            continue
        r = Path(root)
        candidates.extend([
            r / "Google/Chrome/Application/chrome.exe",
            r / "Microsoft/Edge/Application/msedge.exe",
        ])
    for path in candidates:
        if path.exists():
            return path
    return None


def _extract_css() -> str:
    text = spiral._read(UI_PATH)
    m = re.search(r"<style>(.*?)</style>", text, flags=re.S)
    return m.group(1) if m else ""


def _preview_html(css: str) -> str:
    cards = "".join(
        f'<div class="coach-metric-card metric-sample"><div class="coach-metric-label">{label}</div>'
        f'<div class="coach-metric-value">{value}</div><div class="coach-metric-sub">{sub}</div></div>'
        for label, value, sub in [
            ("MATCH RATING", "7.3", "Últim partit · 86% confiança"),
            ("FORMA L5", "6.8", "+0.34 vs 5 anteriors"),
            ("MINUTS", "2.314", "31 aparicions"),
            ("CREACIÓ", "72.0", "Perfil DM/CM"),
        ]
    )
    rows = "".join(
        f"<tr><td>Jugador {i} amb cognom</td><td>{['CB','FB/WB','DM/CM','AM/W','ST'][i%5]}</td><td>{6.0+i/20:.1f}</td><td>{60+i}%</td></tr>"
        for i in range(1, 12)
    )
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box}} body{{margin:0}} {css}
.preview-shell{{display:grid;grid-template-columns:235px 1fr;min-height:100vh}}
.preview-side{{background:#0B1F33;padding:22px 15px;color:white}}
.preview-main{{padding:0 8px}} .metric-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}}
.chart-fake{{height:280px;background:linear-gradient(180deg,#fff,#f8fafb);border:1px solid #E1E8EE;border-radius:12px;padding:18px;overflow:hidden}}
.chart-line{{height:2px;background:#13A37F;width:82%;margin:120px 0 0 7%;transform:rotate(-7deg)}}
table{{width:100%;border-collapse:collapse;background:white}} th,td{{padding:9px;border-bottom:1px solid #E1E8EE;text-align:left;white-space:normal}}
@media(max-width:700px){{.preview-shell{{grid-template-columns:1fr}}.preview-side{{display:none}}.metric-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
</style></head><body>
<div class="preview-shell"><aside class="preview-side"><b>FOOTBALL PERFORMANCE</b><p>Centre de comandament</p><p>Equip</p><p>Partit</p><p>Jugador</p><p>Assistent IA</p></aside>
<main class="preview-main"><div class="block-container">
<div class="coach-page-header"><div><div class="coach-kicker">TEAM MODE</div><div class="coach-title">Centre de comandament</div><div class="coach-subtitle">Visió operativa de rendiment, evolució, disponibilitat d'evidència i context de l'equip.</div></div><span class="coach-badge">DADES ESTRUCTURADES</span></div>
<div class="metric-grid">{cards}</div>
<div class="coach-section-head"><div class="coach-section-title">Evolució recent</div><div class="coach-section-sub">Match Rating i tendència descriptiva</div></div>
<div data-testid="stPlotlyChart" class="chart-fake"><div class="chart-line"></div></div>
<div class="coach-section-head"><div class="coach-section-title">Plantilla</div></div>
<div data-testid="stDataFrame"><table><thead><tr><th>Jugador</th><th>Rol</th><th>Rating</th><th>Conf.</th></tr></thead><tbody>{rows}</tbody></table></div>
</div></main></div>
<pre id="metrics" style="display:none"></pre>
<script>
const elems=[...document.querySelectorAll('.coach-metric-card,[data-testid="stPlotlyChart"],[data-testid="stDataFrame"],.coach-page-header')];
const overflow=elems.filter(e=>e.scrollWidth>e.clientWidth+1).length;
const cards=[...document.querySelectorAll('.metric-sample')];
const hs=cards.map(e=>e.getBoundingClientRect().height); const spread=hs.length?Math.max(...hs)-Math.min(...hs):0;
const m={{innerWidth:window.innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow,cardSpread:spread,bodyHeight:document.body.scrollHeight}};
document.getElementById('metrics').textContent=JSON.stringify(m);
</script></body></html>'''


def _browser_probe(browser: Path | None, run_dir: Path, label: str, width: int, height: int) -> dict[str, Any]:
    if browser is None:
        return {"available": False, "overflow": 0, "horizontal_overflow": 0, "cardSpread": 0.0}
    preview = run_dir / "preview.html"
    preview.write_text(_preview_html(_extract_css()), encoding="utf-8")
    profile = run_dir / "browser_profile"
    cmd = [
        str(browser), "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
        f"--user-data-dir={profile}", f"--window-size={width},{height}", "--dump-dom", preview.resolve().as_uri(),
    ]
    ok, _, out = spiral._run(cmd, timeout=45)
    if not ok:
        return {"available": True, "probe_ok": False, "error": out[-1000:]}
    m = re.search(r'<pre id="metrics"[^>]*>(.*?)</pre>', out, flags=re.S | re.I)
    if not m:
        return {"available": True, "probe_ok": False, "error": "metrics_not_found"}
    try:
        metrics = json.loads(html.unescape(m.group(1)))
    except Exception as exc:
        return {"available": True, "probe_ok": False, "error": repr(exc)}
    metrics["available"] = True
    metrics["probe_ok"] = True
    metrics["horizontal_overflow"] = max(0, int(metrics.get("scrollWidth", width)) - int(metrics.get("innerWidth", width)))
    if label.startswith("best"):
        screenshot = run_dir / f"{label}_{width}x{height}.png"
        shot_cmd = [
            str(browser), "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
            f"--user-data-dir={profile}", f"--window-size={width},{height}", f"--screenshot={screenshot}", preview.resolve().as_uri(),
        ]
        spiral._run(shot_cmd, timeout=45)
    return metrics


def _pdf_probe(cfg: Config, seed: int) -> dict[str, Any]:
    # Reimport on every candidate so module constants reflect the candidate file.
    import importlib
    import reports.pdf_engine as pdf_engine
    importlib.invalidate_caches()
    pdf_engine = importlib.reload(pdf_engine)

    cases = scenario_payloads(seed)
    failures = 0
    pages: list[int] = []
    sizes: list[int] = []
    for label, payload in cases:
        try:
            pdf = pdf_engine.render_pdf_bytes(payload)
            ok = pdf.startswith(b"%PDF-") and len(pdf) >= 1000
            if not ok:
                failures += 1
                continue
            pages.append(max(1, len(re.findall(rb"/Type\s*/Page\b", pdf))))
            sizes.append(len(pdf))
        except Exception:
            failures += 1
    return {
        "cases": len(cases),
        "failures": failures,
        "max_pages": max(pages) if pages else 99,
        "mean_pages": (sum(pages) / len(pages)) if pages else 99.0,
        "mean_bytes": (sum(sizes) / len(sizes)) if sizes else 0.0,
    }


def _near(value: float, target: float, tolerance: float) -> float:
    return max(0.0, 1.0 - abs(value - target) / tolerance)


def _score(cfg: Config, gates: dict, desktop: dict, mobile: dict, pdf: dict) -> tuple[float, dict[str, float]]:
    if not gates.get("all_pass") or pdf.get("failures", 1) > 0:
        return -999.0, {"contracts": 0.0}

    contract = 25.0
    browser_available = bool(desktop.get("available") and mobile.get("available") and desktop.get("probe_ok", True) and mobile.get("probe_ok", True))
    if browser_available:
        horiz = float(desktop.get("horizontal_overflow", 999)) + float(mobile.get("horizontal_overflow", 999))
        elem_over = float(desktop.get("overflow", 99)) + float(mobile.get("overflow", 99))
        spread = float(desktop.get("cardSpread", 999)) + float(mobile.get("cardSpread", 999))
        browser_score = max(0.0, 35.0 - min(18.0, horiz * 0.25) - min(10.0, elem_over * 2.5) - min(7.0, spread * 0.15))
    else:
        browser_score = 24.0  # conservative fallback; never pretend visual browser validation ran

    # PDF score rewards successful dense/long-text rendering without making fonts tiny.
    pdf_score = 20.0
    pdf_score -= max(0.0, float(pdf.get("max_pages", 3)) - 4.0) * 1.5
    pdf_score += 2.0 * _near(cfg.pdf_body, 8.7, 0.8)
    pdf_score += 1.5 * _near(cfg.pdf_table, 6.8, 0.5)
    pdf_score += 1.5 * _near(cfg.pdf_title, 21.0, 1.5)
    pdf_score = max(0.0, min(25.0, pdf_score))

    # Soft design balance prevents the optimizer from gaming layout by shrinking everything.
    design = 0.0
    design += 3.0 * _near(cfg.max_width, 1440, 180)
    design += 2.2 * _near(cfg.page_pad, 1.85, 0.55)
    design += 2.0 * _near(cfg.card_radius, 13, 3)
    design += 2.0 * _near(cfg.card_pad, 0.92, 0.30)
    design += 2.2 * _near(cfg.title_size, 2.00, 0.38)
    design += 1.8 * _near(cfg.section_gap, 1.15, 0.42)
    design += 1.8 * _near(cfg.chart_radius, 12, 3)
    design = min(15.0, design)

    parts = {"contracts": contract, "browser": browser_score, "pdf": pdf_score, "design": design}
    return round(sum(parts.values()), 4), parts


def _mutate(best: Config, rng: random.Random, iteration: int) -> Config:
    values = asdict(best)
    spaces = {**UI_SPACE, **PDF_SPACE}
    keys = list(spaces)
    if iteration % 23 == 0:
        # bounded restart to escape local maxima
        for key in rng.sample(keys, k=min(5, len(keys))):
            values[key] = rng.choice(spaces[key])
    else:
        for key in rng.sample(keys, k=rng.choice([1, 1, 2, 2, 3])):
            choices = [v for v in spaces[key] if v != values[key]]
            values[key] = rng.choice(choices)
    return Config(**values)


def _commit_candidate(iteration: int, score: float) -> tuple[bool, str]:
    ok, _, out = spiral._run(["git", "add", str(UI_PATH), str(PDF_PATH)], timeout=30)
    if not ok:
        return False, out
    return spiral._run(["git", "commit", "-m", f"Product spiral optimizer: iter {iteration} score {score:.2f}"], timeout=60)[0::2]


def _append_row(path: Path, row: dict[str, Any]) -> None:
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    flat = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in row.items()}
    with path.open("a", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(flat.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(flat)


def _evaluate(cfg: Config, browser: Path | None, run_dir: Path, seed: int, screenshot: bool = False) -> dict[str, Any]:
    _apply_config(cfg)
    gates = spiral.run_contract_gates(False)
    pdf = _pdf_probe(cfg, seed)
    label = "best" if screenshot else "candidate"
    desktop = _browser_probe(browser, run_dir, label + "_desktop", 1440, 1000)
    mobile = _browser_probe(browser, run_dir, label + "_mobile", 390, 844)
    score, parts = _score(cfg, gates, desktop, mobile, pdf)
    return {"score": score, "parts": parts, "gates": gates, "pdf": pdf, "desktop": desktop, "mobile": mobile}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=10.0)
    parser.add_argument("--max-cases", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=26092026)
    parser.add_argument("--max-search-iterations", type=int, default=5000)
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = spiral.OUTPUT_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    protected = spiral._protected_dirty_paths()
    if protected:
        raise SystemExit("Protected files are modified locally; refusing optimizer: " + ", ".join(protected))

    _ensure_git_identity()
    branch = spiral._ensure_local_branch(run_id)
    browser = _find_browser()

    print("=" * 100)
    print("FOOTBALL PERFORMANCE SYSTEM · TRUE PRODUCT IMPROVEMENT SPIRAL")
    print(f"branch={branch} hours={args.hours:g} private_db=False browser={browser or 'fallback-static'}")
    print("Loop: mutate UI/PDF -> browser/PDF/contracts -> keep improvement -> repeat.")
    print("No private DB, Ollama/model download, paid API or automatic push.")
    print("=" * 100)

    # First apply the safe structural recipes already defined by the project.
    for recipe in spiral.RECIPES:
        result = spiral.apply_recipe(recipe, False)
        print(f"BOOTSTRAP {recipe.name}: {result.get('status')}")

    best = Config()
    best_eval = _evaluate(best, browser, run_dir, args.seed, screenshot=True)
    if best_eval["score"] < 0:
        spiral._write_json(run_dir / "bootstrap_failure.json", best_eval)
        raise SystemExit(f"Baseline candidate failed contracts; see {run_dir / 'bootstrap_failure.json'}")

    # Commit optimizer instrumentation/baseline if it changed presentation files.
    spiral._run(["git", "add", str(UI_PATH), str(PDF_PATH)], timeout=30)
    spiral._run(["git", "commit", "-m", f"Product spiral optimizer baseline {best_eval['score']:.2f}"], timeout=60)

    best_score = float(best_eval["score"])
    accepted = 0
    attempted = 0
    deadline = time.monotonic() + max(0.0, args.hours) * 3600.0
    leaderboard = run_dir / "leaderboard.csv"
    best_json = run_dir / "best_config.json"
    spiral._write_json(best_json, {"config": asdict(best), "evaluation": best_eval})
    print(f"BASELINE score={best_score:.2f}/100")

    while attempted < args.max_search_iterations and attempted < args.max_cases and time.monotonic() < deadline:
        attempted += 1
        candidate = _mutate(best, rng, attempted)
        snapshot = {UI_PATH: spiral._read(UI_PATH), PDF_PATH: spiral._read(PDF_PATH)}
        try:
            ev = _evaluate(candidate, browser, run_dir, args.seed + attempted)
        except Exception as exc:
            ev = {"score": -999.0, "error": repr(exc)}

        improved = float(ev.get("score", -999.0)) > best_score + 0.01
        if improved:
            ok, _, commit_out = spiral._run(
                ["git", "add", str(UI_PATH), str(PDF_PATH)], timeout=30
            )
            if ok:
                ok, _, commit_out = spiral._run(
                    ["git", "commit", "-m", f"Product spiral optimizer: iter {attempted} score {ev['score']:.2f}"], timeout=60
                )
            if ok:
                best = candidate
                best_score = float(ev["score"])
                best_eval = ev
                accepted += 1
                # Save representative browser screenshots for each new best when browser exists.
                best_eval = _evaluate(best, browser, run_dir, args.seed + attempted, screenshot=True)
                spiral._write_json(best_json, {"config": asdict(best), "evaluation": best_eval, "iteration": attempted})
                print(f"[{attempted:05d}] ACCEPT score={best_score:.2f} accepted={accepted} config={asdict(best)}")
            else:
                for path, text in snapshot.items():
                    spiral._write(path, text)
                spiral._run(["git", "reset"], timeout=30)
                ev["commit_error"] = commit_out[-1000:]
        else:
            for path, text in snapshot.items():
                spiral._write(path, text)

        _append_row(leaderboard, {
            "iteration": attempted,
            "accepted": improved,
            "score": ev.get("score"),
            "best_score": best_score,
            "config": asdict(candidate),
            "parts": ev.get("parts", {}),
            "pdf": ev.get("pdf", {}),
            "desktop": ev.get("desktop", {}),
            "mobile": ev.get("mobile", {}),
            "error": ev.get("error", ""),
        })

        if attempted % 25 == 0:
            print(f"[{attempted:05d}] search best={best_score:.2f} accepted={accepted}")
        if attempted % 20 == 0:
            spiral._write_json(run_dir / "checkpoint.json", {
                "run_id": run_id,
                "mode": "ITERATIVE_PRODUCT_OPTIMIZER",
                "branch": branch,
                "attempted": attempted,
                "accepted": accepted,
                "best_score": best_score,
                "best_config": asdict(best),
                "browser": str(browser) if browser else None,
                "private_db_downloaded": False,
                "model_downloaded": False,
            })

    # Final regression and synthetic stress phase on the best accepted presentation.
    final_gates = spiral.run_contract_gates(False)
    stress_cases = scenario_payloads(args.seed + 900000)
    stress_done = 0
    stress_fail = 0
    from reports.pdf_engine import render_pdf_bytes
    while stress_done < max(50, min(2000, args.max_cases - attempted)) and time.monotonic() < deadline:
        label, payload = rng.choice(stress_cases)
        label, payload = mutated_payload(label, payload, args.seed + stress_done * 37)
        try:
            pdf = render_pdf_bytes(payload)
            ok = pdf.startswith(b"%PDF-") and len(pdf) >= 1000
        except Exception:
            ok = False
        stress_done += 1
        stress_fail += 0 if ok else 1

    final = {
        "run_id": run_id,
        "finished_at": spiral._utc_now(),
        "mode": "ITERATIVE_PRODUCT_OPTIMIZER",
        "branch": branch,
        "attempted_candidates": attempted,
        "accepted_improvements": accepted,
        "best_score": best_score,
        "best_config": asdict(best),
        "best_evaluation": best_eval,
        "browser_validation": str(browser) if browser else "not_available_static_fallback",
        "synthetic_pdf_stress_cases": stress_done,
        "synthetic_pdf_stress_failures": stress_fail,
        "final_gates": final_gates,
        "private_db_downloaded": False,
        "ollama_or_model_downloaded": False,
        "product_changes_pushed": False,
        "note": "Objective browser/layout/PDF optimization still requires final human visual review before merging.",
    }
    spiral._write_json(run_dir / "final_summary.json", final)

    print("=" * 100)
    print("TRUE PRODUCT IMPROVEMENT SPIRAL COMPLETE")
    print(f"attempted={attempted} accepted={accepted} best_score={best_score:.2f}/100")
    print(f"stress={stress_done} failures={stress_fail} contracts={'PASS' if final_gates['all_pass'] else 'FAIL'}")
    print(f"summary={run_dir / 'final_summary.json'}")
    print("Accepted changes are local on the product-spiral branch. Nothing was pushed automatically.")


if __name__ == "__main__":
    main()
