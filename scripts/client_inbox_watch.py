#!/usr/bin/env python3
"""
client_inbox_watch.py — Watch d2mconcierge for inbound mail from registered clients.

Registry: config/client_inbox_watch.json
On new mail from a watched client:
  1. Telegram page to Commander (via core/comms/wing_page.py, source=Dani)
  2. Append to OpsCenter/client_inbox_queue.jsonl — the Wing's draft-response queue
     (Wing drafts the reply into johnloucks3 drafts; WF-17 — Commander sends)

State: OpsCenter/.client_inbox_watch_state.json (seen message ids, capped)
Timer: client-inbox-watch.timer (every 10 min)

Dreams2Memories Travel, LLC · 2026-07-03
"""
import json
import socket
import sys
from datetime import datetime, timezone
from email.header import decode_header, make_header
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httplib2
import google_auth_httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CONFIG = ROOT / "config/client_inbox_watch.json"
STATE = ROOT / "OpsCenter/.client_inbox_watch_state.json"
QUEUE = ROOT / "OpsCenter/client_inbox_queue.jsonl"


def gmail(token_path):
    tp = Path(token_path)
    creds = Credentials.from_authorized_user_file(str(tp))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        tp.write_text(creds.to_json())
    http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http(timeout=30))
    return build("gmail", "v1", http=http)


def hdr(msg, name):
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return str(make_header(decode_header(h["value"])))
    return ""


def main():
    cfg = json.loads(CONFIG.read_text())
    state = json.loads(STATE.read_text()) if STATE.exists() else {"seen": []}
    seen = set(state["seen"])
    svc = gmail(cfg["account_token"])

    new_hits = []
    for client in cfg["clients"]:
        q = f"from:({' OR '.join(client['addresses'])}) newer_than:3d"
        res = svc.users().messages().list(userId="me", q=q, maxResults=20).execute()
        for m in res.get("messages", []):
            if m["id"] in seen:
                continue
            full = svc.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["Subject", "From", "Date"]).execute()
            new_hits.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "client": client["name"],
                "program": client["program"],
                "msg_id": m["id"],
                "thread_id": full.get("threadId"),
                "from": hdr(full, "From"),
                "subject": hdr(full, "Subject"),
                "date": hdr(full, "Date"),
                "snippet": full.get("snippet", "")[:300],
                "action": "DRAFT RESPONSE -> johnloucks3 drafts (WF-17)",
                "status": "PENDING",
            })
            seen.add(m["id"])

    for hit in new_hits:
        with QUEUE.open("a") as f:
            f.write(json.dumps(hit) + "\n")
        try:
            from core.comms.wing_page import send_page
            send_page(
                problem=f"📧 {hit['client']} emailed d2mconcierge: \"{hit['subject']}\"",
                discussion=hit["snippet"],
                action="Wing is drafting a response into johnloucks3 drafts for your review.",
                level="P1",
                source="Dani",
            )
        except Exception as e:
            print(f"telegram page failed (queued anyway): {e}")

    state["seen"] = list(seen)[-500:]
    STATE.write_text(json.dumps(state))
    print(f"{datetime.now():%H:%M} — {len(new_hits)} new client message(s)" +
          (": " + "; ".join(h["subject"] for h in new_hits) if new_hits else ""))


if __name__ == "__main__":
    try:
        main()
    except (TimeoutError, socket.timeout, OSError) as e:
        print(f"{datetime.now():%H:%M} — network timeout, skipping cycle: {e}", file=sys.stderr)
        sys.exit(0)
