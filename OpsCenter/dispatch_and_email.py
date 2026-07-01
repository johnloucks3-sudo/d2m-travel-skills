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
dispatch_and_email.py — Generate reply via Anthropic SDK, send via Gmail.

Calls Anthropic API directly (synchronous, no subprocess spawn chain).
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
import os
import subprocess
import sys
import time
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Audit trail (A2/A3) — defensive import; pipeline must never break ──────
try:
    from core.email.email_audit import record as _audit_record
except ImportError:  # pragma: no cover
    def _audit_record(*a, **k): return True   # type: ignore[misc]

# Unbuffered output so log files get content even if process is killed
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

CLAUDE_CLI = Path.home() / ".local/bin/claude"

POLL_INTERVAL = 5
DEFAULT_TIMEOUT = 1800

# Minimal MCP config — suppresses the 97-server MCP startup that caused 130s hangs
_EMPTY_MCP_CONFIG = Path("/tmp/thunderbird_empty_mcp.json")
if not _EMPTY_MCP_CONFIG.exists():
    import json as _json_init
    _EMPTY_MCP_CONFIG.write_text(_json_init.dumps({"mcpServers": {}}))


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


_MODEL_IDS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus":   "claude-opus-4-8",
}

# Strip vars that cause issues in headless/systemd context.
# ANTHROPIC_BASE_URL=http://localhost:5099 routes Claude CLI to the MAX proxy
# which is dead when no proxy is running — causes a >130s hang then timeout.
_STRIP = {"ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN",
          "CLAUDECODE", "HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"}


def _get_reply(prompt: str, output: str, task: str, model: str) -> str:
    """Generate reply via Claude CLI (OAuth MAX plan, no-MCP, no-proxy)."""
    tier = model.lower() if model.lower() in _MODEL_IDS else "haiku"
    model_id = _MODEL_IDS[tier]

    clean_env = {k: v for k, v in os.environ.items() if k not in _STRIP}

    cmd = [
        str(CLAUDE_CLI),
        "-p", prompt,
        "--model", model_id,
        "--output-format", "text",
        "--strict-mcp-config",
        "--mcp-config", str(_EMPTY_MCP_CONFIG),
    ]

    print(f"[START] {task} — invoking Claude CLI ({tier}, no-MCP)")

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=clean_env,
        timeout=DEFAULT_TIMEOUT,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Claude CLI rc={result.returncode}: {result.stderr[:500]}"
        )

    body = result.stdout.strip()
    out_path.write_text(body, encoding="utf-8")

    print(f"[CLI] {task} — {len(body)} chars")
    return body


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

    try:
        body = _get_reply(args.prompt, args.output, args.task, args.model)
    except Exception as e:
        print(f"[ERR] API call failed: {e}")
        sys.exit(1)

    try:
        if args.thread_id:
            msg_id = _send_threaded_reply(body, args.subject, args.thread_id, args.in_reply_to)
            print(f"[REPLY] threaded — message_id={msg_id} thread={args.thread_id}")
        else:
            msg_id = _send_new_email(body, args.subject)
            print(f"[EMAIL] new email — message_id={msg_id}")
        # ── A3: record confirmed dispatch outcome ──
        # Key on outbound msg_id (may be None on _send_new_email if token missing).
        # Use args.task as fallback so we always get an audit row.
        audit_key = msg_id or f"dispatch-{args.task}"
        _audit_record(audit_key, "dispatch",
                      thread_id=args.thread_id or None,
                      action_taken="reply_sent", outcome="ok",
                      detail=f"task={args.task} subject={args.subject[:80]!r}")
    except Exception as e:
        print(f"[SEND ERR] {e}")
        # ── A3: record failure so callers can detect it in audit ──
        _audit_record(f"dispatch-{args.task}", "dispatch",
                      thread_id=args.thread_id or None,
                      action_taken="reply_sent", outcome="failed",
                      detail=f"send exception: {e}")
        sys.exit(3)

    sys.exit(0)


if __name__ == "__main__":
    main()
