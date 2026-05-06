#!/home/john/Thunderbird/.venv/bin/python
import os
import imaplib
import email
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
from core.communication.email_security import verify_sender

# Load secure env
load_dotenv("/home/john/Thunderbird/.env.concierge")

# Configuration
IMAP_SERVER = "imap.gmail.com"
EMAIL_USER = "d2mconcierge@gmail.com"
EMAIL_PASSWORD = os.environ.get("D2M_CONCIERGE_PASSWORD")
EMAIL_INBOX = Path("/home/john/Thunderbird/OpsCenter/collaboration/email_inbox.md")

def fetch_and_process():
    if not EMAIL_PASSWORD:
        logging.error("D2M_CONCIERGE_PASSWORD not set.")
        return
        
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, 'UNSEEN')
        for num in messages[0].split():
            res, msg = mail.fetch(num, '(RFC822)')
            for response in msg:
                if isinstance(response, tuple):
                    msg = email.message_from_bytes(response[1])
                    sender = msg.get("From")
                    subject = msg.get("Subject", "")
                    if verify_sender(sender):
                        EMAIL_INBOX.parent.mkdir(parents=True, exist_ok=True)
                        with open(EMAIL_INBOX, "a") as f:
                            f.write(f"NEXUS: {subject}\n")
                    else:
                        print(f"Unauthorized: {sender}")
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    while True:
        fetch_and_process()
        time.sleep(60)
