#!/usr/bin/env python3
"""
hale_save_output.py — Save TTYD session output to Ann's email
==============================================================
Dreams2Memories Travel, LLC | Thunderbird Wing

Ann uses TTYD on YOGA to research Japan travel. When she finishes a
session, this script saves her output to a local file AND emails it
to her Outlook inbox so she can access it later.

Two modes:
  1. Pipe mode:   cat session_output.txt | python3 hale_save_output.py
  2. File mode:   python3 hale_save_output.py --file session_output.txt
  3. Message mode: python3 hale_save_output.py --msg "Research notes..."

Always saves to: ~/Thunderbird/ann_workspace/YYYY-MM-DD_HHMM_output.md
Always sends to: iamheer@outlook.com

Usage:
    # Save and email session output
    python3 hale_save_output.py --file my_research.txt

    # Pipe from TTYD session
    python3 hale_save_output.py < research_output.txt

    # Quick note
    python3 hale_save_output.py --msg "Found a great ryokan in Kyoto"

    # Draft only (don't send, just save locally + create Gmail draft)
    python3 hale_save_output.py --file my_research.txt --draft-only

    # Title your session for better email subject
    python3 hale_save_output.py --file my_research.txt --title "Kyoto Ryokan Research"

Author: Ms. Victoria "Victory" Hale, SES-6 — Thunderbird Wing Chief of Staff
Re-Attack: 2026-05-22 — After A7 Sterling audit identified wrong-recipient bug
"""

import argparse
import base64
import json
import logging
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ── Constants ──────────────────────────────────────────────────────────────────

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
ANN_WORKSPACE = THUNDERBIRD_DIR / "ann_workspace"
LOG_DIR = THUNDERBIRD_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
ANN_WORKSPACE.mkdir(exist_ok=True)

ANN_EMAIL = "iamheer@outlook.com"
ANN_NAME = "Ann"
DEFAULT_SUBJECT = "Your TTYD Session Output — Dreams2Memories Travel"

# Commander's Gmail token (verified working)
COMMANDER_TOKEN = THUNDERBIRD_DIR / "creds" / "johnloucks3_token.json"
SEND_FROM = "johnloucks3@gmail.com"

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "hale_save_output.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("hale_save_output")

# ── Gmail Service ─────────────────────────────────────────────────────────────

def get_gmail_service():
    """Load Commander's Gmail service."""
    if not COMMANDER_TOKEN.exists():
        log.error(f"Token not found: {COMMANDER_TOKEN}")
        sys.exit(1)

    token_data = json.loads(COMMANDER_TOKEN.read_text())
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/gmail.modify"]),
    )

    if creds.expired and creds.refresh_token:
        log.info("Token expired — refreshing...")
        creds.refresh(Request())
        token_data["token"] = creds.token
        COMMANDER_TOKEN.write_text(json.dumps(token_data, indent=2))
        log.info("Token refreshed")

    return build("gmail", "v1", credentials=creds)


def send_to_ann(service, subject: str, body_text: str):
    """Send email to Ann's Outlook inbox."""
    msg = MIMEMultipart("alternative")
    msg["From"] = SEND_FROM
    msg["To"] = ANN_EMAIL
    msg["Subject"] = subject

    html = f"""<html><body style="font-family: Georgia, serif; color: #0000ff; background: #f7f3ea; padding: 20px;">
<h2 style="color: #003087;">Your Saved Work — Dreams2Memories Travel</h2>
<hr style="border: 1px solid #003087;">
<pre style="font-family: 'Courier New', monospace; font-size: 13px; white-space: pre-wrap; color: #000; background: #eee8db; padding: 15px; border-radius: 4px;">
{body_text}
</pre>
<hr style="border: 1px solid #003087;">
<p style="font-size: 11px; color: #666;">Saved from your TTYD session on YOGA · {datetime.now().strftime('%Y-%m-%d %H:%M MT')}</p>
</body></html>"""

    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result


def create_draft_to_ann(service, subject: str, body_text: str):
    """Create a Gmail draft addressed to Ann (for Commander review before send)."""
    msg = MIMEMultipart("alternative")
    msg["From"] = SEND_FROM
    msg["To"] = ANN_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Save Ann's TTYD output to local file and email to her"
    )
    parser.add_argument("--file", help="Read output from file")
    parser.add_argument("--msg", help="Quick message instead of file")
    parser.add_argument("--title", default="", help="Session title for email subject")
    parser.add_argument("--draft-only", action="store_true",
                        help="Create draft in Commander's Gmail instead of sending directly")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    # ── Get content ─────────────────────────────────────────────────────────
    content = ""
    source = ""

    if args.file:
        fpath = Path(args.file)
        if not fpath.exists():
            log.error(f"File not found: {args.file}")
            sys.exit(1)
        content = fpath.read_text(encoding="utf-8", errors="replace")
        source = f"file: {args.file}"
    elif args.msg:
        content = args.msg
        source = "inline message"
    else:
        # Read from stdin (pipe mode)
        if not sys.stdin.isatty():
            content = sys.stdin.read()
            source = "stdin (pipe)"
        else:
            log.error("No input. Provide --file, --msg, or pipe content via stdin.")
            sys.exit(1)

    if not content.strip():
        log.error("Empty content — nothing to save or send.")
        sys.exit(1)

    # ── Save to local file ──────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    safe_title = args.title.replace(" ", "_").replace("/", "-") if args.title else "session_output"
    local_file = ANN_WORKSPACE / f"{timestamp}_{safe_title}.md"
    local_file.write_text(
        f"# {args.title or 'TTYD Session Output'}\n"
        f"**Saved:** {datetime.now().strftime('%Y-%m-%d %H:%M MT')}\n"
        f"**Source:** {source}\n\n"
        f"{content}\n"
    )
    log.info(f"Saved locally: {local_file} ({len(content)} chars)")

    if args.dry_run:
        log.info("Dry run — no email sent")
        return 0

    # ── Build subject ───────────────────────────────────────────────────────
    subject = DEFAULT_SUBJECT
    if args.title:
        subject = f"📝 {args.title} — Dreams2Memories Travel"
    elif len(content) > 80:
        subject = f"📝 {content[:80].strip()}..."
    else:
        subject = f"📝 {content.strip()}"

    # ── Send or draft ───────────────────────────────────────────────────────
    service = get_gmail_service()

    if args.draft_only:
        result = create_draft_to_ann(service, subject, content)
        log.info(f"Draft created in your Gmail: {result.get('id')}")
        log.info(f"Review and send from your Drafts folder")
    else:
        result = send_to_ann(service, subject, content)
        log.info(f"Email sent to {ANN_EMAIL}: {result.get('id')}")
        log.info(f"Subject: {subject}")
        log.info(f"Saved to: {local_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
