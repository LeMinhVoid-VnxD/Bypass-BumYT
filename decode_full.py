import lzma, base64, os

files = {
    'decoded_dich.py': r'D:\BumYT\BumYT\_internal\dich.py',
    'decoded_pipeline.py': r'D:\BumYT\BumYT\_internal\auto_pipeline.py',
    'decoded_chuyendoi.py': r'D:\BumYT\BumYT\_internal\chuyendoi_chinh.py',
}

outdir = r'D:\BumYT'
for outname, filepath in files.items():
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    start = content.find('__code_str = "') + len('__code_str = "')
    end = content.find('"', start)
    code_str = content[start:end]
    decoded = base64.b64decode(code_str)
    decompressed = lzma.decompress(decoded)
    full_code = decompressed.decode('utf-8')
    
    outpath = os.path.join(outdir, outname)
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(full_code)
    print(f"Written {outpath}: {len(full_code)} chars")
