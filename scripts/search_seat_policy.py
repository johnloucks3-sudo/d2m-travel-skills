import sys
import json
sys.path.append("/home/john/Thunderbird")
sys.path.append("/home/john/Thunderbird/core/email")

from thunderbird_gmail import _get_gmail_service

def search():
    service = _get_gmail_service()
    # Search query
    query = '"seat assignment" (Ely OR Loucks OR d2mconcierge@gmail.com)'
    
    try:
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])
        print(f"Found {len(messages)} messages.")
        for msg in messages:
            print(f"ID: {msg['id']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    search()
