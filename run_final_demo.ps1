param(
    [switch]$SkipRebuild
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "============================================================"
Write-Host " Football Performance System - FINAL DEMO"
Write-Host "============================================================"
Write-Host ""

$demoDb = Join-Path $PSScriptRoot "data\football_performance_synthetic_demo.duckdb"

if (-not $SkipRebuild) {
    Write-Host "[1/3] Rebuilding and validating the synthetic public demo..."
    python -m publication.validate_synthetic_demo --rebuild
    if ($LASTEXITCODE -ne 0) {
        throw "Synthetic demo validation failed. Streamlit was not started."
    }
} else {
    Write-Host "[1/3] Synthetic rebuild skipped by user."
}

if (-not (Test-Path $demoDb)) {
    throw "Synthetic demo database not found: $demoDb"
}

Write-Host "[2/3] Enabling anonymized demo mode..."
$env:FPS_DB_PATH = $demoDb
$env:FPS_DEMO_MODE = "1"
if (-not $env:FPS_LOCAL_LLM_MODEL) {
    $env:FPS_LOCAL_LLM_MODEL = "qwen3.5:4b"
}

Write-Host "      FPS_DB_PATH=$demoDb"
Write-Host "      FPS_DEMO_MODE=1"
Write-Host "      FPS_LOCAL_LLM_MODEL=$env:FPS_LOCAL_LLM_MODEL"
Write-Host ""
Write-Host "[3/3] Starting Streamlit..."
Write-Host "      Final screenshots must show Equipo Demo / Jugador XX / Rival XX."
Write-Host "      Do not expose API keys, local professional identities or private paths in screenshots."
Write-Host ""

python -m streamlit run app\streamlit_app.py
exit $LASTEXITCODE
