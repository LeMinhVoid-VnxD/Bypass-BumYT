import lzma, base64

with open(r'D:\BumYT\BumYT\_internal\key_verify.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('__code_str = "') + len('__code_str = "')
end = content.find('"', start)
code_str = content[start:end]

decoded = base64.b64decode(code_str)
decompressed = lzma.decompress(decoded)
print(decompressed.decode('utf-8'))
