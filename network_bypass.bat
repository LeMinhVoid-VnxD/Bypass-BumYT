@echo off
chcp 65001 >nul
title BumYT Ultimate Bypass - Network Interception
cd /d "%~dp0"

echo ============================================
echo   BumYT Ultimate Bypass
echo   Intercept API calls at network level
echo   Yeu cau admin de chay
echo ============================================
echo.

:: Request admin elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Dang xin admin...
    powershell -Command "Start-Process '%~0' -Verb RunAs"
    exit /b
)

echo [OK] Admin!

set "APP_DIR=%~dp0BumYT"
set "CERT_FILE=%~dp0server_cert.pem"
set "KEY_FILE=%~dp0server_key.pem"
set "CACERT=%APP_DIR%\_internal\certifi\cacert.pem"
set "SERVER_SCRIPT=%~dp0fake_server.py"
set "HOSTS=%windir%\System32\drivers\etc\hosts"
set "HOSTS_BAK=%TEMP%\hosts_bumyt.bak"

:: Check cert files
if not exist "%CERT_FILE%" (
    echo [!] Thieu server_cert.pem
    echo [!] Copy 2 file server_cert.pem + server_key.pem vao cung thu muc
    pause & exit /b
)

:: Backup certifi
echo [1/4] Backup cacert.pem...
copy /y "%CACERT%" "%CACERT%.bak" >nul

:: Add our cert to certifi
echo [2/4] Them cert vao certifi...
copy /y "%CERT_FILE%" "%TEMP%\bumyt_ca.pem" >nul
type "%TEMP%\bumyt_ca.pem" >> "%CACERT%"

:: Setup port forwarding and hosts
echo [3/4] Cai dat port forwarding + hosts...
netsh interface portproxy delete v4tov4 listenport=443 listenaddress=127.0.0.1 >nul 2>&1
netsh interface portproxy add v4tov4 listenport=443 listenaddress=127.0.0.1 connectport=8443 connectaddress=127.0.0.1

copy /y "%HOSTS%" "%HOSTS_BAK%" >nul 2>&1
findstr /v /i "script.google.com" "%HOSTS%" > "%TEMP%\hosts_new.tmp"
echo 127.0.0.1 script.google.com >> "%TEMP%\hosts_new.tmp"
copy /y "%TEMP%\hosts_new.tmp" "%HOSTS%" >nul

:: Start server
echo [4/4] Khoi dong fake API server...
echo.
start "BumYT Fake API" /B python "%~dp0fake_server.py" 8443 "%CERT_FILE%" "%KEY_FILE%"
timeout /t 3 /nobreak >nul

:: Launch app
echo [*] Mo BumYT.exe...
echo [*] Nhap key BAT KY de dung!
echo [*] Dong cua so nay de stop va cleanup.
echo.
start "" "%APP_DIR%\BumYT.exe"
pause

:: CLEANUP
echo.
echo [*] Don dep...
taskkill /f /im python.exe >nul 2>&1
timeout /t 1 /nobreak >nul
netsh interface portproxy delete v4tov4 listenport=443 listenaddress=127.0.0.1 >nul 2>&1
:: Restore hosts
if exist "%HOSTS_BAK%" (
    copy /y "%HOSTS_BAK%" "%HOSTS%" >nul
    del "%HOSTS_BAK%" 2>nul
)
:: Restore certifi
if exist "%CACERT%.bak" (
    copy /y "%CACERT%.bak" "%CACERT%" >nul
    del "%CACERT%.bak" 2>nul
)
echo [*] Cleanup hoan tat!
pause
