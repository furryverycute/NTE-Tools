@echo off
setlocal
cd /d "%~dp0"

set PYTHONDONTWRITEBYTECODE=1
set PIP_DISABLE_PIP_VERSION_CHECK=1

chcp 65001 >nul 2>nul

echo ===============================================
echo NTE Tool Python Edition - Release Assets
echo ===============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher "py" was not found.
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

echo [2/3] Checking release build requirements...
".venv\Scripts\python.exe" -m app.requirements_sync --include-build
if errorlevel 1 goto :error

echo [3/3] Building release assets...
".venv\Scripts\python.exe" tools\build_release_assets.py
if errorlevel 1 goto :error

echo.
echo [OK] Release files are in the release folder.
pause
exit /b 0

:error
echo.
echo [ERROR] Release build failed.
pause
exit /b 1
