import lzma, base64, re

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
        if any(kw in line.lower() for kw in ['key_verify', 'check_and_activate', 'connect_sheets', 'get_computer_id', 'verify', 'license', 'key_check', 'password', 'login', 'auth']):
            print(f"{name}:{i+1}: {line[:250]}")
