import lzma, base64

with open(r'D:\BumYT\BumYT\_internal\key_verify.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('__code_str = "') + len('__code_str = "')
end = content.find('"', start)
code_str = content[start:end]

decoded = base64.b64decode(code_str)
decompressed = lzma.decompress(decoded)
full_code = decompressed.decode('utf-8')

# Check if our bypass is present
lines = full_code.split('\n')
for i, line in enumerate(lines):
    if 'BYPASS' in line or 'auto-approved' in line or 'check_and_activate_key' in line:
        print(f'Line {i+1}: {line}')
