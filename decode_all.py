import lzma, base64

files = [
    r'D:\BumYT\BumYT\_internal\dich.py',
    r'D:\BumYT\BumYT\_internal\auto_pipeline.py',
    r'D:\BumYT\BumYT\_internal\chuyendoi_chinh.py',
]

for filepath in files:
    print(f"\n{'='*60}")
    print(f"FILE: {filepath}")
    print('='*60)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    start = content.find('__code_str = "') + len('__code_str = "')
    end = content.find('"', start)
    code_str = content[start:end]
    decoded = base64.b64decode(code_str)
    decompressed = lzma.decompress(decoded)
    print(decompressed.decode('utf-8')[:5000])
    print("... (truncated)")
