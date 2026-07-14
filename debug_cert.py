import ssl, tempfile, os, certifi as sys_certifi

# Test system certifi
path = sys_certifi.where()
print(f'System certifi: {path}')
ctx = ssl.create_default_context(cafile=path)
print('System certifi works OK')

# Check app's cacert.pem
p = r'D:\BumYT\BumYT\_internal\certifi\cacert.pem'
with open(p, 'rb') as f:
    raw = f.read()
print(f'App cacert.pem: {len(raw)} bytes')
print(f'Last 200 bytes: {raw[-200:]}')
print(f'Ends with LF only: {raw[-1:] == b"\n"}')
print(f'Ends with CRLF: {raw[-2:] == b"\r\n"}')

# Test each cert block in the bundle
blocks = raw.split(b'-----BEGIN CERTIFICATE-----')
print(f'Total cert blocks: {len(blocks)}')
for i, block in enumerate(blocks):
    if not block.strip():
        continue
    pem = b'-----BEGIN CERTIFICATE-----' + block
    tmp = tempfile.mktemp(suffix='.pem')
    with open(tmp, 'wb') as f:
        f.write(pem)
    try:
        ctx = ssl.create_default_context(cafile=tmp)
        print(f'  Cert block {i}: OK')
    except Exception as e:
        print(f'  Cert block {i}: ERROR - {str(e)[:100]}')
    os.unlink(tmp)
