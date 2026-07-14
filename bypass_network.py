#!/usr/bin/env python3
"""
BumYT Final Bypass - Direct Port 443
Fake server listens on port 443 directly.
No portproxy needed.
"""
import os, sys, subprocess, time, ssl, json, socket, threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Auto-detect BumYT app dir: check cmdline arg, then cwd/BumYT, then parent/BumYT
APP_DIR = None
if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
    APP_DIR = sys.argv[1]
else:
for candidate in [BASE_DIR,
                  os.path.join(BASE_DIR, "BumYT"),
                  os.path.join(BASE_DIR, "..", "BumYT"),
                  os.path.join(os.getcwd(), "BumYT")]:
        candidate = os.path.abspath(candidate)
        if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "BumYT.exe")):
            APP_DIR = candidate
            break
if not APP_DIR:
    print("[!] Khong tim thay thu muc BumYT!")
    print("[!] Nhap duong dan den thu muc chua BumYT.exe")
    print("[!] Vi du: D:\\BumYT\\BumYT  hoac  C:\\Users\\...\\BumYT")
    path = input(">>> ").strip().strip('"').strip("'")
    if os.path.isdir(path) and os.path.isfile(os.path.join(path, "BumYT.exe")):
        APP_DIR = os.path.abspath(path)
        print(f"[OK] Da tim thay: {APP_DIR}")
    else:
        print("[!] Khong hop le hoac khong tim thay BumYT.exe trong thu muc do!")
        sys.exit(1)

CACERT = os.path.join(APP_DIR, "_internal", "certifi", "cacert.pem")
CERT_FILE = os.path.join(BASE_DIR, "server_cert.pem")
KEY_FILE = os.path.join(BASE_DIR, "server_key.pem")
CA_CERT = os.path.join(BASE_DIR, "ca_cert.pem")
HOSTS = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
BACKUP_CACERT = CACERT + ".bak"
BACKUP_HOSTS = os.path.join(os.environ["TEMP"], "bumyt_hosts.bak")
SERVER_PORT = 443  # Direct port, no proxy needed!

# ===== FAKE API =====
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

API_RESPONSES = {
    "config": {"price_create_raw":"220000","price_renew_raw":"200000","bonus_days":"30","thong_bao":"BYPASS ACTIVE","bank_id":"BIDV","bank_account":"8816144490","bank_account_name":"LE VAN DIEU"},
    "verify": {"success":True,"message":"Key hop le! (bypass)","expiry_info":"vinh vien"},
    "status": {"exists":True,"key":"BYPASS","project":"BumYT","expiry":"vinh vien","status":"active"},
    "qr": {"error":"Bypass mode"},
    "check_payment": {"found":False}
}

class FakeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = parse_qs(urlparse(self.path).query)
        action = p.get("action", [""])[0]
        resp = API_RESPONSES.get(action, {"success": True})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(resp).encode())
        print(f"[FAKE] {action} -> OK")
    do_POST = do_GET
    def log_message(self, *a): pass

def start_server():
    httpd = HTTPServer(("0.0.0.0", SERVER_PORT), FakeHandler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT_FILE, KEY_FILE)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    print(f"[*] Fake API on https://0.0.0.0:{SERVER_PORT} (direct)")
    httpd.serve_forever()

# ===== SETUP =====
def setup():
    print("=" * 50)
    print("  BumYT Bypass - Direct 443")
    print("=" * 50)

    # Check admin
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False
    if not is_admin:
        print("[!] CAN QUYEN ADMIN! Chuot phai -> Run as administrator")
        input("Press Enter...")
        sys.exit(1)
    print("[OK] Admin")

    # Check files
    print(f"[*] App dir: {APP_DIR}")
    for f in [CERT_FILE, KEY_FILE, CA_CERT, CACERT, APP_DIR]:
        if not os.path.exists(f):
            print(f"[!] Thieu: {f}")
            if f == CACERT:
                print("[!] Dung: python bypass_network.py D:\path\to\BumYT")
            sys.exit(1)

    # Clean up old portproxy from previous runs
    print("[*] Clean old proxy...")
    subprocess.run("netsh interface portproxy delete v4tov4 listenport=443 listenaddress=127.0.0.1", capture_output=True, shell=True)

    # Step 1: Backup cacert
    print("[1/5] Backup cacert.pem...")
    import shutil
    shutil.copy2(CACERT, BACKUP_CACERT)
    print("[OK]")

    # Step 2: Append our cert to cacert (Python I/O - correct encoding)
    print("[2/5] Add cert to certifi...")
    with open(CACERT, "r", encoding="utf-8") as f:
        orig = f.read()
    with open(CA_CERT, "r", encoding="utf-8") as f:
        ca = f.read()
    # Normalize to LF
    orig = orig.replace("\r\n", "\n").replace("\r", "\n")
    ca = ca.replace("\r\n", "\n").replace("\r", "\n")
    combined = orig.rstrip() + "\n\n" + ca.rstrip() + "\n"
    with open(CACERT, "w", encoding="utf-8") as f:
        f.write(combined)
    print("[OK]")

    # Step 3: Modify hosts
    print("[3/5] Add hosts entry...")
    shutil.copy2(HOSTS, BACKUP_HOSTS)
    with open(HOSTS, "r", encoding="utf-8") as f:
        hosts = f.read()
    lines = [l for l in hosts.splitlines() if "script.google.com" not in l]
    lines.append("127.0.0.1 script.google.com")
    with open(HOSTS, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    # Flush DNS cache
    subprocess.run("ipconfig /flushdns", capture_output=True, shell=True)
    print("[OK]")

    # Step 4: Start fake server
    print("[4/5] Start fake server on port 443...")
    try:
        t = threading.Thread(target=start_server, daemon=True)
        t.start()
        time.sleep(2)
        # Verify server is running
        s = socket.socket()
        s.settimeout(2)
        s.connect(("127.0.0.1", SERVER_PORT))
        s.close()
        print("[OK] Server running!")
    except Exception as e:
        print(f"[!] Server start FAILED: {e}")
        cleanup()
        return

    print("\n" + "=" * 50)
    print("  HOAN TAT! Moi nhap key BAT KY!")
    print("  Dong cua so nay de cleanup.")
    print("=" * 50 + "\n")

    subprocess.Popen([os.path.join(APP_DIR, "BumYT.exe")], cwd=APP_DIR, shell=True)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

# ===== CLEANUP =====
CLEANUP_DONE = False

def cleanup():
    global CLEANUP_DONE
    if CLEANUP_DONE:
        return
    CLEANUP_DONE = True
    print("\n[*] Cleanup...")
    # Remove portproxy (just in case)
    subprocess.run("netsh interface portproxy delete v4tov4 listenport=443 listenaddress=127.0.0.1", capture_output=True, shell=True)
    # Restore hosts
    if os.path.exists(BACKUP_HOSTS):
        import shutil
        shutil.copy2(BACKUP_HOSTS, HOSTS)
        os.remove(BACKUP_HOSTS)
        print("[OK] Hosts restored")
    # Flush DNS after restoring hosts
    subprocess.run("ipconfig /flushdns", capture_output=True, shell=True)
    # Restore cacert
    if os.path.exists(BACKUP_CACERT):
        import shutil
        shutil.copy2(BACKUP_CACERT, CACERT)
        os.remove(BACKUP_CACERT)
        print("[OK] cacert restored")
    print("[*] Done!")

# Console control handler for cleanup on window close
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    handler_type = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
    def console_handler(ctrl_type):
        if ctrl_type in (0, 1, 2, 5):
            cleanup()
            return True
        return False
    kernel32.SetConsoleCtrlHandler(handler_type(console_handler), True)

if __name__ == "__main__":
    try:
        setup()
        cleanup()
    except SystemExit:
        pass
    except:
        cleanup()
        raise
