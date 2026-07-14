import lzma, base64

# Read the CURRENT key_verify.py (after bypass)
with open(r'D:\BumYT\BumYT\_internal\key_verify.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract and decode
start = content.find('__code_str = "') + len('__code_str = "')
end = content.find('"', start)
code_str = content[start:end]

print(f"Base64 length: {len(code_str)}")
print(f"First 50 chars: {code_str[:50]}")
print(f"Last 20 chars: {code_str[-20:]}")

try:
    decoded = base64.b64decode(code_str)
    print(f"Decoded length: {len(decoded)}")
    try:
        decompressed = lzma.decompress(decoded)
        text = decompressed.decode('utf-8')
        print(f"Decompressed length: {len(text)}")
        # Check for key functions
        if 'def check_and_activate_key' in text:
            print("OK: check_and_activate_key found")
        if 'BYPASS' in text:
            print("OK: BYPASS marker found")
        # Show line 1-5
        lines = text.split('\n')
        for i, line in enumerate(lines[:5]):
            print(f"  {i+1}: {line}")
    except Exception as e:
        print(f"LZMA error: {e}")
except Exception as e:
    print(f"Base64 error: {e}")
