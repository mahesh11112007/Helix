import requests
import json
import os

base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
headers = {
    "Authorization": "Bearer fake_key",
    "Content-Type": "application/json"
}
payload = {
    "model": "meta/llama-3.1-70b-instruct",
    "messages": [{"role": "user", "content": "hello"}]
}

print(f"Testing URL: {base_url}")
response = requests.post(base_url, headers=headers, json=payload)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
