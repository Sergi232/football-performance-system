param(
    [double]$Hours = 10,
    [string]$Model = "qwen3:1.7b"
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Repo

$KnownDb = "D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb"
$RepoDb = Join-Path $Repo "data\football_performance.duckdb"
$DbCandidates = @($env:FPS_DB_PATH, $KnownDb, $RepoDb) | Where-Object { $_ -and (Test-Path $_) }
if (-not $DbCandidates) {
    throw "No s'ha trobat football_performance.duckdb."
}
$env:FPS_DB_PATH = $DbCandidates[0]
$env:FPS_LOCAL_LLM_MODEL = $Model
$env:PYTHONPATH = $Repo

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log = Join-Path $env:USERPROFILE "Desktop\TFM_AGENT_AUTOCORRECT_$stamp.txt"

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class FpsAutoCorrectKeepAwake {
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@
$ES_CONTINUOUS = [Convert]::ToUInt32("80000000", 16)
$ES_SYSTEM_REQUIRED = [uint32]1
$ES_KEEP_AWAKE = [uint32]($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED)
[void][FpsAutoCorrectKeepAwake]::SetThreadExecutionState($ES_KEEP_AWAKE)

Start-Transcript -Path $log -Force
try {
    Write-Host "=== COACH COPILOT AUTO-CORRECT ==="
    Write-Host "Repo: $Repo"
    Write-Host "DB: $env:FPS_DB_PATH"
    Write-Host "Model: $Model"
    Write-Host "Durada objectiu: $Hours hores"
    Write-Host "Windows sleep: bloquejat temporalment mentre dura el proces"
    Write-Host "Autocorreccio: router + prompt + runtime profile; analytics/ratings/DB protegits"

    Write-Host "`n=== PREFLIGHT PYTHON/IMPORTS ==="
    python -c "import llm.eval_agent_autocorrect_candidate, llm.run_agent_autocorrect; print('IMPORT PASS')"
    if ($LASTEXITCODE -ne 0) { throw "Python/import preflight failed." }

    Write-Host "`n=== OLLAMA ==="
    try {
        Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | Out-Null
    }
    catch {
        Start-Process -FilePath "ollama" -ArgumentList "serve"
        Start-Sleep -Seconds 7
    }

    $models = ollama list | Out-String
    Write-Host $models
    if ($models -notmatch [regex]::Escape($Model)) {
        throw "El model $Model no esta instal-lat a Ollama."
    }

    Write-Host "`n=== INICIANT AUTOCORRECCIO CONTROLADA ==="
    python -u -m llm.run_agent_autocorrect --hours $Hours --model $Model --db $env:FPS_DB_PATH
    if ($LASTEXITCODE -ne 0) {
        throw "Auto-correct runner ha acabat amb codi $LASTEXITCODE."
    }

    Write-Host "`n=== PROCÉS COMPLETAT ==="
    Write-Host "Resultats: $Repo\outputs\agent_eval\autocorrect"
    Write-Host "Resum: $Repo\outputs\agent_eval\autocorrect\autocorrect_summary_latest.json"
}
finally {
    [void][FpsAutoCorrectKeepAwake]::SetThreadExecutionState($ES_CONTINUOUS)
    Write-Host "`nWindows sleep: politica normal restaurada"
    Write-Host "Log: $log"
    Stop-Transcript
}
