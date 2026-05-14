import sys
import json
sys.path.append("/home/john/Thunderbird")
sys.path.append("/home/john/Thunderbird/core/email")

from thunderbird_gmail import _get_gmail_service, _decode_body, _extract_headers

def read_thread(thread_id):
    service = _get_gmail_service()
    thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()
    
    messages = []
    for msg in thread.get("messages", []):
        payload = msg.get("payload", {})
        headers = _extract_headers(payload.get("headers", []))
        body = _decode_body(payload)
        messages.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "No Subject"),
            "from": headers.get("From", "Unknown"),
            "body": body[:500] # First 500 chars
        })
    print(json.dumps(messages, indent=2))

if __name__ == "__main__":
    thread_id = sys.argv[1]
    read_thread(thread_id)
