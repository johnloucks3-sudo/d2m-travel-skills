#!/usr/bin/env python3
"""
Create Kuklinski Group Excursion Preference Survey — Google Form via Forms API.
Run once. Returns form URL for Commander to share with Kyle.

Auth: Uses google-workspace service account or OAuth via ~/.google_credentials.json
"""

import json
import os
from pathlib import Path

# Google Forms API requires oauth2 with forms.body scope
# Using the google-auth pattern already established in this project

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("google-api-python-client not installed. Run: pip install google-api-python-client")
    exit(1)

SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive.file",
]

TOKEN_PATH = Path.home() / ".gmail-mcp" / "johnloucks3" / "token.json"
CREDS_PATH = Path.home() / ".gmail-mcp" / "johnloucks3" / "credentials.json"


def get_creds():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return creds


GUESTS = [
    "Kyle Kuklinski",
    "Rosalie Kuklinski",
    "Roger Kuklinski",
    "Nicholas (Nick) Kuklinski",
    "Joshua Morton",
    "Erica Dodge",
]

PORTS = [
    "Colón, Panama (Dec 19)",
    "Puerto Limón, Costa Rica (Dec 20)",
    "Roatán, Honduras (Dec 22)",
    "Belize City, Belize (Dec 23)",
    "Cozumel, Mexico (Dec 24)",
]

EXCURSION_TYPES = [
    "Wildlife & Nature (sloths, birds, monkeys)",
    "History & Ancient Ruins (Mayan, colonial)",
    "Beach & Swimming",
    "Water-based (boat tours, snorkeling)",
    "Food, Culture & Local Markets",
    "Scenic / Photography / Easy Sightseeing",
    "Active / Adventure (ziplining, hiking)",
    "I'm flexible — go with the group",
]


def build_form_body():
    """Build the Google Forms API request body."""

    # One checkbox-grid question per port
    # Rows = guests, Columns = excursion types
    questions = []

    for port in PORTS:
        questions.append({
            "createItem": {
                "item": {
                    "title": f"What interests you in {port}?",
                    "description": (
                        "Check all types that interest you. "
                        "One row per person — check what sounds fun to YOU."
                    ),
                    "questionGroupItem": {
                        "questions": [
                            {"rowQuestion": {"title": guest}} for guest in GUESTS
                        ],
                        "grid": {
                            "columns": {
                                "type": "CHECKBOX",
                                "options": [
                                    {"value": etype} for etype in EXCURSION_TYPES
                                ],
                            }
                        },
                    },
                },
                "location": {"index": len(questions)},
            }
        })

    # Overall group preference question
    questions.append({
        "createItem": {
            "item": {
                "title": "Group logistics preference",
                "description": "This helps us plan whether to book together or let couples split off.",
                "questionItem": {
                    "question": {
                        "required": False,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [
                                {"value": "Stay together as a group for all excursions"},
                                {"value": "Mostly together, but OK to split for 1-2 ports"},
                                {"value": "Each couple books their own — we just want recs"},
                            ],
                        },
                    }
                },
            },
            "location": {"index": len(questions)},
        }
    })

    # Free text for anything else
    questions.append({
        "createItem": {
            "item": {
                "title": "Anything else we should know? (mobility concerns, preferences, requests)",
                "questionItem": {
                    "question": {
                        "required": False,
                        "textQuestion": {"paragraph": True},
                    }
                },
            },
            "location": {"index": len(questions)},
        }
    })

    return {
        "info": {
            "title": "Viking Mars Panama Canal — Excursion Preferences",
            "documentTitle": "Kuklinski Group Excursion Survey Dec 2026",
        }
    }, questions


def create_form():
    creds = get_creds()
    forms_service = build("forms", "v1", credentials=creds)

    # Step 1: Create the form shell
    form_body, questions = build_form_body()
    print("Creating form...")
    form = forms_service.forms().create(body=form_body).execute()
    form_id = form["formId"]
    print(f"Form created: {form_id}")

    # Step 2: Batch update to add all questions
    print(f"Adding {len(questions)} questions...")
    forms_service.forms().batchUpdate(
        formId=form_id,
        body={"requests": questions},
    ).execute()

    # Step 3: Set to accepting responses
    forms_service.forms().batchUpdate(
        formId=form_id,
        body={
            "requests": [
                {
                    "updateSettings": {
                        "settings": {"quizSettings": {"isQuiz": False}},
                        "updateMask": "quizSettings.isQuiz",
                    }
                }
            ]
        },
    ).execute()

    form_url = f"https://docs.google.com/forms/d/{form_id}/edit"
    share_url = f"https://docs.google.com/forms/d/{form_id}/viewform"

    print("\n" + "=" * 60)
    print("FORM CREATED SUCCESSFULLY")
    print(f"Edit URL (you): {form_url}")
    print(f"Share URL (Kyle): {share_url}")
    print("=" * 60)

    # Save to output
    result = {
        "form_id": form_id,
        "edit_url": form_url,
        "share_url": share_url,
        "title": "Viking Mars Panama Canal — Excursion Preferences",
        "ports": PORTS,
        "guests": GUESTS,
        "excursion_types": EXCURSION_TYPES,
    }
    out = Path("/home/john/Thunderbird/cache/kuklinski_excursion_form.json")
    out.write_text(json.dumps(result, indent=2))
    print(f"Saved to {out}")
    return result


if __name__ == "__main__":
    create_form()
