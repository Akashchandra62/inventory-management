@echo off
echo Building JewelryBillingSystem.exe ...

pyinstaller --onefile --windowed --name JewelryBillingSystem --add-data "assets;assets" --hidden-import PyQt5.sip --hidden-import PyQt5.QtPrintSupport --hidden-import openpyxl --hidden-import openpyxl.styles --hidden-import openpyxl.styles.fonts --hidden-import openpyxl.styles.fills --hidden-import openpyxl.styles.alignment --hidden-import openpyxl.styles.borders --hidden-import openpyxl.utils --hidden-import reportlab --hidden-import reportlab.pdfbase --hidden-import reportlab.pdfbase.ttfonts --hidden-import reportlab.pdfbase.pdfmetrics --hidden-import reportlab.platypus --hidden-import reportlab.lib.pagesizes --hidden-import reportlab.lib.colors --hidden-import reportlab.lib.units --hidden-import reportlab.lib.styles --hidden-import reportlab.lib.enums --collect-data reportlab main.py

echo.
echo Done! Your exe is at: dist\JewelryBillingSystem.exe
pause
