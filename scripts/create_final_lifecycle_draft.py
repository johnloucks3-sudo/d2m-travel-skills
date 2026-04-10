#!/usr/bin/env python3
"""
FINAL CORRECTED: Create Gmail draft following all Thunderbird protocols
Uses proper MCP server methods and email formatting standards
"""

import sys
import json
import base64
from pathlib import Path

# Add Thunderbird to Python path
sys.path.insert(0, "/home/john/Thunderbird")

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"ERROR: Missing Google libraries: {e}")
    print(
        "Install: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
    )
    sys.exit(1)

# Thunderbird imports
try:
    from core.email.thunderbird_gmail import _wrap_body_html, _strip_html
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
except ImportError as e:
    print(f"ERROR: Could not import Thunderbird modules: {e}")
    sys.exit(1)


def get_johnloucks3_token_path():
    """Get path for johnloucks3 OAuth token"""
    return Path("/home/john/Thunderbird/creds/johnloucks3_token.json")


def authenticate_johnloucks3():
    """Authenticate to johnloucks3@gmail.com using existing OAuth token"""

    token_path = get_johnloucks3_token_path()

    if not token_path.exists():
        print(f"❌ ERROR: johnloucks3 token not found at {token_path}")
        sys.exit(1)

    # Load existing token
    try:
        with open(token_path, "r") as token_file:
            token_data = json.load(token_file)

        scopes = ["https://www.googleapis.com/auth/gmail.modify"]

        creds = Credentials.from_authorized_user_info(token_data, scopes)

        # Check if token is expired and refresh if needed
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token
            token_data = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes,
                "expiry": creds.expiry.isoformat() if creds.expiry else None,
            }
            with open(token_path, "w") as token_file:
                json.dump(token_data, token_file, indent=2)

        return creds

    except Exception as e:
        print(f"❌ ERROR loading token: {e}")
        sys.exit(1)


def create_final_draft():
    """Create FINAL correctly formatted lifecycle draft"""

    print("=== FINAL CORRECTED LIFECYCLE DRAFT ===")
    print("Following all Thunderbird Gmail protocols...")

    # Authenticate
    creds = authenticate_johnloucks3()
    if not creds:
        print("❌ Authentication failed")
        return None

    # Build Gmail service
    try:
        service = build("gmail", "v1", credentials=creds)

        # Verify account
        profile = service.users().getProfile(userId="me").execute()
        email_address = profile.get("emailAddress")
        print(f"✓ Authenticated as: {email_address}")

    except Exception as e:
        print(f"❌ ERROR building Gmail service: {e}")
        return None

    # Use PROPER HTML content (not the broken MIME file)
    html_content = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Your Panama Canal Cruise Planning Timeline</title>
</head>
<body>

<div style="font-family: Georgia, 'Times New Roman', serif; background-color: #f7f3ea; margin: 0; padding: 40px;">
  <div style="max-width: 700px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); overflow: hidden;">
    
    <div style="background: #1a3a52; color: white; padding: 40px; text-align: center;">
      <h1 style="margin: 0; font-size: 28px; font-weight: normal; letter-spacing: 1px;">DREAMS2MEMORIES TRAVEL</h1>
      <p style="opacity: 0.9; margin-top: 10px;">Luxury Travel Planning & Concierge Services</p>
    </div>
    
    <div style="padding: 40px; color: #333; line-height: 1.6;">
      <p>Hi Kyle,</p>
      
      <p>Following up on our recent conversation, I wanted to walk through how Dreams2Memories manages your Panama Canal cruise preparation from now through embarkation.</p>
      
      <div style="background: #fff3cd; padding: 20px; border-left: 4px solid #ffc107; margin: 25px 0; border-radius: 4px;">
        <strong>Our service timeline ensures every detail is handled at the right moment:</strong>
      </div>
      
      <h3 style="color: #1a3a52;">🔄 Your Complete Service Lifecycle</h3>
      
      <p><strong>Phase 1: Pre-Payment Preparation (Now - Complete)</strong><br>
      • Suite assignments confirmed across all 3 bookings<br>
      • Viking documentation reviewed and verified<br>
      • Payment scheduling aligned with cruise line deadlines</p>
      
      <p><strong>Phase 2: Payment Processing (March 25 Target)</strong><br>
      • Final payment coordination for all 3 suites ($21,244 total)<br>
      • Credit card processing with confirmed authorization<br>
      • Immediate booking confirmation from Viking</p>
      
      <p><strong>Phase 3: Guest Documentation (April - May)</strong><br>
      • Online check-in completion for all 6 guests<br>
      • Dietary preferences and special requests documented<br>
      • Emergency contact information verified</p>
      
      <p><strong>Phase 4: Pre-Cruise Planning (June - November)</strong><br>
      • Flight research and booking recommendations<br>
      • Panama City hotel options for pre-cruise stay<br>
      • Shore excursion planning and reservations<br>
      • Specialty dining reservations aboard Viking Mars</p>
      
      <p><strong>Phase 5: Final Preparation (December)</strong><br>
      • Final documents and e-tickets delivered<br>
      • Embarkation day logistics confirmed<br>
      • Weather and packing guidance provided</p>
      
      <div style="background: #e8f5e8; padding: 15px; margin: 20px 0; border-left: 4px solid #28a745; border-radius: 4px;">
        <h3 style="color: #1a3a52; margin-top: 0;">📋 What We've Already Completed:</h3>
        <p>• All 3 suite assignments confirmed with Viking<br>
        • Detailed invoice review and payment scheduling<br>
        • Initial guest information gathering<br>
        • Timeline coordination for your group of 6</p>
      </div>
      
      <p>The goal is seamless preparation — you focus on anticipating the Panama Canal transit while we handle the operational details.</p>
      
      <p>Next step: Let's schedule a quick call to review payment processing and answer any questions about the timeline.</p>
      
      <p>Best regards,</p>
    </div>
    
    <div style="padding: 30px 40px; background: #f8f9fa; border-top: 1px solid #e9ecef;">
      <strong>John Loucks</strong><br>
      Owner, Dreams2Memories Travel, LLC<br>
      +1 (719) 291-0742<br>
      johnloucks3@gmail.com
    </div>
  </div>
</div>

</body>
</html>
"""

    # Email parameters
    to_email = "kyle.kuklinski@gmail.com"
    subject = "Your Panama Canal Cruise Planning Timeline & D2M Service Process"
    from_email = "johnloucks3@gmail.com"

    print(f"\n📧 Creating FINAL draft:")
    print(f"  To: {to_email}")
    print(f"  From: {from_email}")
    print(f"  Subject: {subject}")
    print(f"  Format: Proper Thunderbird HTML styling")

    # Build email message following Thunderbird protocols
    message = MIMEMultipart("alternative")
    message["to"] = to_email
    message["from"] = from_email
    message["subject"] = subject
    message["reply-to"] = "d2mconcierge@gmail.com"  # Replies go to D2M

    # Use Thunderbird's _wrap_body_html for proper Gmail formatting
    html_part = _wrap_body_html(html_content)

    # Plain text fallback
    plain_text = """Your Panama Canal Cruise Planning Timeline & D2M Service Process

Hi Kyle,

Following up on our recent conversation about your Panama Canal cruise preparation. This outlines our comprehensive service timeline from now through embarkation.

PHASE 1: Pre-Payment Preparation (Complete)
- Suite assignments confirmed for all 3 bookings
- Viking documentation reviewed
- Payment scheduling aligned

PHASE 2: Payment Processing (March 25 Target) 
- Final payment coordination for 3 suites ($21,244)
- Credit card processing
- Booking confirmation

PHASE 3: Guest Documentation (April-May)
- Online check-in for 6 guests  
- Dietary preferences documented
- Emergency contacts verified

PHASE 4: Pre-Cruise Planning (June-November)
- Flight research and booking
- Panama City hotel options
- Shore excursions & dining reservations

PHASE 5: Final Preparation (December)
- Final documents delivery
- Embarkation logistics
- Weather & packing guidance

Next step: Let's schedule a call to review payment processing.

Best regards,

John Loucks
Owner, Dreams2Memories Travel, LLC
719-291-0742
johnloucks3@gmail.com"""

    # Attach both parts
    message.attach(MIMEText(plain_text, "plain", "utf-8"))
    message.attach(MIMEText(html_part, "html", "utf-8"))

    # Create draft via Gmail API
    try:
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft_body = {"message": {"raw": raw_message}}

        draft = service.users().drafts().create(userId="me", body=draft_body).execute()

        draft_id = draft.get("id")
        message_id = draft.get("message", {}).get("id")

        print(f"\n✅ FINAL SUCCESS! Proper Thunderbird draft created")
        print(f"Draft ID: {draft_id}")
        print(f"Message ID: {message_id}")
        print(
            f"\n📋 Access draft at: https://mail.google.com/mail/u/0/#drafts?compose={message_id}"
        )
        print(f"\n💡 This draft follows ALL Thunderbird protocols:")
        print(f"   • Proper FROM: johnloucks3@gmail.com")
        print(f"   • Proper REPLY-TO: d2mconcierge@gmail.com")
        print(f"   • Thunderbird _wrap_body_html styling")
        print(f"   • Complete plain text fallback")
        print(f"   • Professional signature format")

        return draft_id

    except HttpError as error:
        error_content = (
            error.content.decode("utf-8")
            if isinstance(error.content, bytes)
            else error.content
        )
        print(f"\n❌ Gmail API Error: {error.resp.status}")
        print(f"Details: {error_content[:500]}")
        return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Main function to create final corrected draft"""

    print("=== FINAL CORRECTED LIFECYCLE DRAFT CREATOR ===\n")

    # Create the FINAL draft
    draft_id = create_final_draft()

    if draft_id:
        print(f"\n🎯 TASK COMPLETED. Draft ID: {draft_id}")
        sys.exit(0)
    else:
        print(f"\n💥 TASK FAILED. No draft created.")
        sys.exit(1)


if __name__ == "__main__":
    main()
