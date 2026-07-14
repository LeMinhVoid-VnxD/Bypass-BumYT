import lzma, base64

# Read dich.py fully
with open(r'D:\BumYT\BumYT\_internal\dich.py', 'r', encoding='utf-8') as f:
    content = f.read()
start = content.find('__code_str = "') + len('__code_str = "')
end = content.find('"', start)
code_str = content[start:end]
decoded = base64.b64decode(code_str)
decompressed = lzma.decompress(decoded)
full_code = decompressed.decode('utf-8')

# Look for key check references
import re
lines = full_code.split('\n')
for i, line in enumerate(lines):
    if 'key_verify' in line.lower() or 'check_and_activate' in line or 'password' in line.lower() or 'verify' in line.lower() or 'connect_sheets' in line:
        print(f"dich.py line {i+1}: {line[:200]}")
