import struct, marshal, dis

with open(r'D:\BumYT\BumYT\BumYT.exe', 'rb') as f:
    data = f.read()

# Find all PYINSTALLER occurrences and check for cookie format
for i in range(len(data) - 40):
    if data[i:i+10] == b'PYINSTALLER':
        # Check if followed by 2 null bytes (the 12-byte magic)
        if data[i+10:i+12] == b'\x00\x00':
            # Try to parse as cookie
            # Magic: 12 bytes, then uint32 version, uint64 toc_off, uint32 toc_len, uint32 pyver
            magic = data[i:i+12]  # "PYINSTALLER\0\0"
            version = struct.unpack('<I', data[i+12:i+16])[0]
            toc_off = struct.unpack('<Q', data[i+16:i+24])[0]
            toc_len = struct.unpack('<I', data[i+24:i+28])[0]
            pyver = struct.unpack('<I', data[i+28:i+32])[0]
            
            # Validate: TOC offset should be within file, TOC length reasonable
            if 0 < toc_off < len(data) and 0 < toc_len < 10000000:
                print(f'Cookie at {i}: magic={magic}, version={version}, toc_off={toc_off}, toc_len={toc_len}, pyver={pyver}')
                if toc_off + toc_len <= len(data):
                    toc_data = data[toc_off:toc_off+toc_len]
                    print(f'TOC: {len(toc_data)} bytes at offset {toc_off}')
                    
                    # Parse TOC
                    p = 0
                    count = 0
                    while p < len(toc_data) - 25:
                        entry_type = toc_data[p]; p += 1
                        # Find null terminator for name
                        null_pos = toc_data.find(b'\x00', p)
                        if null_pos == -1 or null_pos - p > 200:
                            break
                        name = toc_data[p:null_pos].decode('utf-8', errors='replace')
                        p = null_pos + 1
                        
                        # Read 5 ints
                        if p + 20 > len(toc_data):
                            break
                        vals = struct.unpack('<iiiii', toc_data[p:p+20])
                        p += 20
                        count += 1
                        
                        if 'key' in name.lower() or name in ('__main__', 'main', 'dich', 'chuyendoi_chinh', 'auto_pipeline', 'BumYT'):
                            etype = chr(entry_type) if 32 <= entry_type < 127 else f'\\x{entry_type:02x}'
                            print(f'  [{etype}] {name}: ofs={vals[0]}, len={vals[1]}, compr={vals[2]}, flag={vals[3]}')
                        
                        if count > 500:
                            break
                    print(f'  Total entries parsed: {count}')
                    
                    # Find the main script entry
                    p = 0
                    while p < len(toc_data) - 25:
                        entry_type = toc_data[p]; p += 1
                        null_pos = toc_data.find(b'\x00', p)
                        if null_pos == -1:
                            break
                        name = toc_data[p:null_pos].decode('utf-8', errors='replace')
                        p = null_pos + 1
                        if p + 20 > len(toc_data):
                            break
                        vals = struct.unpack('<iiiii', toc_data[p:p+20])
                        p += 20
                        
                        if name == '__main__':
                            print(f'\\nMain script entry found! type={chr(entry_type)}, offset={vals[0]}, length={vals[1]}')
                            # Extract the main script data
                            script_data = data[vals[0]:vals[0]+vals[2]] if vals[2] > 0 else data[vals[0]:vals[0]+vals[1]]
                            print(f'  Data length: {len(script_data)} bytes')
                            print(f'  First 50 bytes hex: {script_data[:50].hex()}')
                            break

# Also try to find any Python code object in the binary
# Code object marshal signature: starts with 'c' (0x63) type marker
print(f'\\nSearching for marshal code objects...')
for i in range(len(data) - 100):
    if data[i] == 0x63:  # 'c' type for code object
        # Try to read the code object
        # Format: argcount(4) + posonly(4) + kwonly(4) + nlocals(4) + stacksize(4) + flags(4) + codestring + ...
        if i + 30 > len(data):
            continue
        try:
            # Look ahead for a short name string like "__main__"
            for j in range(i+50, min(i+500, len(data))):
                if data[j:j+8] == b'__main__':
                    print(f'Found __main__ code object candidate at {i}')
                    ctx = data[max(0,i-10):j+50]
                    text = ctx.decode('utf-8', errors='replace')
                    safe = ''.join(c if c.isprintable() else '.' for c in text)
                    print(f'  Context: ...{safe}...')
                    break
        except:
            pass
