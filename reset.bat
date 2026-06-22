@echo off
cd /d "%~dp0"

echo ================================================
echo   WebGIS - System Reset to Initial State
echo ================================================
echo.

echo [1/3] Terminating server process on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul
echo   Done.

echo.
echo [2/3] Removing database...
if exist "backend\webgis.db" (
    del /f /q "backend\webgis.db" >nul 2>&1
    echo   backend\webgis.db deleted.
) else (
    echo   No database file found.
)

echo.
echo [3/3] Cleaning imported city data...
for /d %%d in ("Data\*") do (
    if /i not "%%~nxd"=="jinan" (
        rmdir /s /q "%%d" >nul 2>&1
        echo   Removed: %%d
    )
)
echo   Original jinan data preserved.

echo.
echo ================================================
echo   Reset complete. System restored to initial state.
echo   Run start.bat to re-initialize and start.
echo ================================================
pause
