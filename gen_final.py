import base64

# The absolute simplest bypass - just define all the functions
# No exec, no lzma, no base64, no obfuscation at all
bypass = r'''# -*- coding: utf-8 -*-
# BUMYT BYPASS - Plain & Simple
import os, sys, random, string, hashlib, logging
from datetime import datetime

BANK_ID = "BIDV"
BANK_ACCOUNT = "8816144490"
BANK_ACCOUNT_NAME = "LE VAN DIEU"
PRICE_FOR_RENEWAL = 200000
PRICE_FOR_NEW_KEY = 220000
BONUS_DAYS = 30
THONG_BAO = "BY PASS ACTIVE - Da remove key check"
_api_connected = True
_tx_callbacks = []

def register_tx_callback(cb):
    _tx_callbacks.append(cb)

logger = logging.getLogger("KeyVerify")
logger.setLevel(logging.INFO)
try:
    log_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    fh = logging.FileHandler(os.path.join(log_dir, "..", "key_verify.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)
except:
    pass

def connect_sheets():
    logger.info("BY PASS: connect_sheets OK")
    return True, True

def get_computer_id():
    return "BYPASS-" + hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:12]

def format_price(p):
    try:
        return f"{int(p):,}".replace(",", ".")
    except:
        return str(p)

def generate_random_key(prefix="BYT", length=6):
    return prefix + "-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def check_and_activate_key(key, a=None, b=None):
    logger.info("BY PASS: Key " + str(key) + " auto-approved")
    return True, "Key hop le! (bypass)", "(vinh vien)"

def check_key_status(key_name):
    k = key_name.strip().upper() if key_name else ""
    return {"exists": True, "key": k, "project": "BumYT", "expiry": "vinh vien", "status": "active"}

def get_renew_qr(key_name):
    return {"error": "Bypass - khong can thanh toan"}

def get_create_qr(key_name=None):
    return {"error": "Bypass - khong can thanh toan"}

def watch_payment(c):
    pass

def start_background_polling():
    return True

def get_help_info():
    return {
        "price_create": "220.000",
        "price_renew": "200.000",
        "bank_id": "BIDV",
        "bank_account": "8816144490",
        "bank_account_name": "LE VAN DIEU",
        "bonus_days": 30,
        "thong_bao": "BY PASS ACTIVE - All keys approved",
    }

def _call_api(action, params=None, method="GET", timeout=None):
    if action == "verify":
        return {"success": True, "message": "Key hop le! (bypass)", "expiry_info": "(vinh vien)"}
    if action == "config":
        return {"price_create_raw": "220000", "price_renew_raw": "200000", "bonus_days": "0", "thong_bao": "BY PASS ACTIVE"}
    if action == "status":
        return {"exists": True, "key": "BYPASS", "project": "BumYT", "expiry": "vinh vien", "status": "active"}
    return {"success": True}
'''

b64 = base64.b64encode(bypass.encode('utf-8')).decode('utf-8')

bat = f"""@echo off
chcp 65001 >nul
title BumYT Bypass FINAL
echo ============================================
echo   BumYT Bypass FINAL
echo   Remove obfuscation, remove key check
echo ============================================
echo.

set "T=%~dp0BumYT\\_internal\\key_verify.py"
if not exist "%T%" (
    echo ERROR: Khong tim thay %T%
    pause & exit /b 1
)

echo [*] Ghi bypass...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.IO.File]::WriteAllBytes('%T%', [System.Convert]::FromBase64String('%b64%'))"
if %errorlevel% equ 0 (
    echo [*] THANH CONG!
    echo [*] KEY NHAP BAT KY DEU DUNG DUOC
) else (
    echo [*] THAT BAI!
)
pause
"""

with open(r'D:\BumYT\bypass_final.bat', 'w', encoding='utf-8') as f:
    f.write(bat)

print("Done! Run bypass_final.bat then start BumYT.exe")
