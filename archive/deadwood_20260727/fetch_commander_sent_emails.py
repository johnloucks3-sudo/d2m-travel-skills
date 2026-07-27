"""Fetch all sent emails from johnloucks3@gmail.com since Dec 1, 2025."""
import json, sys, os
from pathlib import Path
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

sys.stdout.reconfigure(line_buffering=True)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
TOKEN_FILE = THUNDERBIRD_DIR / "gmail_token_commander.json"
OUTPUT_FILE = THUNDERBIRD_DIR / "output" / "johnloucks3_sent_emails_dec2025.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
SINCE_DATE = "2025/12/01"

creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    TOKEN_FILE.write_text(creds.to_json())
service = build("gmail", "v1", credentials=creds)

# Fetch all sent message references with pagination
print("Fetching sent message list...", flush=True)
all_refs = []
page_token = None
page = 0
while True:
    page += 1
    params = {"userId": "me", "q": f"in:sent after:{SINCE_DATE}", "maxResults": 500}
    if page_token:
        params["pageToken"] = page_token
    results = service.users().messages().list(**params).execute()
    batch = results.get("messages", [])
    all_refs.extend(batch)
    page_token = results.get("nextPageToken")
    print(f"  Page {page}: {len(batch)} messages (total: {len(all_refs)})", flush=True)
    if not page_token:
        break

print(f"\nTotal sent messages: {len(all_refs)}", flush=True)

# Fetch details
print("Fetching details...", flush=True)
emails = []
for i, ref in enumerate(all_refs):
    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(all_refs)}...", flush=True)
    try:
        msg = service.users().messages().get(
            userId="me", id=ref["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date", "Cc"]
        ).execute()
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        emails.append({
            "id": msg["id"],
            "date": headers.get("date", ""),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "cc": headers.get("cc", ""),
            "subject": headers.get("subject", ""),
            "snippet": msg.get("snippet", ""),
        })
    except Exception as e:
        print(f"  Error on {ref['id']}: {e}", flush=True)

# Save
output = {
    "fetch_date": datetime.now().isoformat(),
    "account": "johnloucks3@gmail.com",
    "query": f"in:sent after:{SINCE_DATE}",
    "total": len(emails),
    "emails": emails,
}
OUTPUT_FILE.parent.mkdir(exist_ok=True)
with open(OUTPUT_FILE, "w") as f:
    json.dump(output, f, indent=2, default=str)

print(f"\nSaved {len(emails)} emails to {OUTPUT_FILE}", flush=True)
print(f"Date range: {emails[-1]['date'][:10]} to {emails[0]['date'][:10]}", flush=True)

# Show recent 30 subject lines
print(f"\n--- Recent 30 sent emails ---", flush=True)
for e in emails[:30]:
    to = e.get("to", "")[:35]
    subj = e.get("subject", "(no subject)")[:65]
    print(f"  {e['date'][:16]:<16} | {to:<35} | {subj}", flush=True)
