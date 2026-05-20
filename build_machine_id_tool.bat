@echo off
echo ============================================
echo  Building Get Machine ID Tool...
echo ============================================

pyinstaller ^
    --onefile ^
    --noconsole ^
    --name "GetMachineID" ^
    get_machine_id.py

echo.
if exist "dist\GetMachineID.exe" (
    echo  SUCCESS: dist\GetMachineID.exe is ready.
    echo  Share this file with your client.
) else (
    echo  BUILD FAILED. Check errors above.
)
echo ============================================
pause
