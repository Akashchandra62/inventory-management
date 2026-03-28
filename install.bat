@echo off
title Jewelry Billing System - Setup
echo ============================================
echo   JEWELRY BILLING SYSTEM - SETUP
echo ============================================
echo.

REM Check Python version
python --version 2>&1 | findstr /i "3.10 3.11 3.12" >nul
if errorlevel 1 (
    echo WARNING: Python 3.10, 3.11 or 3.12 is recommended.
    echo Your version:
    python --version
    echo.
    echo If you see DLL errors, please install Python 3.11 from:
    echo https://www.python.org/downloads/release/python-3119/
    echo.
)

echo Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

echo Removing old PyQt6...
pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip -y >nul 2>&1

echo Installing PyQt6 6.4.2 (stable, Windows-compatible)...
pip install PyQt6==6.4.2 PyQt6-Qt6==6.4.2 PyQt6-sip==13.4.0
if errorlevel 1 (
    echo Trying PyQt6 6.5.3...
    pip install PyQt6==6.5.3 PyQt6-Qt6==6.5.3 PyQt6-sip==13.5.2
)

echo Installing other packages...
pip install reportlab

echo.
echo ============================================
echo   Installation complete!
echo   Run: python main.py
echo   Or double-click: run.bat
echo ============================================
pause
