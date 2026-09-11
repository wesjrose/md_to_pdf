@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" convert.py %*
) else (
  py -3 convert.py %*
)
if errorlevel 1 (
  echo.
  echo Conversion failed. See the message above.
  pause
)
