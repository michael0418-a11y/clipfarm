@echo off
echo ========================================
echo   ClipFarm Setup - TikTok Clip Pipeline
echo ========================================
echo.

REM Check Python
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

REM Check ffmpeg
ffmpeg -version 2>nul | findstr "version" >nul
if errorlevel 1 (
    echo [WARNING] ffmpeg not found.
    echo Install: winget install ffmpeg
    echo Or download from: https://ffmpeg.org/download.html
    echo.
)

REM Check yt-dlp
yt-dlp --version 2>nul
if errorlevel 1 (
    echo [INFO] yt-dlp not found, will install via pip...
)

REM Install Python deps
echo.
echo [*] Installing Python dependencies...
pip install -r requirements.txt

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Quick start:
echo   python clipfarm.py single https://youtube.com/watch?v=VIDEO_ID
echo.
echo Set your API key for AI features:
echo   set ANTHROPIC_API_KEY=sk-ant-...
echo.
echo Set your TikTok handle:
echo   python clipfarm.py single URL --handle @yourname
echo.
pause
