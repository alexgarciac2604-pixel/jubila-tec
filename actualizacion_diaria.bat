@echo off
rem Actualizacion diaria de Jubila-Tec (datos, scores, alertas, briefing)
cd /d "%~dp0"
".venv\Scripts\python.exe" "jobs\daily_update.py"
