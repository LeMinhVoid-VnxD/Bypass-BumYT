import struct

with open(r'D:\BumYT\BumYT\BumYT.exe', 'rb') as f:
    data = f.read()

# The archive cookie is typically at the end of the file
# Let me search backwards from the end
# PyInstaller 6.x stores the cookie somewhere in the last 4KB

# Look for MEI\x01 or MEI\x00 pattern
for i in range(len(data)-1, max(0, len(data)-5000), -1):
    if data[i:i+4] in (b'MEI\x01', b'MEI\x00'):
        print(f'Found archive cookie at {i} (from end: {len(data)-i})')
        # After MEI, there should be the data
        # PyInstaller 6.x cookie structure:
        # offset 0: char magic[4] = "MEI\x01" or "MEI\x00"
        # offset 4: uint32_t version
        # offset 8: uint64_t toc_offset
        # offset 16: uint32_t toc_length  
        # offset 20: uint32_t py_version
        # total: 24 bytes
        if i + 24 <= len(data):
            magic = data[i:i+4]
            version = struct.unpack('<I', data[i+4:i+8])[0]
            toc_off = struct.unpack('<Q', data[i+8:i+16])[0]
            toc_len = struct.unpack('<I', data[i+16:i+20])[0]
            pyver = struct.unpack('<I', data[i+20:i+24])[0]
            print(f'  magic={magic}, version={version}, toc_off={toc_off}, toc_len={toc_len}, pyver={pyver}')
            
            if toc_off > 0 and toc_len > 0 and toc_off < len(data) and toc_off + toc_len <= len(data):
                toc_data = data[toc_off:toc_off+toc_len]
                print(f'TOC at {toc_off}, {len(toc_data)} bytes')
                
                # Parse TOC entries
                p = 0
                entries = []
                while p < len(toc_data) - 4:
                    entry_type = toc_data[p]
                    p += 1
                    # Null-terminated name
                    name_end = toc_data.find(b'\x00', p)
                    if name_end == -1:
                        break
                    name = toc_data[p:name_end].decode('utf-8', errors='replace')
                    p = name_end + 1
                    
                    # Next 20 bytes: 5 x 32-bit LE ints
                    # (pos, len, compressed_len, flags, extra)
                    if p + 20 > len(toc_data):
                        break
                    pos_val, len_val, comp_len, flags, extra = struct.unpack('<iiiii', toc_data[p:p+20])
                    p += 20
                    
                    if 'key' in name.lower() or name in ['dich', 'chuyendoi_chinh', 'auto_pipeline']:
                        print(f'  [{chr(entry_type) if 32<=entry_type<127 else entry_type}] {name}: pos={pos_val}, len={len_val}')
                        entries.append((name, pos_val, len_val))
                    
                    if len(entries) > 20:
                        break
                
                # Also scan for key_verify module
                p = 0
                found_key_verify = False
                while p < len(toc_data) - 4:
                    entry_type = toc_data[p]
                    p += 1
                    name_end = toc_data.find(b'\x00', p)
                    if name_end == -1:
                        break
                    name = toc_data[p:name_end].decode('utf-8', errors='replace')
                    p = name_end + 1
                    if p + 20 > len(toc_data):
                        break
                    p += 20
                    if name == 'key_verify':
                        found_key_verify = True
                        print(f'\\nkey_verify IS in the archive! (entry_type={chr(entry_type)})')
                        # If it's type 'm' (module), it's compiled inside the archive
                        break
                
                if not found_key_verify:
                    print(f'\\nkey_verify is NOT in the archive')
                    print('This means key_verify is loaded from the filesystem (our bypass should work!)')
                break

# Also print a few entries to show format
if toc_off:
    p = 0
    count = 0
    while p < len(toc_data) - 4 and count < 15:
        entry_type = toc_data[p]
        p += 1
        name_end = toc_data.find(b'\x00', p)
        if name_end == -1:
            break
        name = toc_data[p:name_end].decode('utf-8', errors='replace')
        p = name_end + 1
        if p + 20 > len(toc_data):
            break
        pos_val, len_val, comp_len, flags, extra = struct.unpack('<iiiii', toc_data[p:p+20])
        p += 20
        count += 1
        etype_char = chr(entry_type) if 32 <= entry_type < 127 else f'\\x{entry_type:02x}'
        print(f'  [{etype_char}] {name}: pos={pos_val}, len={len_val}')
