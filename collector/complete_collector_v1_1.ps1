$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    python .\collector\validate_collector_v1.py
    if ($LASTEXITCODE -ne 0) { throw 'validate_collector_v1.py ha fallado.' }

    Write-Host 'Ejecutando tests de contrato sin dependencia de pytest.'
    $fallback = @'
import importlib.util
from pathlib import Path

path = Path("tests/test_collector_contract.py")
spec = importlib.util.spec_from_file_location("test_collector_contract", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
tests = [
    getattr(module, name)
    for name in sorted(dir(module))
    if name.startswith("test_") and callable(getattr(module, name))
]
for test in tests:
    test()
print(f"{len(tests)} collector contract tests: PASS")
'@
    $fallback | python -
    if ($LASTEXITCODE -ne 0) { throw 'test_collector_contract.py ha fallado.' }

    git diff --check
    if ($LASTEXITCODE -ne 0) { throw 'git diff --check ha fallado.' }

    git add -- collector/data_collector_futbol_v1.html collector/data_collector_futbol.html collector/validate_collector_v1.py tests/test_collector_contract.py
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host 'No hay cambios nuevos del Collector para confirmar.'
    }
    else {
        git commit -m "Finalize Collector V1.1"
        if ($LASTEXITCODE -ne 0) { throw 'git commit ha fallado.' }
        git push origin main
        if ($LASTEXITCODE -ne 0) { throw 'git push ha fallado.' }
    }

    Write-Host ''
    Write-Host 'COLLECTOR-01 IMPLEMENTACION FINAL: PASS'
    git status --short
}
finally {
    Pop-Location
}
