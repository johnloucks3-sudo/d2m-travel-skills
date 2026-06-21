#!/usr/bin/env python3
"""
commander_task_intake.py — Commander "handle this" → tracked task, the RIGHT way.

DESIGN (Commander spec 2026-06-20):
  - Trigger = Commander CC/forwards/sends to d2mconcierge. Same for all three (and
    the future Gmail add-on button). That is the ONLY signal — no auto-guessing.
  - SCOPE: ONLY d2mconcierge's INBOX, ONLY from the Commander, ONLY new (watermark).
    (The 137-mess came from also scanning johnloucks3's own mailbox = all sent mail.
     That account is NEVER scanned here.)
  - The poller NEVER replies (no loop). It queues a mission + labels Hale-Alert.
  - The WORKER (Hale/AI) interprets the note-or-thread, does the work, and replies.

  *** HARD RULE — REPLY TO THE COMMANDER ONLY ***
  When a task came from a thread that has a CLIENT (or anyone else) on it, the Wing
  replies To: johnloucks3@gmail.com ONLY. Never reply-all. Never to the client.
  The client hears nothing from the Wing except a WF-17 draft the Commander sends himself.

Run: (default) intake new taskings | --metric | --reset-watermark
"""
import sys, json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

ROOT = Path("/home/john/Thunderbird")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.modify",
          "https://www.googleapis.com/auth/gmail.compose"]
TOKEN = ROOT/"config/persona_gmail_token.json"        # d2mconcierge ONLY
COMMANDER = "from:(johnloucks3@gmail.com OR yodainva OR john.loucks)"
WATERMARK = ROOT/"OpsCenter/state/commander_intake_watermark.json"
STATE = ROOT/"OpsCenter/state/commander_intake_state.json"
BOARD = ROOT/"OpsCenter/mission_board.json"
ALERT = "THUNDERBIRD-Hale-Alert"   # queued, needs Hale
DONE  = "THUNDERBIRD-Processed"     # task executed

def svc():
    c = Credentials.from_authorized_user_info(json.loads(TOKEN.read_text()), SCOPES)
    if not c.valid and c.expired and c.refresh_token:
        c.refresh(Request()); TOKEN.write_text(c.to_json())
    return build("gmail", "v1", credentials=c)

def labels(s):
    return {l["name"]: l["id"] for l in s.users().labels().list(userId="me").execute().get("labels", [])}

def _wm():
    return json.loads(WATERMARK.read_text())["ms"] if WATERMARK.exists() else None

def _set_wm(ms):
    WATERMARK.parent.mkdir(parents=True, exist_ok=True)
    WATERMARK.write_text(json.dumps({"ms": ms}, indent=2))

def metric():
    s = svc(); lab = labels(s)
    if ALERT not in lab:
        print("UNACTIONED_COMMANDER_TASKINGS=0 (label missing)"); return 0
    r = s.users().messages().list(userId="me",
        q=f"{COMMANDER} in:inbox label:{ALERT} -label:{DONE}", maxResults=200).execute()
    n = r.get("resultSizeEstimate", 0)
    print(f"UNACTIONED_COMMANDER_TASKINGS={n} (target 0)")
    (ROOT/"OpsCenter/state").mkdir(parents=True, exist_ok=True)
    (ROOT/"OpsCenter/state/commander_unactioned_metric.json").write_text(json.dumps({"unactioned": n}, indent=2))
    return n

def intake():
    s = svc(); lab = labels(s)
    alert_id = lab.get(ALERT)
    if not alert_id:
        print(f"{ALERT} missing — run label_system.py --setup"); return
    wm = _wm()
    # first run: set watermark = now (newest msg), process nothing historical
    newest = s.users().messages().list(userId="me", q=f"{COMMANDER} in:inbox", maxResults=1).execute()
    if wm is None:
        if newest.get("messages"):
            top = s.users().messages().get(userId="me", id=newest["messages"][0]["id"], format="minimal").execute()
            _set_wm(int(top.get("internalDate", "0")))
        else:
            _set_wm(0)
        print(f"First run — watermark set to now; no historical sweep. (Curated backlog handled separately.)")
        metric(); return
    state = json.loads(STATE.read_text()) if STATE.exists() else {"processed": []}
    seen = set(state["processed"])
    board = json.loads(BOARD.read_text()); ms = board.get("missions", board.get("tasks", []))
    n = max([int(m["id"].split("-")[1]) for m in ms
             if str(m.get("id","")).startswith("MISSION-") and m["id"].split("-")[1].isdigit()] + [0])
    r = s.users().messages().list(userId="me", q=f"{COMMANDER} in:inbox", maxResults=50).execute()
    added = 0; maxms = wm
    for m in r.get("messages", []):
        full = s.users().messages().get(userId="me", id=m["id"], format="metadata").execute()
        internal = int(full.get("internalDate", "0"))
        if internal <= wm or m["id"] in seen or alert_id in full.get("labelIds", []):
            continue
        hs = {h["name"].lower(): h["value"] for h in full.get("payload", {}).get("headers", [])}
        subj = hs.get("subject", "(no subject)")
        n += 1
        ms.append({"id": f"MISSION-{n:03d}", "title": f"Commander: {subj[:65]}",
                   "priority": "P1", "status": "active", "owner": "HALE",
                   "notes": f"Commander CC/fwd to d2mconcierge {hs.get('date','')[:22]} | msg {m['id']} | "
                            f"REPLY TO COMMANDER ONLY | {full.get('snippet','')[:140]}"})
        s.users().messages().modify(userId="me", id=m["id"], body={"addLabelIds": [alert_id]}).execute()
        seen.add(m["id"]); added += 1; maxms = max(maxms, internal)
        print(f"  queued MISSION-{n:03d}: {subj[:55]}")
    if "missions" in board: board["missions"] = ms
    else: board["tasks"] = ms
    BOARD.write_text(json.dumps(board, indent=2))
    state["processed"] = sorted(seen); STATE.write_text(json.dumps(state, indent=2))
    _set_wm(maxms)
    print(f"\nIntake: {added} new Commander taskings queued (d2mconcierge only, from Commander, new).")
    metric()

if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else ""
    if a == "--metric": metric()
    elif a == "--reset-watermark":
        WATERMARK.unlink(missing_ok=True); print("watermark reset")
    else: intake()
