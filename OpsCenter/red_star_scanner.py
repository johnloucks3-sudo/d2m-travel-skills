#!/usr/bin/env python3
"""
red_star_scanner.py — Multi-star triage relay. Zero AI/tokens in scanner.
=========================================================================
Runs every 2 minutes via systemd timer. Queries johnloucks3 for each active
star type, sends a type-specific Telegram alert, labels processed.
Hale in Telegram executes the action using her MCP tools.

Star map (Commander-defined 2026-06-28):
  yellow-star      → IFTTT/Evernote — SKIP (not our scanner)
  red-star         → Urgent alert, full body
  purple-question  → Question in body — Hale reads and answers
  blue-info        → Info + action — Hale reads and acts
  blue-star        → Dembe research
  green-star       → Read, process, draft reply
  orange-star      → Client dossier update

Order of Gmail click-cycling doesn't affect queries — each star type is an
independent Gmail API query (has:red-star, has:green-star, etc.).
"""
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for sub in (ROOT / "core").iterdir():
    if sub.is_dir():
        sys.path.insert(0, str(sub))

from OpsCenter.sweep_tracker import SweepTracker
from google.api_core.retry import Retry

PROCESSED_LABEL_NAME = "THUNDERBIRD-RedStarProcessed"
COMMANDER_TOKEN = ROOT / "gmail_token_commander.json"

# Commander-defined star action map. yellow-star = None → skip (IFTTT owns it).
# label_id: Gmail system label ID — use labelIds param (has: search is broken for system star labels).
# shape stars (orange-guillemet, purple-question, blue-info) have no label_id until first use;
#   they fall back to has: query — will activate once Gmail registers the label.
STAR_MAP = [
    {
        "name": "red-star",
        "label_id": "RED_STAR",
        "emoji": "🔴",
        "label": "URGENT",
        "instruction": "This is flagged URGENT. Hale — surface immediately, determine if action is needed and execute or hold at gate.",
    },
    {
        "name": "green-star",
        "label_id": "GREEN_STAR",
        "emoji": "🟢",
        "label": "DRAFT REPLY",
        "instruction": "Hale — read this email, process it, and draft a reply for Commander review. Surface the draft in Telegram.",
    },
    {
        "name": "blue-star",
        "label_id": "BLUE_STAR",
        "emoji": "🔵",
        "label": "DEMBE RESEARCH",
        "instruction": "Route to Dembe for research and intel. Hale — task Dembe with the content of this email and surface findings.",
    },
    {
        "name": "purple-star",
        "label_id": "PURPLE_STAR",
        "emoji": "🟣",
        "label": "PURPLE — COMMANDER ASSIGNED",
        "instruction": "Hale — Commander starred this purple. Read and determine action from context.",
    },
    {
        "name": "blue-circle",
        "label_id": "BLUE_CIRCLE",
        "emoji": "🔵ℹ️",
        "label": "INFO + ACTION",
        "instruction": "For info and action. Hale — read, determine what action is required, and execute or surface to Commander.",
    },
    {
        "name": "red-circle",
        "label_id": "RED_CIRCLE",
        "emoji": "🔴❗",
        "label": "URGENT ACTION",
        "instruction": "Urgent action flagged. Hale — read, determine immediate action required, execute or gate.",
    },
    {
        "name": "green-circle",
        "label_id": "GREEN_CIRCLE",
        "emoji": "🟢✅",
        "label": "APPROVED / COMPLETE",
        "instruction": "Commander has approved or marked complete. Hale — log, update dossier, close out the item.",
    },
    {
        "name": "orange-guillemet",
        "has_query": "has:orange-guillemet",
        "emoji": "🟠❯❯",
        "label": "DOSSIER UPDATE",
        "instruction": "Hale — identify the client, extract relevant data from this email, and update the appropriate dossier.",
    },
    {
        "name": "purple-question",
        "has_query": "has:purple-question",
        "emoji": "❓",
        "label": "QUESTION",
        "instruction": "Commander has a question in the body of this email. Hale — read the email, formulate an answer, and reply in this thread.",
    },
]

tracker = SweepTracker("red_star_scanner", cooldown_minutes=2)
if tracker.in_cooldown():
    sys.exit(0)


def log_line(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    print(f"[{ts}] {msg}", flush=True)


def build_service():
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        if not COMMANDER_TOKEN.exists():
            log_line("WARN: gmail_token_commander.json not found")
            return None
        creds = Credentials.from_authorized_user_file(
            str(COMMANDER_TOKEN),
            scopes=["https://www.googleapis.com/auth/gmail.modify"]
        )
        # Retry policy for transient API failures
        retry_policy = Retry(
            initial=1.0, maximum=16.0, multiplier=2.0,
            predicate=lambda e: hasattr(e, 'resp') and hasattr(e.resp, 'status') and e.resp.status in (500, 503, 429)
        )
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        log_line(f"ERROR: service build failed: {e}")
        return None


def decode_body(payload) -> str:
    if payload.get("mimeType", "").startswith("text/plain"):
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        result = decode_body(part)
        if result:
            return result
    return ""


def get_or_create_label(service, name: str) -> str:
    """Get or create a label with retry logic for transient API failures."""
    max_retries = 5
    retry_delay = 1.0

    for attempt in range(max_retries):
        try:
            labels = service.users().labels().list(userId="me").execute().get("labels", [])
            for lbl in labels:
                if lbl["name"] == name:
                    return lbl["id"]
            created = service.users().labels().create(
                userId="me",
                body={"name": name, "labelListVisibility": "labelHide",
                      "messageListVisibility": "hide"}
            ).execute()
            return created["id"]
        except Exception as e:
            error_msg = str(e)
            # Check for transient errors (connection reset, network errors)
            is_transient = any(x in error_msg for x in [
                "Connection reset", "104", "ECONNRESET",
                "500", "503", "429", "socket", "timeout"
            ])

            if not is_transient or attempt == max_retries - 1:
                log_line(f"label error (attempt {attempt+1}/{max_retries}): {e}")
                return ""

            log_line(f"label transient error (attempt {attempt+1}/{max_retries}): {e} — retrying in {retry_delay}s")
            time.sleep(retry_delay)
            retry_delay *= 2  # exponential backoff

    return ""


def send_telegram(message: str):
    try:
        import urllib.request as _req
        from dotenv import dotenv_values as _denv
        _env = {**_denv(ROOT / ".env"), **os.environ}
        token = _env.get("TELEGRAM_D2MC2C_TOKEN", "")
        chat_id = _env.get("TELEGRAM_COMMANDER_ID", "7554895206")
        if not token:
            log_line("ERROR: TELEGRAM_D2MC2C_TOKEN not set — alert not sent")
            return
        # Try Markdown first; fall back to plain text if body has problem chars
        for mode in ["Markdown", None]:
            body = {"chat_id": chat_id, "text": message}
            if mode:
                body["parse_mode"] = mode
            payload = json.dumps(body).encode()
            req = _req.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=payload, headers={"Content-Type": "application/json"}
            )
            try:
                resp = _req.urlopen(req, timeout=15)
                if resp.status == 200:
                    return
            except _req.HTTPError as he:
                if he.code == 400 and mode:
                    continue  # retry without parse_mode
                log_line(f"Telegram HTTP {he.code}: {he.read()[:100]}")
                return
    except Exception as e:
        log_line(f"Telegram error: {e}")


def process_star_type(service, star, processed_label_id: str) -> int:
    """Process a star type with retry logic for transient API failures."""
    exclude_q = f"-label:{PROCESSED_LABEL_NAME}"
    max_retries = 3
    retry_delay = 1.0

    # Query with retries
    for attempt in range(max_retries):
        try:
            if "label_id" in star:
                # Use labelIds param — has: search is broken for Gmail system star labels
                results = service.users().messages().list(
                    userId="me", labelIds=[star["label_id"]], q=exclude_q, maxResults=10
                ).execute()
            else:
                # Shape stars (guillemet, bang, etc.) fall back to has: query
                results = service.users().messages().list(
                    userId="me", q=f"{star['has_query']} {exclude_q}", maxResults=10
                ).execute()
            break
        except Exception as e:
            error_msg = str(e)
            is_transient = any(x in error_msg for x in [
                "Connection reset", "104", "ECONNRESET",
                "500", "503", "429", "socket", "timeout"
            ])
            if not is_transient or attempt == max_retries - 1:
                log_line(f"  {star['name']}: query failed (attempt {attempt+1}/{max_retries}): {e}")
                return 0
            log_line(f"  {star['name']}: query transient error (attempt {attempt+1}/{max_retries}) — retrying in {retry_delay}s")
            time.sleep(retry_delay)
            retry_delay *= 2

    messages = results.get("messages", [])
    if not messages:
        return 0

    log_line(f"  {star['name']}: {len(messages)} message(s)")
    alerted = 0
    for msg_ref in messages:
        msg_id = msg_ref["id"]
        try:
            # Mark processed immediately — prevents duplicate alerts
            if processed_label_id:
                service.users().messages().modify(
                    userId="me", id=msg_id,
                    body={"addLabelIds": [processed_label_id]}
                ).execute()

            msg = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
            hdrs = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            subject = hdrs.get("Subject", "(no subject)")
            sender = hdrs.get("From", "unknown")
            date = hdrs.get("Date", "")
            body_text = decode_body(msg["payload"])
            snippet = body_text[:600].strip() if body_text else msg.get("snippet", "")[:400]

            telegram_msg = (
                f"⚡ *{star['emoji']} {star['label']}*\n"
                f"📧 {subject[:100]}\n"
                f"From: {sender[:80]}\n"
                f"Date: {date[:40]}\n\n"
                f"*Preview:*\n{snippet[:500]}\n\n"
                f"_{star['instruction']}_"
            )
            send_telegram(telegram_msg)

            # Write pending context for gateway to inject on next Commander reply
            import json as _json
            pending_path = ROOT / "OpsCenter" / "state" / "red_star_pending.json"
            pending_path.parent.mkdir(parents=True, exist_ok=True)
            pending_path.write_text(_json.dumps({
                "star": star["name"],
                "action": star["label"],
                "subject": subject,
                "sender": sender,
                "date": date,
                "snippet": snippet[:800],
            }, indent=2))

            log_line(f"    alerted: {subject[:80]}")
            alerted += 1

        except Exception as e:
            log_line(f"    error on {msg_id}: {e}")

    return alerted


try:
    service = build_service()
    if not service:
        tracker.mark_complete(status="skip", note="no commander token")
        sys.exit(0)

    processed_label_id = get_or_create_label(service, PROCESSED_LABEL_NAME)
    total_alerted = 0

    for star in STAR_MAP:
        total_alerted += process_star_type(service, star, processed_label_id)

    tracker.mark_complete(status="ok", note=f"alerted={total_alerted}")
    log_line(f"done — total alerted={total_alerted}")
    sys.exit(0)

except Exception as e:
    log_line(f"fatal: {e}")
    tracker.mark_failed(str(e)[:200])
    sys.exit(1)
