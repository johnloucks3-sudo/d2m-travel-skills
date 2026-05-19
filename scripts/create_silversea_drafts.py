#!/usr/bin/env python3
"""Create all three Silversea Cruises draft emails for Commander review."""

import json, base64, sys, html as htmlmod
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = Path("/home/john/Thunderbird/config/persona_gmail_token.json")
FROM_EMAIL = "d2mconcierge@gmail.com"
TO_EMAIL = "johnloucks3@gmail.com"


def get_service():
    with open(TOKEN_FILE) as f:
        td = json.load(f)
    creds = Credentials(
        token=td.get("token"),
        refresh_token=td.get("refresh_token"),
        token_uri=td.get("token_uri"),
        client_id=td.get("client_id"),
        client_secret=td.get("client_secret"),
        scopes=td.get("scopes", ["https://www.googleapis.com/auth/gmail.modify"]),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def create_draft(service, body_html, subject):
    msg = MIMEMultipart("alternative")
    msg["to"] = TO_EMAIL
    msg["from"] = FROM_EMAIL
    msg["subject"] = subject
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()

    print(f"  \u2705 Draft created: {draft['id']} \u2014 \"{subject}\"")
    return draft


def markdown_to_html(md_path):
    """Wrap markdown file in an HTML pre block for Gmail readability."""
    with open(md_path) as f:
        content = f.read()
    escaped = htmlmod.escape(content)
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="background:#f7f3ea; color:#1a1a1a; font-family:Georgia,serif; padding:2em;">
<pre style="white-space:pre-wrap; font-family:'Courier New',monospace; font-size:13px; line-height:1.5;">
{escaped}
</pre>
</body>
</html>"""


def main():
    service = get_service()
    print("Connected to Gmail.\n")

    output_dir = Path("/home/john/Thunderbird/output")

    # 1. Internal Wing HTML
    with open(output_dir / "silversea_v1_internal.html") as f:
        internal_html = f.read()
    create_draft(
        service,
        internal_html,
        "Silversea Cruises \u2014 Full-Spectrum Scan (Internal Wing)",
    )

    # 2. Pro Bono HTML
    with open(output_dir / "silversea_v2_pro_bono.html") as f:
        probono_html = f.read()
    create_draft(
        service,
        probono_html,
        "Silversea Cruises \u2014 Company Profile & Market Analysis (Service Version)",
    )

    # 3. Raw Markdown intel report
    md_html = markdown_to_html(output_dir / "silversea_scan_2026-05-18.md")
    create_draft(
        service,
        md_html,
        "Silversea Cruises \u2014 Full Intel Report (Raw Markdown)",
    )

    print("\nAll three drafts created in d2mconcierge Gmail.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
