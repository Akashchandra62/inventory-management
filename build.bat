@echo off
echo ============================================================
echo  Step 1 — Building JewelryBillingSystem.exe with PyInstaller
echo ============================================================
pyinstaller --onefile --windowed --name JewelryBillingSystem ^
  --add-data "assets;assets" ^
  --hidden-import PyQt5.sip ^
  --hidden-import PyQt5.QtPrintSupport ^
  --hidden-import openpyxl ^
  --hidden-import openpyxl.styles ^
  --hidden-import openpyxl.styles.fonts ^
  --hidden-import openpyxl.styles.fills ^
  --hidden-import openpyxl.styles.alignment ^
  --hidden-import openpyxl.styles.borders ^
  --hidden-import openpyxl.utils ^
  --hidden-import reportlab ^
  --hidden-import reportlab.pdfbase ^
  --hidden-import reportlab.pdfbase.ttfonts ^
  --hidden-import reportlab.pdfbase.pdfmetrics ^
  --hidden-import reportlab.platypus ^
  --hidden-import reportlab.lib.pagesizes ^
  --hidden-import reportlab.lib.colors ^
  --hidden-import reportlab.lib.units ^
  --hidden-import reportlab.lib.styles ^
  --hidden-import reportlab.lib.enums ^
  --collect-data reportlab main.py

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller failed. Fix errors above and try again.
    pause
    exit /b 1
)

echo.
echo Done! Exe built at: dist\JewelryBillingSystem.exe

echo.
echo ============================================================
echo  Step 2 — Building installer with Inno Setup
echo ============================================================

set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe

if "%ISCC%"=="" (
    echo Inno Setup 6 not found — skipping installer build.
    echo To build the installer, install Inno Setup 6 from:
    echo   https://jrsoftware.org/isinfo.php
) else (
    "%ISCC%" setup_installer.iss
    if errorlevel 1 (
        echo ERROR: Inno Setup compilation failed.
    ) else (
        echo.
        echo Installer ready: installer_output\JewelryBillingSystem_Setup_v1.0.0.exe
    )
)

echo.
pause
