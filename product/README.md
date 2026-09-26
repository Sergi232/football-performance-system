# Product Spiral Lab

Autonomous local QA/improvement loop for the **final product layer** of Football Performance System: Streamlit web UI and static PDF exports.

It is intentionally downstream of analytics. It does **not** modify Match Rating, Performance Index formulas, expert-system thresholds, features, GPS calculations, LLM logic or database contents.

## What it does

1. Creates a dedicated local `product-spiral-*` branch.
2. Audits the shared UI/PDF presentation layer and computes a reproducible `product_quality_score`.
3. Applies a small catalog of deterministic, presentation-only improvement recipes.
4. Runs compile/UI contracts after every candidate change.
5. Rolls back candidates that break a contract or reduce the quality score.
6. Commits accepted presentation changes **locally only**.
7. Stress-tests TEAM / PLAYER / MATCH PDFs and product contracts repeatedly.
8. Replays failing scenarios more often and writes checkpoints, CSV case logs and a final summary.
9. Never pushes or merges automatically.

## Two automatic modes

Use the hardened launcher:

```powershell
python product\run_product_spiral_safe.py --hours 10 --max-cases 100000
```

It chooses the mode automatically:

### REAL-DB mode

If `football_performance.duckdb` exists, the loop uses the real local team/player/match data and runs the DB-dependent product validators.

### DB-FREE synthetic-contract mode

If the private DuckDB is not available, the loop uses the **real GitHub UI/PDF code** plus deterministic synthetic fixtures with the same production field shapes.

The DB-free mode includes:

- TEAM / PLAYER / MATCH payloads;
- normal, sparse, long-text, dense and dense+long-text scenarios;
- bounded fixture mutation;
- PDF rendering stress tests;
- code-level web product audit;
- failure replay;
- no Ollama or model download;
- no private database download.

It is useful on a second or work PC and is explicitly not a replacement for the final gate on the real database.

## Safety boundary

Mutation allowlist:

- `app/ui_theme.py`
- `app/coach_ui.py`
- `reports/pdf_engine.py`

Protected areas include `analytics/`, `data/`, `features/`, `decision_tree/`, `models/`, `llm/` and `gps/`.

If protected files are already dirty locally, the run refuses to start.

The launcher configures a repository-local Git identity for Product Spiral commits if the machine has no Git identity configured. It does not change global Git configuration.

## Recommended run

```powershell
cd $HOME\Desktop\football-performance-system
git switch main
git pull
python product\run_product_spiral_safe.py --hours 10 --max-cases 100000
```

No additional database or local-LLM download is required for DB-free mode.

If a real DB is available on the machine, optionally set:

```powershell
$env:FPS_DB_PATH = "D:\ruta\football_performance.duckdb"
```

Do not point two machines at the same writable database file.

## Outputs

Local-only outputs are written under:

```text
outputs/product_spiral/<run_id>/
```

Main artifacts:

- `recipes.json` — accepted/rolled-back presentation recipes;
- `cases.csv` — TEAM/PLAYER/MATCH product scenario probes;
- `checkpoint.json` — current run state;
- `latest_gates.json` — latest regression gates;
- `final_summary.json` — final product score, pass rate and failures.

These outputs are ignored by Git.

## Important limitation

This loop can automatically improve and stress-test **objective product qualities** such as consistency, responsive behavior, accessibility states, PDF pagination safety, contract integrity and scenario robustness. It is not a substitute for the final human visual gate: aesthetic judgement, information hierarchy and coaching usefulness still require inspecting the web and representative PDFs before merging the local branch.
