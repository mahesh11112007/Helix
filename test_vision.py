import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("NVIDIA_NIM_API_KEY")

base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Test nvidia/neva-22b
payload = {
    "model": "nvidia/neva-22b",
    "messages": [
        {
            "role": "user",
            "content": "Hello"
        }
    ],
    "max_tokens": 50
}

response = requests.post(base_url, headers=headers, json=payload)
print("neva-22b:", response.status_code, response.text)

# Test meta/llama-3.2-90b-vision-instruct
payload["model"] = "meta/llama-3.2-90b-vision-instruct"
response = requests.post(base_url, headers=headers, json=payload)
print("llama-3.2-90b-vision-instruct:", response.status_code, response.text)
