import sys
import json
sys.path.append("/home/john/Thunderbird")
sys.path.append("/home/john/Thunderbird/core/email")

from thunderbird_gmail import _get_gmail_service, _decode_body, _extract_headers

def read_thread_all(thread_id):
    service = _get_gmail_service()
    thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()
    
    for msg in thread.get("messages", []):
        payload = msg.get("payload", {})
        headers = _extract_headers(payload.get("headers", []))
        body = _decode_body(payload)
        # Check if the keyword is in the body
        if "ELY" in body or "NICHOLS" in body or "FURLOW" in body:
            print(f"--- Message {msg['id']} ---")
            print(f"Subject: {headers.get('Subject')}")
            print(body[:1000])

if __name__ == "__main__":
    thread_id = sys.argv[1]
    read_thread_all(thread_id)
