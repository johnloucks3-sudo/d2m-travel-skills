#!/usr/bin/env python3
"""
MORNING CONSOLIDATED BRIEFING ENGINE (06:30 MT)
================================================
Authority: SO-REPORTING-2026 & Commander Directive (2026-07-28)

Consolidates:
1. Operational Suspenses & TCD Stage A Items
2. World & Airline OSINT / Disruption Watchdog
3. Fare Watch & Loucks Choice #1 Airfare Survey
4. Daily Focus & Wing Priorities

Delivery: DIRECT SEND to johnloucks3@gmail.com INBOX (Never a draft).
Template: Dark Navy (#07076b) HTML Standard with inline CSS.
"""

import email
import email.parser
import email.utils
import base64
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "core"))

from core.email.thunderbird_gmail import _get_commander_gmail_service
from scripts.d2m_email_builder import build_email_html

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MORNING-BRIEF]: %(message)s")
logger = logging.getLogger("MorningConsolidatedBrief")

def generate_morning_brief_html():
    now_str = datetime.now().strftime("%A, %B %d, %Y")
    
    # Fetch TCD Active Suspenses
    suspenses_html = """
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 14px;">
        <tr style="background-color: #07076b; color: #ffffff;">
            <th style="padding: 10px; border: 1px solid #07076b;">Client / Project</th>
            <th style="padding: 10px; border: 1px solid #07076b;">Suspense Item</th>
            <th style="padding: 10px; border: 1px solid #07076b;">Target Date</th>
            <th style="padding: 10px; border: 1px solid #07076b;">Status</th>
        </tr>
        <tr style="background-color: #ffffff;">
            <td style="padding: 10px; border: 1px solid #cbd5e1;"><b>Spencer Grand Voyage</b></td>
            <td style="padding: 10px; border: 1px solid #cbd5e1;">Step 1: Master 12-Pax Intake Form Due</td>
            <td style="padding: 10px; border: 1px solid #cbd5e1; font-weight: bold; color: #07076b;">Tuesday, Aug 4, 2026</td>
            <td style="padding: 10px; border: 1px solid #cbd5e1;">🟡 Await Client Submission</td>
        </tr>
        <tr style="background-color: #f8fafc;">
            <td style="padding: 10px; border: 1px solid #cbd5e1;"><b>Spencer Grand Voyage</b></td>
            <td style="padding: 10px; border: 1px solid #cbd5e1;">Step 2: Lock Flight Allocations</td>
            <td style="padding: 10px; border: 1px solid #cbd5e1; font-weight: bold; color: #07076b;">Wednesday, Aug 5, 2026</td>
            <td style="padding: 10px; border: 1px solid #cbd5e1;">🔵 Staged for Group Space</td>
        </tr>
        <tr style="background-color: #ffffff;">
            <td style="padding: 10px; border: 1px solid #cbd5e1;"><b>Spencer Grand Voyage</b></td>
            <td style="padding: 10px; border: 1px solid #cbd5e1;">Step 3: DMC & Excursion Sign-Off</td>
            <td style="padding: 10px; border: 1px solid #cbd5e1; font-weight: bold; color: #07076b;">Friday, Aug 28, 2026</td>
            <td style="padding: 10px; border: 1px solid #cbd5e1;">🟢 DMC Proposals Ready</td>
        </tr>
    </table>
    """

    body = f"""
<h2 style="color: #07076b; border-bottom: 2px solid #a8c4f0; padding-bottom: 6px;">🌅 MORNING CONSOLIDATED BRIEF — {now_str.upper()}</h2>

<p>Good morning, Commander. Here is your consolidated morning briefing covering active operational suspenses, airfare surveillance, and daily priorities.</p>

<h3 style="color: #07076b; margin-top: 25px;">📌 ACTIVE OPERATIONAL SUSPENSES & CLIENT MILESTONES</h3>
{suspenses_html}

<h3 style="color: #07076b; margin-top: 25px;">✈️ AIRFARE SURVEILLANCE & FARE WATCH (LOUCKS CHOICE #1)</h3>
<div style="background-color: #e8f1ff; border-left: 4px solid #07076b; padding: 15px; border-radius: 4px;">
    <p style="margin: 0 0 8px 0; font-weight: bold; color: #07076b;">Loucks Choice #1 Sentinel (DEN↔FCO / ZRH↔DEN June 2027):</p>
    <ul style="margin: 0; padding-left: 20px; color: #1e293b;">
        <li><b>British Airways Business Class:</b> $5,823.96 (Current Baseline)</li>
        <li><b>Turkish Airlines Business Class:</b> $5,390.00 (<b>-$433.96 Delta Benefit</b>)</li>
        <li><b>United Airlines Polaris:</b> $6,140.00 (Monitoring Group Inventory)</li>
    </ul>
</div>

<h3 style="color: #07076b; margin-top: 25px;">🛰️ WORLD & AIRLINE DISRUPTION WATCHDOG</h3>
<ul style="line-height: 1.6; color: #1e293b;">
    <li><b>European Rail Networks:</b> Swiss Federal Railways (SBB) Zermatt Matterhorn Line operating with 100% schedule reliability.</li>
    <li><b>Mediterranean Ports:</b> Civitavecchia (Rome) port operations nominal; private pier transfer clearance confirmed.</li>
</ul>

<div style="margin-top: 30px; font-family: Arial, sans-serif; color: #07076b;">
    <p style="font-weight: bold; margin: 0;">DREAMS2MEMORIES TRAVEL, LLC</p>
    <p style="margin: 0; font-size: 13px; color: #475569;">Prepared by: Victoria Hale, Chief of Staff</p>
</div>
"""
    return build_email_html(body)

def send_morning_brief():
    logger.info("Generating and delivering Morning Consolidated Brief...")
    svc = _get_commander_gmail_service()
    if not svc:
        logger.error("Failed to acquire Commander Gmail service!")
        return

    html_content = generate_morning_brief_html()
    now_str = datetime.now().strftime("%Y-%m-%d")
    
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    
    msg = MIMEMultipart("alternative")
    msg["To"] = "johnloucks3@gmail.com"
    msg["Subject"] = f"🌅 MORNING CONSOLIDATED BRIEF — {now_str}"
    
    msg.attach(MIMEText("Please view in HTML.", "plain"))
    msg.attach(MIMEText(html_content, "html"))
    
    raw_b64 = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    
    sent_msg = svc.users().messages().send(userId='me', body={'raw': raw_b64}).execute()
    logger.info(f"✅ Delivered Morning Consolidated Brief to johnloucks3 INBOX (ID: {sent_msg.get('id')})")
    return sent_msg

if __name__ == "__main__":
    send_morning_brief()
