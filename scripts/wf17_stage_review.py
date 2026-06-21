#!/usr/bin/env python3
"""
WF-17 Review Staging — Stage client draft for Commander review in johnloucks3.

Usage:
    python3 scripts/wf17_stage_review.py \
        --subject "Your Regent Booking — Validation" \
        --to "client@email.com" \
        --client "Nancy Lyons" \
        --html drafts/lyons_validation.html \
        [--d2m-draft-id <msg_id>]   # optional — include link to d2mconcierge send copy

What it does:
    1. Creates a review copy in johnloucks3 labeled Commander Review/New (red)
    2. Optionally includes a direct link to the d2mconcierge draft for sending
    3. Prints the message ID for logging

Flow after staging:
    Commander opens Commander Review/New in johnloucks3 → reviews →
    clicks d2mconcierge link in footer → sends from d2mconcierge →
    Wing relabels to Commander Review/Done (run with --mark-done <msg_id>)
"""

import argparse, json, os, sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
import base64

sys.path.insert(0, '/home/john/Thunderbird')
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

LABEL_NEW  = 'THUNDERBIRD-Commander-Review'   # canonical (label_system.py)
LABEL_DONE_ADD    = 'THUNDERBIRD-Processed'           # canonical done state
LABEL_DONE_REMOVE = 'THUNDERBIRD-Commander-Review'    # remove from review queue


def _label_id(service, name: str) -> str:
    """Resolve a label name to its Gmail API ID. Raises KeyError if absent."""
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    for lbl in labels:
        if lbl['name'] == name:
            return lbl['id']
    raise KeyError(f"Label not found in Gmail: {name!r} — run scripts/label_system.py setup")

# d2mconcierge Gmail URL for direct draft link
D2M_DRAFT_URL = "https://mail.google.com/mail/?authuser=d2mconcierge%40gmail.com#drafts/{msg_id}"


def _get_johnloucks3_service():
    token = json.load(open('/home/john/.config/google-workspace-mcp/tokens.json'))
    creds_data = json.load(open('/home/john/.config/google-workspace-mcp/credentials.json'))
    creds = Credentials(
        token=token['access_token'],
        refresh_token=token['refresh_token'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=creds_data['client_id'],
        client_secret=creds_data['client_secret'],
    )
    if creds.expired:
        creds.refresh(Request())
    return build('gmail', 'v1', credentials=creds)


def _get_d2mconcierge_service():
    token_path = '/home/john/Thunderbird/config/persona_gmail_token.json'
    creds = Credentials.from_authorized_user_file(token_path)
    return build('gmail', 'v1', credentials=creds)


def _build_review_html(subject, to_addr, client, html_body, d2m_draft_id=None):
    """Wrap draft content in a review card for johnloucks3."""
    d2m_link_section = ""
    if d2m_draft_id:
        url = D2M_DRAFT_URL.format(msg_id=d2m_draft_id)
        d2m_link_section = f"""
        <div style="margin:16px 0;padding:12px 16px;background:#fff3cd;border-left:4px solid #ff9800;font-family:Georgia,serif;">
          <strong>📤 Ready to send?</strong> Open this draft in d2mconcierge and send from there:<br>
          <a href="{url}" style="color:#0000ff;font-weight:bold;">→ Open draft in d2mconcierge</a>
          <br><small>From: concierge@d2mluxury.quest | To: {to_addr}</small>
        </div>"""

    return f"""<!DOCTYPE html><html><body style="font-family:Georgia,serif;background:#f7f3ea;margin:0;padding:16px;">
<div style="max-width:700px;margin:0 auto;">
  <!-- WF-17 Review Banner -->
  <div style="background:#fb4c2f;color:#fff;padding:12px 16px;font-family:Georgia,serif;font-size:14px;font-weight:bold;border-radius:4px 4px 0 0;">
    🔴 WF-17 — COMMANDER REVIEW REQUIRED &nbsp;|&nbsp; Client: {client} &nbsp;|&nbsp; To: {to_addr}
  </div>
  <div style="background:#fff;border:1px solid #ddd;border-top:none;padding:16px;border-radius:0 0 4px 4px;">
    {d2m_link_section}
    <hr style="border:1px solid #eee;margin:16px 0;">
    <div style="font-size:12px;color:#666;margin-bottom:12px;">
      <strong>Subject:</strong> {subject}<br>
      <strong>To:</strong> {to_addr}
    </div>
    <!-- Actual email content below -->
    {html_body}
    <hr style="border:1px solid #eee;margin:16px 0;">
    <div style="font-size:11px;color:#999;">
      Staged by Thunderbird Wing · WF-17 Gate · Reply "SEND" to trigger d2mconcierge dispatch
    </div>
  </div>
</div>
</body></html>"""


def stage_for_review(subject, to_addr, client, html_body, d2m_draft_id=None):
    """Create a review draft in johnloucks3 labeled THUNDERBIRD-Commander-Review."""
    service = _get_johnloucks3_service()
    label_id = _label_id(service, LABEL_NEW)

    review_html = _build_review_html(subject, to_addr, client, html_body, d2m_draft_id)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[WF-17] {subject}"
    msg['To'] = 'johnloucks3@gmail.com'
    msg['From'] = 'johnloucks3@gmail.com'
    msg['Date'] = formatdate()
    msg.attach(MIMEText(review_html, 'html'))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId='me',
        body={'message': {'raw': raw, 'labelIds': [label_id, 'DRAFT']}}
    ).execute()

    msg_id = draft.get('message', {}).get('id', '')
    draft_id = draft.get('id', '')

    if msg_id:
        service.users().messages().modify(
            userId='me', id=msg_id,
            body={'addLabelIds': [label_id], 'removeLabelIds': []}
        ).execute()

    print(f"✅ Staged: [{subject[:50]}]")
    print(f"   DraftID={draft_id} | MsgID={msg_id}")
    print(f"   Label: {LABEL_NEW}")
    return msg_id, draft_id


def mark_done(msg_id):
    """Move a review item from Commander-Review → Processed."""
    service = _get_johnloucks3_service()
    done_id = _label_id(service, LABEL_DONE_ADD)
    review_id = _label_id(service, LABEL_DONE_REMOVE)
    service.users().messages().modify(
        userId='me', id=msg_id,
        body={'addLabelIds': [done_id], 'removeLabelIds': [review_id]}
    ).execute()
    print(f"✅ Marked done: {msg_id} → {LABEL_DONE_ADD}")


def create_d2m_draft(subject, to_addr, html_body):
    """Create the actual send copy in d2mconcierge. Returns message ID."""
    service = _get_d2mconcierge_service()

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['To'] = to_addr
    msg['From'] = 'concierge@d2mluxury.quest'
    msg['Date'] = formatdate()
    msg.attach(MIMEText(html_body, 'html'))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId='me',
        body={'message': {'raw': raw, 'labelIds': ['DRAFT']}}
    ).execute()

    msg_id = draft.get('message', {}).get('id', '')
    print(f"✅ d2mconcierge send copy: MsgID={msg_id}")
    return msg_id


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Stage WF-17 review item in johnloucks3')
    parser.add_argument('--subject', required=True)
    parser.add_argument('--to', required=True, dest='to_addr')
    parser.add_argument('--client', required=True)
    parser.add_argument('--html', required=True, help='Path to HTML file with email body')
    parser.add_argument('--d2m-draft-id', default=None, help='d2mconcierge message ID for send link')
    parser.add_argument('--mark-done', default=None, help='Move message ID from New to Done')
    parser.add_argument('--create-d2m', action='store_true', help='Also create d2mconcierge send copy')
    args = parser.parse_args()

    if args.mark_done:
        mark_done(args.mark_done)
        sys.exit(0)

    html_body = Path(args.html).read_text()

    d2m_draft_msg_id = args.d2m_draft_id
    if args.create_d2m:
        d2m_draft_msg_id = create_d2m_draft(args.subject, args.to_addr, html_body)

    stage_for_review(args.subject, args.to_addr, args.client, html_body, d2m_draft_msg_id)
