#!/usr/bin/env python3
"""
One-shot: send the Grace-gift email as a REPLY IN THREAD on johnloucks3.
Commander directive 2026-06-16: WF-17 waived, Hale executes the send.
To: stef@bbenefits.net  Cc: johnloucks3@gmail.com  From: johnloucks3@gmail.com
Thread: 19eac7e1135c239f (the Oya/Explora Journeys thread).
"""
import base64, json, sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN = "/home/john/Thunderbird/creds/johnloucks3_token.json"  # gitleaks:allow — file path, not a credential
THREAD_ID = "19eac7e1135c239f"
TO = "stef@bbenefits.net"
CC = "johnloucks3@gmail.com"
HTML = "/home/john/Thunderbird/drafts/burcham_send_final.gmail.html"
TXT  = "/home/john/Thunderbird/drafts/burcham_firstcontact.txt"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.modify",
          "https://www.googleapis.com/auth/gmail.compose"]

def hdr(headers, name):
    return next((h["value"] for h in headers if h["name"].lower()==name.lower()), "")

creds = Credentials.from_authorized_user_info(json.loads(Path(TOKEN).read_text()), SCOPES)
if not creds.valid:
    creds.refresh(Request())
    Path(TOKEN).write_text(creds.to_json())
svc = build("gmail","v1",credentials=creds)

prof = svc.users().getProfile(userId="me").execute()
acct = prof.get("emailAddress")
print("ACCOUNT:", acct)
assert acct == "johnloucks3@gmail.com", f"WRONG ACCOUNT {acct} — aborting"

thread = svc.users().threads().get(userId="me", id=THREAD_ID, format="metadata",
            metadataHeaders=["Message-ID","References","Subject","From"]).execute()
msgs = thread.get("messages", [])
last = msgs[-1]
lh = last["payload"]["headers"]
last_msgid = hdr(lh,"Message-ID")
refs = hdr(lh,"References")
subj = hdr(lh,"Subject")
if not subj.lower().startswith("re:"):
    subj = "Re: " + subj
references = (refs + " " + last_msgid).strip() if refs else last_msgid
print(f"THREAD last msg from: {hdr(lh,'From')}")
print(f"IN-REPLY-TO: {last_msgid}")
print(f"SUBJECT: {subj}")

msg = MIMEMultipart("alternative")
msg["To"] = TO
msg["Cc"] = CC
msg["From"] = "johnloucks3@gmail.com"
msg["Subject"] = subj
if last_msgid:
    msg["In-Reply-To"] = last_msgid
    msg["References"] = references
msg.attach(MIMEText(Path(TXT).read_text(), "plain", "utf-8"))
msg.attach(MIMEText(Path(HTML).read_text(), "html", "utf-8"))

raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
if "--send" not in sys.argv:
    print("\nDRY RUN (pass --send to actually send). Nothing sent.")
    sys.exit(0)

sent = svc.users().messages().send(userId="me", body={"raw": raw, "threadId": THREAD_ID}).execute()
print("\n✅ SENT. id:", sent.get("id"), "threadId:", sent.get("threadId"), "labels:", sent.get("labelIds"))
