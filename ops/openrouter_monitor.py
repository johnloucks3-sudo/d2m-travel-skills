import requests
import json
import os
from datetime import datetime, timedelta

def get_openrouter_usage():
    # Use API key from env or passed config
    api_key = os.getenv("OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/auth/key"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def check_budget():
    # Placeholder for actual budget logic
    # OpenRouter API doesn't have a direct "budget" endpoint in v1 auth/key 
    # but we can track usage logs
    pass

if __name__ == "__main__":
    usage = get_openrouter_usage()
    if usage:
        print(f"Usage data: {usage}")
    else:
        print("Failed to fetch usage.")
