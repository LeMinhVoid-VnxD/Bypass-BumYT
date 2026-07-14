@echo off
chcp 65001 >nul
title BumYT Final Bypass - Network Level
cd /d "%~dp0"

:: ============================================
:: BumYT Ultimate Bypass
:: Intercept ALL API calls at network level
:: Yeu cau: Admin rights
:: ============================================

echo ============================================
echo   BumYT Ultimate Bypass - Network Level
echo   Fake API server returns success for all keys
echo ============================================
echo.

:: Check admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Can admin de chay!
    echo [!] Click Yes khi Windows hoi...
    powershell -Command "Start-Process '%~0' -Verb RunAs"
    exit /b
)
echo [OK] Admin privileges granted!
echo.

:: Paths
set "APP_DIR=%~dp0BumYT"
set "CACERT=%APP_DIR%\_internal\certifi\cacert.pem"
set "HOSTS=%windir%\System32\drivers\etc\hosts"
set "HOSTS_BAK=%TEMP%\bumyt_hosts.bak"
set "SVR_SCRIPT=%~dp0fake_server.py"
set "CERT_FILE=%TEMP%\bumyt_server.pem"
set "KEY_FILE=%TEMP%\bumyt_key.pem"

:: Step 1: Write cert files
echo [1/5] Tao SSL certificate...
set "CERT_B64=LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tDQpNSUlETnpDQ0FoK2dBd0lCQWdJVURzMDVjUHpITnRVcnJET0tCUk9WVVdUNDc2d3dEUVlKS29aSWh2Y05BUUVMDQpCUUF3SERFYU1CZ0dBMVVFQXd3UmMyTnlhWEIwTG1kdmIyZHNaUzVqYjIwd0hoY05Nall3TnpFME1ETXhPVE0yDQpXaGNOTXpZd016RXhNRE14T1RNMldqQWNNUm93R0FZRFZRUUREQkZ6WTNKcGNIUXVaMjl2WjJ4bExtTnZiVENDDQpBU0l3RFFZSktvWklodmNOQVFFQkJRQURnZ0VQQURDQ0FRb0NnZ0VCQUl0WXJvZWltbzZNM2NPcW02cm14aXNXDQppRmN6Rk0zQmp2UlBxemNNeXRWQ0FZUEd4WWJ0UWJaNXdCYmVyRVJWYTBRYjYvQ2M2YXhhNmVmV0lMRFUvUUlnDQpFTE9wek1rcjNLV3ZrUzMxaG9DL2ZHYWxCS21jWGl4TTYwM2FKekZBWFcyY3U5Qkw4YXVzRGh5MDNxeDBJcFJLDQpsYjM2OHBOTC94aHNrQ2FsWHNWbDgxVEU5Z1UzSTBtTUR0ajJxempWZDlZeGsvRVVITUNUWDU4OUFKcEIzMW02DQpWZC9vYnhqMko5ZW5rREJObmtmMWVRb2pMclB5alhDQWs2SW9WMUVNQWZyaDlLR0NnVlI4RktPNGxaYk1rL0x3DQpnOGI5VklNV2NFeHc0dW5YMmZ2aTJmbzVDVzY1a251QWFBSWU1NEJ1K3NJMyt3eUJGVkh6dlZIcS9EOG5uTWtDDQpBd0VBQWFOeE1HOHdIUVlEVlIwT0JCWUVGRUhVRnp0dlh1UDNCS0RvV3IxdjNyR3pSRW5ETUI4R0ExVWRJd1FZDQpNQmFBRkVIVUZ6dHZYdVAzQktEb1dyMXYzckd6UkVuRE1BOEdBMVVkRXdFQi93UUZNQU1CQWY4d0hBWURWUjBSDQpCQlV3RTRJUmMyTnlhWEIwTG1kdmIyZHNaUzVqYjIwd0RRWUpLb1pJaHZjTkFRRUxCUUFEZ2dFQkFEelNXd0F3DQoxZXNnSUpNZXlFMHd1UUd0em9VeCtsWElBQUJUUDZLMXpHdC9iUmdmWDJ5alRRWGRNc294RXgzUVltUkpMQlQvDQpHd1lkQ21NSHFRODJ3UDRQRmZGdjVXa0x6NzdxczcrQlpicFJRUHRtTmNmTHVCQnFXNVBwKzN6WFhYK2YvZ1JTDQpQUmJpL1J0NkxwT253dTc4NVF5eWNUcFNCd3pVRnBxVXlublpCTWRSZmhVaTU4OW84TnRNV2EwWjE3Uk5mWk5uDQpocXBZQnNNeEk0L0ZtN2ExV05VcjZjbkNpR3FMSjlkcmRtcWhYeFBhejcxeU1sUWZMSWs4eDN1SllrUTZJWU5IDQpWVjU3Vkg2VFhYaU9iaUxTTXJTQnR5eFpIRmovNHFDcE9FU2puMFkvNG4zTy9zU0hkY21wNlk1VVpPc3orMWR5DQppeEgxMjY0RDUraDVlQ09RDQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0t"

set "KEY_B64=LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tDQpNSUlFdlFJQkFEQU5CZ2txaGtpRzl3MEJBUUVGQUFTQ0JLY3dnZ1NqQWdFQUFvSUJBUUNMV0s2SG9wcU9qTjNEDQpxcHVxNXNZckZvaFhNeFROd1k3MFQ2czNETXJWUWdHRHhzV0c3VUcyZWNBVzNxeEVWV3RFRyt2d25PbXNXdW5uDQoxaUN3MVAwQ0lCQ3pxY3pKSzl5bHI1RXQ5WWFBdjN4bXBRU3BuRjRzVE90TjJpY3hRRjF0bkx2UVMvR3JyQTRjDQp0TjZzZENLVVNwVzkrdktUUy84WWJKQW1wVjdGWmZOVXhQWUZOeU5KakE3WTlxczQxWGZXTVpQeEZCekFrMStmDQpQUUNhUWQ5WnVsWGY2RzhZOWlmWHA1QXdUWjVIOVhrS0l5Nno4bzF3Z0pPaUtGZFJEQUg2NGZTaGdvRlVmQlNqDQp1SldXekpQeThJUEcvVlNERm5CTWNPTHAxOW43NHRuNk9RbHV1Wko3Z0dnQ0h1ZUFidnJDTi9zTWdSVlI4NzFSDQo2dncvSjV6SkFnTUJBQUVDZ2dFQU1RZFRhVTlTR0VRQ0p6MVpKa21xZ2pDY2Fpb0Q4TjFnd2g5aCs2MlpsRzEwDQpBUHlvTlhBM1JkQVN3VGs1M1pVOGQ2dG5XYktzR1VPbnR6WEZMTkxUN3JKL2plZDVzWEtvWVBla0drcWdONTZvDQpVNmxPT2F0V0N6cEpOSXhFYS9UY3FwdVNEWmtiQUM4Nmkra3J5L3ZVeXQ1dlQzZ0RiOFkyakU1dWJkcVR2Tm84DQpSYmprOHAvLzRCVXdaTnE3U2dVU1R2NlJYQjJVQjNQWElSTGc2ZkxINDF3S05rM3NLbHdWcTJpeTQvdDZacjV3DQo5cHJzY3J4T24vcFB1cFp2RVhTT1NzQ2FrU2VzMzBHdW51dlhJUzFuak5neDhsLythLzNIRC9zdnVBQ1oyV28xDQpHbmE0Ull1aHd5QU1YenpZZVNEQURCdFlRQ2pWYmNhUmY5VjlsVFBSZlFLQmdRRERjTXdIcnVWSi9tVGtuTXhPDQpvMkUxRENzRE9qanlobmRLQzMyVGpBa0VHNFBFOTBnb2Nxd1ZZaXVOeHJhMFNhSmphakRJYks2SG42TlQ3ait5DQpicVZERkNlREdWNERrZUZpL2ZNRFV0ekhJc29tRFNjM1BXUElBNnV3eCsyM09DNWhybWkybnBlcVNENXo0Y2JDDQpUQkRwWG53djhSL0pLZ2taeEJYbU9semJMd0tCZ1FDMmhqOXhkT1VrM1JrODRzVm85RUxHblBFbFM1YjJ5cEhlDQpuTUJZL0RJbkZEUkMrQm5JR3prMU9ZcDErZXdFY210ZytTYi8vL1hueFZSOHNySmtoRGR1bGhpUDlDOGdhbXBRDQpId3RlYUc4YjlNY3VKZENOOVEvcHh3SUVBMHEybnNITUw2bENObkFqbkFkbGVXRXNwMzRFZFJlNWh1Yk5sanlhDQpBSHQ5Rk9LcGh3S0JnQzdFMkY1aVVRWlM5VXZyNWN4UHRweGVMQkRhcHZRS2o1Tk5pcUI3VzFEN1VKNGEyczZyDQpHbGtIcEFxS2FnQmN1cHAxdC9UT1pUbVpUeGx2b3hpTTk4bEVrbXdCN3dpRnFWenFEblJXS1BVU2N6T0Y1RU9JDQowazd6NmVzay9OTGlnOTdtUUxLcTR2cGh6V2dudUV1WXJsZGFQL2V0Q1FFM3FQUGNnNjBUZkZNTEFvR0FSTjhwDQpKMDE5ZlVoMFVuWWJHVHc1eWluRUVGZVNjak1Ea2FWQ0t4R1dkd3Azb2VGdUVRUzh0R211NWs5VWtHVUFRWW9oDQovaXorQStPQXVzRE84WUMyVGVNVEI1YVRCYjlCdUZQT2ZXUVlzTXJQTVltUlJVOTRIclU1L0h1bGdIMHRFVGZXDQp2U1kvY0NCYTVoNUQzWTZoelZyRmhmcnlNaGNEYlBUTG8rbnlrUmNDZ1lFQXRjOVpBZU9WZGd0VlF6SExudzgzDQowYm95RmFSb0FwWGhpYUxlVHNCbEFLajJKRVIySDVhcjYxK1Rhb2dtS0s4NlVsS2ZkUVVFaDR3MytBQ3dIWkN5DQpHYlJHTnZxbDV6VEVGd3lZcFJab3lmemNiYlZ3UVZNeUYwVXNEUFprOUVHS3lobUk5YlVnRjJDcGxzZUQ1UDlyDQpsN25GUU1YbVZiRnN1S0M3cWRMRDA4UT0NCi0tLS0tRU5EIFBSSVZBVEUgS0VZLS0tLS0="

echo %CERT_B64% | powershell -Command "$input | ForEach-Object { [System.IO.File]::WriteAllBytes('%CERT_FILE%', [System.Convert]::FromBase64String($_)) }" >nul
echo %KEY_B64% | powershell -Command "$input | ForEach-Object { [System.IO.File]::WriteAllBytes('%KEY_FILE%', [System.Convert]::FromBase64String($_)) }" >nul
if not exist "%CERT_FILE%" (
    echo [!] Loi tao cert file!
    pause & exit /b
)

:: Step 2: Add cert to certifi
echo [2/5] Them cert vao certifi...
copy /y "%CACERT%" "%CACERT%.bak" >nul 2>&1
type "%CERT_FILE%" >> "%CACERT%"

:: Step 3: Setup port forwarding (443 -> 8443)
echo [3/5] Cai dat port forwarding...
netsh interface portproxy delete v4tov4 listenport=443 listenaddress=127.0.0.1 >nul 2>&1
netsh interface portproxy add v4tov4 listenport=443 listenaddress=127.0.0.1 connectport=8443 connectaddress=127.0.0.1
if %errorlevel% neq 0 (
    echo [!] Loi port forwarding! Co the thieu quyen hoac port 443 dang dung.
    echo [!] Tiep tuc thu...
)

:: Step 4: Modify hosts
echo [4/5] Them hosts entry...
copy /y "%HOSTS%" "%HOSTS_BAK%" >nul 2>&1
findstr /v /i "script.google.com" "%HOSTS%" > "%TEMP%\hosts_new.tmp"
echo 127.0.0.1 script.google.com >> "%TEMP%\hosts_new.tmp"
copy /y "%TEMP%\hosts_new.tmp" "%HOSTS%" >nul

:: Step 5: Start server and launch app
echo [5/5] Khoi dong fake API server...
echo.
start "BumYT Fake API" /B python "%~dp0fake_server.py" 8443 "%CERT_FILE%" "%KEY_FILE%"
timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo   HOAN TAT! Dang mo BumYT.exe...
echo   NHAP KEY BAT KY DE DUNG!
echo   Dong cua so nay de CLEANUP.
echo ============================================
echo.
start "" "%APP_DIR%\BumYT.exe"
pause

:: ===== CLEANUP =====
cls
echo [*] Dang cleanup...
taskkill /f /im python.exe >nul 2>&1
timeout /t 2 /nobreak >nul
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
:: Delete temp files
if exist "%CERT_FILE%" del "%CERT_FILE%" 2>nul
if exist "%KEY_FILE%" del "%KEY_FILE%" 2>nul
if exist "%TEMP%\hosts_new.tmp" del "%TEMP%\hosts_new.tmp" 2>nul
echo [*] CLEANUP HOAN TAT!
pause
