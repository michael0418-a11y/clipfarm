@echo off
title Lead Scraper
echo.
echo  Starting Lead Scraper...
echo  Your browser will open automatically.
echo  Keep this window open while using the app.
echo  Press Ctrl+C to stop.
echo.
cd /d "%~dp0"
python app.py
pause
