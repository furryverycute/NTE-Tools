@echo off
setlocal
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
set PIP_DISABLE_PIP_VERSION_CHECK=1
chcp 65001 >nul 2>nul

echo ===============================================
echo NTE Tool - One-time setup
echo ===============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher "py" was not found.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Creating virtual environment...
  py -3.11 -m venv .venv 2>nul
  if errorlevel 1 py -3 -m venv .venv
  if errorlevel 1 goto :error
) else (
  echo [1/5] Virtual environment already exists.
)

echo [2/5] Checking app requirements...
".venv\Scripts\python.exe" -m app.requirements_sync
if errorlevel 1 goto :error

echo [3/5] Checking portable Tesseract OCR...
".venv\Scripts\python.exe" -c "from app.scanner.tesseract_locator import locate_tesseract; loc=locate_tesseract(require_languages=True); print('[OK] Found Tesseract:', loc.exe)" >nul 2>nul
if errorlevel 1 (
  if "%~1"=="" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "tools\setup_tesseract_portable.ps1"
  ) else (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "tools\setup_tesseract_portable.ps1" -SourceDir "%~1"
  )
  if errorlevel 1 goto :tess_error
)

echo [4/5] Downloading controller runtime installer...
".venv\Scripts\python.exe" -m app.scanner.runtime_setup --download-only

echo [5/5] Verifying scanner runtime...
".venv\Scripts\python.exe" -c "from app.scanner.tesseract_locator import locate_tesseract; loc=locate_tesseract(require_languages=True); print('[OK] Tesseract:', loc.exe); print('[OK] tessdata:', loc.tessdata_dir)"
if errorlevel 1 goto :tess_error

echo.
echo [OK] Setup complete. vgamepad may have opened the ViGEmBus driver installer; finish it if Windows asks.
pause
exit /b 0

:tess_error
echo.
echo [ERROR] Portable Tesseract setup failed.
echo Put Tesseract files into tools\tesseract\ or run:
echo setup.bat "C:\Program Files\Tesseract-OCR"
pause
exit /b 1

:error
echo.
echo [ERROR] Setup failed.
pause
exit /b 1
