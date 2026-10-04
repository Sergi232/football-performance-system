@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
set "FPS_DB_PATH=%CD%\data\football_performance.duckdb"
set "COLLECTOR_URL=http://127.0.0.1:8765/health"
set "DASHBOARD_URL=http://127.0.0.1:8503/_stcore/health"
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8765,8503 -State Listen -ErrorAction SilentlyContinue | Select-Object -Expand OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
timeout /t 1 /nobreak >nul
start "Football Performance Collector" /B "%PYTHON%" local_collector_service.py --db "%FPS_DB_PATH%" --port 8765
start "Football Performance Dashboard" /B "%PYTHON%" -m streamlit run app\streamlit_app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true
powershell -NoProfile -Command "$ErrorActionPreference='SilentlyContinue'; 1..30 | %% { if((Invoke-WebRequest -UseBasicParsing '%COLLECTOR_URL%').StatusCode -eq 200){exit 0}; Start-Sleep -Seconds 1 }; exit 1"
powershell -NoProfile -Command "$ErrorActionPreference='SilentlyContinue'; 1..30 | %% { if((Invoke-WebRequest -UseBasicParsing '%DASHBOARD_URL%').StatusCode -eq 200){exit 0}; Start-Sleep -Seconds 1 }; exit 1"
start "Football Performance Collector" http://127.0.0.1:8765/
endlocal
