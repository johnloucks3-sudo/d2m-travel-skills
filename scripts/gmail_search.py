import sys
from pathlib import Path
import json

# Add necessary paths
sys.path.append("/home/john/Thunderbird")
sys.path.append("/home/john/Thunderbird/core/email")

from thunderbird_gmail import _get_gmail_service

def search():
    service = _get_gmail_service()
    # Search query: (FURLOW OR ELY OR NICHOLS) AND (cruise OR hotel OR transfer) AND after:2026-05-07
    query = "(FURLOW OR ELY OR NICHOLS) (cruise OR hotel OR transfer) after:2026-05-07"
    
    try:
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])
        print(json.dumps(messages))
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    search()
