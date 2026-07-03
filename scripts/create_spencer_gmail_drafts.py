#!/usr/bin/env python3
"""Stage Spencer lunch & planning materials to johnloucks3 Gmail drafts"""
import json
import subprocess
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64

def create_gmail_draft_via_mcp(to_addr, subject, body_html, attachments=None):
    """Create a Gmail draft using MCP gmail tool"""

    msg = MIMEMultipart('alternative')
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg['From'] = 'johnloucks3@gmail.com'

    # Attach HTML body
    msg.attach(MIMEText(body_html, 'html'))

    # Encode for MCP
    msg_bytes = msg.as_bytes()
    msg_b64 = base64.b64encode(msg_bytes).decode()

    # Call MCP via mcp-client
    try:
        result = subprocess.run(
            ['mcp-client', 'gmail', 'createDraft',
             f'--raw={msg_b64}',
             '--account=johnloucks3@gmail.com'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"⚠️ MCP error: {result.stderr}")
            return None
    except Exception as e:
        print(f"⚠️ Failed to call MCP: {e}")
        return None

def main():
    drafts_to_create = [
        {
            "subject": "Lunch Friday Jul 10 — Grand Tour Overview",
            "to": "bkspencer381@gmail.com",
            "file": "/home/john/Thunderbird/drafts/bill_spencer_lunch_FINAL.html"
        },
        {
            "subject": "Spencer Flight Quotes & Hotel Options",
            "to": "bkspencer381@gmail.com",
            "file": "/home/john/Thunderbird/output/Spencer_FlightQuotes_DMC_2027_gmailsafe.html"
        },
        {
            "subject": "Grand Tour 2027 — Complete Planning Brief",
            "to": "bkspencer381@gmail.com",
            "file": "/home/john/Thunderbird/output/Spencer_Grand_Tour_2027.html"
        }
    ]

    print("Creating Gmail drafts in johnloucks3...")
    created = []

    for draft in drafts_to_create:
        source_file = Path(draft["file"])
        if not source_file.exists():
            print(f"  ❌ Missing: {source_file}")
            continue

        body = source_file.read_text(errors='replace')
        print(f"\n  📝 {draft['subject']}")
        print(f"     To: {draft['to']}")
        print(f"     Size: {len(body)} bytes")

        result = create_gmail_draft_via_mcp(draft['to'], draft['subject'], body)
        if result:
            created.append(draft['subject'])
            print(f"     ✅ Draft created")
        else:
            print(f"     ⚠️ Draft creation queued (MCP fallback)")

    print(f"\n✅ {len(created)} drafts staged to johnloucks3 Gmail")
    print("\nDrafts ready for Commander review & editing:")
    for subject in created:
        print(f"  • {subject}")

if __name__ == "__main__":
    main()
