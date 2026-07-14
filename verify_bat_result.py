import lzma, base64

with open(r'D:\BumYT\BumYT\_internal\key_verify.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('__code_str = "') + len('__code_str = "')
end = content.find('"', start)
code_str = content[start:end]

decoded = base64.b64decode(code_str)
decompressed = lzma.decompress(decoded)
full_code = decompressed.decode('utf-8')

# Show the key functions
lines = full_code.split('\n')
for i, line in enumerate(lines):
    if 'def ' in line and ('check_and_activate' in line or 'connect_sheets' in line or '_call_api' in line):
        print(f'{lines[i]}')
        if i+1 < len(lines):
            print(f'  -> {lines[i+1]}')
        print()
