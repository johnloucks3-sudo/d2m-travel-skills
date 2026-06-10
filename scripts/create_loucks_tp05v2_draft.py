#!/usr/bin/env python3
"""Create Loucks TP 0.5 v2 Gmail draft with preference form attachment."""
import base64
import json
import sys
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.email.thunderbird_gmail import _get_gmail_service, _tag_commander_review

EMAIL_HTML  = Path("/home/john/Thunderbird/drafts/Loucks_SilverNova_TP05_Validation_v2_DRAFT.html")
FORM_HTML   = Path("/home/john/Thunderbird/D2M/aar/Loucks_ClientTest/forms/D2M_Guest_Preference_Form_v1.html")
TO          = "johnloucks3@gmail.com"
CC          = "susanna.loucks@gmail.com"
SUBJECT     = "Your Silver Nova Mediterranean — Confirmed · May 5–29, 2027 (+ one small form)"

def main():
    email_body = EMAIL_HTML.read_text(encoding="utf-8")

    # Plain text fallback (strip tags)
    import re
    plain = re.sub(r'<[^>]+>', '', email_body)
    plain = re.sub(r'\n{3,}', '\n\n', plain).strip()

    root = MIMEMultipart("mixed")
    root["to"]      = TO
    root["cc"]      = CC
    root["from"]    = "Danielle Moreau <concierge@d2mluxury.quest>"
    root["subject"] = SUBJECT

    # HTML body
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain, "plain"))
    alt.attach(MIMEText(email_body, "html"))
    root.attach(alt)

    # Preference form attachment
    form_bytes = FORM_HTML.read_bytes()
    att = MIMEBase("text", "html")
    att.set_payload(form_bytes)
    encoders.encode_base64(att)
    att.add_header("Content-Disposition", "attachment",
                   filename="D2M_Guest_Preference_Form.html")
    root.attach(att)

    raw = base64.urlsafe_b64encode(root.as_bytes()).decode()

    service = _get_gmail_service()
    draft = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()

    draft_id   = draft["id"]
    message_id = draft.get("message", {}).get("id", "")

    if message_id:
        try:
            _tag_commander_review(service, message_id)
        except Exception as e:
            print(f"Label tag failed (non-fatal): {e}")

    print(json.dumps({
        "draft_id":   draft_id,
        "message_id": message_id,
        "subject":    SUBJECT,
        "to":         TO,
        "cc":         CC,
        "attachment": FORM_HTML.name,
        "status":     "draft_created",
        "review_url": f"https://mail.google.com/mail/b/d2mconcierge@gmail.com/#drafts/{draft_id}",
    }, indent=2))


if __name__ == "__main__":
    main()
