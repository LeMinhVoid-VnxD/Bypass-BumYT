import struct

with open(r'D:\BumYT\BumYT\BumYT.exe', 'rb') as f:
    data = f.read()

# In PyInstaller 6.x, the archive is stored as a CArchive
# The CArchive TOC contains all the files/modules bundled
# Let me search for the TOC data by looking for a pattern of entry types
# that look like the CArchive TOC format

# CArchive TOC entries are: 1 byte type + null-terminated name + 5 x int32
# The first entry is usually 'M' (module) for the main script

# Let me search for potential main entry file names
# Common PyInstaller main scripts: __main__.py, main.py, etc.
# The main script name is usually stored as a filename in the TOC

# Search for known patterns
for i in range(len(data) - 100):
    # Look for a pattern: type byte + "main" string + null
    if data[i] == ord('M') or data[i] == ord('m') or data[i] == ord('s') or data[i] == ord('d'):
        # Check if it could be a CArchive entry
        # After type byte, there should be a null-terminated name
        null_pos = data.find(b'\x00', i+1, i+100)
        if null_pos and (null_pos - i) < 80:
            name = data[i+1:null_pos]
            if len(name) > 3:
                try:
                    name_str = name.decode('utf-8', errors='replace')
                    if all(c.isprintable() or c in '_.' for c in name_str):
                        # Check if name looks like a Python module/file
                        if name_str.endswith('.py') or name_str.endswith('.pyc') or name_str.endswith('.pyd'):
                            # Check if next bytes look like valid int32 values
                            if null_pos + 21 <= len(data):
                                pos_val, len_val, comp_len, flags, extra = struct.unpack('<iiiii', data[null_pos+1:null_pos+21])
                                # Check if these look sensible
                                if 0 <= pos_val < len(data) and 0 <= len_val < 10000000:
                                    print(f'  [{chr(data[i])}] {name_str}: pos={pos_val}, len={len_val}, compr={comp_len}')
                except:
                    pass

# Also search for __main__ as a python module
for i in range(len(data) - 20):
    if data[i:i+8] == b'__main__':
        # Check if this is in a TOC context (before null terminator)
        ctx = data[max(0,i-10):i+50]
        text = ctx.decode('utf-8', errors='replace')
        safe = ''.join(c if c.isprintable() else '.' for c in text)
        print(f'__main__ at {i}: {safe}')
