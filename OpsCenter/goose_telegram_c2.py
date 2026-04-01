#!/usr/bin/env python3
import time
import requests
import json
import os

TOKEN = "***REMOVED-SECRET***"
COMMANDER_ID = 7554895206
OFFSET_FILE = "/home/john/Thunderbird/OpsCenter/telegram_offset.txt"
DEBUG_LOG = "/home/john/Thunderbird/OpsCenter/telegram_debug.log"

def get_offset():
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE, 'r') as f:
            return int(f.read().strip())
    return 0

def save_offset(offset):
    with open(OFFSET_FILE, 'w') as f:
        f.write(str(offset))

def poll_updates():
    offset = get_offset()
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    
    # We will pass the offset but we'll also log raw responses
    params = {"timeout": 5, "offset": offset}
    try:
        response = requests.get(url, params=params).json()
        
        with open(DEBUG_LOG, 'a') as f:
            f.write(f"\n[{time.time()}] RAW RESPONSE: {json.dumps(response)}\n")
            
        if not response.get("ok"):
            return "Failed to get updates"
            
        messages = []
        for result in response.get("result", []):
            update_id = result["update_id"]
            if update_id >= offset:
                offset = update_id + 1
                
            msg = result.get("message", {})
            text = msg.get("text", "")
            if text:
                messages.append(text)
                
        save_offset(offset)
        return messages
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        if os.path.exists(OFFSET_FILE):
            os.remove(OFFSET_FILE)
        print("Offset reset.")
    else:
        print(json.dumps(poll_updates()))
