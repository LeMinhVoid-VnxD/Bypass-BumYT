@echo off
cd /d D:\BumYT
openssl req -x509 -newkey rsa:2048 -keyout server_key.pem -out server_cert.pem -days 3650 -nodes -subj "/CN=script.google.com" -addext "subjectAltName=DNS:script.google.com" 2>nul
echo Done
