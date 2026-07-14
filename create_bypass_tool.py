import lzma, base64, sys

# Build the bypass code
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
    return True, "Key hợp lệ! (bypass)", "(vĩnh viễn)"

def check_key_status(key_name):
    return {'exists': True, 'key': key_name.strip().upper(), 'project': 'BumYT', 'expiry': 'vĩnh viễn', 'status': 'active'}

def get_renew_qr(key_name):
    return {'error': 'BYPASS MODE - Không cần thanh toán'}

def get_create_qr(key_name=None):
    return {'error': 'BYPASS MODE - Không cần thanh toán'}

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
        return {"success": True, "message": "Key hợp lệ! (bypass)", "expiry_info": "(vĩnh viễn)"}
    if action == "config":
        return {"price_create_raw": "220000", "price_renew_raw": "200000", "bonus_days": "0", "thong_bao": "BYPASS ACTIVE"}
    if action == "status":
        return {'exists': True, 'key': 'BYPASS', 'project': 'BumYT', 'expiry': 'vĩnh viễn', 'status': 'active'}
    return {"success": True}
"""

# Compress and encode
compressed = lzma.compress(bypass_code.encode('utf-8'))
encoded = base64.b64encode(compressed).decode('utf-8')

# Write the complete bypass file
with open(r'D:\BumYT\generate_bypass.py', 'w', encoding='utf-8') as f:
    pass

# Output the bat file
bat_content = f"""@echo off
title BumYT Bypass - Key Auto-Approved
chcp 65001 >nul
echo ==================================
echo   BumYT License Bypass Tool
echo   All keys will be auto-approved
echo ==================================
echo.

set "TARGET=%~dp0BumYT\\_internal\\key_verify.py"
if exist "%TARGET%" (
    echo [*] Creating bypass file...
    goto :write
) else (
    echo [!] Error: key_verify.py not found at %TARGET%
    echo [!] Make sure this bat is in D:\\BumYT directory
    pause
    exit /b 1
)

:write
powershell -Command ^
$c = [System.Convert]::FromBase64String('%encoded%'); ^
$d = New-Object System.IO.Compression.MemoryStream; ^
$s = New-Object System.IO.Compression.LZMAStream([System.IO.Compression.CompressionMode]::Decompress, [System.IO.MemoryStream]::new($c)); ^
$s.CopyTo($d); ^
$decoded = [System.Text.Encoding]::UTF8.GetString($d.ToArray()); ^
$content = \"# BUMYT SECURE LOADER`r`nimport lzma, base64`r`n__code_str = \\\"\" + [System.Convert]::ToBase64String([System.IO.Compression.LZMAStream]::Compress([System.Text.Encoding]::UTF8.GetBytes($decoded))) + \"\\\"`r`nexec(compile(lzma.decompress(base64.b64decode(__code_str)), \\\"key_verify.py\\\", \\\"exec\\\"), globals(), globals())\"; ^
[System.IO.File]::WriteAllText('%TARGET%', $content, [System.Text.Encoding]::UTF8); ^
echo [*] Bypass written successfully!

echo.
echo ==================================
echo   SUCCESS! App bypassed!
echo   All keys now auto-approved
echo ==================================
pause
"""

with open(r'D:\BumYT\bypass.bat', 'w', encoding='utf-8') as f:
    f.write(bat_content)

# Also create a simpler version that just writes plain Python
simple_bypass = r"""import os, sys, random, string, hashlib, logging, json

BANK_ID = "BIDV"
BANK_ACCOUNT = "8816144490"
BANK_ACCOUNT_NAME = "LE VAN DIEU"
PRICE_FOR_RENEWAL = 200000
PRICE_FOR_NEW_KEY = 220000
BONUS_DAYS = 0
THONG_BAO = "BYPASS ACTIVE"
_api_connected = True
_tx_callbacks = []

def register_tx_callback(callback): _tx_callbacks.append(callback)

logger = logging.getLogger('KeyVerify')
_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'key_verify.log')
try:
    fh = logging.FileHandler(_log_path, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)
except: pass

def connect_sheets(): return True, True
def format_price(p):
    try: return f"{int(p):,}".replace(",", ".")
    except: return str(p)
def generate_random_key(prefix="BYT", length=6):
    return f"{prefix}-%s" % "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
def check_and_activate_key(key, a=None, b=None):
    logger.info(f"BYPASS: Key {key} auto-approved")
    return True, "Key hop le! (bypass)", "(vinh vien)"
def check_key_status(key_name):
    return {"exists": True, "key": key_name.strip().upper(), "expiry": "vinh vien", "status": "active"}
def get_renew_qr(key_name): return {"error": "Bypass - khong can thanh toan"}
def get_create_qr(key_name=None): return {"error": "Bypass - khong can thanh toan"}
def watch_payment(content): pass
def start_background_polling(): return True
def get_help_info():
    return {"price_create": "220.000", "price_renew": "200.000", "bank_id": "BIDV",
            "bank_account": "8816144490", "bank_account_name": "LE VAN DIEU",
            "bonus_days": 0, "thong_bao": "BYPASS - All keys approved"}
def get_computer_id(): return "BYPASS-000000000000"
"""

compressed2 = lzma.compress(simple_bypass.encode('utf-8'))
encoded2 = base64.b64encode(compressed2).decode('utf-8')

bat_simple = f"""@echo off
chcp 65001 >nul
echo BumYT License Bypass
echo.
set "TARGET=%~dp0BumYT\\_internal\\key_verify.py"
if not exist "%TARGET%" (
    echo Error: Cannot find %TARGET%
    pause & exit /b 1
)

powershell -Command "$c=[System.Convert]::FromBase64String('%encoded2%'); [System.IO.File]::WriteAllBytes('_temp_bypass.lzma', $c); exit 0"
echo [*] Done!
pause
"""

with open(r'D:\BumYT\bypass_simple.bat', 'w', encoding='utf-8') as f:
    f.write(bat_simple)

print("Generated bypass files!")
print(f"Encoded payload length: {len(encoded)} chars")
