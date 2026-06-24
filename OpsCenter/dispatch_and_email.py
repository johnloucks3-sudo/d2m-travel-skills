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


_MODEL_IDS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus":   "claude-opus-4-8",
}
_COST_PER_TOK = {
    "haiku":  (0.25e-6, 1.25e-6),
    "sonnet": (3.0e-6,  15.0e-6),
    "opus":   (15.0e-6, 75.0e-6),
}


def _get_reply(prompt: str, output: str, task: str, model: str) -> str:
    """Generate reply via Anthropic SDK — synchronous, no subprocess chain."""
    import os
    import anthropic as _ant

    if not os.environ.get("ANTHROPIC_API_KEY"):
        env_path = ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY=") and "=" in line:
                    os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip()
                    break

    tier = model.lower() if model.lower() in _MODEL_IDS else "haiku"
    model_id = _MODEL_IDS[tier]
    client = _ant.Anthropic()
    msg = client.messages.create(
        model=model_id,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    body = msg.content[0].text.strip()

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")

    in_tok, out_tok = msg.usage.input_tokens, msg.usage.output_tokens
    cin, cout = _COST_PER_TOK[tier]
    cost = in_tok * cin + out_tok * cout
    print(f"[API] {task} — {in_tok}in/{out_tok}out tokens, ${cost:.5f} ({tier})")
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
    except Exception as e:
        print(f"[SEND ERR] {e}")
        sys.exit(3)

    sys.exit(0)


if __name__ == "__main__":
    main()
