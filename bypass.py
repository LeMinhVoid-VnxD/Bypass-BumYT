import lzma, base64

# Read the original key_verify.py structure
with open(r'D:\BumYT\BumYT\_internal\key_verify.py', 'r', encoding='utf-8') as f:
    original_content = f.read()

# Extract the encoded string
start = original_content.find('__code_str = "') + len('__code_str = "')
end = original_content.find('"', start)
original_code_str = original_content[start:end]

# Decode to see the actual code
decoded = base64.b64decode(original_code_str)
decompressed = lzma.decompress(decoded)
original_code = decompressed.decode('utf-8')

# Now create a modified version where check_and_activate_key always succeeds
# We'll replace the check_and_activate_key function
modified_code = original_code.replace(
    'def check_and_activate_key(key: str, p_sheet_keys=None, p_data_keys=None) -> tuple:',
    'def check_and_activate_key(key: str, p_sheet_keys=None, p_data_keys=None) -> tuple:\n    logger.info(f"🔓 BYPASS: Key {key} auto-approved")\n    return True, "Key hợp lệ! (bypass)", "(vĩnh viễn)"\n    '
)

# Verify the replacement worked
if 'def check_and_activate_key' in modified_code and 'auto-approved' in modified_code:
    # Encode back
    compressed = lzma.compress(modified_code.encode('utf-8'))
    new_code_str = base64.b64encode(compressed).decode('utf-8')
    
    # Create new file content
    new_content = f"""# BUMYT SECURE LOADER
import lzma, base64
__code_str = "{new_code_str}"
exec(compile(lzma.decompress(base64.b64decode(__code_str)), "key_verify.py", "exec"), globals(), globals())
"""
    
    with open(r'D:\BumYT\BumYT\_internal\key_verify.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ key_verify.py has been patched - ALL KEYS WILL BE AUTO-APPROVED")
else:
    print("❌ Failed to patch")
    print(f"Found check_and_activate: {'def check_and_activate_key' in original_code}")
