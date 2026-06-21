#!/usr/bin/env python3
"""
Full chain: OAuth (forms.body + drive.file) -> create Kuklinski excursion form
-> save share URL -> insert URL into staged Gmail draft (d2mconcierge).
Commander's only step: approve in the browser that opens.
"""
import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES_FORMS = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive.file",
]
CLIENT_SECRETS = Path.home() / ".credentials" / "client_secrets.json"
TOKEN_PATH = Path.home() / ".gmail-mcp" / "johnloucks3" / "forms_token.json"

GUESTS = ["Kyle Kuklinski", "Rosalie Kuklinski", "Roger Kuklinski",
          "Nicholas (Nick) Kuklinski", "Joshua Morton", "Erica Dodge"]
PORTS = ["Colón, Panama (Dec 19)", "Puerto Limón, Costa Rica (Dec 20)",
         "Roatán, Honduras (Dec 22)", "Belize City, Belize (Dec 23)",
         "Cozumel, Mexico (Dec 24)"]
TYPES = ["Wildlife & Nature (sloths, birds, monkeys)",
         "History & Ancient Ruins (Mayan, colonial)", "Beach & Swimming",
         "Water-based (boat tours, snorkeling)", "Food, Culture & Local Markets",
         "Scenic / Photography / Easy Sightseeing",
         "Active / Adventure (ziplining, hiking)", "I'm flexible — go with the group"]


def get_creds():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES_FORMS)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print(">>> Opening browser for Google approval. Approve, then I take over.",
                  flush=True)
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES_FORMS)
            creds = flow.run_local_server(port=0, open_browser=True,
                                          authorization_prompt_message=
                                          "Open this URL to approve: {url}")
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json())
    return creds


def create_form(creds):
    svc = build("forms", "v1", credentials=creds)
    form = svc.forms().create(body={"info": {
        "title": "Viking Mars Panama Canal — Excursion Preferences",
        "documentTitle": "Kuklinski Group Excursion Survey Dec 2026"}}).execute()
    fid = form["formId"]
    reqs = []
    for i, port in enumerate(PORTS):
        reqs.append({"createItem": {"item": {
            "title": f"What interests you in {port}?",
            "description": "Check all that interest you. One row per person.",
            "questionGroupItem": {
                "questions": [{"rowQuestion": {"title": g}} for g in GUESTS],
                "grid": {"columns": {"type": "CHECKBOX",
                                     "options": [{"value": t} for t in TYPES]}}}},
            "location": {"index": i}}})
    reqs.append({"createItem": {"item": {
        "title": "Group logistics preference",
        "questionItem": {"question": {"choiceQuestion": {"type": "RADIO", "options": [
            {"value": "Stay together as a group for all excursions"},
            {"value": "Mostly together, OK to split for 1-2 ports"},
            {"value": "Each cabin books its own — we just want recs"}]}}}},
        "location": {"index": len(reqs)}}})
    reqs.append({"createItem": {"item": {
        "title": "Anything else? (mobility, preferences, requests)",
        "questionItem": {"question": {"textQuestion": {"paragraph": True}}}},
        "location": {"index": len(reqs)}}})
    svc.forms().batchUpdate(formId=fid, body={"requests": reqs}).execute()
    share = f"https://docs.google.com/forms/d/{fid}/viewform"
    edit = f"https://docs.google.com/forms/d/{fid}/edit"
    Path("/home/john/Thunderbird/cache/kuklinski_excursion_form.json").write_text(
        json.dumps({"form_id": fid, "share_url": share, "edit_url": edit}, indent=2))
    print(f">>> FORM CREATED. Share: {share}", flush=True)
    return share


def insert_url_into_draft(share_url):
    """Replace FORM_URL_PLACEHOLDER in the staged d2mconcierge draft."""
    import base64
    from email.mime.text import MIMEText
    TOKEN = Path("/home/john/Thunderbird/config/persona_gmail_token.json")
    creds = Credentials.from_authorized_user_file(str(TOKEN), [
        "https://www.googleapis.com/auth/gmail.modify"])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    g = build("gmail", "v1", credentials=creds)
    # find the staged draft by subject
    drafts = g.users().drafts().list(userId="me", q="subject:Viking Mars Panama").execute()
    items = drafts.get("drafts", [])
    if not items:
        print(">>> WARN: staged draft not found by subject; URL saved to cache only.", flush=True)
        return False
    # Rebuild the draft from the corrected local HTML with URL inserted
    html = Path("/home/john/Thunderbird/drafts/kuklinski_excursion_survey_intro_dani.html").read_text()
    html = html.replace("FORM_URL_PLACEHOLDER", share_url)
    did = items[0]["id"]
    full = g.users().drafts().get(userId="me", id=did, format="metadata").execute()
    mid = full["message"]["id"]
    hdrs = {h["name"]: h["value"] for h in
            g.users().messages().get(userId="me", id=mid, format="metadata").execute()
            ["payload"]["headers"]}
    msg = MIMEText(html, "html")
    msg["To"] = hdrs.get("To", "kyle.kuklinski@gmail.com")
    msg["From"] = hdrs.get("From", "concierge@d2mluxury.quest")
    msg["Subject"] = hdrs.get("Subject", "Viking Mars Panama — Let's Plan Your Excursions")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    g.users().drafts().update(userId="me", id=did,
                              body={"message": {"raw": raw}}).execute()
    print(">>> DRAFT UPDATED with live form URL. Ready for your review + send.", flush=True)
    return True


if __name__ == "__main__":
    creds = get_creds()
    share = create_form(creds)
    insert_url_into_draft(share)
    print(">>> CHAIN COMPLETE.", flush=True)
