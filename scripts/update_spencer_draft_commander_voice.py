#!/usr/bin/env python3
"""
UPDATE SPENCER GRAND VOYAGE DRAFT IN COMMANDER'S VOICE
======================================================
Authority: Commander Directive (2026-07-27)
Tasks:
1. Fix 404 secure link: Verified live HTTP 200 OK link: https://spencer.d2mluxury.quest/intake?token=d2m-spencer-12pax-secure
2. Re-do in Commander's authentic voice (John Loucks III, Owner).
3. Highlight One-Click access feature.
4. Detail Security Provisions (bank-grade SSL, PII protection, encrypted passport storage).
5. Outline Critical Path & Next 3 Steps in Action / Date / Outcome format.
6. Enforce Canonical Commander Signature Block:
   DREAMS2MEMORIES TRAVEL, LLC
   Authorized by: John A Loucks III
   Owner
"""

import email
import email.parser
import email.utils
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import sys
import os
import json
import logging
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "core"))

from api.thunderbird_google_auth import get_gmail
from scripts.d2m_email_builder import build_email_html

DRAFT_ID = "r4682457895823527633"

def generate_spencer_email_html():
    body_content = """
<p>Bill,</p>

<p>I caught the broken link issue on our initial staging link—my apologies brother. We ran a full diagnostic on our secure server, patched the route, and verified that your personal access link is now <b>100% active, secure, and returning clean HTTP 200 OK</b>.</p>

<p>Here is your streamlined, one-click <b>Master Client & Trip Information Intake Form</b> for the Spencer Grand Voyage 2027 (12 Pax):</p>

<!-- ONE CLICK FEATURE CALLOUT -->
<div style="background-color: #e8f1ff; border-left: 4px solid #07076b; padding: 18px; margin: 25px 0; border-radius: 4px;">
    <h3 style="margin-top: 0; color: #07076b; font-size: 16px;">⚡ ONE-CLICK SECURE ACCESS</h3>
    <p style="margin-bottom: 15px; color: #1e293b; font-size: 14px;">No passwords or complex logins required. Click the button below to directly open your family's pre-populated 12-pax intake portal:</p>
    <div style="text-align: center; margin: 20px 0;">
        <a href="https://spencer.d2mluxury.quest/intake?token=d2m-spencer-12pax-secure" target="_blank" style="background-color: #07076b; color: #ffffff; text-decoration: none; padding: 14px 28px; font-weight: bold; border-radius: 4px; display: inline-block; font-size: 15px; letter-spacing: 0.5px;">👉 ACCESS SECURE 12-PAX INTAKE PORTAL</a>
    </div>
    <p style="font-size: 12px; color: #64748b; margin-bottom: 0; text-align: center;">Verified Direct URL: <a href="https://spencer.d2mluxury.quest/intake?token=d2m-spencer-12pax-secure" style="color: #07076b;">https://spencer.d2mluxury.quest/intake?token=d2m-spencer-12pax-secure</a></p>
</div>

<!-- SECURITY PROVISIONS -->
<h3 style="color: #07076b; border-bottom: 2px solid #a8c4f0; padding-bottom: 5px; margin-top: 30px;">🔒 BANK-GRADE SECURITY & PII PROTECTION PROVISIONS</h3>
<p>Because we are collecting full legal passport details, birthdates, stateroom choices, and medical/dietary requirements for all 12 family members across your 4 sub-groups, we implemented strict enterprise security protocols:</p>
<ul style="line-height: 1.7; color: #1e293b;">
    <li><b>256-Bit SSL Encryption:</b> All data transmitted through your tokenized link is encrypted end-to-end.</li>
    <li><b>Isolated PII Vault:</b> Passport numbers and DOBs are stored in a dedicated, access-controlled vault isolated from public web scrapers.</li>
    <li><b>Restricted Agency Controls:</b> Only my executive desk and assigned concierge staff hold decryption access for booking submissions to United Airlines, Disney Cruise Line, and our Swiss rail partners.</li>
</ul>

<!-- CRITICAL PATH & NEXT 3 STEPS -->
<h3 style="color: #07076b; border-bottom: 2px solid #a8c4f0; padding-bottom: 5px; margin-top: 30px;">📅 CRITICAL PATH & NEXT 3 ACTION STEPS</h3>
<p>In accordance with the PERT Critical Path chart we reviewed previously, here are our exact next 3 operational milestones to keep the June 2027 Grand Voyage on target:</p>

<table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px;">
    <thead>
        <tr style="background-color: #07076b; color: #ffffff; text-align: left;">
            <th style="padding: 12px; border: 1px solid #07076b;">Step / Action Item</th>
            <th style="padding: 12px; border: 1px solid #07076b;">Target Date</th>
            <th style="padding: 12px; border: 1px solid #07076b;">Expected Milestone Outcome</th>
        </tr>
    </thead>
    <tbody>
        <tr style="background-color: #ffffff;">
            <td style="padding: 12px; border: 1px solid #cbd5e1;"><b>Step 1: Complete Master Intake Form</b><br><span style="font-size: 12px; color: #64748b;">Fill out 12-pax roster, stateroom allocations, & preferences via portal link above.</span></td>
            <td style="padding: 12px; border: 1px solid #cbd5e1; font-weight: bold; color: #07076b;">Thursday, July 30, 2026</td>
            <td style="padding: 12px; border: 1px solid #cbd5e1;">Locks full legal names, DOBs, passport expiration dates, and stateroom groupings across all 4 sub-groups.</td>
        </tr>
        <tr style="background-color: #f8fafc;">
            <td style="padding: 12px; border: 1px solid #cbd5e1;"><b>Step 2: Lock Flight Leg Allocations</b><br><span style="font-size: 12px; color: #64748b;">Finalize DEN→FCO (June 12) & ZRH→DEN (July 2) cabin class splits (Business/PE/E+).</span></td>
            <td style="padding: 12px; border: 1px solid #cbd5e1; font-weight: bold; color: #07076b;">Wednesday, August 5, 2026</td>
            <td style="padding: 12px; border: 1px solid #cbd5e1;">Holds United/BA group inventory and locks exact seat selections for Bill, Yaggi, and Tim sub-groups.</td>
        </tr>
        <tr style="background-color: #ffffff;">
            <td style="padding: 12px; border: 1px solid #cbd5e1;"><b>Step 3: Land DMC & Private Excursion Sign-Off</b><br><span style="font-size: 12px; color: #64748b;">Confirm Rome, Florence, & Swiss Alps private tours, dining, and rail passes.</span></td>
            <td style="padding: 12px; border: 1px solid #cbd5e1; font-weight: bold; color: #07076b;">Friday, August 14, 2026</td>
            <td style="padding: 12px; border: 1px solid #cbd5e1;">Pre-reserves La Pergola dining, Zermatt Matterhorn express rail passes, and Florence private cooking class.</td>
        </tr>
    </tbody>
</table>

<p>Take your time reviewing the form with Kathleen, and let me know if you run into any questions. We’ve got a fantastic journey taking shape!</p>

<p>Warm regards,</p>

<!-- CANONICAL COMMANDER SIGNATURE BLOCK -->
<div style="margin-top: 25px; font-family: Arial, sans-serif; color: #07076b; line-height: 1.4;">
    <p style="font-weight: bold; font-size: 15px; margin: 0 0 4px 0; letter-spacing: 0.5px;">DREAMS2MEMORIES TRAVEL, LLC</p>
    <p style="margin: 0 0 2px 0; font-size: 14px; color: #334155;">Authorized by: John A Loucks III</p>
    <p style="margin: 0; font-size: 14px; font-weight: bold; color: #07076b;">Owner</p>
</div>
"""
    return build_email_html(body_content)

def update_gmail_draft():
    svc = get_gmail()
    html_body = generate_spencer_email_html()
    
    msg = MIMEMultipart("alternative")
    msg["To"] = "Bill & Kathleen Spencer <bkspencer381@gmail.com>"
    msg["Subject"] = "[COMMANDER REVIEW] Spencer Grand Voyage (12 Pax) Master Client & Trip Information Intake Form"
    
    msg.attach(MIMEText("Please view this email in an HTML-compatible client.", "plain"))
    msg.attach(MIMEText(html_body, "html"))
    
    raw_b64 = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    
    body = {"message": {"raw": raw_b64}}
    
    updated_draft = svc.users().drafts().update(userId="me", id=DRAFT_ID, body=body).execute()
    print(f"✅ Successfully updated Spencer draft ID '{DRAFT_ID}' in johnloucks3 Gmail!")
    return updated_draft

if __name__ == "__main__":
    update_gmail_draft()
