import struct

with open(r'D:\BumYT\BumYT\BumYT.exe', 'rb') as f:
    data = f.read()

# Find MEI markers which indicate PyInstaller cookie
for pos in range(len(data) - 20):
    if data[pos:pos+3] == b'MEI' and data[pos+3] in (0x00, 0x01):
        magic = data[pos-12:pos]
        if magic == b'PYINSTALLER':
            ver, toc_off, toc_len, pyver = struct.unpack('<iiii', data[pos-12+12:pos-12+12+16])
            print(f'MEI at {pos}: version={ver}, toc_off={toc_off}, toc_len={toc_len}, pyver={pyver}')
            
            if toc_off > 0 and toc_len > 0 and toc_off < len(data):
                toc_data = data[toc_off:toc_off+toc_len]
                print(f'TOC data: {len(toc_data)} bytes')
                
                # Parse PyInstaller 6.x TOC
                # Format: 1 byte type, null-terminated name, 5 x 32-bit LE ints
                p = 0
                count = 0
                while p < len(toc_data):
                    entry_type = toc_data[p]; p += 1
                    name_end = toc_data.find(b'\x00', p)
                    if name_end == -1:
                        break
                    name = toc_data[p:name_end].decode('utf-8', errors='replace')
                    p = name_end + 1
                    # read 5 ints (pos, len, compr_len, compr_flag, something)
                    if p + 20 > len(toc_data):
                        break
                    vals = struct.unpack('<iiiii', toc_data[p:p+20])
                    p += 20
                    
                    if 'key' in name.lower() or name in ['dich', 'chuyendoi_chinh', 'auto_pipeline']:
                        print(f'  [{chr(entry_type)}] {name}: pos={vals[0]}, len={vals[1]}, compr_len={vals[2]}, flag={vals[3]}')
                    count += 1
                    
                    if count > 200:
                        break
                print(f'Total entries scanned: {count}')
                break
