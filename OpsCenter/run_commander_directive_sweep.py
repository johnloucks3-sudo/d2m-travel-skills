#!/usr/bin/env python3
"""
run_commander_directive_sweep.py — Lightweight Commander Directive Sweep
=========================================================================
Runs every 10 minutes via systemd timer. Scans the d2mconcierge inbox for
emails from johnloucks3@gmail.com. Tasks any message where COS, COO, or HALE
appears in either the subject or the body salutation.

Thread tracking: thread IDs of identified directive threads are saved. Any
subsequent reply in that thread is automatically tasked without re-checking.

Sweep Tracker: uses "commander_directive_sweep" with 9-min cooldown.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for sub in (ROOT / "core").iterdir():
    if sub.is_dir():
        sys.path.insert(0, str(sub))

from OpsCenter.sweep_tracker import SweepTracker

COMMANDER_QUERY = "from:johnloucks3@gmail.com is:unread"
PROCESSED_LABEL = "THUNDERBIRD-Scanned"
SCRIPTS_LOG = ROOT / "logs" / "commander_directive_sweep.log"
THREAD_STATE_FILE = ROOT / "logs" / "commander_directive_threads.json"

DIRECTIVE_KEYWORDS = ("cos", "coo", "hale")
SUBJECT_PREFIXES = ("re:", "fwd:", "fw:", "aw:")

tracker = SweepTracker("commander_directive_sweep", cooldown_minutes=9)

if tracker.in_cooldown():
    sys.exit(0)

def log_line(msg: str):
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(SCRIPTS_LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def load_thread_state() -> set:
    try:
        if THREAD_STATE_FILE.exists():
            data = json.loads(THREAD_STATE_FILE.read_text())
            return set(data.get("directive_thread_ids", []))
    except Exception:
        pass
    return set()

def save_thread_state(thread_ids: set):
    try:
        THREAD_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        THREAD_STATE_FILE.write_text(json.dumps({
            "directive_thread_ids": sorted(thread_ids)
        }, indent=2))
    except Exception as e:
        log_line(f"failed to save thread state: {e}")

def clean_subject(subj: str) -> str:
    s = subj.lower().strip()
    for p in SUBJECT_PREFIXES:
        if s.startswith(p):
            s = s[len(p):].strip().lstrip(",").strip()
            break
    return s

def has_keyword_in_subject(subj: str) -> bool:
    clean = clean_subject(subj)
    for kw in DIRECTIVE_KEYWORDS:
        if kw in clean:
            return True
    return False

def has_keyword_in_body(body: str) -> bool:
    first_chars = body[:500].lower()
    for kw in DIRECTIVE_KEYWORDS:
        if kw in first_chars:
            return True
    return False

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_file = ROOT / "gmail_token.json"
    if not token_file.exists():
        log_line("d2mconcierge token not found — skipping")
        sys.exit(0)

    creds = Credentials.from_authorized_user_file(str(token_file))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json())
    if not creds.valid:
        log_line("d2mconcierge token invalid — skipping")
        sys.exit(0)

    service = build("gmail", "v1", credentials=creds)

    # Fetch unread threads from johnloucks3 (not just messages — to track thread context)
    thread_results = service.users().threads().list(
        userId="me", q=COMMANDER_QUERY
    ).execute()
    thread_refs = thread_results.get("threads", [])
    log_line(f"found {len(thread_refs)} unread threads from Commander in d2mconcierge")

    # Load previously identified directive thread IDs
    directive_thread_ids = load_thread_state()
    new_directive_ids = set()

    # Get/create processed label
    label_id = None
    try:
        labels = service.users().labels().list(userId="me").execute()
        for lbl in labels.get("labels", []):
            if lbl["name"] == PROCESSED_LABEL:
                label_id = lbl["id"]
                break
        if not label_id:
            lbl = service.users().labels().create(
                userId="me",
                body={"name": PROCESSED_LABEL, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
            ).execute()
            label_id = lbl["id"]
    except Exception:
        pass

    from core.email.thunderbird_commander_inbox import _notify_cos

    tasked = 0
    for thread_ref in thread_refs:
        thread_id = thread_ref["id"]
        try:
            thread = service.users().threads().get(
                userId="me", id=thread_id,
                format="full"
            ).execute()
        except Exception as e:
            log_line(f"failed to get thread {thread_id}: {e}")
            continue

        # Only process the LATEST message in the thread from johnloucks3
        latest_msg = thread["messages"][-1]
        msg_id = latest_msg["id"]
        headers = {h["name"]: h["value"] for h in latest_msg["payload"]["headers"]}
        subject = headers.get("Subject", "")
        is_reply = any(subject.lower().startswith(p) for p in SUBJECT_PREFIXES)

        # Check if this thread is already known as a directive
        thread_is_directive = thread_id in directive_thread_ids

        # If not already known, check subject and body
        if not thread_is_directive:
            if has_keyword_in_subject(subject):
                thread_is_directive = True
            else:
                # Need body to check
                body_text = ""
                if "parts" in latest_msg["payload"]:
                    for part in latest_msg["payload"]["parts"]:
                        if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                            import base64
                            body_text = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                            break
                elif "body" in latest_msg["payload"] and "data" in latest_msg["payload"]["body"]:
                    import base64
                    body_text = base64.urlsafe_b64decode(latest_msg["payload"]["body"]["data"]).decode("utf-8", errors="replace")
                if has_keyword_in_body(body_text):
                    thread_is_directive = True

        if thread_is_directive:
            new_directive_ids.add(thread_id)
            log_line(f"  DIRECTIVE ({'thread' if thread_id in directive_thread_ids else 'new'}): {subject[:80]}")

            try:
                _notify_cos(
                    classification="commander_directive",
                    sender="johnloucks3@gmail.com",
                    subject=subject,
                    persona_id="COS",
                    draft_id=None,
                    persona_note=f"⚡ COMMANDER DIRECTIVE\n\nSubject: {subject}\n\n"
                                 f"Action: Task to Hale for immediate execution."
                )
            except Exception as e:
                log_line(f"  notify failed: {e}")

            if label_id:
                try:
                    service.users().messages().modify(
                        userId="me", id=msg_id,
                        body={"addLabelIds": [label_id]}
                    ).execute()
                except Exception:
                    pass

            tasked += 1

    all_directive_ids = directive_thread_ids | new_directive_ids
    save_thread_state(all_directive_ids)

    log_line(f"done — scanned={len(thread_refs)} tasked={tasked} tracked_threads={len(all_directive_ids)}")
    tracker.mark_complete(status="ok", note=f"found={len(thread_refs)} tasked={tasked}")
    sys.exit(0)

except Exception as e:
    log_line(f"error: {e}")
    tracker.mark_failed(str(e)[:200])
    sys.exit(1)
