@echo off
title Jewelry Billing System - Launcher
echo ============================================
echo   Jewelry Billing System
echo   Checking environment...
echo ============================================

REM ── Check Python is installed ────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10 or 3.11 from https://python.org
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo Python found. OK.

REM ── Uninstall any broken PyQt6 versions first ────────────
echo.
echo Step 1: Removing any existing PyQt6 installation...
pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip PyQt6-tools -y >nul 2>&1
echo Done.

REM ── Install pinned compatible versions ───────────────────
echo.
echo Step 2: Installing compatible PyQt6 (this may take a minute)...
pip install "PyQt6==6.4.2" "PyQt6-Qt6==6.4.2" "PyQt6-sip==13.4.0"
if errorlevel 1 (
    echo.
    echo FAILED to install PyQt6. Trying alternative version...
    pip install "PyQt6==6.5.3" "PyQt6-Qt6==6.5.3" "PyQt6-sip==13.5.2"
    if errorlevel 1 (
        echo ERROR: Could not install PyQt6. Check your internet connection.
        pause
        exit /b 1
    )
)
echo PyQt6 installed. OK.

REM ── Install other requirements ───────────────────────────
echo.
echo Step 3: Installing other dependencies...
pip install reportlab >nul 2>&1
echo Done.

REM ── Launch the application ───────────────────────────────
echo.
echo Step 4: Launching Jewelry Billing System...
echo.
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    echo Check C:\JewelryBillingSystem\logs\app.log for details.
    pause
)
