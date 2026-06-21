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

PROCESSED_LABEL = "THUNDERBIRD-DirectiveReplied"  # 2026-06-16: was "THUNDERBIRD-Scanned" — SHARED with the inbox-sweep, which stamped Commander emails first so this sweep skipped them as "processed" → labeled-but-never-replied. Distinct label fixes it.
COMMANDER_QUERY = f"from:johnloucks3@gmail.com -label:{PROCESSED_LABEL} newer_than:3d"
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
    # Print to stdout only — systemd appends stdout to SCRIPTS_LOG.
    # Direct file write removed: was causing every line to appear twice.
    print(line, flush=True)

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

def validate_authentication(headers: list) -> bool:
    """
    ⚠️  CRITICAL SECURITY: Verify Gmail authenticated this email.

    The SMTP From header is forgeable. Gmail adds Authentication-Results
    after verifying SPF/DKIM/DMARC. We check DKIM=pass to ensure the
    message genuinely came from johnloucks3@gmail.com.

    This is the fix for MISSION-254: spoofable-From trust boundary.
    """
    auth_results = ""
    for h in headers:
        if h.get("name", "").lower() == "authentication-results":
            auth_results = h.get("value", "").lower()
            break

    if not auth_results:
        # No Authentication-Results header — Gmail didn't authenticate this.
        # This can happen for local/test emails, but for johnloucks3@gmail.com
        # it should always be present. Log and reject.
        log_line("  ⚠️  SECURITY: No Authentication-Results header found — rejecting")
        return False

    # Check for DKIM pass. Gmail's format: "...dkim=pass..." or "...dkim=PASS..."
    if "dkim=pass" not in auth_results:
        log_line(f"  ⚠️  SECURITY: DKIM authentication failed — rejecting | auth={auth_results[:100]}")
        return False

    return True

def sanitize_prompt_input(text: str, max_len: int = 2000, field_name: str = "field") -> str:
    """
    Sanitize user input before interpolation into prompt.

    Prevents prompt injection by:
    1. Truncating to max_len (already done downstream, but explicit here)
    2. Warning if input contains suspicious patterns
    3. Escaping newlines so multi-line injections can't break prompt structure
    """
    if not text:
        return ""

    # Truncate
    text = text[:max_len]

    # Warn on suspicious patterns (don't block — just log)
    suspicious = [
        ("SYSTEM:", "system override attempt"),
        ("WRITE ", "file write injection"),
        ("--prompt", "prompt override"),
        ("--model", "model override"),
        ("execute", "command execution"),
    ]
    for pattern, reason in suspicious:
        if pattern.lower() in text.lower():
            log_line(f"  ⚠️  PROMPT_INJECTION_ATTEMPT ({field_name}): {reason} detected")

    return text

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

    # johnloucks3 token — scans Commander's sent mail for emails TO d2mconcierge
    jl3_token_file = ROOT / "gmail_token.json"
    if not jl3_token_file.exists():
        log_line("johnloucks3 token not found — skipping")
        sys.exit(0)

    creds = Credentials.from_authorized_user_file(str(jl3_token_file))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        jl3_token_file.write_text(creds.to_json())
    if not creds.valid:
        log_line("johnloucks3 token invalid — skipping")
        sys.exit(0)

    service = build("gmail", "v1", credentials=creds)

    # d2mconcierge token — scans d2mconcierge inbox for self-sends (d2m→d2m)
    d2mc_token_file = ROOT / "config" / "persona_gmail_token.json"
    d2mc_service = None
    if d2mc_token_file.exists():
        try:
            d2mc_creds = Credentials.from_authorized_user_file(str(d2mc_token_file))
            if d2mc_creds.expired and d2mc_creds.refresh_token:
                d2mc_creds.refresh(Request())
                d2mc_token_file.write_text(d2mc_creds.to_json())
            if d2mc_creds.valid:
                d2mc_service = build("gmail", "v1", credentials=d2mc_creds)
        except Exception as e:
            log_line(f"d2mconcierge token load failed: {e}")

    # Collect messages from both accounts
    # 1. johnloucks3 sent to d2mconcierge (from:johnloucks3, any unread in sent)
    # 2. d2mconcierge inbox unread (self-sends or Commander emails via d2mc)
    D2MC_QUERY = f"from:johnloucks3@gmail.com -label:{PROCESSED_LABEL} newer_than:3d"
    D2MC_SELF_QUERY = f"in:inbox -label:{PROCESSED_LABEL} newer_than:3d"

    # jl3 SENT-mail path DISABLED 2026-06-16 (Commander spec: reply when an email "hits the
    # d2m inbox from johnloucks3"). The d2mconcierge INBOX loop below is the SOLE replier.
    # Scanning jl3's sent copies caused (a) double-replies (sent copy + inbox copy) and
    # (b) a separate label namespace that re-fired on old mail. One path = one reply.
    all_msgs = []

    # Also collect from d2mconcierge inbox if token available
    d2mc_msgs = []
    if d2mc_service:
        try:
            _d2mc_page = d2mc_service.users().messages().list(
                userId="me", q=D2MC_SELF_QUERY, maxResults=20
            ).execute()
            d2mc_msgs = _d2mc_page.get("messages", [])
        except Exception as e:
            log_line(f"d2mconcierge inbox scan failed: {e}")
    log_line(f"found {len(all_msgs)} jl3 msgs + {len(d2mc_msgs)} d2mc inbox msgs")

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
                metadataHeaders=["From", "Subject", "Date", "Authentication-Results"]
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

        # ⚠️  SECURITY FIX (MISSION-254): Verify Gmail authenticated this email
        # before processing. The SMTP From header is forgeable; we check Gmail's
        # Authentication-Results header to confirm the message genuinely came from
        # johnloucks3@gmail.com via DKIM signature verification.
        if not validate_authentication(msg_meta["payload"]["headers"]):
            # Skip this message — not authenticated by Gmail
            continue

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
            msg_id_header = full_hdrs.get("Message-ID", "")
            body_text = _decode_text(msg_full["payload"])
            thread_id = msg_full.get("threadId", thread_id)
        except Exception as e:
            log_line(f"full fetch failed {msg_id}: {e}")
            continue

        # Determine routing type — used in Claude prompt below
        has_prefix = has_command_prefix_in_subject(subject) or has_command_prefix_in_body(body_text)
        d2m_is_cc = "d2mconcierge" in cc_addr.lower() or "d2mluxury" in cc_addr.lower()
        d2m_is_to = "d2mconcierge" in to_addr.lower() or "d2mluxury" in to_addr.lower()

        # Skip emails not addressed to d2m and without a command prefix.
        # Apply label even on skip so non-directive d2m emails drain from the queue.
        if not has_prefix and not d2m_is_cc and not d2m_is_to:
            if label_id:
                try:
                    service.users().messages().modify(
                        userId="me", id=msg_id,
                        body={"addLabelIds": [label_id]}
                    ).execute()
                except Exception:
                    pass
            continue

        # If email is directly TO d2mconcierge, skip jl3 dispatch — d2mc path handles
        # it with the correct thread_id. Label to drain from jl3 queue.
        if d2m_is_to and not d2m_is_cc:
            if label_id:
                try:
                    service.users().messages().modify(
                        userId="me", id=msg_id,
                        body={"addLabelIds": [label_id]}
                    ).execute()
                except Exception:
                    pass
            continue

        # Every Commander email that reaches here gets dispatched (CC'd or prefix-only)
        new_directive_ids.add(thread_id)
        log_line(f"  DIRECTIVE ({'thread' if thread_id in directive_thread_ids else 'new'}): {subject[:80]}")

        # ── Dispatch to Claude headless for execution ────────────────────────
        try:
            import subprocess as _sp
            import time as _time

            ts = int(_time.time())
            out_file = ROOT / f"output/directive_{ts}.md"
            out_file.parent.mkdir(parents=True, exist_ok=True)

            # ⚠️  SECURITY: Sanitize subject + body before prompt interpolation (MISSION-254)
            safe_subject = sanitize_prompt_input(subject, max_len=200, field_name="subject")
            safe_body = sanitize_prompt_input(body_text, max_len=2000, field_name="body")

            task_prompt = (
                f"You are Hale, COS for John Loucks at Dreams2Memories Travel. "
                f"John just emailed you:\n\n"
                f"Subject: {safe_subject}\n\n"
                f"{safe_body}\n\n"
                f"Reply using pilot brevity. No formal header, no sign-off, no wings branding.\n"
                f"- If it's a task you will execute: start with 'Wilco —' then RESTATE the task in your own words so Commander knows you understood it correctly. One sentence.\n"
                f"- If it's information or a question you're answering: start with 'Roger —' then RESTATE what was asked, then answer it.\n"
                f"- If something is already done or confirmed complete: start with 'Done —' then RESTATE what was completed.\n"
                f"The restatement is the confirmation. Never skip it. Under 100 words total.\n\n"
                f"WRITE your reply to {out_file}"
            )

            _sp.Popen(
                [
                    sys.executable,
                    str(ROOT / "OpsCenter/dispatch_and_email.py"),
                    "--task", f"directive-{ts}",
                    "--output", str(out_file),
                    "--prompt", task_prompt,
                    "--subject", subject or "(no subject)",
                    "--model", "haiku",
                    "--timeout", "1800",
                    "--thread-id", thread_id or "",
                    "--in-reply-to", msg_id_header or "",
                ],
                stdout=open(ROOT / f"logs/directive_{ts}.log", "w"),
                stderr=subprocess.STDOUT,
                start_new_session=True,
                cwd=str(ROOT),
            )
            log_line(f"  dispatched (threaded reply) — output: {out_file}")
        except Exception as e:
            log_line(f"  dispatch failed: {e}")

        # Mark processed so it doesn't re-trigger
        if label_id:
            try:
                service.users().messages().modify(
                    userId="me", id=msg_id,
                    body={"addLabelIds": [label_id]}
                ).execute()
            except Exception:
                pass

        tasked += 1

    # ── Process d2mconcierge inbox messages (d2m→d2m self-sends) ────────────────
    if d2mc_service and d2mc_msgs:
        d2mc_label_id = None
        try:
            d2mc_labels = d2mc_service.users().labels().list(userId="me").execute()
            for lbl in d2mc_labels.get("labels", []):
                if lbl["name"] == PROCESSED_LABEL:
                    d2mc_label_id = lbl["id"]
                    break
            if not d2mc_label_id:
                lbl = d2mc_service.users().labels().create(
                    userId="me",
                    body={"name": PROCESSED_LABEL, "labelListVisibility": "labelShow",
                          "messageListVisibility": "show"}
                ).execute()
                d2mc_label_id = lbl["id"]
        except Exception:
            pass

        for d_ref in d2mc_msgs:
            d_msg_id = d_ref["id"]
            try:
                d_full = d2mc_service.users().messages().get(
                    userId="me", id=d_msg_id, format="full"
                ).execute()
                d_hdrs = {h["name"]: h["value"] for h in d_full["payload"]["headers"]}
                d_from = d_hdrs.get("From", "").lower()
                d_to = d_hdrs.get("To", "").lower()
                d_subject = d_hdrs.get("Subject", "")
                d_thread_id = d_full.get("threadId", d_msg_id)
                d_msg_id_hdr = d_hdrs.get("Message-ID", "")
                d_body = _decode_text(d_full["payload"])

                # ⚠️  SECURITY FIX (MISSION-254): Verify Gmail authenticated this email
                # before processing. The SMTP From header is forgeable; check Gmail's
                # Authentication-Results header to confirm genuine DKIM signature.
                if not validate_authentication(d_full["payload"]["headers"]):
                    # Skip this message — not authenticated by Gmail
                    if d2mc_label_id:
                        d2mc_service.users().messages().modify(
                            userId="me", id=d_msg_id,
                            body={"addLabelIds": [d2mc_label_id]}
                        ).execute()
                    continue

                # Reply ONLY to the Commander (johnloucks3). Do NOT reply to the wing's
                # own d2mconcierge sends — that self-reply loop was the 2026-06-16 flood.
                if "johnloucks3" not in d_from:
                    if d2mc_label_id:
                        d2mc_service.users().messages().modify(
                            userId="me", id=d_msg_id,
                            body={"addLabelIds": [d2mc_label_id]}
                        ).execute()
                    continue

                _clean_sub = d_subject.lstrip().lower()

                # Commander directive 2026-06-16: EVERY email from johnloucks3 gets a reply —
                # NO prefix/code required, forwards included. (Forwards used to be dropped as
                # "filing"; that's retired.) Only pure acks are skipped (below) to avoid ping-pong.

                # Re: replies — skip pure acknowledgments, dispatch everything else.
                # Match a tight list of ack phrases. Any real question or instruction
                # won't match and will dispatch normally.
                if _clean_sub.startswith("re:"):
                    _ACK_PHRASES = {
                        # Pilot brevity — same protocol both directions
                        "roger", "roger.", "roger that", "roger that.",
                        "wilco", "wilco.",
                        "done", "done.",
                    }
                    _body_stripped = d_body.strip().lower().rstrip("!")
                    if _body_stripped in _ACK_PHRASES:
                        if d2mc_label_id:
                            d2mc_service.users().messages().modify(
                                userId="me", id=d_msg_id,
                                body={"addLabelIds": [d2mc_label_id]}
                            ).execute()
                        log_line(f"  d2mc skip (Re: ack): {d_subject[:60]}")
                        continue

                log_line(f"  D2MC DIRECTIVE: {d_subject[:80]}")
                new_directive_ids.add(d_thread_id)

                import time as _time2
                ts2 = int(_time2.time())
                out_file2 = ROOT / f"output/directive_{ts2}.md"
                out_file2.parent.mkdir(parents=True, exist_ok=True)

                # ⚠️  SECURITY: Sanitize subject + body before prompt interpolation (MISSION-254)
                safe_d_subject = sanitize_prompt_input(d_subject, max_len=200, field_name="d2mc_subject")
                safe_d_body = sanitize_prompt_input(d_body, max_len=2000, field_name="d2mc_body")

                task_prompt2 = (
                    f"You are Hale, COS for John Loucks at Dreams2Memories Travel. "
                    f"Commander just emailed you:\n\n"
                    f"Subject: {safe_d_subject}\n\n"
                    f"{safe_d_body}\n\n"
                    f"Reply using pilot brevity. No formal header, no sign-off, no wings branding.\n"
                    f"- If it's a task you will execute: start with 'Wilco —' then one sentence on what you're doing.\n"
                    f"- If it's information or a question you're answering: start with 'Roger —' then your answer.\n"
                    f"- If something is already done or confirmed complete: start with 'Done —' then what was done.\n"
                    f"Never use all three. Pick the one that fits. Under 100 words total.\n\n"
                    f"WRITE your reply to {out_file2}"
                )

                import subprocess as _sp2
                _sp2.Popen(
                    [
                        sys.executable,
                        str(ROOT / "OpsCenter/dispatch_and_email.py"),
                        "--task", f"d2mc-directive-{ts2}",
                        "--output", str(out_file2),
                        "--prompt", task_prompt2,
                        "--subject", d_subject or "(no subject)",
                        "--model", "haiku",
                        "--timeout", "1800",
                        "--thread-id", d_thread_id or "",
                        "--in-reply-to", d_msg_id_hdr or "",
                    ],
                    stdout=open(ROOT / f"logs/directive_{ts2}.log", "w"),
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    cwd=str(ROOT),
                )
                log_line(f"  d2mc dispatched — output: {out_file2}")

                if d2mc_label_id:
                    d2mc_service.users().messages().modify(
                        userId="me", id=d_msg_id,
                        body={"addLabelIds": [d2mc_label_id]}
                    ).execute()
                tasked += 1
            except Exception as e:
                log_line(f"  d2mc msg {d_msg_id} failed: {e}")

    all_directive_ids = directive_thread_ids | new_directive_ids
    save_thread_state(all_directive_ids)

    log_line(f"done — scanned={len(all_msgs)+len(d2mc_msgs)} tasked={tasked} tracked_threads={len(all_directive_ids)}")
    tracker.mark_complete(status="ok", note=f"found={len(all_msgs)} tasked={tasked}")
    sys.exit(0)

except Exception as e:
    log_line(f"error: {e}")
    tracker.mark_failed(str(e)[:200])
    sys.exit(1)
