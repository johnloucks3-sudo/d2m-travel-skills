#!/usr/bin/env python3
"""
Stage Spencer Grand Voyage Master Intake Form Email Draft in d2mconcierge.
Deadline Accelerated: Monday 21:00 MT (for Commander review and edits).
"""
import sys
import os
from pathlib import Path

# Add Thunderbird root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.email.thunderbird_gmail import gmail_create_draft_sync

def stage_draft():
    to_email = "johnloucks3@gmail.com"  # Staged for Commander review
    subject = "[COMMANDER REVIEW] Spencer Grand Voyage (12 Pax) Master Client & Trip Information Intake Form"
    
    body_html = """<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }
  .container { max-width: 650px; background: #ffffff; margin: 0 auto; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border: 1px solid #dcdcdc; }
  .header { background-color: #07076b; color: #ffffff; padding: 25px; text-align: center; }
  .header h1 { margin: 0; font-size: 22px; text-transform: uppercase; letter-spacing: 1px; }
  .header p { margin: 5px 0 0 0; font-size: 13px; color: #a8c4f0; }
  .content { padding: 30px; line-height: 1.6; }
  .section-title { font-size: 16px; font-weight: bold; color: #07076b; border-bottom: 2px solid #07076b; padding-bottom: 5px; margin-top: 25px; }
  .button-container { text-align: center; margin: 30px 0; }
  .btn { background-color: #07076b; color: #ffffff !important; text-decoration: none; padding: 14px 28px; font-weight: bold; border-radius: 4px; display: inline-block; font-size: 15px; }
  .footer { background-color: #07076b; color: #a8c4f0; padding: 20px; text-align: center; font-size: 12px; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>DREAMS2MEMORIES TRAVEL</h1>
    <p>Grand Voyage Master Client & Trip Information Intake</p>
  </div>
  <div class="content">
    <p>Dear Spencer,</p>
    <p>To ensure flawless coordination, stateroom allocations, flight seating, visa compliance, and dining reservations for your party of 12 on the upcoming Grand Voyage, we have prepared your personalized Master Client & Trip Information Intake portal.</p>
    
    <div class="button-container">
      <a href="https://spencer.d2mluxury.quest/intake?token=d2m-spencer-12pax-secure" class="btn">ACCESS SECURE 12-PAX INTAKE FORM</a>
    </div>

    <div class="section-title">WHAT THIS FORM COVERS FOR YOUR PARTY OF 12:</div>
    <ul>
      <li><strong>Section 1:</strong> Primary Contact Logistics & Billing</li>
      <li><strong>Section 2:</strong> 12-Passenger Passport Details & Stateroom Pairing</li>
      <li><strong>Section 3:</strong> Departure Airports, Airfare Class & Pre/Post Land Extensions</li>
      <li><strong>Section 4:</strong> Dietary Restrictions, CPAP/Medical Needs & Milestone Celebrations</li>
      <li><strong>Section 5:</strong> Non-Traveling Emergency Contacts & Travel Insurance Selection</li>
    </ul>

    <p>Please complete this at your earliest convenience so our Travel Architecture team can lock in your group arrangements.</p>

    <p>Warm regards,<br>
    <strong>Victory Hale</strong><br>
    Chief of Staff, Thunderbird Wing<br>
    Dreams2Memories Travel, LLC</p>
  </div>
  <div class="footer">
    DREAMS2MEMORIES TRAVEL, LLC · Authorized by John A Loucks III, Owner<br>
    Confidential & Secure Client Intake Portal
  </div>
</div>
</body>
</html>"""

    print("Staging draft in d2mconcierge under THUNDERBIRD-Commander-Review...")
    draft = gmail_create_draft_sync(to_email, subject, body_html, persona_id="CONCIERGE")
    print(f"✅ Draft staged successfully! Draft ID: {draft.get('id')}")

if __name__ == "__main__":
    stage_draft()
