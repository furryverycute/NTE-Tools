@echo off
setlocal
cd /d "%~dp0"

set PYTHONDONTWRITEBYTECODE=1
set PIP_DISABLE_PIP_VERSION_CHECK=1

chcp 65001 >nul 2>nul

echo ===============================================
echo NTE Tool Python Edition - Onefile EXE Build
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

echo [3/4] Building onefile EXE...
set TESS_ADD_DATA=
if exist "tools\tesseract\tesseract.exe" set TESS_ADD_DATA=--add-data "tools\tesseract;tools\tesseract"
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name "NTE Tool Demo" --icon "app\assets\icon.ico" --add-data "app\assets;app\assets" %TESS_ADD_DATA% app\main.py
if errorlevel 1 goto :error

echo [4/4] Done.
echo Output: dist\NTE Tool Demo.exe
pause
exit /b 0

:error
echo.
echo [ERROR] Build failed.
pause
exit /b 1
