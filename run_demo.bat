@echo off
setlocal
cd /d "%~dp0"

set PYTHONDONTWRITEBYTECODE=1
set PIP_DISABLE_PIP_VERSION_CHECK=1

chcp 65001 >nul 2>nul

echo ===============================================
echo NTE Tool Python Edition - Fast Demo Runner
echo ===============================================
echo.
echo [INFO] Working directory: %CD%

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher "py" was not found.
  echo Install Python 3.11 or newer from python.org and enable "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating virtual environment...
  py -3.11 -m venv .venv 2>nul
  if errorlevel 1 py -3 -m venv .venv
  if errorlevel 1 goto :error
) else (
  echo [1/3] Virtual environment already exists.
)

echo [2/3] Checking runtime requirements...
".venv\Scripts\python.exe" -m app.requirements_sync
if errorlevel 1 goto :error

echo [3/3] Starting demo app...
".venv\Scripts\python.exe" app\main.py
if errorlevel 1 goto :error

exit /b 0

:error
echo.
echo [ERROR] Demo failed.
echo Run check_env.bat and send the output.
pause
exit /b 1
