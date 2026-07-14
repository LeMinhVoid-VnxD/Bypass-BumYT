with open(r'D:\BumYT\BumYT\BumYT.exe', 'rb') as f:
    data = f.read()

# Search for error patterns using raw bytes
patterns = [
    b'ton tai',
    b'khong ton',
    b'key ko',
    b'sai key',
    b'key h',
    b'ma key',
    b'nhap key',
    b'not found',
    b'invalid key',
    b'key does not',
    b'key not found',
    b'verify',
    b'activation',
    b'activ',
    b'licen',
    b'Key ',
]

for p in patterns:
    idx = data.find(p)
    count = 0
    while idx >= 0 and count < 8:
        ctx = data[max(0,idx-40):idx+120]
        text = ctx.decode('utf-8', errors='replace')
        safe = ''.join(c if c.isprintable() or c in '\n\r' else '.' for c in text)
        print(f'[{p.decode()}] at {idx}: ...{safe}...')
        print()
        idx = data.find(p, idx+1)
        count += 1
