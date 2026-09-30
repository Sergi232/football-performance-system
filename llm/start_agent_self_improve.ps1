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

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log = Join-Path $env:USERPROFILE "Desktop\TFM_AGENT_SELF_IMPROVE_$stamp.txt"

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class FpsKeepAwake {
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@
# Windows PowerShell 5.1 parses 0x80000000 as signed Int32 (-2147483648).
# Build the unsigned flags explicitly so SetThreadExecutionState works reliably.
$ES_CONTINUOUS = [Convert]::ToUInt32("80000000", 16)
$ES_SYSTEM_REQUIRED = [uint32]1
$ES_KEEP_AWAKE = [uint32]($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED)
[void][FpsKeepAwake]::SetThreadExecutionState($ES_KEEP_AWAKE)

Start-Transcript -Path $log -Force
try {
    Write-Host "=== COACH COPILOT SELF-IMPROVE ==="
    Write-Host "Repo: $Repo"
    Write-Host "DB: $env:FPS_DB_PATH"
    Write-Host "Model: $Model"
    Write-Host "Durada objectiu: $Hours hores"
    Write-Host "Windows sleep: bloquejat temporalment mentre dura el procés"

    Write-Host "`n=== PREFLIGHT PYTHON ==="
    python -c "import py_compile; py_compile.compile(r'llm\run_agent_self_improve.py', doraise=True); py_compile.compile(r'llm\run_agent_self_improve_entry.py', doraise=True); py_compile.compile(r'llm\summarize_self_improve.py', doraise=True); print('SYNTAX PASS')"
    if ($LASTEXITCODE -ne 0) { throw "Python preflight failed." }

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
        throw "El model $Model no està instal·lat a Ollama."
    }

    Write-Host "`n=== INICIANT PROCÉS AUTÒNOM ==="
    python -u .\llm\run_agent_self_improve_entry.py --hours $Hours --model $Model
    if ($LASTEXITCODE -ne 0) {
        throw "Self-improvement runner ha acabat amb codi $LASTEXITCODE."
    }

    Write-Host "`n=== RESUM AUDITAT ROUTER vs SYNTHESIS ==="
    python -u .\llm\summarize_self_improve.py
    if ($LASTEXITCODE -ne 0) {
        throw "Audited summary ha acabat amb codi $LASTEXITCODE."
    }

    Write-Host "`n=== PROCÉS COMPLETAT ==="
    Write-Host "Resultats: $Repo\outputs\agent_eval\self_improve"
    Write-Host "Resum principal: $Repo\outputs\agent_eval\self_improve\audited_summary_latest.json"
}
finally {
    [void][FpsKeepAwake]::SetThreadExecutionState($ES_CONTINUOUS)
    Write-Host "`nWindows sleep: política normal restaurada"
    Write-Host "Log: $log"
    Stop-Transcript
}
