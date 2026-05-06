#!/usr/bin/env python3
"""
EMAIL TASKING SYSTEM v2 — Secure email-to-task pipeline
Fetches unread emails from Commander, validates sender, parses task directives, routes to personas.
Integrated with: MCP Gmail tools, Groq parser, systemd timer (2-minute polling).
"""

import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is importable (for `agents.email_hale_dispatch`).
_TB_ROOT = "/home/john/Thunderbird"
if _TB_ROOT not in sys.path:
    sys.path.insert(0, _TB_ROOT)

# ── Hale Dispatcher integration (Hale Everywhere — Phase 2 hook) ──────────────
# Defensive: ingest service must keep running if Hale infra fails to import.
try:
    from agents.email_hale_dispatch import handle_email_task, is_hale_tier_email
    _HALE_DISPATCHER_AVAILABLE = True
except Exception as _hale_import_err:  # pragma: no cover
    _HALE_DISPATCHER_AVAILABLE = False

logging.basicConfig(
    filename="/home/john/Thunderbird/OpsCenter/logs/email_task_ingest.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ── SECURITY GATES ──
AUTHORIZED_SENDERS = ["johnloucks3@gmail.com", "john.a.loucks3@gmail.com"]

VALID_PERSONAS = {
    "COS": "hale",
    "HALE": "hale",
    "A2": "dembe",
    "DEMBE": "dembe",
    "WRAITH": "dembe",
    "A3": "dani",
    "DANI": "dani",
    "MOREAU": "dani",
    "A5": "castillo",
    "CASTILLO": "castillo",
    "VIPER": "castillo",
    "A6": "voss",
    "LUNA": "voss",
    "VOSS": "voss",
    "A7": "sterling",
    "GAUGE": "sterling",
    "STERLING": "sterling",
    "A9": "harlan",
    "HARLAN": "harlan",
    "VIC": "harlan",
    "A12": "elon",
    "ELON": "elon",
    "EXEC": "naia",
    "NAIA": "naia",
    "SOLBERG-VEGA": "naia",
    "CH": "padre",
    "PADRE": "padre",
    "WASHINGTON": "padre",
}

TRIGGER_KEYWORDS = [
    "[WING-TASK]",
    "[COS]",
    "[COO]",
    "[EXEC]",
    "[A2]",
    "[A3]",
    "[A5]",
    "[A6]",
    "[A7]",
    "[A9]",
    "[A12]",
    "[CH]",
    "[CLIENT]",
    "🔴 RED!",
    "🔴RED",
    "[RED]",
    "URGENT:",
    "TASK:",
    "WING-TASK",
]

# ── DEDUP STATE ──
SEEN_FILE = Path("/home/john/Thunderbird/state/email_ingest_seen.json")


def load_seen() -> set:
    try:
        return set(json.loads(SEEN_FILE.read_text()))
    except Exception:
        return set()


def save_seen(seen: set):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(list(seen)[-500:]))


# In-session dedup (fast path within one process lifetime)
_processed_this_run: set = set()


def check_for_tasks():
    """Fetch unread emails from Commander, deduplicate, process each."""
    logging.info("[EMAIL INGEST] ▶ Polling d2mconcierge for Commander tasking...")

    search_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_search_messages",
        json.dumps({"query": "is:unread", "max_results": 20}),
    ]

    try:
        result = subprocess.run(search_cmd, capture_output=True, text=True, timeout=15)
        data = json.loads(result.stdout)

        if "result" not in data or "messages" not in data["result"]:
            logging.info("[EMAIL INGEST] No unread messages found.")
            return

        messages = data["result"]["messages"]
        seen_persistent = load_seen()
        new_messages = [
            m
            for m in messages
            if m["id"] not in _processed_this_run and m["id"] not in seen_persistent
        ]

        if not new_messages:
            logging.info(
                f"[EMAIL INGEST] All {len(messages)} UNREAD messages already processed (dedup active)."
            )
            return

        logging.info(
            f"[EMAIL INGEST] Found {len(new_messages)} new messages to process."
        )
        for msg in new_messages:
            process_message(msg["id"])

    except json.JSONDecodeError as e:
        logging.error(f"[EMAIL INGEST] JSON decode error: {e}")
    except subprocess.TimeoutExpired:
        logging.error("[EMAIL INGEST] Search timeout (mcp_bridge.sh)")
    except Exception as e:
        logging.error(f"[EMAIL INGEST] Search failed: {e}")


def process_message(msg_id):
    """Read message, validate sender, check for trigger, route to persona."""
    # Register in both caches immediately — prevents reprocessing on failure.
    _processed_this_run.add(msg_id)
    seen = load_seen()
    seen.add(msg_id)
    save_seen(seen)

    read_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_read_message",
        json.dumps({"message_id": msg_id}),
    ]

    try:
        result = subprocess.run(read_cmd, capture_output=True, text=True, timeout=10)
        msg_data = json.loads(result.stdout).get("result", {})

        sender = msg_data.get("from", "").strip().lower()
        subject = msg_data.get("subject", "").strip()
        body = msg_data.get("body", "").strip()

        # ── SECURITY GATE 1: Sender verification ──
        if not _verify_sender(sender):
            logging.warning(
                f"[EMAIL INGEST] ⚠️  REJECTED: {msg_id} from unauthorized {sender}"
            )
            mark_read(msg_id)
            return

        # ── SECURITY GATE 2: Trigger keyword requirement ──
        if not _has_trigger(subject, body):
            logging.info(
                f"[EMAIL INGEST] No trigger in msg {msg_id} from {sender}. Marking read."
            )
            mark_read(msg_id)
            return

        # ── ROUTING: Extract persona tag ──
        assigned_persona = _extract_persona(subject, body)
        if not assigned_persona:
            logging.warning(
                f"[EMAIL INGEST] Trigger found but no persona tag in {msg_id}. Routing to COS (default)."
            )
            assigned_persona = "hale"

        logging.info(f"[EMAIL INGEST] ✅ Task for {assigned_persona}: {subject[:40]}")
        route_task(assigned_persona, subject, body, msg_id, sender)

    except json.JSONDecodeError as e:
        logging.error(f"[EMAIL INGEST] JSON decode error for {msg_id}: {e}")
    except subprocess.TimeoutExpired:
        logging.error(f"[EMAIL INGEST] gmail_read_message timeout for {msg_id}")
    except Exception as e:
        logging.error(f"[EMAIL INGEST] Failed to process {msg_id}: {e}")


def _verify_sender(sender: str) -> bool:
    """Check if email is from authorized Commander addresses."""
    for auth in AUTHORIZED_SENDERS:
        if auth.lower() in sender.lower():
            return True
    return False


def _has_trigger(subject: str, body: str) -> bool:
    """Check if subject or body contains trigger keyword."""
    combined = f"{subject} {body}".upper()
    for trigger in TRIGGER_KEYWORDS:
        if trigger.upper() in combined:
            return True
    return False


def _extract_persona(subject: str, body: str) -> str:
    """Extract persona tag from [PERSONA] or infer from content."""
    combined = f"{subject} {body}".upper()

    # Check for explicit tags like [COS], [A3], etc.
    for tag in VALID_PERSONAS.keys():
        if f"[{tag}]" in combined:
            return VALID_PERSONAS[tag]

    # Infer from content keywords
    if "client" in combined or "booking" in combined or "dani" in combined:
        return VALID_PERSONAS.get("A3", "dani")
    if "research" in combined or "intel" in combined or "a2" in combined:
        return VALID_PERSONAS.get("A2", "dembe")
    if "strategy" in combined or "business" in combined or "a5" in combined:
        return VALID_PERSONAS.get("A5", "castillo")
    if "finance" in combined or "commission" in combined or "a9" in combined:
        return VALID_PERSONAS.get("A9", "harlan")
    if "write" in combined or "draft" in combined or "a7" in combined:
        return VALID_PERSONAS.get("A7", "sterling")

    # Default to COS
    return VALID_PERSONAS.get("COS", "hale")


def route_task(persona: str, subject: str, body: str, msg_id: str, sender: str):
    """Create task JSON and add to queue."""

    # ── Hale Dispatcher early-exit ──
    # If the inbound email warrants Sonnet/Opus tier handling, route through
    # the Hale dispatcher (substrate-aware: MAX OAuth → Sonnet/Opus, fallback
    # Haiku) and skip the legacy queue.  Falls through on any error so the
    # legacy persona queue still receives the task.
    if _HALE_DISPATCHER_AVAILABLE:
        try:
            if is_hale_tier_email(subject, body):
                result = handle_email_task(subject=subject, body=body, sender=sender)
                logging.info(
                    "[EMAIL INGEST] Hale dispatcher handled %s: substrate=%s savings=$%.4f",
                    msg_id[:8],
                    result.get("substrate_used", "?"),
                    result.get("telemetry", {}).get("savings_usd", 0),
                )
                send_receipt(persona, subject)
                ok = mark_read(msg_id)
                if not ok:
                    logging.warning(
                        f"[EMAIL INGEST] mark_read FAILED post-Hale for {msg_id} (in-session dedup blocks reprocess)."
                    )
                return  # task handled — skip legacy persona queue
        except Exception as e:
            logging.warning(
                f"[EMAIL INGEST] Hale dispatcher error for {msg_id} — falling through to legacy queue: {e}"
            )

    task_json = {
        "task_id": f"EMAIL-TASK-{msg_id[:8]}",
        "task_type": "commander_email",
        "source": "EMAIL",
        "from": sender,
        "assigned_to": persona,
        "subject": subject,
        "body": body,
        "content": f"{subject}\n\n{body}",
        "timestamp": datetime.now().isoformat(),
        "priority": "HIGH" if "🔴" in subject or "RED" in subject.upper() else "NORMAL",
    }

    queue_path = "/home/john/Thunderbird/OpsCenter/01_TASK_QUEUE.json"
    try:
        with open(queue_path, "r") as f:
            queue = json.load(f)
    except Exception:
        queue = []

    queue.append(task_json)
    try:
        with open(queue_path, "w") as f:
            json.dump(queue, f, indent=2)
        logging.info(f"[EMAIL INGEST] Task queued: {task_json['task_id']}")
    except Exception as e:
        logging.error(f"[EMAIL INGEST] Failed to queue task: {e}")
        return

    send_receipt(persona, subject)
    success = mark_read(msg_id)
    if not success:
        logging.warning(
            f"[EMAIL INGEST] ⚠️  mark_read FAILED for {msg_id} — in-session dedup will block re-processing."
        )


def send_receipt(persona: str, subject: str):
    """Send task receipt email to Commander."""
    logging.info(f"[EMAIL INGEST] Sending receipt to Commander for {persona}")

    persona_map = {
        "hale": "Chief of Staff (COS)",
        "dembe": "A2 (Research & Intel)",
        "dani": "A3 (Concierge)",
        "castillo": "A5 (Strategy)",
        "voss": "A6 (Creative)",
        "sterling": "A7 (Process)",
        "harlan": "A9 (Finance)",
        "elon": "A12 (Innovation)",
        "padre": "CH (Wisdom)",
        "naia": "EXEC (Voice)",
    }

    persona_desc = persona_map.get(persona, persona.upper())
    body = f"✅ Task accepted.\n\n{persona_desc} is processing your task:\n{subject}\n\nOutput will post to OpsCenter or reply to this thread.\n\n— The Wing"

    send_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_create_draft",
        json.dumps(
            {
                "to": "johnloucks3@gmail.com",
                "subject": f"Re: {subject} - ACCEPTED",
                "body": body,
            }
        ),
    ]

    try:
        result = subprocess.run(send_cmd, capture_output=True, text=True, timeout=10)
        draft_data = json.loads(result.stdout)
        draft_id = draft_data.get("result", {}).get("id")
        if draft_id:
            send_result = subprocess.run(
                [
                    "/home/john/Thunderbird/mcp_bridge.sh",
                    "gmail_send_draft",
                    json.dumps({"draft_id": draft_id}),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if send_result.returncode == 0:
                logging.info(f"[EMAIL INGEST] Receipt sent to Commander")
            else:
                logging.warning(f"[EMAIL INGEST] Draft created but send failed")
        else:
            logging.warning(f"[EMAIL INGEST] Failed to get draft ID for receipt")
    except Exception as e:
        logging.error(f"[EMAIL INGEST] Failed to send receipt: {e}")


def mark_read(msg_id: str) -> bool:
    """Remove UNREAD label from message. Returns True on success, False on failure."""
    cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_modify_message",
        json.dumps({"message_id": msg_id, "remove_labels": "UNREAD"}),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        response = json.loads(result.stdout)
        if result.returncode != 0 or "error" in response:
            logging.error(f"[EMAIL INGEST] mark_read API error: {response}")
            return False
        logging.info(f"[EMAIL INGEST] Message {msg_id[:8]} marked READ")
        return True
    except subprocess.TimeoutExpired:
        logging.warning(f"[EMAIL INGEST] mark_read timeout for {msg_id}")
        return False
    except Exception as e:
        logging.error(f"[EMAIL INGEST] mark_read exception: {e}")
        return False


if __name__ == "__main__":
    Path("/home/john/Thunderbird/OpsCenter/logs").mkdir(parents=True, exist_ok=True)
    check_for_tasks()
