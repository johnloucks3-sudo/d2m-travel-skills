import base64
from email.mime.text import MIMEText
from thunderbird_gmail import _get_gmail_service, USER_EMAIL

try:
    print("Getting service")
    service = _get_gmail_service()
    print(f"Service got for {USER_EMAIL}")
    
    msg = MIMEText("Manual python test from goose", 'plain')
    msg["to"] = "7192910742@tmomail.net"
    msg["from"] = USER_EMAIL
    
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    res = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"Sent: {res}")
except Exception as e:
    import traceback
    traceback.print_exc()
