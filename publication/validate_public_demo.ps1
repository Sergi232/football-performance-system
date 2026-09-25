$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
python publication\validate_public_demo.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host ""
Write-Host "Per provar la web amb la demo anonimitzada:" -ForegroundColor Cyan
Write-Host '$env:FPS_DB_PATH = "$PWD\publication\output\football_performance_public_demo.duckdb"'
Write-Host 'streamlit run app\streamlit_app.py'
