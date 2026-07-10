@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul 2>nul

echo ===============================================
echo NTE Tool - Environment Check
echo ===============================================
echo.

echo [Working directory]
echo %CD%
echo.

echo [Python launcher]
where py
py -0p
py -3 --version
echo.

echo [Virtual environment]
if exist ".venv\Scripts\python.exe" (
  echo .venv found
  ".venv\Scripts\python.exe" --version
  ".venv\Scripts\python.exe" -m pip --version
  ".venv\Scripts\python.exe" -c "import PySide6; print('PySide6', PySide6.__version__)"
  ".venv\Scripts\python.exe" -c "import sys; print(sys.executable)"
) else (
  echo .venv not found
)
echo.

echo [Tesseract OCR]
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "from app.scanner.tesseract_locator import locate_tesseract; loc=locate_tesseract(require_languages=True); print('tesseract:', loc.exe); print('tessdata:', loc.tessdata_dir)"
) else (
  echo skipped: .venv not found
)
echo.
pause
