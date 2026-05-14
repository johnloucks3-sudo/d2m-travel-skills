import sys
import json
sys.path.append("/home/john/Thunderbird")
sys.path.append("/home/john/Thunderbird/core/email")

from thunderbird_gmail import _get_gmail_service

def list_snippets():
    service = _get_gmail_service()
    query = "(FURLOW OR ELY OR NICHOLS) (cruise OR hotel OR transfer) after:2026-05-07"
    results = service.users().messages().list(userId="me", q=query).execute()
    messages = results.get("messages", [])
    
    for msg in messages:
        m = service.users().messages().get(userId="me", id=msg["id"], format="metadata", metadataHeaders=["Subject"]).execute()
        print(f"ID: {msg['id']}, Subject: {m.get('payload', {}).get('headers', [{}])[0].get('value', 'No Subject')}, Snippet: {m.get('snippet', '')}")

if __name__ == "__main__":
    list_snippets()
