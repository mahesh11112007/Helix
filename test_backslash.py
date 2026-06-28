import json
import re

text = r'{"a": "\[f(x)\]"}'

text_cleaned = re.sub(r'(?<!\\)\\(?![\\"/bfnrtu])', r'\\\\', text)

try:
    print(json.loads(text_cleaned))
except Exception as e:
    print("Error:", e)
