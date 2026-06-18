#!/usr/bin/env python3
"""
Create Gmail drafts in Commander's johnloucks3@gmail.com account
Uses OAuth credentials from Google Keep note
"""

import json
import base64
import sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import webbrowser
import os

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"ERROR: Missing Google libraries: {e}")
    print(
        "Install: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
    )
    sys.exit(1)


def get_johnloucks3_token_path():
    """Get path for johnloucks3 OAuth token"""
    return Path("/home/john/Thunderbird/creds/johnloucks3_token.json")


def authenticate_johnloucks3():
    """Authenticate to johnloucks3@gmail.com using OAuth"""

    print("=== JOHNLOUCKS3 GMAIL AUTHENTICATION ===")

    # OAuth credentials from Google Keep (Thunderbird Desktop Auth)
    oauth_config = {
        "installed": {
            "client_id": "739340749717-5175ilopk6pvu9lec1r7i5ab81hsgpdl.apps.googleusercontent.com",
            "project_id": "d2m-python-pipeline",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "***REMOVED-SECRET***",
            "redirect_uris": ["http://localhost"],
        }
    }

    scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.compose",
    ]

    token_path = get_johnloucks3_token_path()

    # Try to load existing token
    creds = None
    if token_path.exists():
        try:
            with open(token_path, "r") as token_file:
                token_data = json.load(token_file)
                creds = Credentials.from_authorized_user_info(token_data, scopes)
            print("✓ Loaded existing johnloucks3 token")
        except Exception as e:
            print(f"⚠️ Warning: Could not load existing token: {e}")
            creds = None

    # If no valid credentials, do OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("✓ Refreshed expired token")
            except Exception as e:
                print(f"⚠️ Warning: Could not refresh token: {e}")
                creds = None

        if not creds:
            print("🔑 Starting OAuth flow for johnloucks3@gmail.com...")
            print("A browser window will open. Log in as johnloucks3@gmail.com")

            # Use InstalledAppFlow for OAuth
            flow = InstalledAppFlow.from_client_config(oauth_config, scopes)
            flow.redirect_uri = "http://localhost"

            try:
                # Run local server flow
                creds = flow.run_local_server(port=0, open_browser=True)

                # Save token
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

                print(f"✓ OAuth token saved to {token_path}")

            except Exception as e:
                print(f"❌ OAuth failed: {e}")
                print("\nAlternative method: Use authorization URL")
                try:
                    auth_url, _ = flow.authorization_url(prompt="consent")
                    print(f"\n📋 Manually authorize at: {auth_url}")
                    print("\nAfter authorization, paste the code from the URL here")
                    code = input("Enter authorization code: ").strip()
                    flow.fetch_token(code=code)
                    creds = flow.credentials

                    # Save token
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

                    print(f"✓ OAuth completed and token saved")

                except Exception as e2:
                    print(f"❌ Manual OAuth also failed: {e2}")
                    return None

    return creds


def create_johnloucks3_draft(
    html_file_path, to_email, subject, from_email="d2mconcierge@gmail.com"
):
    """Create Gmail draft in Commander's johnloucks3@gmail.com account"""

    print("\n=== CREATING DRAFT IN JOHNLOUCKS3 GMAIL ===")

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
        if email_address != "johnloucks3@gmail.com":
            print(f"⚠️ WARNING: Logged in as {email_address}, not johnloucks3@gmail.com")

    except Exception as e:
        print(f"❌ ERROR building Gmail service: {e}")
        return None

    # Read HTML email body
    html_file = Path(html_file_path)
    if not html_file.exists():
        print(f"❌ ERROR: HTML file not found at {html_file_path}")
        return None

    with open(html_file, "r", encoding="utf-8") as f:
        html_body = f.read()

    # Preprocess HTML for Gmail compatibility:
    # inline CSS from <style> blocks, add bgcolor attributes, strip unsafe tags.
    # Try premailer first; fall back to gmail_template_stripper (bs4-based).
    preprocessed = False
    try:
        import premailer
        html_body = premailer.transform(html_body, remove_classes=False, strip_important=False)
        preprocessed = True
        print("✓ HTML preprocessed via premailer")
    except Exception:
        pass
    if not preprocessed:
        try:
            _this_dir = str(Path(__file__).parent)
            if _this_dir not in sys.path:
                sys.path.insert(0, _this_dir)
            from gmail_template_stripper import GmailSafePreprocessor
            html_body, _log = GmailSafePreprocessor().process(html_body)
            preprocessed = True
            print("✓ HTML preprocessed via gmail_template_stripper (bs4 fallback)")
        except Exception as _e:
            print(f"⚠️ HTML preprocessing skipped ({_e}) — Gmail may strip <style> blocks")

    print(f"\n📧 Creating draft:")
    print(f"  To: {to_email}")
    print(f"  From: {from_email} (via johnloucks3@gmail.com)")
    print(f"  Subject: {subject}")
    print(f"  HTML file: {html_file_path}")

    # Build email message
    message = MIMEMultipart("alternative")
    message["to"] = to_email
    message["from"] = f"{from_email} via johnloucks3@gmail.com"
    message["subject"] = subject
    message["reply-to"] = from_email  # So replies go to D2M

    # Add HTML part
    msg_html = MIMEText(html_body, "html", "utf-8")
    message.attach(msg_html)

    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Create draft via Gmail API
    try:
        draft_body = {"message": {"raw": raw_message}}

        draft = service.users().drafts().create(userId="me", body=draft_body).execute()

        draft_id = draft.get("id")
        message_id = draft.get("message", {}).get("id")

        print(f"\n✅ SUCCESS! Draft created in Commander's johnloucks3@gmail.com")
        print(f"Draft ID: {draft_id}")
        print(f"Message ID: {message_id}")
        print(
            f"\n📋 Access draft at: https://mail.google.com/mail/u/0/#drafts?compose={message_id}"
        )
        print(f"\n💡 Commander: Check your Gmail drafts folder for this message")
        print(f"   Draft will appear in johnloucks3@gmail.com drafts folder")

        # Also list drafts to confirm
        try:
            drafts = (
                service.users().drafts().list(userId="me").execute().get("drafts", [])
            )
            print(f"\n📊 Current draft count in johnloucks3@gmail.com: {len(drafts)}")
            if drafts:
                print("Recent drafts:")
                for i, d in enumerate(drafts[-3:], 1):
                    try:
                        msg = (
                            service.users()
                            .drafts()
                            .get(userId="me", id=d["id"])
                            .execute()
                        )
                        headers = (
                            msg.get("message", {}).get("payload", {}).get("headers", [])
                        )
                        subj = next(
                            (h["value"] for h in headers if h["name"] == "Subject"),
                            "No subject",
                        )
                        to_addr = next(
                            (h["value"] for h in headers if h["name"] == "To"),
                            "Unknown",
                        )
                        print(f"  {i}. To: {to_addr[:30]}... | Subject: {subj[:40]}...")
                    except:
                        print(f"  {i}. [Could not retrieve draft details]")
        except Exception as e:
            print(f"⚠️ Could not list drafts: {e}")

        return draft_id

    except HttpError as error:
        error_content = (
            error.content.decode("utf-8")
            if isinstance(error.content, bytes)
            else error.content
        )
        print(f"\n❌ Gmail API Error: {error.resp.status}")
        print(f"Details: {error_content}")

        if error.resp.status == 401:
            print("\n🔑 Authentication failed")
            print("Token may be expired or invalid")
            print("\nFix: Delete token file and re-authenticate:")
            print(f"  rm {get_johnloucks3_token_path()}")
            print(f"  python {Path(__file__).name}")
        elif error.resp.status == 403:
            print("\n🔒 Permission denied")
            print("Possible causes:")
            print("  1. Gmail API not enabled for this project")
            print("  2. Account doesn't have Gmail access")
            print("  3. Wrong OAuth scopes")
            print("  4. Domain restrictions")
        elif error.resp.status == 400:
            print("\n📝 Bad request")
            print("Possible causes:")
            print("  1. Invalid message format")
            print("  2. Missing required fields")
            print("  3. HTML content encoding issue")

        return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Main function to create Kuklinski lifecycle email draft"""

    import argparse

    print("=== JOHNLOUCKS3 GMAIL DRAFT CREATOR ===\n")

    parser = argparse.ArgumentParser()
    parser.add_argument('--html', required=True)
    parser.add_argument('--to', required=True)
    parser.add_argument('--subject', required=True)
    args = parser.parse_args()
    html_file = args.html
    to_email = args.to
    subject = args.subject
    from_email = "d2mconcierge@gmail.com"

    # Check if HTML file exists
    if not Path(html_file).exists():
        print(f"❌ ERROR: HTML file not found: {html_file}")
        print(f"\n💡 Create the HTML file first with lifecycle explanation")
        print(f"Expected location: {html_file}")
        sys.exit(1)

    print(f"📁 Using HTML file: {html_file}")
    print(f"📧 Draft will be created in: johnloucks3@gmail.com drafts folder")
    print(f"📝 From: {from_email}")
    print(f"📨 To: {to_email}")
    print(f"📋 Subject: {subject}")
    print(f"\nReady to create draft...\n")

    # Create the draft
    draft_id_result = create_johnloucks3_draft(html_file, to_email, subject, from_email)

    if draft_id_result:
        print(f"\n🎯 Task completed. Draft ID: {draft_id_result}")
        sys.exit(0)
    else:
        print(f"\n💥 Task failed. No draft created.")
        sys.exit(1)


if __name__ == "__main__":
    main()
