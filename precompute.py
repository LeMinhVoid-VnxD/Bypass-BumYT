import lzma, base64, os

# The bypass Python code
bypass_code = r"""# -*- coding: utf-8 -*-
# BUMYT BYPASS - Auto-approved
import os, sys, platform, uuid, re, string, random, json, threading, logging, time, hashlib, subprocess
from datetime import datetime, timedelta

API_URL = "https://script.google.com/macros/s/AKfycbxB6hfXAWaZfvth16IC3UUp5hZes1Qbqv5JnEcKTgRKTR5owbnC7nNWZDMo4DxTOXPN/exec"
API_TIMEOUT = 30
BANK_ID = "BIDV"
BANK_ACCOUNT = "8816144490"
BANK_ACCOUNT_NAME = "LE VAN DIEU"
PRICE_FOR_RENEWAL = 200000
PRICE_FOR_NEW_KEY = 220000
BONUS_DAYS = 0
THONG_BAO = ""
_api_connected = False
_tx_callbacks = []

def register_tx_callback(callback):
    _tx_callbacks.append(callback)

logger = logging.getLogger('KeyVerify')
logger.setLevel(logging.INFO)
_log_path = os.path.join(
    os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)
    else os.path.dirname(os.path.abspath(__file__)),
    'key_verify.log'
)
try:
    _fh = logging.FileHandler(_log_path, encoding='utf-8')
    _fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(_fh)
except:
    pass

def connect_sheets():
    global PRICE_FOR_RENEWAL, PRICE_FOR_NEW_KEY, BONUS_DAYS, THONG_BAO, BANK_ID, BANK_ACCOUNT, BANK_ACCOUNT_NAME, _api_connected
    logger.info("BYPASS: connect_sheets returning True")
    _api_connected = True
    return True, True

def get_computer_id():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography', 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        value, _ = winreg.QueryValueEx(key, 'MachineGuid')
        winreg.CloseKey(key)
        return f"BYPASS-{hashlib.sha256(value.encode()).hexdigest()[:12]}"
    except:
        return "BYPASS-000000000000"

def format_price(price):
    try:
        return f"{int(price):,}".replace(",", ".")
    except:
        return str(price)

def generate_random_key(prefix="BYT", length=6):
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=length))
    return f"{prefix}-{random_part}"

def check_and_activate_key(key, p_sheet_keys=None, p_data_keys=None):
    logger.info(f"BYPASS: check_and_activate_key({key}) returning True")
    return True, "Key hop le! (bypass)", "(vinh vien)"

def check_key_status(key_name):
    return {'exists': True, 'key': key_name.strip().upper(), 'project': 'BumYT', 'expiry': 'vinh vien', 'status': 'active'}

def get_renew_qr(key_name):
    return {'error': 'BYPASS MODE - Khong can thanh toan'}

def get_create_qr(key_name=None):
    return {'error': 'BYPASS MODE - Khong can thanh toan'}

def watch_payment(content):
    pass

def start_background_polling():
    return True

def get_help_info():
    return {
        'price_create': format_price(PRICE_FOR_NEW_KEY),
        'price_renew': format_price(PRICE_FOR_RENEWAL),
        'bank_id': BANK_ID,
        'bank_account': BANK_ACCOUNT,
        'bank_account_name': BANK_ACCOUNT_NAME,
        'bonus_days': BONUS_DAYS,
        'thong_bao': 'BYPASS ACTIVE - All keys approved',
    }

def _call_api(action, params=None, method="GET", timeout=None):
    if action == "verify":
        return {"success": True, "message": "Key hop le! (bypass)", "expiry_info": "(vinh vien)"}
    if action == "config":
        return {"price_create_raw": "220000", "price_renew_raw": "200000", "bonus_days": "0", "thong_bao": "BYPASS ACTIVE"}
    if action == "status":
        return {'exists': True, 'key': 'BYPASS', 'project': 'BumYT', 'expiry': 'vinh vien', 'status': 'active'}
    return {"success": True}
"""

# Compress and encode
compressed = lzma.compress(bypass_code.encode('utf-8'))
encoded = base64.b64encode(compressed).decode('utf-8')

# Generate the complete file content
new_file_content = f"""# BUMYT SECURE LOADER
import lzma, base64
__code_str = "{encoded}"
exec(compile(lzma.decompress(base64.b64decode(__code_str)), "key_verify.py", "exec"), globals(), globals())
"""

# Save the precomputed file
out_path = r'D:\BumYT\bypass_precomputed.py'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(new_file_content)
print(f"Saved precomputed bypass to {out_path}")
print(f"Encoded payload length: {len(encoded)} chars")

# Also create a .bat version that has this embedded
bat_content = f"""@echo off
chcp 65001 >nul
title BumYT License Bypass Tool
echo ============================================
echo   BumYT License Bypass Tool
echo   By pass key - auto approve all keys
echo ============================================
echo.

set "TARGET=%~dp0BumYT\\_internal\\key_verify.py"

if not exist "%TARGET%" (
    echo ERROR: Khong tim thay %TARGET%
    pause
    exit /b 1
)

echo [*] Dang ghi bypass vao key_verify.py...

powershell -NoProfile -ExecutionPolicy Bypass -Command "
$encoded = '{encoded}'
$content = @'
# BUMYT SECURE LOADER
import lzma, base64
__code_str = \"$encoded\"
exec(compile(lzma.decompress(base64.b64decode(__code_str)), \"key_verify.py\", \"exec\"), globals(), globals())
'@
[System.IO.File]::WriteAllText('%TARGET%', $content, [System.Text.Encoding]::UTF8)
Write-Host '[OK] Done!'
"

if %errorlevel% equ 0 (
    echo [*] THANH CONG! File key_verify.py da duoc ghi de.
    echo [*] MOI KEY DEU DUOC AUTO-APPROVE!
) else (
    echo [*] THAT BAI!
)
pause
"""

bat_path = r'D:\BumYT\bypass.bat'
with open(bat_path, 'w', encoding='utf-8') as f:
    f.write(bat_content)
print(f"Saved batch file to {bat_path}")
