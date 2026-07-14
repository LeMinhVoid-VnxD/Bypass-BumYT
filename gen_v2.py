import lzma, base64

bypass_code = r"""# -*- coding: utf-8 -*-
import os, sys, platform, uuid, re, string, random, json, threading, logging, time, hashlib, subprocess
from datetime import datetime, timedelta

# ============ MONKEY-PATCH HTTP LAYER ============
# Intercept ALL HTTP requests to the license API
API_URL = "https://script.google.com/macros/s/AKfycbxB6hfXAWaZfvth16IC3UUp5hZes1Qbqv5JnEcKTgRKTR5owbnC7nNWZDMo4DxTOXPN/exec"

class FakeResponse:
    def __init__(self, data):
        self._data = data
    def json(self):
        return self._data
    def raise_for_status(self):
        pass
    @property
    def status_code(self):
        return 200
    def read(self):
        return json.dumps(self._data).encode('utf-8')
    def __enter__(self):
        return self
    def __exit__(self, *a):
        pass

# Patch requests
try:
    import requests
    _original_get = requests.get
    _original_post = requests.post
    def _patched_get(url, **kw):
        if API_URL in url:
            return FakeResponse({"success": True, "message": "Key hop le! (bypass)", "expiry_info": "(vinh vien)",
                "price_create_raw": "220000", "price_renew_raw": "200000", "bonus_days": "0",
                "thong_bao": "BYPASS ACTIVE", "exists": True, "key": "BYPASS", "project": "BumYT", "expiry": "vinh vien", "status": "active"})
        return _original_get(url, **kw)
    def _patched_post(url, **kw):
        if API_URL in url:
            return FakeResponse({"success": True, "message": "Key hop le! (bypass)", "expiry_info": "(vinh vien)"})
        return _original_post(url, **kw)
    requests.get = _patched_get
    requests.post = _patched_post
except ImportError:
    pass

# Patch urllib
try:
    import urllib.request
    _original_urlopen = urllib.request.urlopen
    def _patched_urlopen(req, **kw):
        url = req if isinstance(req, str) else req.full_url if hasattr(req, 'full_url') else str(req)
        if API_URL in str(url):
            return FakeResponse({"success": True})
        return _original_urlopen(req, **kw)
    urllib.request.urlopen = _patched_urlopen
except:
    pass

# ============ STANDARD KEY_VERIFY FUNCTIONS ============
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
_log_path = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__)), 'key_verify.log')
try:
    _fh = logging.FileHandler(_log_path, encoding='utf-8')
    _fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(_fh)
except:
    pass

def connect_sheets():
    global PRICE_FOR_RENEWAL, PRICE_FOR_NEW_KEY, BONUS_DAYS, THONG_BAO, BANK_ID, BANK_ACCOUNT, BANK_ACCOUNT_NAME, _api_connected
    logger.info("BYPASS: connect_sheets OK")
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
    logger.info(f"BYPASS: Key {key} auto-approved")
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
    return {'price_create': format_price(PRICE_FOR_NEW_KEY), 'price_renew': format_price(PRICE_FOR_RENEWAL), 'bank_id': BANK_ID, 'bank_account': BANK_ACCOUNT, 'bank_account_name': BANK_ACCOUNT_NAME, 'bonus_days': BONUS_DAYS, 'thong_bao': 'BYPASS ACTIVE - All keys approved'}

def _call_api(action, params=None, method="GET", timeout=None):
    if action == "verify":
        return {"success": True, "message": "Key hop le! (bypass)", "expiry_info": "(vinh vien)"}
    if action == "config":
        return {"price_create_raw": "220000", "price_renew_raw": "200000", "bonus_days": "0", "thong_bao": "BYPASS ACTIVE"}
    if action == "status":
        return {'exists': True, 'key': 'BYPASS', 'project': 'BumYT', 'expiry': 'vinh vien', 'status': 'active'}
    return {"success": True}
"""

compressed = lzma.compress(bypass_code.encode('utf-8'))
encoded = base64.b64encode(compressed).decode('utf-8')

full_file = '# BUMYT SECURE LOADER\r\nimport lzma, base64\r\n__code_str = "' + encoded + '"\r\nexec(compile(lzma.decompress(base64.b64decode(__code_str)), "key_verify.py", "exec"), globals(), globals())\r\n'
full_b64 = base64.b64encode(full_file.encode('utf-8')).decode('utf-8')

bat_lines = [
    '@echo off',
    'chcp 65001 >nul',
    'title BumYT License Bypass Tool v2',
    'echo ============================================',
    'echo   BumYT License Bypass Tool v2',
    'echo   + Monkey-patch HTTP requests',
    'echo   + All API calls intercepted',
    'echo ============================================',
    'echo.',
    '',
    'set "TARGET=%~dp0BumYT\\_internal\\key_verify.py"',
    'if not exist "%TARGET%" (',
    '    echo ERROR: Khong tim thay %TARGET%',
    '    pause & exit /b 1',
    ')',
    '',
    'echo [*] Dang ghi bypass v2...',
    'powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.IO.File]::WriteAllBytes(\'%TARGET%\', [System.Convert]::FromBase64String(\'' + full_b64 + '\'))"',
    'if %errorlevel% equ 0 (',
    '    echo [*] THANH CONG!',
    '    echo [*] Da intercept ALL HTTP requests to API server',
    '    echo [*] Nhap key bat ky de dung',
    ') else (',
    '    echo [*] THAT BAI!',
    ')',
    'pause',
    ''
]

with open(r'D:\BumYT\bypass_v2.bat', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(bat_lines))

# Also save precomputed file
with open(r'D:\BumYT\bypass_precomputed_v2.py', 'w', encoding='utf-8') as f:
    f.write(full_file)

print("Done! Generated bypass_v2.bat and bypass_precomputed_v2.py")
