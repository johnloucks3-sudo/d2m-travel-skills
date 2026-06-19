#!/usr/bin/env python3
"""
push_wf17_to_johnloucks3.py — Batch-push 5 WF-17 lifecycle drafts to Commander's
johnloucks3@gmail.com inbox as drafts. Hold orders rescinded 2026-06-19.

Kuklinski: TP 0.5 / 4.1 / 4.2 / 4.3
Nichols:   TP 0.5
"""
import json, base64, sys, logging
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
log = logging.getLogger("wf17_push")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

DRAFTS = [
    {
        "label": "Kuklinski TP 0.5 — Welcome",
        "file":  ROOT / "drafts/TASK-0.5-kuklinski_group_welcome_final.html",
        "to":    "kyle.kuklinski@gmail.com",
        "subject": "Welcome Aboard — Your Viking Mars Panama Canal Voyage [D2M]",
    },
    {
        "label": "Kuklinski TP 4.1 — Specialty Dining",
        "file":  ROOT / "drafts/kuklinski_specialty_dining_preprocessed.html",
        "to":    "kyle.kuklinski@gmail.com",
        "subject": "Specialty Dining Aboard Viking Mars — Reservation Planning [D2M]",
    },
    {
        "label": "Kuklinski TP 4.2 — Excursion Planning",
        "file":  ROOT / "drafts/kuklinski_excursion_survey_intro_dani.html",
        "to":    "kyle.kuklinski@gmail.com",
        "subject": "Viking Mars Panama — Your Excursion Planning Guide [D2M]",
    },
    {
        "label": "Kuklinski TP 4.3 — Pre-Departure Logistics",
        "file":  ROOT / "drafts/kuklinski_logistics_v2_20260530.html",
        "to":    "kyle.kuklinski@gmail.com",
        "subject": "December Voyage — Hotels, Flights & Transfer Details [D2M]",
    },
    {
        "label": "Nichols TP 0.5 — Booking Validation",
        "file":  ROOT / "output/Nichols_Validation_TP0.5_Gmail.html",
        "to":    "larry.nichols4811@gmail.com",
        "subject": "Your Regent Seven Seas Grandeur Voyage — Booking Confirmation [D2M]",
    },
]


def get_gmail_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    token_path = ROOT / "creds/johnloucks3_token.json"
    scopes = [
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.modify",
    ]
    token_data = json.loads(token_path.read_text())
    creds = Credentials.from_authorized_user_info(token_data, scopes)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
        log.info("Token refreshed")
    return build("gmail", "v1", credentials=creds)


def create_draft(service, draft_def: dict) -> bool:
    html_file = draft_def["file"]
    if not html_file.exists():
        log.error("File missing: %s — skipping %s", html_file, draft_def["label"])
        return False

    html_body = html_file.read_text(encoding="utf-8", errors="replace")

    # Inline CSS via premailer if available
    try:
        import premailer
        html_body = premailer.transform(html_body, remove_classes=False, strip_important=False)
    except Exception:
        pass  # fall through with raw HTML

    msg = MIMEMultipart("alternative")
    msg["to"] = draft_def["to"]
    msg["from"] = "d2mconcierge@gmail.com"
    msg["subject"] = draft_def["subject"]
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    log.info("✅ Draft created: %s → ID %s", draft_def["label"], draft.get("id"))
    return True


def main():
    try:
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        log.info("Authenticated as: %s", profile["emailAddress"])
    except Exception as e:
        log.error("Gmail auth failed: %s", e)
        sys.exit(1)

    ok, fail = 0, 0
    for d in DRAFTS:
        try:
            if create_draft(service, d):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            log.error("Failed %s: %s", d["label"], e)
            fail += 1

    print(f"\n{'='*50}")
    print(f"WF-17 Draft Push Complete — {ok} created, {fail} failed")
    print("Check johnloucks3@gmail.com drafts folder.")
    print("="*50)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
