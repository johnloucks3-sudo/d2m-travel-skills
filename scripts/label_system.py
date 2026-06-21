#!/usr/bin/env python3
"""
label_system.py — canonical Gmail label set + Commander-Review aging, both accounts.

Commander directive 2026-06-20:
  - Commander-Review: yellow -> red at 7d -> "flash" red at 14d (flash = 🚨 + active page)
  - Thunderbird-Processed (Wing handled it) + Hale-Alert (needs Hale)
  - Same set mirrored in johnloucks3 AND d2mconcierge
  - Cleanse the cruft labels

Subcommands:  --setup | --cleanse | --age   (default: --age, for the timer)
"""
import sys, json, time, datetime
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

ROOT = Path("/home/john/Thunderbird")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.modify",
          "https://www.googleapis.com/auth/gmail.compose"]
ACCOUNTS = {
    "johnloucks3": ROOT / "creds/johnloucks3_token.json",
    "d2mconcierge": ROOT / "config/persona_gmail_token.json",
}
STATE = ROOT / "OpsCenter/state/label_aging_state.json"

# valid Gmail color pairs
YELLOW = {"backgroundColor": "#fad165", "textColor": "#684e00"}
RED    = {"backgroundColor": "#fb4c2f", "textColor": "#ffffff"}
GREEN  = {"backgroundColor": "#149e60", "textColor": "#ffffff"}
ORANGE = {"backgroundColor": "#ffad47", "textColor": "#594c05"}

REVIEW   = "THUNDERBIRD-Commander-Review"   # base, 19-file canonical — recolor only
R7       = "🔴 Review 7d+"
R14      = "🚨 Review 14d+"
PROCESSED= "THUNDERBIRD-Processed"
HALE     = "THUNDERBIRD-Hale-Alert"

CANONICAL = [(REVIEW, YELLOW), (R7, RED), (R14, RED), (PROCESSED, GREEN), (HALE, ORANGE)]

# cruft to delete (old superseded schemes). johnloucks3 only unless noted.
CLEANSE = {
    "johnloucks3": ["jbzsolutionsllc@gmail.com", "AI Screening - Routine",
        "AI/Screening-Hold", "AI/Screening-Review", "AI/Screening-Routine", "AI/Screening-Urgent",
        "PIPELINE/Dani-Queue", "PIPELINE/Inbound", "PIPELINE/Processed",
        "Commander Review/New", "Commander Review/Done"],
    "d2mconcierge": [],
}

def svc(tok):
    c = Credentials.from_authorized_user_info(json.loads(tok.read_text()), SCOPES)
    if not c.valid and c.expired and c.refresh_token:
        c.refresh(Request()); tok.write_text(c.to_json())
    return build("gmail", "v1", credentials=c)

def labels_by_name(s):
    return {l["name"]: l for l in s.users().labels().list(userId="me").execute().get("labels", [])}

def setup():
    for acct, tok in ACCOUNTS.items():
        s = svc(tok); have = labels_by_name(s)
        print(f"\n[{acct}]")
        for name, color in CANONICAL:
            try:
                if name in have:
                    s.users().labels().update(userId="me", id=have[name]["id"],
                        body={"id": have[name]["id"], "name": name, "color": color,
                              "labelListVisibility": "labelShow", "messageListVisibility": "show"}).execute()
                    print(f"  recolored {name}")
                else:
                    s.users().labels().create(userId="me",
                        body={"name": name, "color": color,
                              "labelListVisibility": "labelShow", "messageListVisibility": "show"}).execute()
                    print(f"  created   {name}")
            except Exception as e:
                print(f"  ! {name}: {str(e)[:80]}")

def cleanse():
    for acct, tok in ACCOUNTS.items():
        s = svc(tok); have = labels_by_name(s)
        print(f"\n[{acct}]")
        for name in CLEANSE.get(acct, []):
            if name in have:
                try:
                    s.users().labels().delete(userId="me", id=have[name]["id"]).execute()
                    print(f"  deleted {name}")
                except Exception as e:
                    print(f"  ! {name}: {str(e)[:70]}")
            else:
                print(f"  (absent) {name}")

def page_commander(msg):
    """14d 'flash' = active page (Gmail labels cannot animate)."""
    try:
        sys.path.insert(0, str(ROOT))
        from wing_page import page  # type: ignore
        page(f"🚨 Commander-Review 14d+ OVERDUE: {msg}")
        return True
    except Exception:
        (ROOT / "OpsCenter/state/review_14d_pages.log").open("a").write(
            f"{datetime.datetime.now().isoformat()} {msg}\n")
        return False

def age():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    now = time.time()
    for acct, tok in ACCOUNTS.items():
        s = svc(tok); have = labels_by_name(s)
        if REVIEW not in have:
            continue
        ids = {n: have[n]["id"] for n in (REVIEW, R7, R14) if n in have}
        q = s.users().messages().list(userId="me", labelIds=[ids[REVIEW]], maxResults=200).execute()
        for m in q.get("messages", []):
            full = s.users().messages().get(userId="me", id=m["id"], format="minimal").execute()
            internal = int(full.get("internalDate", "0")) / 1000.0
            key = f"{acct}:{m['id']}"
            first = state.get(key, internal or now)
            state[key] = first
            age_days = (now - first) / 86400.0
            cur = set(full.get("labelIds", []))
            add, rem = [], []
            if age_days >= 14:
                if ids.get(R14) and ids[R14] not in cur: add.append(ids[R14])
                if ids.get(R7) and ids[R7] in cur: rem.append(ids[R7])
                if not state.get(key + ":paged"):
                    page_commander(f"{acct} msg {m['id']} — {age_days:.0f}d in Commander-Review")
                    state[key + ":paged"] = True
            elif age_days >= 7:
                if ids.get(R7) and ids[R7] not in cur: add.append(ids[R7])
                if ids.get(R14) and ids[R14] in cur: rem.append(ids[R14])
            if add or rem:
                s.users().messages().modify(userId="me", id=m["id"],
                    body={"addLabelIds": add, "removeLabelIds": rem}).execute()
        print(f"[{acct}] aged {len(q.get('messages', []))} review items")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "--age"
    if cmd == "--setup": setup()
    elif cmd == "--cleanse": cleanse()
    else: age()
