# Product Spiral Lab

Autonomous local QA/improvement loop for the **final product layer** of Football Performance System: Streamlit web UI and static PDF exports.

It is intentionally downstream of analytics. It does **not** modify Match Rating, Performance Index formulas, expert-system thresholds, features, GPS calculations, LLM logic or database contents.

## What it does

1. Creates a dedicated local `product-spiral-*` branch.
2. Audits the shared UI/PDF presentation layer and computes a reproducible `product_quality_score`.
3. Applies a small catalog of deterministic, presentation-only improvement recipes.
4. Runs compile/UI/dashboard/match/report contracts after every candidate change.
5. Rolls back candidates that break a contract or reduce the quality score.
6. Commits accepted presentation changes **locally only**.
7. Uses real team/player/match data to repeatedly build report payloads and PDFs.
8. Replays failing scenarios more often and writes checkpoints, CSV case logs and a final summary.
9. Never pushes or merges automatically.

## Safety boundary

Mutation allowlist:

- `app/ui_theme.py`
- `app/coach_ui.py`
- `reports/pdf_engine.py`

Protected areas include `analytics/`, `data/`, `features/`, `decision_tree/`, `models/`, `llm/` and `gps/`.

If protected files are already dirty locally, the run refuses to start.

## Run

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull

$env:FPS_DB_PATH = "D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb"

python product\run_product_spiral.py --hours 10 --max-cases 100000
```

The PC must remain on. The database should be a local copy on that PC; do not point two machines at the same writable database file.

## Outputs

Local-only outputs are written under:

```text
outputs/product_spiral/<run_id>/
```

Main artifacts:

- `recipes.json` — accepted/rolled-back presentation recipes;
- `cases.csv` — real TEAM/PLAYER/MATCH PDF scenario probes;
- `checkpoint.json` — current run state;
- `latest_gates.json` — latest regression gates;
- `final_summary.json` — final product score, pass rate and failures.

These outputs are ignored by Git.

## Important limitation

This loop can automatically improve and stress-test **objective product qualities** such as consistency, responsive behavior, accessibility states, PDF pagination safety, contract integrity and coverage across real data. It is not a substitute for the final human visual gate: aesthetic judgement, information hierarchy and coaching usefulness still require inspecting the web and representative PDFs before merging the local branch.
