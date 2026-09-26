# Product Spiral Lab

Autonomous local QA/improvement loop for the **final product layer** of Football Performance System: Streamlit web UI and static PDF exports.

It is intentionally downstream of analytics. It does **not** modify Match Rating, Performance Index formulas, expert-system thresholds, features, GPS calculations, LLM logic or database contents.

## What it does

1. Creates a dedicated local `product-spiral-*` branch.
2. Uses the real GitHub UI/PDF code as the starting point.
3. Repeatedly mutates presentation parameters for web and PDF.
4. Evaluates each candidate with browser layout probes, synthetic TEAM/PLAYER/MATCH PDFs and repository contracts.
5. Keeps only candidates that improve the objective product score.
6. Uses the accepted candidate as the baseline for the next iteration: **real iterative spiral**.
7. Rolls back candidates that fail contracts or do not improve the score.
8. Saves desktop/mobile screenshots of accepted best candidates when Chrome/Edge is already installed.
9. Commits accepted presentation changes **locally only** and never pushes or merges automatically.

## Two automatic modes

Use the hardened launcher:

```powershell
python product\run_product_spiral_safe.py --hours 10 --max-cases 100000
```

It chooses the mode automatically.

### REAL-DB mode

If `football_performance.duckdb` exists, the loop uses the real local team/player/match data and DB-dependent product validators.

### TRUE ITERATIVE DB-FREE OPTIMIZER

If the private DuckDB is not available, the launcher now uses `run_product_spiral_optimizer.py`.

The loop is:

```text
current best web/PDF
→ mutate presentation parameters
→ compile + UI contracts
→ browser desktop/mobile layout probe
→ TEAM/PLAYER/MATCH synthetic PDF stress
→ objective score
→ better? keep + local commit
→ worse/fail? rollback
→ mutate the new best
→ repeat
```

The DB-free optimizer uses:

- the real Streamlit presentation code from GitHub;
- contract-compatible TEAM / PLAYER / MATCH synthetic payloads;
- normal, sparse, long-text, dense and dense+long-text scenarios;
- desktop and mobile browser layout checks when Chrome/Edge is already installed;
- PDF rendering and pagination stress;
- bounded search over spacing, width, card density, hierarchy and PDF typography;
- no Ollama/model download;
- no private database download;
- no browser download;
- no paid API.

## Safety boundary

Automatic mutations are limited to presentation files:

- `app/ui_theme.py`
- `app/coach_ui.py`
- `reports/pdf_engine.py`

Protected areas include `analytics/`, `data/`, `features/`, `decision_tree/`, `models/`, `llm/` and `gps/`.

If protected files are dirty locally, the run refuses to start.

The launcher configures a repository-local Git identity for Product Spiral commits if the machine has no Git identity configured. It does not change global Git configuration.

## Recommended run

```powershell
cd $HOME\Desktop\football-performance-system
git reset --hard
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

Main artifacts in iterative optimizer mode:

- `leaderboard.csv` — every candidate and its score;
- `best_config.json` — best accepted presentation configuration;
- `checkpoint.json` — current search state;
- desktop/mobile PNG screenshots of accepted best states when a browser is available;
- `final_summary.json` — attempts, accepted improvements, best score, PDF stress and final contracts.

These outputs are ignored by Git.

## Important limitation

The optimizer improves **objective, measurable product qualities**: responsive layout, overflow/clipping risk, spacing/density balance, presentation consistency, PDF rendering/pagination robustness and contract integrity. It cannot replace the final human visual gate for aesthetics, information hierarchy and usefulness to a coaching staff. Accepted changes therefore remain on a local branch until reviewed.
