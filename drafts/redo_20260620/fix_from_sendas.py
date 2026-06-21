#!/usr/bin/env python3
"""
Re-stage the 6 client TP drafts with From = concierge@d2mluxury.quest (verified
send-as on johnloucks3) so they are send-ready with D2M brand identity.
Delete the 6 interim drafts that had the informal 'via' From header.
"""
import json, base64, datetime
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

ROOT = Path("/home/john/Thunderbird")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.modify",
          "https://www.googleapis.com/auth/gmail.compose"]
TP = ROOT / "creds/johnloucks3_token.json"
FROM = "concierge@d2mluxury.quest"

c = Credentials.from_authorized_user_info(json.loads(TP.read_text()), SCOPES)
if not c.valid and c.expired and c.refresh_token:
    c.refresh(Request()); TP.write_text(c.to_json())
s = build("gmail", "v1", credentials=c)

def prep(html):
    try:
        import premailer
        return premailer.transform(html, remove_classes=False, strip_important=False)
    except Exception:
        return html

def create(to, subject, html):
    m = MIMEMultipart("alternative")
    m["to"] = to; m["from"] = FROM; m["reply-to"] = FROM; m["subject"] = subject
    m.attach(MIMEText(prep(html), "html", "utf-8"))
    raw = base64.urlsafe_b64encode(m.as_bytes()).decode()
    return s.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()["id"]

D = ROOT / "drafts"; R = D / "redo_20260620"
NEW = [
    (R/"nichols_voyage_checkin.html","larry.nichols4811@gmail.com, heidi.nichols1@yahoo.com",
     "Your Scandinavia Voyage — You're Set, and Heidi's Birthday Aboard"),
    (R/"ely_voyage_checkin.html","al.ely58@gmail.com, amy.darrow@me.com",
     "Your Scandinavia Voyage — Set, with One Open Day in Kristiansand"),
    (R/"furlow_voyage_checkin.html","missy.furlow@gmail.com, john.furlow@tpf.org",
     "Your Scandinavia Voyage — Where We Are, and What's Ahead"),
    (R/"kuklinski_tp05_status.html","kyle.kuklinski@gmail.com",
     "Your Viking Mars Panama Voyage — Where We Stand"),
    (R/"kuklinski_tp43_logistics.html","kyle.kuklinski@gmail.com",
     "Panama December — Hotels, Transfers & Five Quick Questions"),
    (D/"kuklinski_excursion_survey_intro_dani.html","kyle.kuklinski@gmail.com",
     "Panama Excursions — Our Picks and a 3-Minute Survey, Kyle"),
]
# interim draft IDs (informal From) to delete after re-create
OLD_IDS = ["r934151172488144160","r-6966468892545556704","r-2758595241808495699",
           "r7666586377371665644","r-8842984001262693212","r7965154844441022097"]

print(f"=== RE-CREATE with From={FROM} ===")
created=[]
for f,to,subj in NEW:
    did=create(to,subj,Path(f).read_text(encoding="utf-8"))
    created.append((did,to,subj)); print(f"  + {did}  {to[:34]:34s} {subj[:46]}")

print("\n=== DELETE interim (informal From) ===")
for did in OLD_IDS:
    try:
        s.users().drafts().delete(userId="me",id=did).execute(); print(f"  - {did}")
    except Exception as e:
        print(f"  ! {did} {str(e)[:60]}")

log=ROOT/"hale_decisions.md"
ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M MT")
with open(log,"a",encoding="utf-8") as fh:
    fh.write(f"\n### {ts} — Re-stage 6 client drafts with send-as {FROM}\n")
    fh.write("Per revised TP-draft routing SO: drafts live in johnloucks3 (Commander review), send AS concierge@d2mluxury.quest (D2M brand identity preserved). Replaced 6 interim drafts.\n")
    for did,to,subj in created: fh.write(f"- `{did}` → {to} — {subj}\n")
print(f"\nLogged. {len(created)} send-ready drafts now in johnloucks3.")
PY