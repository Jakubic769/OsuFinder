@echo off
setlocal
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Nie udalo sie zainstalowac zaleznosci.
  pause
  exit /b 1
)
python osu_finder.py
if errorlevel 1 pause
