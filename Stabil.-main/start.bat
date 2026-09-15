@echo off
title STABIL - Surgical Precision Tracking
echo ========================================================
echo          STABIL - 1-Click Launcher
echo ========================================================
echo.

cd /d "%~dp0"

:: Check for virtual environment
if exist "venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [*] Running with system Python...
)

:: Run launcher
python run.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] An error occurred. Press any key to exit.
    pause >nul
)
