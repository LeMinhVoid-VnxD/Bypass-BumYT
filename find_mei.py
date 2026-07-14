import struct

with open(r'D:\BumYT\BumYT\BumYT.exe', 'rb') as f:
    data = f.read()

# Search for MEI pattern anywhere in the file
for i in range(len(data) - 24):
    if data[i:i+4] in (b'MEI\x01', b'MEI\x00'):
        magic = data[i:i+4]
        version = struct.unpack('<I', data[i+4:i+8])[0]
        toc_off = struct.unpack('<Q', data[i+8:i+16])[0]
        toc_len = struct.unpack('<I', data[i+16:i+20])[0]
        pyver = struct.unpack('<I', data[i+20:i+24])[0]
        
        # Sanity check - TOC offset should be within the file
        if 0 < toc_off < len(data) and 0 < toc_len < 1000000:
            print(f'Found cookie at {i}: magic={magic}, ver={version}, toc_off={toc_off}, toc_len={toc_len}, pyver={pyver}')
            
            # Parse TOC
            if toc_off + toc_len <= len(data):
                toc_data = data[toc_off:toc_off+toc_len]
                print(f'TOC is {len(toc_data)} bytes at offset {toc_off}')
                
                p = 0
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
                    pos_val, len_val, comp_len, flags, extra = struct.unpack('<iiiii', toc_data[p:p+20])
                    p += 20
                    
                    if 'key' in name.lower() or name in ('dich', 'chuyendoi_chinh', 'auto_pipeline', '__main__'):
                        etype_char = chr(entry_type) if 32 <= entry_type < 127 else f'\\x{entry_type:02x}'
                        print(f'  [{etype_char}] {name}: pos={pos_val}, len={len_val}, compr={comp_len}')
                break
