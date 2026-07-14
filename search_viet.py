with open(r'D:\BumYT\BumYT\BumYT.exe', 'rb') as f:
    data = f.read()

# Search for common Vietnamese 1-byte encoded patterns (as used in the source)
# In Vietnamese, common encoding is UTF-8
# "key ko tồn tại" in UTF-8: key ko t\xe1\xbb\x93n t\xe1\xba\xa1i
# "không tồn tại": kh\xc3\xb4ng t\xe1\xbb\x93n t\xe1\xba\xa1i

# Let search for parts that might be in the py source
# In Python marshal, strings are stored as:
# type 't' (short) or 'T' (long) + length + chars
# Let me just search for 'key' in context of error messages

# Search for any occurrence of 'key' followed by Vietnamese chars or 'khong'
import re

# Find all 'key' strings that might be error messages
for i in range(len(data) - 100):
    if data[i:i+3] == b'key' and data[i-1:i] in (b'\x00', b'\x01', b'\x02', b'\x03'):
        # Potential string in marshal
        ctx = data[i:i+50]
        try:
            text = ctx.decode('utf-8', errors='replace')
            safe = ''.join(c if c.isprintable() else '.' for c in text)
            if 'kh' in safe.lower() or 't' in safe.lower():
                print(f'  at {i}: ...{safe}...')
        except:
            pass

# Also search for the exact Vietnamese phrase in UTF-8
# "tồn tại" in UTF-8 bytes
tan_tai_bytes = bytes([0x74, 0xe1, 0xbb, 0x93, 0x6e, 0x20, 0x74, 0xe1, 0xba, 0xa1, 0x69])
# Also try latin-style Vietnamese (no accents): 'ton tai'
# Also try 'khong ton tai'

patterns = [
    b'ton tai', b'khong ton',
    b'key khong', b'sai key',
    b'key bi', b'key khong ton',
    b'key hong', b'key het han',
    b'khong hop le',
]

for p in patterns:
    idx = data.find(p)
    if idx >= 0:
        print(f'Found "{p.decode()}" at {idx}')
        ctx = data[max(0,idx-30):idx+80]
        safe = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
        print(f'  Context: {safe}')
