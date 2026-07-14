import base64

# Create a test key_verify.py that creates a marker file when imported
# This will tell us if the exe actually imports key_verify.py
test_code = '''# -*- coding: utf-8 -*-
import os
# Write marker file to prove this module was imported
marker = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "BYPASS_LOADED.txt")
try:
    with open(marker, "w") as f:
        f.write("key_verify.py was loaded at runtime!")
except:
    pass

# Now define all functions needed
import sys, random, string, hashlib, logging
from datetime import datetime

BANK_ID = "BIDV"
BANK_ACCOUNT = "8816144490"
BANK_ACCOUNT_NAME = "LE VAN DIEU"
PRICE_FOR_RENEWAL = 200000
PRICE_FOR_NEW_KEY = 220000
BONUS_DAYS = 30
THONG_BAO = "BYPASS ACTIVE"
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
    logger.info("BYPASS: connect_sheets OK")
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
    logger.info("BYPASS: Key " + str(key) + " auto-approved")
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
    return {"price_create": "220.000", "price_renew": "200.000", "bank_id": "BIDV", "bank_account": "8816144490", "bank_account_name": "LE VAN DIEU", "bonus_days": 30, "thong_bao": "BYPASS ACTIVE"}
def _call_api(action, params=None, method="GET", timeout=None):
    if action == "verify":
        return {"success": True, "message": "Key hop le! (bypass)", "expiry_info": "(vinh vien)"}
    if action == "config":
        return {"price_create_raw": "220000", "price_renew_raw": "200000", "bonus_days": "0", "thong_bao": "BYPASS ACTIVE"}
    if action == "status":
        return {"exists": True, "key": "BYPASS", "project": "BumYT", "expiry": "vinh vien", "status": "active"}
    return {"success": True}
'''

b64 = base64.b64encode(test_code.encode('utf-8')).decode('utf-8')

bat = []
bat.append('@echo off')
bat.append('chcp 65001 >nul')
bat.append('title BumYT Bypass - TEST')
bat.append('echo [*] Dang ghi test key_verify.py...')
bat.append('')
bat.append('set "T=%~dp0BumYT\\_internal\\key_verify.py"')
bat.append('if exist "%T%" (')
bat.append('    powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.IO.File]::WriteAllBytes(\'' + '%T%' + '\', [System.Convert]::FromBase64String(\'' + b64 + '\'))"')
bat.append('    echo [*] Done!')
bat.append('    echo [*] Chay BumYT.exe, neu file BYPASS_LOADED.txt xuat hien = module dc load')
bat.append(') else (')
bat.append('    echo [*] Khong tim thay %T%')
bat.append(')')
bat.append('pause')

with open(r'D:\BumYT\bypass_test.bat', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(bat))

print("Done! Run bypass_test.bat then BumYT.exe, check for BYPASS_LOADED.txt")
