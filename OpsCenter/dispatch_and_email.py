#!/usr/bin/env python3
# ============================================================
# ⚠️  PROTECTED FILE — THUNDERBIRD WING STANDING ORDER
# ============================================================
# DO NOT MODIFY this file without explicit authorization from
# Commander (John Loucks / Yoda) via Claude Code session.
#
# This file controls threaded Gmail reply delivery and the
# THUNDERBIRD-Hale blue label pipeline. Unauthorized changes
# WILL break Commander's email C2 channel.
#
# Before ANY edit: read SO_EMAIL_SCANNER_PROTECT_20260608.md
# and confirm with Hale (Claude Code) before proceeding.
# ============================================================
"""
dispatch_and_email.py — Dispatch to headless Claude, reply via Gmail.

When --thread-id is provided, sends a threaded reply in the original Gmail
thread (channel-fidelity rule: email in → email out, same thread).
When omitted, falls back to a new email (legacy behavior).

Usage:
  python3 dispatch_and_email.py \\
      --task <task_name> \\
      --output <output_path> \\
      --prompt <prompt_text> \\
      --subject <reply_subject> \\
      [--thread-id <gmail_thread_id>] \\
      [--in-reply-to <message_id_header>] \\
      [--model haiku|sonnet|opus] \\
      [--timeout 1800]
"""

import argparse
import base64
import json
import subprocess
import sys
import time
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

POLL_INTERVAL = 5
DEFAULT_TIMEOUT = 1800


D2MC_TOKEN = ROOT / "config" / "persona_gmail_token.json"


JL3_TOKEN = ROOT / "gmail_token.json"
HALE_LABEL_ID = "Label_103"   # THUNDERBIRD-Hale — light blue in johnloucks3


def _send_threaded_reply(body: str, subject: str, thread_id: str, in_reply_to: str):
    """Send a reply in the existing Gmail thread via d2mconcierge, then
    label the incoming message in johnloucks3 with THUNDERBIRD-Hale (blue)."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_file = D2MC_TOKEN
    creds = Credentials.from_authorized_user_file(str(token_file))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json())

    service = build("gmail", "v1", credentials=creds)

    # Confirm we're sending as d2mconcierge
    profile = service.users().getProfile(userId="me").execute()
    sender_addr = profile.get("emailAddress", "d2mconcierge@gmail.com")

    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = "johnloucks3@gmail.com"
    msg["From"] = sender_addr
    msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    send_body = {"raw": raw}
    if thread_id:
        send_body["threadId"] = thread_id

    result = service.users().messages().send(userId="me", body=send_body).execute()
    sent_id = result.get("id")

    # Label the incoming reply in johnloucks3 as THUNDERBIRD-Hale (light blue).
    # jl3 uses a different thread_id than d2mc, so search by sender + recency.
    try:
        jl3_creds = Credentials.from_authorized_user_file(str(JL3_TOKEN))
        if jl3_creds.expired and jl3_creds.refresh_token:
            jl3_creds.refresh(Request())
            JL3_TOKEN.write_text(jl3_creds.to_json())
        jl3_svc = build("gmail", "v1", credentials=jl3_creds)
        time.sleep(4)  # brief pause for delivery
        recent = jl3_svc.users().messages().list(
            userId="me",
            q="from:d2mconcierge@gmail.com newer_than:1d in:inbox",
            maxResults=5,
        ).execute().get("messages", [])
        if recent:
            jl3_svc.users().messages().modify(
                userId="me", id=recent[0]["id"],
                body={"addLabelIds": [HALE_LABEL_ID]}
            ).execute()
            print(f"[LABEL] blue label applied to msg {recent[0]['id']}")
    except Exception as e:
        print(f"[LABEL] blue label failed (non-fatal): {e}")

    return sent_id


def _send_new_email(body: str, subject: str):
    """Fallback: send a new email to johnloucks3 (no thread context)."""
    import importlib.util as ilu
    spec = ilu.spec_from_file_location("tg", str(ROOT / "core/email/thunderbird_gmail.py"))
    m = ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    subj = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    result = m.gmail_send_from_wing(
        to="johnloucks3@gmail.com",
        subject=subj,
        body=body,
        persona_id="COS",
    )
    return result.get("message_id")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--task", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--model", default="haiku")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p.add_argument("--thread-id", default="", dest="thread_id")
    p.add_argument("--in-reply-to", default="", dest="in_reply_to")
    args = p.parse_args()

    out_path = Path(args.output)

    dispatch_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "OpsCenter/dispatch_claude.py"),
            "--task", args.task,
            "--output", args.output,
            "--prompt", args.prompt,
            "--model", args.model,
        ],
        capture_output=True, text=True, timeout=30,
    )

    try:
        result = json.loads(dispatch_result.stdout)
    except json.JSONDecodeError:
        print(f"[ERR] dispatch_claude stdout not JSON: {dispatch_result.stdout[:300]}")
        sys.exit(1)

    if result.get("status") not in ("SPAWNED", "COMPLETED"):
        print(f"[ERR] dispatch failed: {result}")
        sys.exit(1)

    pid = result.get("pid")
    print(f"[DISPATCH] spawned pid={pid}, waiting for {out_path}")

    # Find the spawn log file (dispatch_claude.py writes it to logs/ dir)
    spawn_log = ROOT / "logs" / f"claude_{args.task}_{time.strftime('%Y%m%d')}.log"
    # Also check with timestamp pattern
    import glob as _glob
    spawn_log_pattern = str(ROOT / "logs" / f"claude_{args.task}_*.log")

    start = time.monotonic()
    body = None
    while True:
        if out_path.exists() and out_path.stat().st_size > 0:
            time.sleep(2)
            body = out_path.read_text(encoding="utf-8").strip()
            break
        # Fallback: if elapsed > 90s and Claude has finished (result in spawn log), extract it
        if time.monotonic() - start > 90:
            logs = sorted(_glob.glob(spawn_log_pattern))
            for log_path in reversed(logs):
                try:
                    for line in open(log_path):
                        if '"subtype":"success"' in line or '"type":"result"' in line:
                            import re as _re
                            m = _re.search(r'"result"\s*:\s*"((?:[^"\\]|\\.)*)"', line)
                            if m:
                                body = m.group(1).replace('\\n', '\n').replace('\\"', '"').strip()
                                print(f"[FALLBACK] extracted result from spawn log (file write missed)")
                                break
                    if body:
                        break
                except Exception:
                    pass
        if body:
            break
        if time.monotonic() - start > args.timeout:
            print(f"[TIMEOUT] output file never appeared after {args.timeout}s")
            sys.exit(2)
        time.sleep(POLL_INTERVAL)

    try:
        if args.thread_id:
            msg_id = _send_threaded_reply(body, args.subject, args.thread_id, args.in_reply_to)
            print(f"[REPLY] threaded — message_id={msg_id} thread={args.thread_id}")
        else:
            msg_id = _send_new_email(body, args.subject)
            print(f"[EMAIL] new email — message_id={msg_id}")

    except Exception as e:
        print(f"[SEND ERR] {e}")
        sys.exit(3)

    sys.exit(0)


if __name__ == "__main__":
    main()
