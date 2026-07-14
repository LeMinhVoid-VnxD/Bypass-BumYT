#!/usr/bin/env python3
import json, ssl, sys
from http.server import HTTPServer, BaseHTTPRequestHandler

API = {
    "config": {"price_create_raw":"220000","price_renew_raw":"200000","bonus_days":"30","thong_bao":"BYPASS ACTIVE","bank_id":"BIDV","bank_account":"8816144490","bank_account_name":"LE VAN DIEU"},
    "verify": {"success":True,"message":"Key hop le! (bypass)","expiry_info":"(vinh vien)"},
    "status": {"exists":True,"key":"BYPASS","project":"BumYT","expiry":"vinh vien","status":"active"},
    "qr": {"error":"Bypass mode"},
    "check_payment": {"found":False}
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        p = parse_qs(urlparse(self.path).query)
        a = p.get("action",[""])[0]
        r = API.get(a, {"success":True})
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.end_headers()
        self.wfile.write(json.dumps(r).encode())
        print(f"[FAKE] {a} -> OK")
    do_POST = do_GET
    def log_message(self, *a): pass

port = int(sys.argv[1]) if len(sys.argv)>1 else 8443
cert = sys.argv[2] if len(sys.argv)>2 else "server_cert.pem"
key = sys.argv[3] if len(sys.argv)>3 else cert

httpd = HTTPServer(("0.0.0.0",port), Handler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(cert, key)
httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
print(f"[*] Fake API on https://0.0.0.0:{port}")
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\n[*] Stop")
