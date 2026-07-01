import requests
import json
import os
import sys

# Add the current directory to sys.path so we can import services
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.ai_service import ai_service

def test_all_keys():
    print("=== Automated API Key Tester ===\n")
    print("Fetching all keys from the database and environment variables...")
    
    # This uses the exact same logic the background queue uses to load your keys
    configs = ai_service.get_prioritized_configs()
    
    if not configs:
        print("No API keys found in the system!")
        return

    print(f"Found {len(configs)} total API keys loaded in priority order.\n")
    
    for i, cfg in enumerate(configs, 1):
        key, base_url, chat_model, vision_model, platform = cfg
        
        print(f"--- Key #{i} | Platform: {platform.upper()} ---")
        print(f"Model: {chat_model}")
        print(f"Key Prefix: {key[:8]}...{key[-4:] if len(key) > 12 else ''}")
        
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": chat_model,
            "messages": [
                {"role": "user", "content": "Hello! Reply with exactly 'OK' if you can read this."}
            ],
            "max_tokens": 10
        }
        
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                print(f"Result: SUCCESS! API responded with: '{content}'\n")
            elif response.status_code == 429:
                print("Result: ERROR 429 - Rate Limited (Too Many Requests).\n")
            elif response.status_code == 401:
                print("Result: ERROR 401 - Unauthorized (Invalid or Revoked API Key).\n")
            elif response.status_code == 404:
                print(f"Result: ERROR 404 - Not Found (Model {chat_model} might not exist).\n")
            else:
                print(f"Result: FAILED with Status {response.status_code}.\n")
                
        except Exception as e:
            print(f"Connection Error: {e}\n")

if __name__ == "__main__":
    test_all_keys()
