#!/usr/bin/env python3
"""
Hale Brief Email Sender — Direct Gmail API Integration
Composes and sends daily brief email to Commander (johnloucks3@gmail.com).
Sends from d2mconcierge@gmail.com.
SO 27 MAR 2026: Briefs are FULL SENDS, not drafts. Bypasses WF-17 gate.
"""

import logging
import json
import base64
from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger("hale_brief_email_sender")

MT = timezone(timedelta(hours=-6))
BRIEFS_DOMAIN = "itinerary.d2mluxury.quest"
FROM_EMAIL = "d2mconcierge@gmail.com"
TO_EMAIL = "johnloucks3@gmail.com"
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_FILE = Path.home() / "Thunderbird" / "gmail_token.json"
CREDENTIALS_FILE = Path.home() / ".credentials.json"


def compose_brief_email(date_str: str) -> tuple[str, str]:
    """
    Compose brief email subject and body.
    Returns: (subject, html_body)
    """
    brief_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    brief_time = datetime.now(MT).strftime("%H:%M")

    subject = f"HALE — DAILY BRIEF | {date_str} 06:00 MT"

    html_body = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.6; color: #1a1a1a; }}
            .container {{ max-width: 900px; margin: 0 auto; background: #f7f3ea; padding: 20px; }}
            .header {{ text-align: center; padding: 20px 0; border-bottom: 3px solid #0000ff; margin-bottom: 30px; }}
            .header h1 {{ color: #0000ff; margin: 0; font-size: 24px; }}
            .header p {{ color: #666; margin: 5px 0 0 0; font-size: 13px; }}
            .visual-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 30px; }}
            .visual-card {{
                background: white;
                border-radius: 8px;
                padding: 20px;
                border: 1px solid #ddd;
                text-align: center;
            }}
            .visual-card h3 {{ margin: 0 0 10px 0; color: #0000ff; font-size: 16px; }}
            .visual-card p {{ margin: 0 0 15px 0; color: #666; font-size: 13px; }}
            .visual-link {{
                display: inline-block;
                background: #0000ff;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                text-decoration: none;
                font-weight: bold;
                font-size: 13px;
            }}
            .visual-link:hover {{ background: #0000cc; }}
            .decisions {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #ffa500; }}
            .decisions h3 {{ margin: 0 0 15px 0; color: #ffa500; font-size: 14px; }}
            .decision-item {{ margin-bottom: 12px; font-size: 13px; padding-left: 20px; position: relative; }}
            .decision-item:before {{ content: "→"; position: absolute; left: 0; color: #0000ff; font-weight: bold; }}
            .footer {{ text-align: center; padding: 20px 0; border-top: 1px solid #ddd; color: #999; font-size: 11px; margin-top: 20px; }}
            .footer p {{ margin: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 HALE — DAILY OPERATIONAL BRIEF</h1>
                <p>Generated {date_str} · 06:00 MT · Commander John Loucks</p>
            </div>

            <div class="visual-grid">
                <div class="visual-card">
                    <h3>📊 Client Lifecycle Wheel</h3>
                    <p>7 active clients, urgency-coded segments, FPD countdown arcs. Click segment for detail panel.</p>
                    <a href="https://{BRIEFS_DOMAIN}/briefs/{date_str}/lifecycle-wheel/" class="visual-link">View Lifecycle Wheel →</a>
                </div>

                <div class="visual-card">
                    <h3>💰 Financial Waterfall</h3>
                    <p>Commission pipeline flow: Prospects → Booked → At-Risk → Projected. Allianz claim divergence shown.</p>
                    <a href="https://{BRIEFS_DOMAIN}/briefs/{date_str}/financial-waterfall/" class="visual-link">View Waterfall →</a>
                </div>

                <div class="visual-card">
                    <h3>🔥 Task Heat Map</h3>
                    <p>Clients × Task Types grid. Urgency-colored, effort-encoded. Hover for task roster by cell.</p>
                    <a href="https://{BRIEFS_DOMAIN}/briefs/{date_str}/task-heatmap/" class="visual-link">View Heat Map →</a>
                </div>

                <div class="visual-card">
                    <h3>⚠️ Risk Matrix</h3>
                    <p>Likelihood × Disruption scatter. Quadrants: Escalate (red), Mitigate (yellow), Monitor, Accept. Action registry below.</p>
                    <a href="https://{BRIEFS_DOMAIN}/briefs/{date_str}/risk-matrix/" class="visual-link">View Risk Matrix →</a>
                </div>
            </div>

            <div class="decisions">
                <h3>⚡ DECISIONS NEEDED FROM COMMANDER</h3>
                <div class="decision-item">
                    <strong>Approve 11 Gmail Drafts?</strong> Kuklinski (validation), McLeod (Silver Muse 60-day + Grandeur TP0.5/TP0.6), Westbrook (Perx + SkyLux), Furlow/Nichols/Ely (CAK). All staged in d2mconcierge drafts folder.
                </div>
                <div class="decision-item">
                    <strong>Initiate Lyons FPD Outreach?</strong> Nancy & Ken Lyons — FPD May 11 (14 days remaining). Direct Commander action required.
                </div>
                <div class="decision-item">
                    <strong>Chase Furlow $15,486 Payment?</strong> Final payment was due Apr 1. Confirm received or authorize A9 follow-up.
                </div>
                <div class="decision-item">
                    <strong>Re-Auth TESS?</strong> Financial feed is blind. Run: <code>python3 thunderbird_tess.py --authorize</code> to restore commission visibility.
                </div>
            </div>

            <div class="footer">
                <p><strong>HALE — Col Victoria "Iron Vic" Hale | Chief of Staff | Dreams2Memories Travel, LLC</strong></p>
                <p>This brief is generated automatically at 05:50 MT daily and sent at 06:00 MT.</p>
                <p style="margin-top: 10px; color: #ccc;">Link expires in 90 days. Briefs archived locally + Google Drive.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return subject, html_body


def _get_gmail_service():
    """Get authenticated Gmail service using stored token."""
    creds = None

    # Load stored token
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError(f"Gmail token not found at {TOKEN_FILE}. Run: python3 thunderbird_gmail.py --authorize")

    return build("gmail", "v1", credentials=creds)


def send_brief_email(date_str: str) -> bool:
    """
    Send brief email via Gmail API directly (no MCP, no headless Claude).
    SO 27 MAR 2026: Briefs are FULL SENDS to johnloucks3@gmail.com.
    """
    try:
        subject, html_body = compose_brief_email(date_str)

        logger.info(f"Composing brief email for {date_str}...")
        logger.info(f"Subject: {subject}")
        logger.info(f"To: {TO_EMAIL}")
        logger.info(f"From: {FROM_EMAIL}")

        # Build MIME message
        message = MIMEMultipart("alternative")
        message["to"] = TO_EMAIL
        message["from"] = FROM_EMAIL
        message["subject"] = subject
        message.attach(MIMEText("", "plain"))  # Plain text part (empty)
        message.attach(MIMEText(html_body, "html"))  # HTML part

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Send via Gmail API
        service = _get_gmail_service()
        sent = service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()

        message_id = sent.get("id")
        logger.info(f"✅ Brief email sent successfully for {date_str}")
        logger.info(f"Message ID: {message_id}")

        # Update pending marker to sent status
        pending_dir = Path("/home/john/Thunderbird/output/briefs")
        pending_file = pending_dir / f"pending_brief_send_{date_str}.json"
        if pending_file.exists():
            email_data = json.loads(pending_file.read_text())
            email_data["status"] = "sent"
            email_data["sent_at"] = datetime.now(MT).isoformat()
            email_data["message_id"] = message_id
            pending_file.write_text(json.dumps(email_data, indent=2))
            logger.info(f"Updated pending marker to sent status")

        return True

    except HttpError as e:
        logger.error(f"Gmail API error: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to send brief email: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    today_str = datetime.now(MT).strftime("%Y-%m-%d")
    success = send_brief_email(today_str)
    exit(0 if success else 1)
