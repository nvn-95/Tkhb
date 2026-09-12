@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [SCREAM VOLUME] Virtual environment not found. Creating .venv...
  py -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --disable-pip-version-check -q -r requirements.txt
python scream_volume_manager.py
