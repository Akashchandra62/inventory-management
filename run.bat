@echo off
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo Error launching app. Run fix_and_run.bat to repair.
    pause
)
