@echo off
cd /d "%~dp0"
python scraper.py
echo.
start "" "competitions.xlsx"
pause
