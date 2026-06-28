#!/usr/bin/env python3
"""
red_star_scanner.py — Red-star alert relay. Zero AI/tokens.
============================================================
Runs every 2 minutes via systemd timer.
Commander red-stars any email in johnloucks3 → Wing sends a Telegram alert
with subject, sender, and body snippet. Commander then opens Claude Code to
process with Hale manually. No model calls. No Sonnet. No token spend.

Flow:
  1. Query johnloucks3 for is:starred -label:THUNDERBIRD-RedStarProcessed
  2. For each: fetch subject, sender, first 500 chars of body
  3. Apply THUNDERBIRD-RedStarProcessed label (prevents re-alert)
  4. Send Telegram alert with full context — Commander starts chat manually

Authentication: gmail_token_commander.json (johnloucks3 read/modify)
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

PROCESSED_LABEL_NAME = "THUNDERBIRD-RedStarProcessed"
COMMANDER_TOKEN = ROOT / "gmail_token_commander.json"

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
        log_line(f"label error: {e}")
        return ""


def send_telegram(message: str):
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "OpsCenter/wing_page.py"),
             "--message", message, "--priority", "high"],
            capture_output=True, text=True, timeout=30, cwd=str(ROOT)
        )
        if result.returncode != 0:
            log_line(f"Telegram warn: {result.stderr[:200]}")
    except Exception as e:
        log_line(f"Telegram error: {e}")


try:
    service = build_service()
    if not service:
        tracker.mark_complete(status="skip", note="no commander token")
        sys.exit(0)

    processed_label_id = get_or_create_label(service, PROCESSED_LABEL_NAME)

    query = f"is:starred -label:{PROCESSED_LABEL_NAME}"
    results = service.users().messages().list(
        userId="me", q=query, maxResults=10
    ).execute()
    messages = results.get("messages", [])

    log_line(f"found {len(messages)} red-starred emails")

    if not messages:
        tracker.mark_complete(status="ok", note="0 starred")
        sys.exit(0)

    alerted = 0
    for msg_ref in messages:
        msg_id = msg_ref["id"]
        try:
            # Mark processed immediately — no duplicate alerts
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
            snippet = body_text[:500].strip() if body_text else msg.get("snippet", "")[:300]

            log_line(f"  alert: {subject[:80]}")

            telegram_msg = (
                f"⚡ *RED STAR*\n"
                f"📧 {subject[:100]}\n"
                f"From: {sender[:80]}\n"
                f"Date: {date[:40]}\n\n"
                f"*Preview:*\n{snippet[:400]}\n\n"
                f"💬 _Open Claude Code to process with Hale_"
            )
            send_telegram(telegram_msg)
            log_line(f"  alerted: {subject[:80]}")
            alerted += 1

        except Exception as e:
            log_line(f"  error on {msg_id}: {e}")

    tracker.mark_complete(status="ok", note=f"alerted={alerted}")
    log_line(f"done — alerted={alerted}")
    sys.exit(0)

except Exception as e:
    log_line(f"fatal: {e}")
    tracker.mark_failed(str(e)[:200])
    sys.exit(1)
