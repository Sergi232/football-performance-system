@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
start "Football Performance Collector" /B "%PYTHON%" local_collector_service.py --db data\football_performance.duckdb --port 8765
timeout /t 2 /nobreak >nul
start "Football Performance Collector" http://127.0.0.1:8765/
endlocal
