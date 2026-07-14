import sys
sys.path.insert(0, r'D:\BumYT\BumYT\_internal')

# Import will exec key_verify.py which will exec our modified version
import key_verify

# Test - should return True without hitting the network
success, message, expiry = key_verify.check_and_activate_key("ANY_KEY_123")
print(f"Kết quả: success={success}")
print(f"Message: {message}")
print(f"Expiry: {expiry}")

# Test connect_sheets too
connected, _ = key_verify.connect_sheets()
print(f"Connected: {connected}")
if connected:
    print(f"Price create: {key_verify.PRICE_FOR_NEW_KEY}")
    print(f"Price renew: {key_verify.PRICE_FOR_RENEWAL}")
