import sys
import json
sys.path.append("/home/john/Thunderbird")
sys.path.append("/home/john/Thunderbird/core/email")

from thunderbird_gmail import _get_gmail_service, _decode_body, _extract_headers

def read_message(message_id):
    service = _get_gmail_service()
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    
    payload = msg.get("payload", {})
    headers = _extract_headers(payload.get("headers", []))
    body = _decode_body(payload)
    
    print(f"Subject: {headers.get('Subject', 'No Subject')}")
    print(f"From: {headers.get('From', 'Unknown')}")
    print(f"Body: {body[:1000]}")
    print("-" * 20)

if __name__ == "__main__":
    message_id = sys.argv[1]
    read_message(message_id)
