#!/usr/bin/env python3
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VALID_TRIGGERS = ["COS", "A2", "A3", "A5", "A6", "A7", "A9", "A12", "DANI", "LUNA", "GAUGE", "WRAITH", "VIPER", "PADRE"]

# Persistent dedup: survives across process restarts.
# Keeps last 500 IDs so the file doesn't grow unbounded.
_SEEN_FILE = Path('/home/john/Thunderbird/state/email_ingest_seen.json')

def _load_seen() -> set:
    try:
        return set(json.loads(_SEEN_FILE.read_text()))
    except Exception:
        return set()

def _save_seen(seen: set):
    _SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SEEN_FILE.write_text(json.dumps(list(seen)[-500:]))

# In-session dedup (fast path within one process lifetime)
_processed_this_run: set = set()


def check_for_tasks():
    logging.info("[EMAIL INGEST] Polling d2mconcierge for Commander tasking...")

    search_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_search_messages",
        json.dumps({"query": "is:unread", "max_results": 10})
    ]

    try:
        result = subprocess.run(search_cmd, capture_output=True, text=True, timeout=15)
        data = json.loads(result.stdout)

        if "result" not in data or "messages" not in data["result"]:
            return

        messages = data["result"]["messages"]
        _seen_persistent = _load_seen()
        new_messages = [m for m in messages
                        if m["id"] not in _processed_this_run
                        and m["id"] not in _seen_persistent]

        if not new_messages:
            logging.info("[EMAIL INGEST] All UNREAD messages already processed this run — no infinite loop.")
            return

        for msg in new_messages:
            process_message(msg["id"])

    except Exception as e:
        logging.error(f"[EMAIL INGEST] Search failed: {e}")


def process_message(msg_id):
    # Register in both caches immediately — before any API calls.
    # Persistent cache survives process restarts; in-session cache is fast path.
    _processed_this_run.add(msg_id)
    _seen = _load_seen()
    _seen.add(msg_id)
    _save_seen(_seen)

    read_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_read_message",
        json.dumps({"message_id": msg_id})
    ]

    try:
        result = subprocess.run(read_cmd, capture_output=True, text=True, timeout=10)
        msg_data = json.loads(result.stdout).get("result", {})

        subject = msg_data.get("subject", "").upper()
        body = msg_data.get("body", "").strip()

        assigned_persona = None

        # Check for brackets first (e.g. [COS])
        for trigger in VALID_TRIGGERS:
            if f"[{trigger}]" in subject or body.upper().startswith(f"[{trigger}]"):
                assigned_persona = trigger
                break

        # If no brackets, check raw words
        if not assigned_persona:
            for trigger in VALID_TRIGGERS:
                if trigger in subject.split() or body.upper().startswith(trigger):
                    assigned_persona = trigger
                    break

        if assigned_persona:
            logging.info(f"[EMAIL INGEST] Task detected for {assigned_persona} in msg {msg_id}")
            route_task(assigned_persona, subject, body, msg_id)
        else:
            logging.info(f"[EMAIL INGEST] No trigger found in msg {msg_id}. Marking read.")
            mark_read(msg_id)

    except Exception as e:
        logging.error(f"[EMAIL INGEST] Failed to process {msg_id}: {e}")


def route_task(persona, subject, body, msg_id):
    task_json = {
        "task_id": f"EMAIL_{msg_id}",
        "task_type": "commander_message",
        "source": "EMAIL",
        "assigned_to": persona,
        "subject": subject,
        "body": body,
        "content": f"{subject}\n\n{body}",
        "timestamp": datetime.now().isoformat()
    }

    queue_path = "/home/john/Thunderbird/OpsCenter/01_TASK_QUEUE.json"
    try:
        with open(queue_path, 'r') as f:
            queue = json.load(f)
    except Exception:
        queue = []

    queue.append(task_json)
    with open(queue_path, 'w') as f:
        json.dump(queue, f, indent=2)

    send_receipt(persona, subject)
    success = mark_read(msg_id)
    if not success:
        logging.warning(f"[EMAIL INGEST] mark_read FAILED for {msg_id} — in-session dedup will block re-processing, but UNREAD label persists on Gmail.")


def send_receipt(persona, subject):
    logging.info(f"[EMAIL INGEST] Sending receipt for {persona}")
    body = f"Thank you, Yoda. \n\nThe {persona} persona has received your task regarding '{subject}' and is actively processing it. We will reply to this thread or output to the OpsCenter upon completion.\n\nThe Wing"

    send_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_create_draft",
        json.dumps({
            "to": "johnloucks3@gmail.com",
            "subject": f"Re: {subject} - TASK ACCEPTED",
            "body": body
        })
    ]

    try:
        result = subprocess.run(send_cmd, capture_output=True, text=True, timeout=10)
        draft_data = json.loads(result.stdout)
        draft_id = draft_data.get("result", {}).get("id")
        if draft_id:
            subprocess.run([
                "/home/john/Thunderbird/mcp_bridge.sh",
                "gmail_send_draft",
                json.dumps({"draft_id": draft_id})
            ], timeout=10)
    except Exception as e:
        logging.error(f"[EMAIL INGEST] Failed to send receipt: {e}")


def mark_read(msg_id: str) -> bool:
    """
    Remove UNREAD label from msg_id. Returns True on success, False on failure.
    Caller should log a warning if False — UNREAD will persist on Gmail but
    in-session dedup (_processed_this_run) prevents the infinite loop.
    """
    logging.info(f"[EMAIL INGEST] Marking {msg_id} as READ to prevent loop.")
    cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_modify_message",
        json.dumps({"message_id": msg_id, "remove_labels": "UNREAD"})
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        # Verify the API call actually succeeded
        response = json.loads(result.stdout)
        if result.returncode != 0 or "error" in response:
            logging.error(f"[EMAIL INGEST] mark_read API error for {msg_id}: {response}")
            return False
        logging.info(f"[EMAIL INGEST] {msg_id} marked READ successfully.")
        return True
    except subprocess.TimeoutExpired:
        logging.warning(f"[EMAIL INGEST] mark_read timeout for {msg_id}")
        return False
    except Exception as e:
        logging.error(f"[EMAIL INGEST] mark_read exception for {msg_id}: {e}")
        return False


if __name__ == "__main__":
    check_for_tasks()
