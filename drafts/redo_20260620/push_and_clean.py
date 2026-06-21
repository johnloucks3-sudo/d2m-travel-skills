#!/usr/bin/env python3
"""
Push redone client drafts to johnloucks3 + remove the specific old rejected ones.
Create-first, delete-second (never a gap). Logs every deletion to hale_decisions.md.
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

def svc():
    c = Credentials.from_authorized_user_info(json.loads(TP.read_text()), SCOPES)
    if not c.valid and c.expired and c.refresh_token:
        c.refresh(Request()); TP.write_text(c.to_json())
    return build("gmail", "v1", credentials=c)

def prep(html):
    try:
        import premailer
        return premailer.transform(html, remove_classes=False, strip_important=False)
    except Exception:
        return html

def create(s, to, subject, html):
    msg = MIMEMultipart("alternative")
    msg["to"] = to
    msg["from"] = "d2mconcierge@gmail.com via johnloucks3@gmail.com"
    msg["reply-to"] = "d2mconcierge@gmail.com"
    msg["subject"] = subject
    msg.attach(MIMEText(prep(html), "html", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    d = s.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return d["id"]

D = ROOT / "drafts"
R = D / "redo_20260620"

# (file, To, Subject)
NEW = [
    (R/"nichols_voyage_checkin.html",  "larry.nichols4811@gmail.com, heidi.nichols1@yahoo.com",
     "Your Scandinavia Voyage — You're Set, and Heidi's Birthday Aboard"),
    (R/"ely_voyage_checkin.html",      "al.ely58@gmail.com, amy.darrow@me.com",
     "Your Scandinavia Voyage — Set, with One Open Day in Kristiansand"),
    (R/"furlow_voyage_checkin.html",   "missy.furlow@gmail.com, john.furlow@tpf.org",
     "Your Scandinavia Voyage — Where We Are, and What's Ahead"),
    (R/"kuklinski_tp05_status.html",   "kyle.kuklinski@gmail.com",
     "Your Viking Mars Panama Voyage — Where We Stand"),
    (R/"kuklinski_tp43_logistics.html","kyle.kuklinski@gmail.com",
     "Panama December — Hotels, Transfers & Five Quick Questions"),
    (D/"kuklinski_excursion_survey_intro_dani.html", "kyle.kuklinski@gmail.com",
     "Panama Excursions — Our Picks and a 3-Minute Survey, Kyle"),
]

# Old rejected client drafts to remove AFTER new ones land.
# label = why
OLD = [
    ("r3123063344331594273", "Kuklinski Welcome (old) — replaced by TP0.5 status rewrite"),
    ("r661885286550684345",  "Kuklinski Logistics (old) — replaced by TP4.3 rewrite"),
    ("r8565223516252625193", "Kuklinski Excursion Guide (old) — replaced by form-locked version"),
    ("r-4265166377214822999","Kuklinski Excursion (duplicate, old) — removed; one excursion draft only"),
    ("r9019699247342968531", "Kuklinski Specialty Dining (old) — NOT re-staged; content already sent May 15 (2x). Removed to prevent double-send."),
    ("r-1522787698840779830","Nichols Booking Confirmation (old) — replaced by Scandinavia voyage check-in"),
]

s = svc()
print("=== CREATE (new drafts) ===")
created = []
for f, to, subj in NEW:
    did = create(s, to, subj, Path(f).read_text(encoding="utf-8"))
    created.append((did, to, subj))
    print(f"  + {did}  {to[:38]:38s} {subj[:48]}")

print("\n=== DELETE (old rejected) ===")
deleted = []
for did, why in OLD:
    try:
        s.users().drafts().delete(userId="me", id=did).execute()
        deleted.append((did, why)); print(f"  - {did}  {why[:70]}")
    except Exception as e:
        print(f"  ! {did}  could not delete: {e}")

# Audit log
log = ROOT / "hale_decisions.md"
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M MT")
entry = [f"\n## {ts} — Redo batch: Kuklinski + Scandinavia trio (johnloucks3 drafts)\n",
         "Commander directives 2026-06-20: \"re-do all 5 WF-17s\", \"keep on kuklinski, when you do Nichols add the other 2\", retain excursion form.\n",
         "**Created (new, John-voice, voice-QC passed):**\n"]
for did, to, subj in created:
    entry.append(f"- `{did}` → {to} — {subj}\n")
entry.append("**Deleted (old rejected; source HTML retained, recoverable):**\n")
for did, why in deleted:
    entry.append(f"- `{did}` — {why}\n")
entry.append("Untouched: Ely/Amy insurance draft, Spencer, internal reports, McLeod/Silversea, all other mailbox drafts.\n")
with open(log, "a", encoding="utf-8") as fh:
    fh.writelines(entry)
print(f"\nLogged to {log}")
print(f"\nSUMMARY: {len(created)} created, {len(deleted)} deleted.")
