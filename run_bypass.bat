@echo off
chcp 65001 >nul
title BumYT Bypass - Network Level
cd /d "%~dp0"

:: Check admin, re-launch if needed
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Dang xin admin...
    powershell -Command "Start-Process '%~0' -Verb RunAs"
    exit /b
)

:: Run the Python bypass script
python bypass_network.py
pause
