#!/usr/bin/env python3
"""
One-time script: Create the combined D2M Guest Profile form under John's account.
Merges Client Intro + Client Profile into a single polished form.

Usage:
    python3 create_guest_profile_form.py

Will open a browser for Google OAuth consent (one time only).
"""

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive",
]
TOKEN_FILE = Path(__file__).parent / "forms_token.json"
CLIENT_FILE = Path(__file__).parent / "gmail_oauth_credentials.json"
EARA_SHEET_ID = "1RIOIFmmI4u4OSPA00HaBPPI9DnEftYBcS0TXWQ21ueU"


def get_creds():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
            creds = flow.run_local_server(port=8401)
        TOKEN_FILE.write_text(creds.to_json())
    return creds


def text_q(title, required=False, paragraph=False, idx=0):
    return {
        "createItem": {
            "item": {
                "title": title,
                "questionItem": {
                    "question": {
                        "required": required,
                        "textQuestion": {"paragraph": paragraph},
                    }
                },
            },
            "location": {"index": idx},
        }
    }


def choice_q(title, options, required=False, multi=False, idx=0):
    return {
        "createItem": {
            "item": {
                "title": title,
                "questionItem": {
                    "question": {
                        "required": required,
                        "choiceQuestion": {
                            "type": "CHECKBOX" if multi else "RADIO",
                            "options": [{"value": o} for o in options],
                        },
                    }
                },
            },
            "location": {"index": idx},
        }
    }


def date_q(title, required=False, idx=0):
    return {
        "createItem": {
            "item": {
                "title": title,
                "questionItem": {
                    "question": {
                        "required": required,
                        "dateQuestion": {"includeYear": True},
                    }
                },
            },
            "location": {"index": idx},
        }
    }


def section(title, description="", idx=0):
    return {
        "createItem": {
            "item": {
                "title": title,
                "description": description,
                "pageBreakItem": {},
            },
            "location": {"index": idx},
        }
    }


def main():
    creds = get_creds()
    forms_svc = build("forms", "v1", credentials=creds)
    drive_svc = build("drive", "v3", credentials=creds)

    # Step 1: Create the form
    print("Creating form...")
    form = forms_svc.forms().create(
        body={"info": {"title": "Dreams2Memories — Guest Profile", "documentTitle": "D2M Guest Profile"}}
    ).execute()

    form_id = form["formId"]
    print(f"Form ID: {form_id}")
    print(f"Edit:    https://docs.google.com/forms/d/{form_id}/edit")

    # Step 2: Add description + all fields
    reqs = []
    i = 0

    reqs.append({
        "updateFormInfo": {
            "info": {
                "description": (
                    "Welcome! This short form helps us personalize your voyage "
                    "with Dreams2Memories Travel. Your information is kept secure "
                    "and used only to make your trip unforgettable.\n\n"
                    "Takes about 5 minutes. Fields marked * are required."
                ),
            },
            "updateMask": "description",
        }
    })

    # ── Section 1: About You ──
    reqs.append(section("About You", "Basic information so we can take care of the details.", idx=i)); i += 1
    reqs.append(text_q("Booking / Confirmation Number", required=True, idx=i)); i += 1
    reqs.append(text_q("Ship or Hotel Name", idx=i)); i += 1
    reqs.append(choice_q("Title", ["Mr.", "Mrs.", "Ms.", "Dr.", "Other"], idx=i)); i += 1
    reqs.append(text_q("Legal First Name (as on passport)", required=True, idx=i)); i += 1
    reqs.append(text_q("Legal Middle Name (as on passport)", idx=i)); i += 1
    reqs.append(text_q("Legal Last Name (as on passport)", required=True, idx=i)); i += 1
    reqs.append(date_q("Date of Birth", required=True, idx=i)); i += 1
    reqs.append(text_q("Home Address", idx=i)); i += 1
    reqs.append(text_q("Primary Phone", required=True, idx=i)); i += 1
    reqs.append(text_q("Email", required=True, idx=i)); i += 1
    reqs.append(text_q("Emergency Contact — Name & Phone", required=True, idx=i)); i += 1

    # ── Section 2: Travel Style ──
    reqs.append(section("Your Travel Style",
        "Help us understand how you like to travel so we can tailor everything to you.", idx=i)); i += 1
    reqs.append(choice_q("Travel Pace", [
        "Slow & Steady — savor every moment",
        "Moderate — mix of activity and downtime",
        "High Energy — pack it all in",
    ], idx=i)); i += 1
    reqs.append(choice_q("What matters most to you on a trip? (select all that apply)", [
        "Fine Dining & Wine",
        "History & Architecture",
        "Shows & Entertainment",
        "Wellness & Spa",
        "Quiet Spaces & Relaxation",
        "Nature & Wildlife",
    ], multi=True, idx=i)); i += 1
    reqs.append(choice_q("What kind of traveler are you?", [
        "Relaxing / Zen",
        "High-Energy / Adventure",
        "Cultural Immersion",
        "Ultra-Luxury / Pampering",
    ], idx=i)); i += 1
    reqs.append(choice_q("Excursion Interests (select all that apply)", [
        "Panoramic Sightseeing",
        "Iconic Landmarks",
        "Food & Culinary Tours",
        "Nature & Wildlife",
        "Walking Tours & Local Culture",
    ], multi=True, idx=i)); i += 1
    reqs.append(choice_q("Bedding Preference", [
        "King bed", "Twin beds", "No preference",
    ], idx=i)); i += 1
    reqs.append(text_q("Special Milestones or Celebrations During This Trip?", idx=i)); i += 1
    reqs.append(text_q("Dietary Restrictions or Allergies", idx=i)); i += 1

    # ── Section 3: Flight & Hotel ──
    reqs.append(section("Flight & Hotel Preferences",
        "If we're arranging flights or hotels for you.", idx=i)); i += 1
    reqs.append(choice_q("Preferred Air Class", [
        "Business Class", "Premium Economy", "Economy", "No preference",
    ], idx=i)); i += 1
    reqs.append(choice_q("Seat Preference", [
        "Window", "Aisle", "Front of Cabin", "Exit Row", "No preference",
    ], idx=i)); i += 1
    reqs.append(choice_q("Hotel Style", [
        "Boutique & Unique",
        "Historic & Grand",
        "International Brands (Hilton, Marriott, etc.)",
        "No preference",
    ], idx=i)); i += 1

    # ── Section 4: Cruise Preferences ──
    reqs.append(section("Cruise Preferences",
        "If your trip includes a cruise.", idx=i)); i += 1
    reqs.append(choice_q("Preferred Suite Category", [
        "Penthouse / Top Tier", "Balcony Suite", "Standard Balcony", "No preference",
    ], idx=i)); i += 1
    reqs.append(choice_q("Ship Position Preference", [
        "Aft (back)", "Forward (front)", "Midship (center)", "No preference",
    ], idx=i)); i += 1

    # ── Section 5: Loyalty & Dreams ──
    reqs.append(section("Loyalty Programs & Your Dream Trip",
        "So we can make sure you get credit — and we know what lights you up.", idx=i)); i += 1
    reqs.append(text_q("Airline Loyalty / Frequent Flyer Numbers", idx=i)); i += 1
    reqs.append(text_q("Hotel or Cruise Loyalty Program Numbers", idx=i)); i += 1
    reqs.append(text_q(
        "What is your travel dream? The one thing that would make this trip a 10 out of 10.",
        paragraph=True, idx=i,
    )); i += 1
    reqs.append(text_q("Anything else you'd like us to know?", paragraph=True, idx=i)); i += 1

    print(f"Adding {len(reqs)} items...")
    forms_svc.forms().batchUpdate(formId=form_id, body={"requests": reqs}).execute()
    print("Fields added.")

    # Step 3: Link to EARA sheet as response destination
    print(f"Linking responses to EARA sheet {EARA_SHEET_ID}...")
    try:
        forms_svc.forms().batchUpdate(
            formId=form_id,
            body={
                "requests": [
                    {
                        "updateSettings": {
                            "settings": {
                                "quizSettings": {"isQuiz": False}
                            },
                            "updateMask": "quizSettings.isQuiz",
                        }
                    }
                ]
            },
        ).execute()
    except Exception as e:
        print(f"  Settings update note: {e}")

    # Move form to a D2M folder (optional)
    print()
    resp_uri = forms_svc.forms().get(formId=form_id).execute().get("responderUri", "")
    print("=" * 60)
    print("DONE!")
    print(f"  Edit URL:  https://docs.google.com/forms/d/{form_id}/edit")
    print(f"  Fill URL:  {resp_uri}")
    print(f"  Form ID:   {form_id}")
    print()
    print("NEXT STEPS:")
    print("  1. Open the Edit URL above")
    print("  2. Click Responses tab → Link to Sheets")
    print("  3. Select 'Existing spreadsheet' → EARA_D2M_Command_Center")
    print("  4. Settings → uncheck 'Limit to 1 response'")
    print("  5. Settings → 'Collect email addresses' = ON")
    print("=" * 60)


if __name__ == "__main__":
    main()
