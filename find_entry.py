import lzma, base64

files = {
    'dich.py': r'D:\BumYT\BumYT\_internal\dich.py',
    'auto_pipeline.py': r'D:\BumYT\BumYT\_internal\auto_pipeline.py',
    'chuyendoi_chinh.py': r'D:\BumYT\BumYT\_internal\chuyendoi_chinh.py',
}

for name, filepath in files.items():
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    start = content.find('__code_str = "') + len('__code_str = "')
    end = content.find('"', start)
    code_str = content[start:end]
    decoded = base64.b64decode(code_str)
    decompressed = lzma.decompress(decoded)
    full_code = decompressed.decode('utf-8')
    
    lines = full_code.split('\n')
    for i, line in enumerate(lines):
        lower = line.lower()
        if 'key_verify' in lower or 'import key' in lower or 'from key' in lower:
            print(f'{name}:{i+1}: {line}')
    
    # Find the last 50 lines for entry point
    print(f'\n=== Last 20 lines of {name} ===')
    for line in lines[-20:]:
        print(line)
    print()
