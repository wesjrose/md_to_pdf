@echo off
setlocal
cd /d "%~dp0"

py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium

echo.
echo Setup complete. Edit config.yaml, then run run.bat or bind it to a G915 key.
pause
