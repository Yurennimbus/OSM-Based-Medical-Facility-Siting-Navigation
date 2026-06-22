@echo off
cd /d "%~dp0"

echo ================================================
echo   WebGIS - Medical Facility Site Selection
echo ================================================
echo.

REM Kill any existing process on port 8000
echo [1/3] Checking port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo.
echo [2/3] Checking data...
E:\Miniconda3\python.exe init.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error: init.py failed. Check config.yaml and data.
    pause
    exit /b 1
)

echo.
echo [3/3] Starting server...
echo   URL: http://localhost:8000
echo   Press Ctrl+C to stop
echo ================================================
E:\Miniconda3\python.exe run.py
pause
