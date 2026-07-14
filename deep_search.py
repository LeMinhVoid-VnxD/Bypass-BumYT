import struct, zlib

with open(r'D:\BumYT\BumYT\BumYT.exe', 'rb') as f:
    data = f.read()

# The pyz archives were found at offsets: 193925, 12038783, 19089857
# Let me try to decompress these as zlib (Python marshal uses zlib)
pyz_offsets = [193925, 12038783, 19089857]

for off in pyz_offsets:
    print(f'\n=== Checking PYZ at offset {off} ===')
    # PyInstaller PYZ format:
    # 4 bytes: magic (usually "PYZ\0")
    # 4 bytes: version
    # 4 bytes: timestamp
    # Then compressed entries
    magic = data[off:off+4]
    print(f'  Magic: {magic}')
    
    # Try to find key_verify in each PYZ
    for sub_off in range(off, min(off + 50000, len(data))):
        if data[sub_off:sub_off+10] == b'key_verify':
            ctx = data[max(0,sub_off-20):sub_off+100]
            text = ctx.decode('utf-8', errors='replace')
            safe = ''.join(c if c.isprintable() else '.' for c in text)
            print(f'  Found key_verify at {sub_off}: ...{safe}...')
            break
    else:
        print(f'  key_verify not found in this PYZ range')

# Also check with zlib decompression - the archive might be compressed
# The TOC entries have compression flags
# Let me look for a large chunk of zlib-compressed data
# Python marshal data is often zlib compressed in PyInstaller

# Search for key_verify module reference
# PYZ entries are stored as: filename (bytes) + compressed_data
# Let me search for "key_verify" in the raw data more broadly
matches = []
search_start = 0
while True:
    idx = data.find(b'key_verify', search_start)
    if idx == -1:
        break
    matches.append(idx)
    search_start = idx + 1

print(f'\nAll key_verify occurrences:')
for idx in matches:
    ctx = data[max(0,idx-10):idx+50]
    text = ctx.decode('utf-8', errors='replace')
    safe = ''.join(c if c.isprintable() else '.' for c in text)
    print(f'  Offset {idx}: ...{safe}...')
