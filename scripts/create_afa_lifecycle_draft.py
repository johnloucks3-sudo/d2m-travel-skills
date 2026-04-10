#!/usr/bin/env python3
"""
FINAL AFA COLORS: Create Gmail draft with Air Force Academy color scheme (#003087)
Updated April 8, 2026 - all fares paid in full
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
    from core.email.thunderbird_gmail import _wrap_body_html
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


def create_afa_draft():
    """Create AFA-colored lifecycle draft"""

    print("=== AFA COLORS LIFECYCLE DRAFT ===")
    print("Air Force Academy color scheme (#003087 blue)")
    print("Status: All payments complete March 27, 2026")

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

    # HTML content with AFA colors (#003087 = Air Force Academy blue)
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
    
    <div style="background: linear-gradient(135deg, #003087 0%, #001a5c 100%); color: white; padding: 40px; text-align: center; border-bottom: 4px solid #A9B0B7;">
      <h1 style="margin: 0; font-size: 28px; font-weight: normal; letter-spacing: 1px;">DREAMS2MEMORIES TRAVEL</h1>
      <p style="opacity: 0.9; margin-top: 10px; color: #E6E8EA;">Luxury Travel Planning & Concierge Services</p>
    </div>
    
    <div style="padding: 40px; color: #333; line-height: 1.6;">
      <p>Hi Kyle,</p>
      
      <p>I wanted to share how Dreams2Memories manages your Panama Canal cruise preparation from now through embarkation—now that <strong>all payments are complete as of March 27, 2026</strong>.</p>
      
      <div style="background: #f0f8ff; padding: 20px; border-left: 4px solid #003087; margin: 25px 0; border-radius: 4px;">
        <strong style="color: #003087;">Our service timeline ensures every detail is handled at the right moment:</strong>
      </div>
      
      <h3 style="color: #003087; border-bottom: 2px solid #A9B0B7; padding-bottom: 10px; margin-top: 30px;">🔄 Your Complete Service Lifecycle</h3>
      
      <div style="margin: 25px 0; background: #f8f9fa; padding: 20px; border-radius: 8px;">
        <h4 style="color: #001a5c; margin-top: 0;">✅ COMPLETE: Phase 1 & 2 (January – April 8)</h4>
        <p><strong>Booking Preparation & Payment Processing</strong></p>
        <ul style="margin: 10px 0 0 20px;">
          <li>All 3 suite assignments confirmed with Viking</li>
          <li>Detailed invoice review complete</li>
          <li><strong>FINAL PAYMENT: $21,244 total for 3 suites processed and verified</strong></li>
          <li>Booking confirmation received from Viking</li>
          <li>Initial guest information gathered for your group of 6</li>
        </ul>
      </div>
      
      <div style="margin: 25px 0;">
        <h4 style="color: #003087;">📋 Phase 3: Guest Documentation (April – May)</h4>
        <ul style="margin: 10px 0 0 20px;">
          <li>Online check-in completion for all 6 guests</li>
          <li>Dietary preferences and special requests documented</li>
          <li>Emergency contact information verified</li>
          <li>Travel insurance confirmation (if applicable)</li>
        </ul>
      </div>
      
      <div style="margin: 25px 0;">
        <h4 style="color: #003087;">✈️ Phase 4: Travel Planning (June – November)</h4>
        <ul style="margin: 10px 0 0 20px;">
          <li>Flight research and booking recommendations</li>
          <li>Panama City hotel options for pre-cruise stay</li>
          <li>Shore excursion planning and reservations</li>
          <li>Specialty dining reservations aboard Viking Mars</li>
          <li>Port transportation and transfers coordination</li>
        </ul>
      </div>
      
      <div style="margin: 25px 0;">
        <h4 style="color: #003087;">📄 Phase 5: Final Preparation (December)</h4>
        <ul style="margin: 10px 0 0 20px;">
          <li>Final documents and e-tickets delivered</li>
          <li>Embarkation day logistics confirmed</li>
          <li>Weather and packing guidance provided</li>
          <li>Last-minute details and reminders</li>
        </ul>
      </div>
      
      <div style="background: #f0f8ff; padding: 20px; margin: 30px 0; border-radius: 8px; border: 1px solid #003087;">
        <h3 style="color: #001a5c; margin-top: 0;">📊 Executive Timeline View</h3>
        <p>I've prepared several visualizations that show your complete planning timeline:</p>
        <ul style="margin: 10px 0 0 20px;">
          <li><strong>Executive Gantt Chart</strong> – Full 12-month planning overview</li>
          <li><strong>Timeline Proposal</strong> – Key decision points and milestones</li>
          <li><strong>Service Phase Mapping</strong> – What happens when, from now to embarkation</li>
        </ul>
        <p>These are available for review whenever you'd like to see the full picture.</p>
      </div>
      
      <p>The goal remains seamless preparation—you focus on anticipating the Panama Canal transit while our team handles the operational details.</p>
      
      <p><strong>Next step:</strong> Would you like to schedule a brief call to review the guest documentation phase and answer any questions about the timeline?</p>
      
      <p>Best regards,</p>
    </div>
    
    <div style="padding: 30px 40px; background: #f8f9fa; border-top: 2px solid #003087;">
      <p style="color: #003087;"><strong>John Loucks</strong><br>
      <span style="color: #666;">Owner, Dreams2Memories Travel, LLC</span></p>
      <p style="margin-top: 10px; color: #333;">
        <strong>Phone:</strong> +1 (719) 291-0742<br>
        <strong>Email:</strong> johnloucks3@gmail.com<br>
        <strong>Reply-to:</strong> d2mconcierge@gmail.com
      </p>
    </div>
  </div>
</div>

</body>
</html>
"""

    # Email parameters
    to_email = "kyle.kuklinski@gmail.com"
    subject = (
        "Kuklinski Group Panama Canal Cruise Planning Timeline (All Payments Complete)"
    )
    from_email = "johnloucks3@gmail.com"

    print(f"\n📧 Creating AFA-color draft:")
    print(f"  To: {to_email}")
    print(f"  From: {from_email}")
    print(f"  Subject: {subject}")
    print(f"  Status: All payments complete as of March 27, 2026")
    print(f"  Colors: AFA Blue (#003087) + cream paper styling")

    # Build email message
    message = MIMEMultipart("alternative")
    message["to"] = to_email
    message["from"] = from_email
    message["subject"] = subject
    message["reply-to"] = "d2mconcierge@gmail.com"

    # Use Thunderbird's _wrap_body_html for proper Gmail formatting
    html_part = _wrap_body_html(html_content)

    # Plain text fallback
    plain_text = """Kuklinski Group Panama Canal Cruise Planning Timeline (All Payments Complete)

Hi Kyle,

Following up on our recent conversation about your Panama Canal cruise preparation. This outlines our comprehensive service timeline from now through embarkation—now that all payments are complete as of April 8, 2026.

COMPLETE: PHASE 1 & 2 (January – April 8)
- All 3 suite assignments confirmed with Viking
- Detailed invoice review complete
- FINAL PAYMENT: $21,244 total for 3 suites processed and verified
- Booking confirmation received from Viking
- Initial guest information gathered for your group of 6

PHASE 3: GUEST DOCUMENTATION (April – May)
- Online check-in completion for all 6 guests
- Dietary preferences and special requests documented
- Emergency contact information verified
- Travel insurance confirmation (if applicable)

PHASE 4: TRAVEL PLANNING (June – November)
- Flight research and booking recommendations
- Panama City hotel options for pre-cruise stay
- Shore excursion planning and reservations
- Specialty dining reservations aboard Viking Mars
- Port transportation and transfers coordination

PHASE 5: FINAL PREPARATION (December)
- Final documents and e-tickets delivered
- Embarkation day logistics confirmed
- Weather and packing guidance provided
- Last-minute details and reminders

EXECUTIVE TIMELINE VIEW
I've prepared several visualizations that show your complete planning timeline:
- Executive Gantt Chart – Full 12-month planning overview
- Timeline Proposal – Key decision points and milestones
- Service Phase Mapping – What happens when, from now to embarkation

These are available for review whenever you'd like to see the full picture.

The goal remains seamless preparation—you focus on anticipating the Panama Canal transit while our team handles the operational details.

Next step: Would you like to schedule a brief call to review the guest documentation phase and answer any questions about the timeline?

Best regards,

John Loucks
Owner, Dreams2Memories Travel, LLC
Phone: +1 (719) 291-0742
Email: johnloucks3@gmail.com
Reply-to: d2mconcierge@gmail.com
"""

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

        print(f"\n✅ AFA DRAFT CREATED!")
        print(f"Draft ID: {draft_id}")
        print(f"Message ID: {message_id}")
        print(
            f"\n📋 Access at: https://mail.google.com/mail/u/0/#drafts?compose={message_id}"
        )
        print(f"\n🎨 Colors applied:")
        print(f"   • Primary: #003087 (Air Force Academy blue)")
        print(f"   • Secondary: #001a5c (navy gradient)")
        print(f"   • Accent: #A9B0B7 (silver)")
        print(f"   • Background: #f7f3ea (cream paper)")
        print(f"   • Status: All payments complete (March 27, 2026)")
        print(f"   • REPLY-TO: d2mconcierge@gmail.com")

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
    """Main function to create AFA-colored draft"""

    print("=== AIR FORCE ACADEMY COLOR SCHEME DRAFT ===\n")
    print("Air Force Academy blue (#003087) with updated April 8 status\n")

    # Create the AFA draft
    draft_id = create_afa_draft()

    if draft_id:
        print(f"\n🎯 AFA DRAFT COMPLETED. Draft ID: {draft_id}")
        sys.exit(0)
    else:
        print(f"\n💥 DRAFT FAILED. No draft created.")
        sys.exit(1)


if __name__ == "__main__":
    main()
