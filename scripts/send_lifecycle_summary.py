#!/usr/bin/env python3
"""
Send lifecycle summary email to Commander (johnloucks3@gmail.com)
FROM d2mconcierge@gmail.com — per Intel Full Send SO 27 MAR 2026
"""

import json
import base64
import sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError as e:
    print(f"ERROR: Missing Google libraries: {e}")
    sys.exit(1)

TOKEN_PATH = Path("/home/john/Thunderbird/creds/gmail_token.json")

def get_gmail_service():
    """Authenticate to d2mconcierge Gmail."""
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def send_email(service, to, subject, html_body):
    """Send email from d2mconcierge."""
    msg = MIMEMultipart("alternative")
    msg["To"] = to
    msg["Subject"] = subject
    msg["From"] = "d2mconcierge@gmail.com"
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    return result.get("id", "UNKNOWN")

def main():
    service = get_gmail_service()

    subject = "[COS HALE] D2M Client Lifecycle — Canonical Framework Locked · 3 Voyages · 73 Touchpoints"

    html_body = """
<html>
<body style="font-family: Georgia, serif; background-color: #f7f3ea; padding: 20px; color: #1a1a1a;">

<div style="max-width: 700px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; border: 1px solid #ddd;">

<h2 style="color: #0000ff; margin-top: 0;">D2M Client Lifecycle — HEART OF THE BUSINESS</h2>
<p style="color: #666; font-size: 14px;">COS Report · Victoria 'Victory' Hale, SES-6 · 2026-04-17</p>

<hr style="border: 1px solid #0000ff;">

<h3>Commander —</h3>

<p>Canonical lifecycle framework locked and coded. Three production voyages. 73 touchpoints. All timers armed. Summary below.</p>

<h3 style="color: #0000ff;">Documents Produced</h3>

<table style="width: 100%; border-collapse: collapse; font-size: 14px;">
<tr style="background: #1a1a6e; color: white;">
  <th style="padding: 8px; text-align: left;">Document</th>
  <th style="padding: 8px; text-align: left;">Location</th>
  <th style="padding: 8px; text-align: left;">TPs</th>
</tr>

<tr style="background: #f0f0f0;">
  <td style="padding: 8px;"><strong>Canonical 23-TP Framework</strong></td>
  <td style="padding: 8px;">Memory: reference_canonical_lifecycle_touchpoints.md</td>
  <td style="padding: 8px;">23</td>
</tr>

<tr>
  <td colspan="3" style="padding: 4px 8px; background: #0000ff; color: white; font-weight: bold;">KUKLINSKI — Viking Mars Panama Canal · Dec 17–27, 2026</td>
</tr>
<tr>
  <td style="padding: 6px 8px;">Lifecycle Plan</td>
  <td style="padding: 6px 8px;">D2M/lifecycle/Kuklinski_Viking_Panama_Lifecycle.md</td>
  <td style="padding: 6px 8px;">16</td>
</tr>
<tr style="background: #f0f0f0;">
  <td style="padding: 6px 8px;">Touchpoints JSON</td>
  <td style="padding: 6px 8px;">D2M/clients/kuklinski_touchpoints.json</td>
  <td style="padding: 6px 8px;">24 (incl arcs)</td>
</tr>
<tr>
  <td style="padding: 6px 8px;">Email Drafts (all TPs)</td>
  <td style="padding: 6px 8px;">output/Drafts_for_Client_Lifecycle_Engagement.md</td>
  <td style="padding: 6px 8px;">16 emails</td>
</tr>

<tr>
  <td colspan="3" style="padding: 4px 8px; background: #0000ff; color: white; font-weight: bold;">LOUCKS — Regent Grandeur Panama Canal · Dec 29 – Jan 14, 2027</td>
</tr>
<tr>
  <td style="padding: 6px 8px;">Lifecycle Plan</td>
  <td style="padding: 6px 8px;">D2M/lifecycle/Loucks_Grandeur_PanamaPacific_Lifecycle.md</td>
  <td style="padding: 6px 8px;">22</td>
</tr>
<tr style="background: #f0f0f0;">
  <td style="padding: 6px 8px;">Touchpoints JSON</td>
  <td style="padding: 6px 8px;">D2M/clients/loucks_regent_touchpoints.json</td>
  <td style="padding: 6px 8px;">22</td>
</tr>
<tr>
  <td style="padding: 6px 8px;">Email Drafts (all TPs)</td>
  <td style="padding: 6px 8px;">output/Loucks_Regent_Lifecycle_Engagement.md</td>
  <td style="padding: 6px 8px;">22 emails</td>
</tr>

<tr>
  <td colspan="3" style="padding: 4px 8px; background: #0000ff; color: white; font-weight: bold;">McLEOD — Regent Grandeur Lesser Antilles · Dec 19–29, 2026</td>
</tr>
<tr>
  <td style="padding: 6px 8px;">Lifecycle Plan</td>
  <td style="padding: 6px 8px;">D2M/lifecycle/McLeod_Grandeur_LesserAntilles_Lifecycle.md</td>
  <td style="padding: 6px 8px;">27</td>
</tr>
<tr style="background: #f0f0f0;">
  <td style="padding: 6px 8px;">Touchpoints JSON</td>
  <td style="padding: 6px 8px;">D2M/clients/mcleod_lesser_antilles_touchpoints.json</td>
  <td style="padding: 6px 8px;">27</td>
</tr>
<tr>
  <td style="padding: 6px 8px;">Email Drafts (all TPs)</td>
  <td style="padding: 6px 8px;">output/McLeod_LesserAntilles_Lifecycle_Engagement.md</td>
  <td style="padding: 6px 8px;">27 emails</td>
</tr>
</table>

<h3 style="color: #0000ff;">Automation</h3>
<ul>
  <li><strong>Lifecycle Scheduler:</strong> D2M/d2m_lifecycle_scheduler.py — reads all touchpoint JSONs daily</li>
  <li><strong>Systemd Timer:</strong> d2m-lifecycle.timer — fires daily at 0530 MDT</li>
  <li><strong>Actions:</strong> Search window initiations, weekly intel reports (Mondays), portal opening alerts, TP email placement, payment alerts, monthly validations</li>
  <li><strong>State tracking:</strong> state/lifecycle_scheduler_state.json — prevents duplicate firings</li>
</ul>

<h3 style="color: #0000ff;">Key Dates (Next 90 Days)</h3>
<table style="width: 100%; border-collapse: collapse; font-size: 13px;">
<tr style="background: #1a1a6e; color: white;">
  <th style="padding: 6px;">Date</th>
  <th style="padding: 6px;">Event</th>
  <th style="padding: 6px;">Client</th>
</tr>
<tr><td style="padding: 4px 6px;">Apr 22</td><td style="padding: 4px 6px;">McLeod TP-0.5 Booking Validation</td><td style="padding: 4px 6px;">McLeod</td></tr>
<tr style="background:#f0f0f0;"><td style="padding: 4px 6px;">Apr 24</td><td style="padding: 4px 6px;">Loucks TP-0.5 Welcome/Validation</td><td style="padding: 4px 6px;">Loucks</td></tr>
<tr><td style="padding: 4px 6px;">Apr 25</td><td style="padding: 4px 6px;">McLeod TP-0.6 Insurance Advisory</td><td style="padding: 4px 6px;">McLeod</td></tr>
<tr style="background:#f0f0f0;"><td style="padding: 4px 6px;">Apr 30</td><td style="padding: 4px 6px;">Loucks TP-0.6 Insurance Review</td><td style="padding: 4px 6px;">Loucks</td></tr>
<tr><td style="padding: 4px 6px;">May 1</td><td style="padding: 4px 6px;">McLeod FCC Application + Kuklinski TP-2</td><td style="padding: 4px 6px;">Both</td></tr>
<tr style="background:#f0f0f0;"><td style="padding: 4px 6px;">May 15</td><td style="padding: 4px 6px;">Voyage Previews — Loucks + McLeod</td><td style="padding: 4px 6px;">Both</td></tr>
<tr><td style="padding: 4px 6px;">May 23</td><td style="padding: 4px 6px;"><strong>McLeod excursion portal opens</strong></td><td style="padding: 4px 6px;">McLeod</td></tr>
<tr style="background:#f0f0f0;"><td style="padding: 4px 6px;">Jun 2</td><td style="padding: 4px 6px;"><strong>Loucks excursion portal opens (8pm ET)</strong></td><td style="padding: 4px 6px;">Loucks</td></tr>
<tr><td style="padding: 4px 6px;">Jun 15-17</td><td style="padding: 4px 6px;">Airfare deliveries — all 3 clients</td><td style="padding: 4px 6px;">All</td></tr>
<tr style="background:#f0f0f0;"><td style="padding: 4px 6px;">Jul 1</td><td style="padding: 4px 6px;">McLeod payment reminder #1</td><td style="padding: 4px 6px;">McLeod</td></tr>
<tr><td style="padding: 4px 6px;">Jul 11</td><td style="padding: 4px 6px;">Loucks payment reminder #1</td><td style="padding: 4px 6px;">Loucks</td></tr>
<tr style="background:#f0f0f0;"><td style="padding: 4px 6px;"><strong>Jul 22</strong></td><td style="padding: 4px 6px;"><strong>McLeod FINAL PAYMENT — $12,193.15</strong></td><td style="padding: 4px 6px;"><strong>McLeod</strong></td></tr>
</table>

<h3 style="color: #0000ff;">Drive Sync</h3>
<p>All files are under ~/Thunderbird/ which mirrors nightly at 23:00 to Google Drive (d2mconcierge:Thunderbird_Mirror/). Tonight's sync will capture everything.</p>

<h3 style="color: #0000ff;">COO Authority Acknowledged</h3>
<p>Standing Order 2026-04-17: <em>"From this point on, I am putting you in charge of day-to-day and week-to-week operations and staff assignments, COO."</em></p>
<p>Saved to persistent memory. All staff tasking, search windows, weekly reports, and draft placement now run under COS authority. Financial commits and client sends still require your approval.</p>

<hr style="border: 1px solid #0000ff;">
<p style="font-size: 13px; color: #666;">
73 touchpoints across 3 voyages. Timer armed at 0530 daily. All artifacts in Drive sync path.<br>
The Wing is running.<br><br>
— Hale, COS<br>
Dreams2Memories Travel, LLC
</p>

</div>
</body>
</html>
"""

    msg_id = send_email(service, "johnloucks3@gmail.com", subject, html_body)
    print(f"✅ Summary email sent to johnloucks3@gmail.com — Message ID: {msg_id}")

if __name__ == "__main__":
    main()
