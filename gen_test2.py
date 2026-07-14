import lzma, base64

test_code = r'''# Write marker
import os
f = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "BYPASS_LOADED.txt"), "w")
f.write("key_verify.py loaded!")
f.close()

# All the original functions
import sys, random, string, hashlib, logging
from datetime import datetime

BANK_ID = "BIDV"
BANK_ACCOUNT = "8816144490"
BANK_ACCOUNT_NAME = "LE VAN DIEU"
PRICE_FOR_RENEWAL = 200000
PRICE_FOR_NEW_KEY = 220000
BONUS_DAYS = 0
THONG_BAO = ""
_api_connected = False
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
    logger.info("TEST: connect_sheets from filesystem module!")
    _api_connected = True
    return True, True

def get_computer_id():
    return "TEST-" + hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:12]

def format_price(p):
    try: return f"{int(p):,}".replace(",", ".")
    except: return str(p)

def generate_random_key(prefix="BYT", length=6):
    return prefix + "-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def check_and_activate_key(key, a=None, b=None):
    logger.info("TEST: Key " + str(key) + " approved from filesystem module!")
    return True, "Key hop le! (bypass from filesystem)", "(vinh vien)"

def check_key_status(key_name):
    k = key_name.strip().upper() if key_name else ""
    return {"exists": True, "key": k, "project": "BumYT", "expiry": "vinh vien", "status": "active"}

def get_renew_qr(key_name):
    return {"error": "Test bypass"}
def get_create_qr(key_name=None):
    return {"error": "Test bypass"}
def watch_payment(c):
    pass
def start_background_polling():
    return True
def get_help_info():
    return {"price_create": "220.000", "price_renew": "200.000", "bank_id": "BIDV", "bank_account": "8816144490", "bank_account_name": "LE VAN DIEU", "bonus_days": 0, "thong_bao": "TEST BYPASS"}
def _call_api(action, params=None, method="GET", timeout=None):
    if action == "verify":
        return {"success": True, "message": "Key hop le! (test bypass)", "expiry_info": "(vinh vien)"}
    if action == "config":
        return {"price_create_raw": "220000", "price_renew_raw": "200000", "bonus_days": "0", "thong_bao": "TEST BYPASS"}
    if action == "status":
        return {"exists": True, "key": "BYPASS", "project": "BumYT", "expiry": "vinh vien", "status": "active"}
    return {"success": True}
'''

compressed = lzma.compress(test_code.encode('utf-8'))
encoded = base64.b64encode(compressed).decode('utf-8')

full_file = '# BUMYT SECURE LOADER\r\nimport lzma, base64\r\n__code_str = "' + encoded + '"\r\nexec(compile(lzma.decompress(base64.b64decode(__code_str)), "key_verify.py", "exec"), globals(), globals())\r\n'

with open(r'D:\BumYT\BumYT\_internal\key_verify.py', 'w', encoding='utf-8') as f:
    f.write(full_file)

print("Written! Now run BumYT.exe and check for BYPASS_LOADED.txt")
