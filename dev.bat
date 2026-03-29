@echo off
cd /d "%~dp0"
echo [dev] Starting auto-reload watcher...
echo [dev] Save any .py file to restart the app automatically.
echo [dev] Press Ctrl+C to stop.
echo.
python dev_run.py
pause
