import json

text = r'{"a": "\sin"}'

try:
    print(json.loads(text, strict=False))
except Exception as e:
    print("Error:", e)
