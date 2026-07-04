#!/usr/bin/env python3
"""
d2m_inbox_triage.py — General-purpose d2mconcierge INBOX triage (closed loop).

Every new inbound message gets an explicit disposition — no silent reads
(SO_EMAIL_CLOSED_LOOP_20260625). Rules-first, ZERO model calls in this loop
(ELON P0 doctrine 2026-06-28); classification via core/email/rules_classifier.

Dispositions by category:
  client_inquiry / booking_confirmation / financial
      → Telegram page (P1) + OpsCenter/client_inbox_queue.jsonl
  commander_directive / direct_command / internal_wing
      → delegated (owned by directive-sweep / email-task-ingest / d2m-email-c2)
  spam
      → Label_102 (ForDeletion) + archive — inbox-hygiene trashes Label_102
  supplier_intel / intel / other
      → D2M-TRIAGED label (audit trail, no page)

Cursor: OpsCenter/state/d2m_inbox_triage_cursor.json — initialized to NOW on
first run so pre-deployment mail is never touched (Commander order 2026-07-04).
Log:    OpsCenter/state/d2m_inbox_triage_log.jsonl (one line per disposition)
Timer:  d2m-inbox-triage.timer (every 5 min)

Default is --dry-run. Pass --apply to mutate labels / page / write the queue.

Dreams2Memories Travel, LLC · 2026-07-04
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from email.header import decode_header, make_header
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from core.email.rules_classifier import classify, is_d2m_relevant

# d2mconcierge token. NOT ROOT/gmail_token.json — that file is actually the
# johnloucks3 account (verified via Gmail profile 2026-07-04).
TOKEN = ROOT / "config/persona_gmail_token.json"
CURSOR = ROOT / "OpsCenter/state/d2m_inbox_triage_cursor.json"
LOG = ROOT / "OpsCenter/state/d2m_inbox_triage_log.jsonl"
QUEUE = ROOT / "OpsCenter/client_inbox_queue.jsonl"

LABEL_FOR_DELETION = "Label_102"   # same id inbox_hygiene sweeps to trash
TRIAGED_LABEL_NAME = "D2M-TRIAGED"

DELEGATED = {"commander_directive", "direct_command", "internal_wing"}
PAGE = {"client_inquiry", "booking_confirmation", "financial"}


def gmail():
    creds = Credentials.from_authorized_user_file(str(TOKEN))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def hdr(msg, name):
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return str(make_header(decode_header(h["value"])))
    return ""


def load_cursor():
    if CURSOR.exists():
        return json.loads(CURSOR.read_text())
    # First run: fence off everything already sitting in the inbox.
    return {"after_epoch": int(time.time()), "seen": [],
            "initialized": datetime.now(timezone.utc).isoformat()}


def save_cursor(cur):
    cur["seen"] = cur["seen"][-1000:]
    cur["last_run"] = datetime.now(timezone.utc).isoformat()
    CURSOR.parent.mkdir(parents=True, exist_ok=True)
    CURSOR.write_text(json.dumps(cur, indent=1))


def queued_msg_ids():
    """Message ids already queued by client_inbox_watch — avoid double-paging."""
    if not QUEUE.exists():
        return set()
    ids = set()
    for line in QUEUE.read_text().splitlines():
        try:
            ids.add(json.loads(line).get("msg_id"))
        except (json.JSONDecodeError, AttributeError):
            continue
    return ids


def get_triaged_label_id(svc, cur, apply):
    if cur.get("triaged_label_id"):
        return cur["triaged_label_id"]
    labels = svc.users().labels().list(userId="me").execute().get("labels", [])
    for lb in labels:
        if lb["name"] == TRIAGED_LABEL_NAME:
            cur["triaged_label_id"] = lb["id"]
            return lb["id"]
    if not apply:
        return None  # dry-run: don't create
    created = svc.users().labels().create(
        userId="me",
        body={"name": TRIAGED_LABEL_NAME, "labelListVisibility": "labelShow",
              "messageListVisibility": "show"}).execute()
    cur["triaged_label_id"] = created["id"]
    return created["id"]


def disposition_for(category):
    if category in DELEGATED:
        return "delegated"
    if category in PAGE:
        return "page+queue"
    if category == "spam":
        return "for_deletion+archive"
    return "triaged"


def page_commander(hit):
    from core.comms.wing_page import send_page
    send_page(
        problem=f"📧 d2m inbound ({hit['category']}): \"{hit['subject']}\"",
        discussion=f"From: {hit['from']}\n{hit['snippet']}",
        action="Queued in client_inbox_queue — Wing drafts reply to johnloucks3 drafts (WF-17).",
        level="P1",
        source="Hale",
    )


def main():
    ap = argparse.ArgumentParser(description="d2mconcierge general inbox triage")
    ap.add_argument("--apply", action="store_true",
                    help="Mutate labels, page Commander, write queue (default: dry-run)")
    args = ap.parse_args()
    apply = args.apply

    cur = load_cursor()
    seen = set(cur["seen"])
    already_queued = queued_msg_ids()
    svc = gmail()

    q = f"in:inbox after:{cur['after_epoch']}"
    res = svc.users().messages().list(userId="me", q=q, maxResults=50).execute()
    msgs = [m for m in res.get("messages", []) if m["id"] not in seen]

    dispositions = []
    max_epoch = cur["after_epoch"]
    triaged_label = get_triaged_label_id(svc, cur, apply) if msgs else cur.get("triaged_label_id")

    for m in msgs:
        full = svc.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"]).execute()
        sender = hdr(full, "From")
        subject = hdr(full, "Subject")
        snippet = full.get("snippet", "")[:300]
        category = classify(sender, subject, snippet)
        dispo = disposition_for(category)
        if dispo == "page+queue" and m["id"] in already_queued:
            dispo = "delegated"  # client_inbox_watch already paged this one

        hit = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "msg_id": m["id"],
            "thread_id": full.get("threadId"),
            "from": sender,
            "subject": subject,
            "snippet": snippet,
            "category": category,
            "disposition": dispo,
            "applied": apply,
        }

        if apply:
            if dispo == "page+queue":
                with QUEUE.open("a") as f:
                    f.write(json.dumps({**hit,
                        "action": "DRAFT RESPONSE -> johnloucks3 drafts (WF-17)",
                        "status": "PENDING"}) + "\n")
                try:
                    page_commander(hit)
                except Exception as e:
                    print(f"telegram page failed (queued anyway): {e}")
            elif dispo == "for_deletion+archive":
                svc.users().messages().modify(
                    userId="me", id=m["id"],
                    body={"addLabelIds": [LABEL_FOR_DELETION],
                          "removeLabelIds": ["INBOX", "UNREAD"]}).execute()
            elif dispo == "triaged" and triaged_label:
                svc.users().messages().modify(
                    userId="me", id=m["id"],
                    body={"addLabelIds": [triaged_label]}).execute()

        dispositions.append(hit)
        seen.add(m["id"])
        # internalDate is ms; Gmail `after:` is inclusive-second, so keep max-1s back-off
        max_epoch = max(max_epoch, int(int(full.get("internalDate", "0")) / 1000) - 1)

    if apply and dispositions:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            for d in dispositions:
                f.write(json.dumps(d) + "\n")

    cur["seen"] = list(seen)
    cur["after_epoch"] = max_epoch
    if apply or not CURSOR.exists():
        save_cursor(cur)  # first dry-run still plants the fence-off cursor

    mode = "APPLY" if apply else "DRY-RUN"
    summary = ", ".join(f"{d['category']}→{d['disposition']}" for d in dispositions) or "none"
    print(f"{datetime.now():%H:%M} [{mode}] — {len(dispositions)} new message(s): {summary}")


if __name__ == "__main__":
    main()
