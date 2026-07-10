#!/usr/bin/env python3
"""
send_d2mconcierge_email.py — Direct-send from d2mconcierge@gmail.com.

Built 2026-07-05 per Commander directive: "ALL AI sending should be from d2m
or else we get the spam, phishing warnings." Sends from d2mconcierge@gmail.com
(NOT the custom domain alias — avoids the SPF/DKIM/DMARC gap on d2mluxury.quest
that caused the iCloud bounce; NOT johnloucks3 personal inbox — avoids Google
flagging automated API sends on a personal account).

Credential: reconstructed from the working MCP gmail-mcp OAuth pair
(~/.gmail-mcp/d2mconcierge/gcp-oauth.keys.json + credentials.json) since
creds/d2mconcierge_token.json (separate, older token) is revoked/expired.

Usage:
  python3 scripts/send_d2mconcierge_email.py \
    --body path/to/body_content.html \
    --to recipient@example.com \
    --cc "cc1@example.com, cc2@example.com" \
    --subject "Subject line" \
    [--brand]   # wrap body in canonical D2M dark-navy template (d2m_email_builder.py)
"""
import argparse
import base64
import json
import sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

THUNDERBIRD = Path(__file__).parent.parent
OAUTH_KEYS = Path("/home/john/.gmail-mcp/d2mconcierge/gcp-oauth.keys.json")
TOKEN_PATH = Path("/home/john/.gmail-mcp/d2mconcierge/credentials.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def authenticate():
    oauth = json.loads(OAUTH_KEYS.read_text())["installed"]
    tok = json.loads(TOKEN_PATH.read_text())
    creds = Credentials(
        token=tok["access_token"],
        refresh_token=tok["refresh_token"],
        token_uri=oauth["token_uri"],
        client_id=oauth["client_id"],
        client_secret=oauth["client_secret"],
        scopes=[tok["scope"]],
    )
    if not creds.valid:
        creds.refresh(Request())
        tok["access_token"] = creds.token
        TOKEN_PATH.write_text(json.dumps(tok, indent=2))
    return creds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--body", required=True)
    ap.add_argument("--to", required=True)
    ap.add_argument("--cc", default=None)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--brand", action="store_true", help="wrap in canonical D2M dark-navy template")
    args = ap.parse_args()

    body_html = Path(args.body).read_text(encoding="utf-8")

    if args.brand:
        sys.path.insert(0, str(THUNDERBIRD / "scripts"))
        from d2m_email_builder import build_email_html
        body_html = build_email_html(body_html)

    creds = authenticate()
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    email_address = profile.get("emailAddress")
    print(f"Authenticated as: {email_address}")
    if email_address != "d2mconcierge@gmail.com":
        print("WARNING: not d2mconcierge@gmail.com — aborting")
        sys.exit(1)

    message = MIMEMultipart("alternative")
    message["to"] = args.to
    if args.cc:
        message["cc"] = args.cc
    message["from"] = "Dreams2Memories <d2mconcierge@gmail.com>"
    message["subject"] = args.subject
    message.attach(MIMEText(body_html, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        print(f"SENT message_id={sent.get('id')}")
        verify = service.users().messages().get(userId="me", id=sent["id"]).execute()
        print(f"VERIFIED labels: {verify.get('labelIds')}")
    except HttpError as e:
        print(f"Gmail API Error: {e.resp.status} {e.content}")
        sys.exit(1)


if __name__ == "__main__":
    main()
