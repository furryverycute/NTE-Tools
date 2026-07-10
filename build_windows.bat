@echo off
setlocal
cd /d "%~dp0"

set PYTHONDONTWRITEBYTECODE=1
set PIP_DISABLE_PIP_VERSION_CHECK=1

chcp 65001 >nul 2>nul

echo ===============================================
echo NTE Tool - Folder EXE Build
echo ===============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher "py" was not found.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating virtual environment...
  py -3.11 -m venv .venv 2>nul
  if errorlevel 1 py -3 -m venv .venv
  if errorlevel 1 goto :error
) else (
  echo [1/4] Virtual environment already exists.
)

echo [2/4] Checking build requirements...
".venv\Scripts\python.exe" -m app.requirements_sync --include-build
if errorlevel 1 goto :error

echo [3/4] Building folder EXE...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean nte_tool.spec
if errorlevel 1 goto :error

echo [4/4] Done.
echo Output: dist\NTE Tool\NTE Tool.exe
pause
exit /b 0

:error
echo.
echo [ERROR] Build failed.
pause
exit /b 1
