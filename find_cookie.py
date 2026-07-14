import struct

with open(r'D:\BumYT\BumYT\BumYT.exe', 'rb') as f:
    data = f.read()

# Look for the archive cookie
# PyInstaller 6.x cookie format:
# MEI01 magic (4 bytes) + version (4 bytes LE) + toc_offset (8 bytes) + toc_length (4 bytes) + pyver (4 bytes)
# The cookie might be at a known location

# Check the known PYINSTALLER location at 189984
pos = 189984
print(f'Bytes at {pos}: {data[pos:pos+80].hex()}')
text = data[pos:pos+80].decode('utf-8', errors='replace')
print(f'Text: {text}')

# The actual PYINSTALLER environment strings are at 189984
# They're just environment variables
# The REAL archive cookie might be elsewhere

# Let me look for 'MEI' patterns
for i in range(len(data) - 8):
    if data[i:i+3] == b'MEI':
        ctx = data[max(0,i-20):i+40]
        try:
            text = ctx.decode('utf-8', errors='replace')
            safe = ''.join(c if c.isprintable() else '.' for c in text)
            # Check if this looks like a cookie (followed by version ints)
            vals = struct.unpack('<I', data[i+4:i+8]) if i+8 <= len(data) else (0,)
            if vals[0] > 100000 and vals[0] < len(data):  # Looks like a TOC offset
                print(f'MEI at {i}: version={vals[0]}, ctx={safe}')
        except:
            pass

# Actually, in PyInstaller 6.x, the archive is stored as a separate section
# Let me look for 'PYINSTALLER' specifically as the magic
# The cookie structure is:
#   char magic[12];  // "PYINSTALLER"
#   uint32_t ver;
#   uint64_t toc_offset;
#   uint32_t toc_length;
#   uint32_t pyver;
#   uint32_t unused;

# Let me search for this pattern
for i in range(len(data) - 30):
    if data[i:i+10] == b'PYINSTALLER':
        # Check if next 2 bytes are 0 (part of 12-byte magic)
        if data[i+10:i+12] == b'\x00\x00':
            # Try to parse cookie
            try:
                ver = struct.unpack('<I', data[i+12:i+16])[0]
                toc_off = struct.unpack('<Q', data[i+16:i+24])[0]
                toc_len = struct.unpack('<I', data[i+24:i+28])[0]
                pyver = struct.unpack('<I', data[i+28:i+32])[0]
                print(f'Cookie at {i}: ver={ver}, toc_off={toc_off}, toc_len={toc_len}, pyver={pyver}')
                if toc_off > 0 and toc_off < len(data):
                    print(f'  TOC first 50 bytes: {data[toc_off:toc_off+50].hex()}')
            except Exception as e:
                print(f'Cookie at {i}: parse error {e}')
