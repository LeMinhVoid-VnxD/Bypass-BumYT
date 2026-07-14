import struct, zlib, marshal, sys

with open(r'D:\BumYT\BumYT\BumYT.exe', 'rb') as f:
    data = f.read()

# PYZ at offset 193925 (first one - likely main modules)
pyz_off = 193925

# PYZ format: magic(4) + flags(4) + (entries...)
# Each entry: name_length (LE 32) + name + data_length (LE 32) + compressed_data
# Actually PyInstaller PYZ format is different per version

# Let me look at the pyz structure
magic = data[pyz_off:pyz_off+4]
print(f'Magic: {magic}')

# Try to find entry names in this PYZ
# PYZ is a zlib-compressed archive of marshal-compiled code objects
# The table of contents might be uncompressed

# Let me look for import names in this range
for off in range(pyz_off, min(pyz_off + 100000, len(data))):
    if off + 5 > len(data):
        break
    # Look for module names that would be in PYZ
    # Typical module names like 'os', 'sys', etc.
    # Try to find marshal type markers
    b = data[off]
    # In marshal, type codes for strings:
    # 't' = 116 (short string), 'z' = 122 (short ASCII string)
    # 'u' = 117 (unicode), 'Z' = 90 (ASCII string)
    if b in (116, 122, 90, 117):  # string type
        # Try to read length (short: 1 byte, or more)
        if off + 2 > len(data):
            continue
        if b in (116, 117):  # short string with length < 256
            length = data[off+1]
            if length > 0 and length < 100 and off + 2 + length <= len(data):
                name = data[off+2:off+2+length]
                try:
                    name_str = name.decode('utf-8', errors='replace')
                    if all(c.isprintable() or c in '_' for c in name_str):
                        if name_str in ('key_verify', '__main__', 'dich', 'chuyendoi_chinh', 'auto_pipeline', 'main'):
                            print(f'Found module name "{name_str}" at offset {off}')
                except:
                    pass
        elif b in (122, 90):  # short ASCII string (PyInstaller 5+)
            length = data[off+1]
            if length > 0 and length < 100 and off + 2 + length <= len(data):
                name = data[off+2:off+2+length]
                try:
                    name_str = name.decode('ascii', errors='replace')
                    if all(c.isprintable() or c in '_' for c in name_str):
                        if name_str in ('key_verify', '__main__', 'dich', 'chuyendoi_chinh', 'auto_pipeline', 'main'):
                            print(f'Found module name "{name_str}" at offset {off}')
                except:
                    pass

# Also check the other pyz archives
for pyz_off in [12038783, 19089857]:
    magic = data[pyz_off:pyz_off+4]
    print(f'\nPYZ at {pyz_off}, magic={magic}')
    
    for off in range(pyz_off, min(pyz_off + 50000, len(data))):
        if off + 5 > len(data):
            break
        b = data[off]
        if b in (122, 90):  # short ASCII string
            length = data[off+1]
            if length > 0 and length < 100 and off + 2 + length <= len(data):
                name = data[off+2:off+2+length]
                try:
                    name_str = name.decode('ascii', errors='replace')
                    if all(c.isprintable() or c in '_' for c in name_str):
                        if name_str in ('key_verify', '__main__', 'dich', 'chuyendoi_chinh', 'auto_pipeline', 'main', '__main_script'):
                            print(f'  Found "{name_str}" at offset {off}')
                except:
                    pass
