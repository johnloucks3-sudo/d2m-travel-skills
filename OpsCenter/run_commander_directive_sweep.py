#!/usr/bin/env python3
# ============================================================
# ⚠️  PROTECTED FILE — THUNDERBIRD WING STANDING ORDER
# ============================================================
# DO NOT MODIFY this file without explicit authorization from
# Commander (John Loucks / Yoda) via Claude Code session.
#
# This file controls Commander email command detection.
# Unauthorized changes WILL break the COS tasking pipeline.
#
# Before ANY edit: read SO_EMAIL_SCANNER_PROTECT_20260608.md
# and confirm with Hale (Claude Code) before proceeding.
# ============================================================
"""
run_commander_directive_sweep.py — Lightweight Commander Directive Sweep
=========================================================================
Runs every 5 minutes via systemd timer. Scans the d2mconcierge inbox for
emails FROM johnloucks3@gmail.com where Commander has written a command prefix.

Detection rules (Commander directive 2026-06-08):
  - Subject STARTS WITH: cos: coo: hale: vic: cos-- coo-- hale-- (after stripping Re:/Fwd:)
  - OR body STARTS WITH one of those same prefixes
  - "cos" substring match DISABLED — was firing on SEA→COS (airport code), [COS] labels, etc.

Thread tracking: thread IDs of identified directive threads are saved. Any
subsequent reply in that thread is automatically tasked without re-checking.

Sweep Tracker: uses "commander_directive_sweep" with 4-min cooldown.
"""
import base64
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for sub in (ROOT / "core").iterdir():
    if sub.is_dir():
        sys.path.insert(0, str(sub))

from OpsCenter.sweep_tracker import SweepTracker

PROCESSED_LABEL = "THUNDERBIRD-Scanned"
COMMANDER_QUERY = f"from:johnloucks3@gmail.com -label:{PROCESSED_LABEL} newer_than:7d"
SCRIPTS_LOG = ROOT / "logs" / "commander_directive_sweep.log"
THREAD_STATE_FILE = ROOT / "logs" / "commander_directive_threads.json"

# Command detection: keyword (COS/COO/HALE/VIC) followed by ANY non-letter separator
# Matches: COS: COS-- COS- COS — HALE: HALE-- COO: COO-- Vic: etc.
import re as _re
COMMAND_PATTERN = _re.compile(r'^(cos|coo|hale|vic)\W', _re.IGNORECASE)
SUBJECT_PREFIXES = ("re:", "fwd:", "fw:", "aw:")

tracker = SweepTracker("commander_directive_sweep", cooldown_minutes=4)

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
    """Strip Re:/Fwd: prefixes from subject for prefix detection."""
    import re as _re
    return _re.sub(r'^(re:|fwd?:|aw:)\s*', '', subj.strip(), flags=_re.IGNORECASE)

def has_command_prefix_in_subject(subj: str) -> bool:
    """Subject must START WITH COS/COO/HALE/VIC + any non-letter separator."""
    return bool(COMMAND_PATTERN.match(clean_subject(subj)))

def has_command_prefix_in_body(body: str) -> bool:
    """Body must START WITH COS/COO/HALE/VIC + any non-letter separator."""
    return bool(COMMAND_PATTERN.match(body.strip()))

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

    # Fetch individual messages (not threads) — metadata-first for speed.
    # Paginate to catch all results (50-message limit would miss older commands).
    all_msgs = []
    _page_token = None
    while True:
        _kw = dict(userId="me", q=COMMANDER_QUERY, maxResults=50)
        if _page_token:
            _kw["pageToken"] = _page_token
        _page = service.users().messages().list(**_kw).execute()
        all_msgs.extend(_page.get("messages", []))
        _page_token = _page.get("nextPageToken")
        if not _page_token:
            break
    log_line(f"found {len(all_msgs)} messages from Commander in d2mconcierge")

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

    def _decode_text(payload):
        """Recursively extract text/plain from any MIME nesting depth."""
        if payload.get("mimeType", "").startswith("text/plain"):
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            result = _decode_text(part)
            if result:
                return result
        return ""

    tasked = 0
    for msg_ref in all_msgs:
        msg_id = msg_ref["id"]

        # Step 1: metadata fetch (fast — no body)
        try:
            msg_meta = service.users().messages().get(
                userId="me", id=msg_id, format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
        except Exception as e:
            log_line(f"metadata fetch failed {msg_id}: {e}")
            continue

        hdrs = {h["name"]: h["value"] for h in msg_meta["payload"]["headers"]}
        from_addr = hdrs.get("From", "").lower()
        if "johnloucks3" not in from_addr:
            continue

        subject = hdrs.get("Subject", "")
        thread_id = msg_meta.get("threadId", msg_id)

        # Fetch full message — needed for body text and To/CC routing
        body_text = ""
        to_addr = ""
        cc_addr = ""
        try:
            msg_full = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
            full_hdrs = {h["name"]: h["value"] for h in msg_full["payload"]["headers"]}
            to_addr = full_hdrs.get("To", "")
            cc_addr = full_hdrs.get("Cc", "")
            body_text = _decode_text(msg_full["payload"])
            thread_id = msg_full.get("threadId", thread_id)
        except Exception as e:
            log_line(f"full fetch failed {msg_id}: {e}")
            continue

        # Determine routing type — used in Claude prompt below
        has_prefix = has_command_prefix_in_subject(subject) or has_command_prefix_in_body(body_text)
        d2m_is_cc = "d2mconcierge" in cc_addr.lower() or "d2mluxury" in cc_addr.lower()
        d2m_is_to = "d2mconcierge" in to_addr.lower() or "d2mluxury" in to_addr.lower()

        # Only process if Commander explicitly directed d2m or used a command prefix.
        # - has_prefix:  COS:/COO:/HALE: at start of subject or body
        # - d2m_is_cc:   Commander CC'd d2mconcierge on a client/3rd-party email
        # - d2m_is_to:   Commander sent directly TO d2mconcierge
        # This filters out wing receipts (FROM johnloucks3 via send-as, TO johnloucks3)
        # and unrelated self-sends that happen to flow through d2mconcierge.
        if not has_prefix and not d2m_is_cc and not d2m_is_to:
            continue

        # Every Commander email that reaches here gets processed
        thread_is_directive = True

        if thread_is_directive:
            new_directive_ids.add(thread_id)
            log_line(f"  DIRECTIVE ({'thread' if thread_id in directive_thread_ids else 'new'}): {subject[:80]}")

            # body_text already extracted correctly above via _decode_text()

            # ── Dispatch to Claude headless for execution ────────────────────────
            try:
                import subprocess as _sp
                import tempfile as _tf
                import time as _time

                ts = int(_time.time())
                out_file = ROOT / f"output/directive_{ts}.md"
                out_file.parent.mkdir(parents=True, exist_ok=True)

                # Routing hint for Claude based on email type
                if has_prefix:
                    routing_hint = (
                        "This email has a COS/COO/HALE command prefix — treat as a direct "
                        "tasking to the Wing. Execute the command fully."
                    )
                elif d2m_is_cc:
                    routing_hint = (
                        "Commander CC'd d2mconcierge on this email (likely sent to a client "
                        "or third party). Route to Dani (A3) — note any commitments made, "
                        "update the client dossier if relevant, and flag any follow-up needed."
                    )
                else:
                    routing_hint = (
                        "Commander sent this email to d2mconcierge. Classify it: if it "
                        "contains a task or question, execute it. If it is forwarding "
                        "information, summarize and route to the right persona."
                    )

                task_prompt = (
                    f"Commander John Loucks sent this email to the Wing.\n\n"
                    f"FROM: johnloucks3@gmail.com\n"
                    f"TO: {to_addr[:200]}\n"
                    f"CC: {cc_addr[:200]}\n"
                    f"Subject: {subject}\n\n"
                    f"Body:\n{body_text[:3000]}\n\n"
                    f"ROUTING CONTEXT: {routing_hint}\n\n"
                    f"Produce a complete Wing response. Sign as: — V. Hale, VCS | Thunderbird Wing\n\n"
                    f"WRITE your complete response to {out_file}"
                )

                _sp.Popen(
                    [
                        sys.executable,
                        str(ROOT / "OpsCenter/dispatch_claude.py"),
                        "--task", f"directive-{ts}",
                        "--output", str(out_file),
                        "--prompt", task_prompt,
                        "--model", "sonnet",
                    ],
                    stdout=open(ROOT / f"logs/directive_{ts}.log", "w"),
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    cwd=str(ROOT),
                )
                log_line(f"  dispatched to Claude — output: {out_file}")
            except Exception as e:
                log_line(f"  dispatch failed: {e}")

            # ── Telegram notification ────────────────────────────────────────────
            try:
                _notify_cos(
                    classification="commander_directive",
                    sender="johnloucks3@gmail.com",
                    subject=subject,
                    persona_id="COS",
                    draft_id=None,
                    persona_note=f"⚡ COMMANDER DIRECTIVE — dispatched to Claude\n\n"
                                 f"Subject: {subject}\n\n"
                                 f"Body preview: {body_text[:200]}"
                )
            except Exception as e:
                log_line(f"  notify failed: {e}")

            # ── Apply processed label ────────────────────────────────────────────
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

    log_line(f"done — scanned={len(all_msgs)} tasked={tasked} tracked_threads={len(all_directive_ids)}")
    tracker.mark_complete(status="ok", note=f"found={len(all_msgs)} tasked={tasked}")
    sys.exit(0)

except Exception as e:
    log_line(f"error: {e}")
    tracker.mark_failed(str(e)[:200])
    sys.exit(1)
