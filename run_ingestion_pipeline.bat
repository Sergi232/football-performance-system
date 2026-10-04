@echo off
setlocal
if "%~1"=="" (echo Usage: run_ingestion_pipeline.bat ^<duckdb-path^> & exit /b 2)
.venv\Scripts\python.exe run_ingestion_pipeline.py --db "%~1"
