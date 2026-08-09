#!/usr/bin/env python3
# ============================================================
# RETIRED 2026-08-08 — replaced by run_commander_directive_sweep +
# directive_executor Round Table flow. Do not extend.
# ============================================================
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

# ── Audit trail (A2/A3) — defensive import; pipeline must never break ──────
try:
    from core.email.email_audit import record as _audit_record, already_done as _audit_already_done
except ImportError:  # pragma: no cover
    def _audit_record(*a, **k): return True   # type: ignore[misc]
    def _audit_already_done(*a, **k): return False  # type: ignore[misc]

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
        json.dumps({"query": "from:johnloucks3@gmail.com -label:THUNDERBIRD-Scanned newer_than:1d", "max_results": 20}),
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


import re as _re
# Command prefix regex — COS/COO/HALE/VIC followed by ANY non-letter separator
# Must appear at START of subject (after Re:/Fwd:) or START of body.
# Disables old TRIGGER_KEYWORDS broad-scan which fired on [COS] in wing-generated
# email subjects and "WASHINGTON" in body text (caused Chaplain feedback loop).
_CMD_PATTERN = _re.compile(r'^(cos|coo|hale|vic)\W', _re.IGNORECASE)

def _strip_reply_prefix(s: str) -> str:
    return _re.sub(r'^(re:|fwd?:|fw:)\s*', '', s.strip(), flags=_re.IGNORECASE)

def _has_trigger(subject: str, body: str) -> bool:
    """Command prefix must appear at START of subject or START of body.
    Checks subject first (after stripping Re:/Fwd:), then body first line.
    Does NOT scan mid-subject or mid-body — prevents false positives from
    [COS] wing labels in subject or 'Washington' references in body text.
    """
    if _CMD_PATTERN.match(_strip_reply_prefix(subject)):
        return True
    if _CMD_PATTERN.match(body.strip()):
        return True
    return False


def _extract_persona(subject: str, body: str) -> str:
    """Extract persona from explicit [TAG] in subject or body prefix keyword.
    Only checks the first 200 chars of subject+body to avoid false matches
    in quoted reply text.
    """
    combined = f"{subject} {body[:200]}".upper()

    # Explicit bracketed tags only — no keyword inference from body content
    for tag in VALID_PERSONAS.keys():
        if f"[{tag}]" in combined:
            return VALID_PERSONAS[tag]

    # Default to COS/Hale — Commander addressed us, Hale handles it
    return VALID_PERSONAS.get("COS", "hale")


def route_task(persona: str, subject: str, body: str, msg_id: str, sender: str):
    """Create task, write to opencode_inbox.md, then handle via Hale dispatcher if applicable."""

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

    # ── A3: Idempotency guard — skip if this email was already turned into a task ──
    if _audit_already_done(msg_id, "mission_created"):
        logging.info(
            f"[EMAIL INGEST] SKIP {msg_id[:12]} — already queued (audit: mission_created)"
        )
        _audit_record(msg_id, "ingest", classified_as="commander_email",
                      action_taken=None, outcome="skipped-duplicate",
                      detail="route_task: already_done=True")
        return

    # Write to opencode_inbox.md FIRST — always. This is the primary C2 channel
    # that the thunderbird_tasking_watcher monitors. [COS]/[COO] emails MUST
    # reach the watcher regardless of Hale dispatcher routing.
    _write_to_opencode_inbox(task_json)

    # Write to JSON task queue (legacy — task_processor.py consumer)
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
        # ── A3: Record successful task creation ──
        _audit_record(msg_id, "ingest", classified_as="commander_email",
                      action_taken="mission_created",
                      detail=f"task_id={task_json['task_id']} persona={persona}")
    except Exception as e:
        logging.error(f"[EMAIL INGEST] Failed to queue task: {e}")
        _audit_record(msg_id, "ingest", classified_as="commander_email",
                      action_taken="mission_created", outcome="failed",
                      detail=f"queue write failed: {e}")

    # ── Hale Dispatcher (fast-path for high-tier tasks) ──
    # Runs alongside the watcher path — does NOT early-return. The watcher
    # sees the task in opencode_inbox.md and spawns OpenCode; the Hale
    # dispatcher handles it immediately via Sonnet/Opus as a speed bonus.
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
        except Exception as e:
            logging.warning(
                f"[EMAIL INGEST] Hale dispatcher error for {msg_id} — task already in opencode_inbox.md for watcher: {e}"
            )

    send_receipt(persona, subject)
    success = mark_read(msg_id)
    if not success:
        logging.warning(
            f"[EMAIL INGEST] ⚠️  mark_read FAILED for {msg_id} — in-session dedup will block re-processing."
        )


def _write_to_opencode_inbox(task: dict):
    """Append task to opencode_inbox.md in watcher-compatible format."""
    inbox = Path("/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md")

    priority_map = {"HIGH": "P0", "NORMAL": "P1", "LOW": "P2"}
    prio = priority_map.get(task.get("priority", "NORMAL"), "P1")

    persona_label = task.get("assigned_to", "hale").upper()

    entry = (
        f"---\n"
        f"## TASK: {task['task_id']}\n"
        f"status: PENDING\n"
        f"from: Commander via Email\n"
        f"to: HALE-OC\n"
        f"priority: {prio}\n"
        f"persona: {persona_label}\n"
        f"updated: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"\n"
        f"task: |\n"
        f"  {task.get('subject', 'No subject')}\n"
        f"  {task.get('body', 'No body')}\n"
        f"\n"
    )

    try:
        inbox.parent.mkdir(parents=True, exist_ok=True)
        with open(inbox, "a") as f:
            f.write(entry)
        logging.info(f"[EMAIL INGEST] Task written to opencode_inbox.md: {task['task_id']}")
    except Exception as e:
        logging.error(f"[EMAIL INGEST] Failed to write to opencode_inbox.md: {e}")


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
    body = f"✅ Task accepted.\n\n{persona_desc} is on it:\n{subject}\n\nResults will be emailed back to you from d2mconcierge@gmail.com when complete.\n\n— The Wing"

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
    if os.environ.get("THUNDERBIRD_RETIRED_EMAIL") == "1":
        logging.info("[EMAIL INGEST] RETIRED — THUNDERBIRD_RETIRED_EMAIL=1, skipping poll.")
        sys.exit(0)
    Path("/home/john/Thunderbird/OpsCenter/logs").mkdir(parents=True, exist_ok=True)
    check_for_tasks()
