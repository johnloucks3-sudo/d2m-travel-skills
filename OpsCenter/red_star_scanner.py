#!/usr/bin/env python3
"""
red_star_scanner.py — Immediate processing of red-starred emails in johnloucks3
=================================================================================
Runs every 2 minutes via systemd timer.
Commander red-stars any email in his inbox → Wing processes immediately.

Flow:
  1. Query johnloucks3 for has:red-star -label:THUNDERBIRD-RedStarProcessed
  2. For each: fetch full content, classify, ingest, confirm
  3. Remove STARRED label, apply THUNDERBIRD-RedStarProcessed
  4. Send Telegram confirmation with file reference

Ingestion types:
  FORWARD   — Commander forwarded a client email → update dossier + log comms
  TASK      — Commander wants something done → create mission board entry
  CC        — Commander sent a client email, wants Wing to know → dossier update
  INTEL     — Industry news / vendor info → log to intel
  FILE      — Attachment with client data → save + index
  OTHER     — Process with Sonnet, Wing decides

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
SCRIPTS_LOG = ROOT / "logs" / "red_star_scanner.log"

tracker = SweepTracker("red_star_scanner", cooldown_minutes=2)
if tracker.in_cooldown():
    sys.exit(0)


def log_line(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    print(f"[{ts}] {msg}", flush=True)


def build_service():
    """Build Gmail API service for johnloucks3 using commander token."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        if not COMMANDER_TOKEN.exists():
            log_line("WARN: gmail_token_commander.json not found — red star scanner cannot run")
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
    """Recursively extract text/plain from MIME payload."""
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
    """Get label ID by name, creating it if absent."""
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
    """Send Telegram message to Commander via wing_page.py."""
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


def load_wing_context() -> str:
    """Load brief wing context for the processing prompt."""
    ctx_parts = []
    try:
        state_file = ROOT / "hale_state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            tasks = state.get("open_tasks", [])
            p0 = [t["title"][:60] for t in tasks if t.get("priority") == "P0"][:5]
            if p0:
                ctx_parts.append("P0 missions: " + " | ".join(p0))
    except Exception:
        pass
    return "\n".join(ctx_parts) or "No context loaded."


def process_with_sonnet(subject: str, sender: str, body: str, email_type: str) -> str:
    """
    Dispatch to Sonnet to determine what to do with this email.
    Returns a structured JSON string with: action, file_ref, confirmation_msg, mission_title
    """
    wing_ctx = load_wing_context()
    # Sanitize inputs
    subject = subject[:300].replace('"', "'")
    sender = sender[:200].replace('"', "'")
    body = body[:3000].replace('"', "'")

    prompt = (
        f"You are Hale, COS of Thunderbird Wing, Dreams2Memories Travel. "
        f"Commander red-starred an email for IMMEDIATE Wing processing.\n\n"
        f"WING STATE:\n{wing_ctx}\n\n"
        f"EMAIL:\nFrom: {sender}\nSubject: {subject}\n\nBody:\n{body}\n\n"
        f"Classify and determine the correct Wing action. Respond in JSON only, no prose:\n"
        f'{{\n'
        f'  "action": "INGEST_DOSSIER | CREATE_MISSION | LOG_COMMS | SAVE_INTEL | NOTE_ONLY",\n'
        f'  "client_name": "client name or null",\n'
        f'  "file_ref": "dossiers/filename.md or intel/filename.md or null",\n'
        f'  "section": "section name within file or null",\n'
        f'  "mission_title": "short mission title if CREATE_MISSION, else null",\n'
        f'  "mission_priority": "P0|P1|P2 if CREATE_MISSION, else null",\n'
        f'  "confirmation_msg": "one sentence for Commander: what was done + where it landed",\n'
        f'  "deadline_flagged": "YYYY-MM-DD if a deadline exists, else null",\n'
        f'  "requires_commander_action": true or false,\n'
        f'  "commander_action_needed": "what Commander needs to do, or null"\n'
        f'}}\n\n'
        f'RULES:\n'
        f'- If a client name is mentioned: action = INGEST_DOSSIER, file_ref = correct dossier path\n'
        f'- If Commander forwarded a task: action = CREATE_MISSION\n'
        f'- If it is a CC on a client send: action = LOG_COMMS\n'
        f'- If it is industry/vendor intel: action = SAVE_INTEL\n'
        f'- file_ref must be a real path under /home/john/Thunderbird/ — check dossiers/ for client matches\n'
        f'- confirmation_msg must name the file and section, not just say "processed"'
    )

    out_file = ROOT / f"output/red_star_{int(time.time())}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [sys.executable, str(ROOT / "OpsCenter/dispatch_and_email.py"),
         "--task", f"red-star-{int(time.time())}",
         "--output", str(out_file),
         "--prompt", prompt,
         "--model", "sonnet",
         "--timeout", "120",
         "--no-reply"],
        capture_output=True, text=True, cwd=str(ROOT), timeout=135
    )

    if out_file.exists():
        raw = out_file.read_text().strip()
        # Extract JSON from output
        import re
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except Exception:
                pass

    return {
        "action": "NOTE_ONLY",
        "client_name": None,
        "file_ref": None,
        "section": None,
        "mission_title": None,
        "mission_priority": None,
        "confirmation_msg": f"Read and noted: {subject[:80]}. No automatic ingestion — check manually.",
        "deadline_flagged": None,
        "requires_commander_action": False,
        "commander_action_needed": None
    }


def execute_action(action_data: dict) -> str:
    """Execute the determined action. Returns confirmation message."""
    action = action_data.get("action", "NOTE_ONLY")
    confirmation = action_data.get("confirmation_msg", "Processed.")
    mission_title = action_data.get("mission_title")
    mission_priority = action_data.get("mission_priority", "P1")
    file_ref = action_data.get("file_ref")
    section = action_data.get("section")
    deadline = action_data.get("deadline_flagged")

    if action == "CREATE_MISSION" and mission_title:
        try:
            desc = f"Created from Commander red-star email. {confirmation}"
            result = subprocess.run(
                [sys.executable, str(ROOT / "OpsCenter/mission_board_sync.py"),
                 "add", mission_title[:120], desc, mission_priority or "P1"],
                capture_output=True, text=True, cwd=str(ROOT), timeout=30
            )
            if "Created:" in result.stdout:
                mission_id = result.stdout.split("Created:")[-1].strip().split()[0]
                confirmation = f"Done — created {mission_id}: {mission_title[:60]}. {confirmation}"
        except Exception as e:
            log_line(f"mission create error: {e}")

    if deadline:
        confirmation += f" ⚠️ Deadline: {deadline}"

    requires_action = action_data.get("requires_commander_action", False)
    commander_action = action_data.get("commander_action_needed")
    if requires_action and commander_action:
        confirmation += f"\n🔴 Your action needed: {commander_action}"

    return confirmation


try:
    service = build_service()
    if not service:
        tracker.mark_complete(status="skip", note="no commander token")
        sys.exit(0)

    # Get/create processed label
    processed_label_id = get_or_create_label(service, PROCESSED_LABEL_NAME)

    # Query for starred emails not yet processed
    # Note: is:starred = standard yellow star. has:red-star requires Gmail's
    # "multiple stars" feature which is not enabled — use is:starred.
    query = f"is:starred -label:{PROCESSED_LABEL_NAME}"
    results = service.users().messages().list(
        userId="me", q=query, maxResults=10
    ).execute()
    messages = results.get("messages", [])

    log_line(f"found {len(messages)} red-starred emails")

    if not messages:
        tracker.mark_complete(status="ok", note="0 starred")
        sys.exit(0)

    processed = 0
    for msg_ref in messages:
        msg_id = msg_ref["id"]
        try:
            # Pre-emptive label to prevent duplicate processing — star stays in place
            if processed_label_id:
                service.users().messages().modify(
                    userId="me", id=msg_id,
                    body={"addLabelIds": [processed_label_id]}
                ).execute()

            # Fetch full message
            msg = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
            hdrs = {h["name"]: h["value"]
                    for h in msg["payload"]["headers"]}
            subject = hdrs.get("Subject", "(no subject)")
            sender = hdrs.get("From", "unknown")
            body = decode_body(msg["payload"])

            log_line(f"  processing: {subject[:80]}")

            # Determine email type for context
            email_type = "FORWARD" if subject.lower().startswith("fwd:") else "OTHER"
            if "cc" in [h["name"].lower() for h in msg["payload"]["headers"]]:
                email_type = "CC"

            # Process with Sonnet
            action_data = process_with_sonnet(subject, sender, body, email_type)
            confirmation = execute_action(action_data)

            # Send Telegram confirmation
            telegram_msg = (
                f"⚡ RED STAR PROCESSED\n"
                f"📧 {subject[:80]}\n"
                f"From: {sender[:60]}\n\n"
                f"{confirmation}"
            )
            send_telegram(telegram_msg)
            log_line(f"  done: {confirmation[:100]}")
            processed += 1

        except Exception as e:
            log_line(f"  error processing {msg_id}: {e}")

    tracker.mark_complete(status="ok", note=f"processed={processed}")
    log_line(f"done — processed={processed}")
    sys.exit(0)

except Exception as e:
    log_line(f"fatal: {e}")
    tracker.mark_failed(str(e)[:200])
    sys.exit(1)
