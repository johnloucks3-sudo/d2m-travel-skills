#!/usr/bin/env python3
"""AgentMail real-time listener — WebSocket, no public URL/webhook needed.

Subscribes to hale-thunderbird@agentmail.to and appends every inbound message
to OpsCenter/agentmail_inbox_queue.jsonl, then pings Telegram (bridge
notification during the Email-as-primary-C2 transition, so nothing is missed
while both channels run in parallel).

Run persistently via systemd (see deploy/agentmail-listener.service) or
foreground for testing: python3 core/email/agentmail_listener.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")

from agentmail import AgentMail, Subscribe, Subscribed, MessageReceivedEvent

from core.email.agentmail_client import _api_key

INBOX_ID = "hale-thunderbird@agentmail.to"
QUEUE_PATH = Path("/home/john/Thunderbird/OpsCenter/agentmail_inbox_queue.jsonl")

_seen_message_ids: set[str] = set()


def _load_seen():
    if QUEUE_PATH.exists():
        for line in QUEUE_PATH.read_text().splitlines():
            try:
                _seen_message_ids.add(json.loads(line)["message_id"])
            except (json.JSONDecodeError, KeyError):
                continue


def _notify_telegram(text: str):
    try:
        import subprocess
        subprocess.run(
            ["python3", "/home/john/Thunderbird/OpsCenter/thunderbird_telegram_gw.py", "send", text[:4000]],
            timeout=15, capture_output=True,
        )
    except Exception:
        pass  # bridge notification is best-effort; the JSONL queue is the source of truth


def _record(event: MessageReceivedEvent):
    msg = event.message
    if msg.message_id in _seen_message_ids:
        return  # AgentMail can redeliver the same event over the socket; dedup on message_id
    _seen_message_ids.add(msg.message_id)
    entry = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "message_id": msg.message_id,
        "thread_id": msg.thread_id,
        "from": msg.from_,
        "to": msg.to,
        "subject": msg.subject,
        "preview": getattr(msg, "preview", None) or getattr(msg, "text", None),
    }
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[agentmail_listener] recorded {entry['message_id']} from {entry['from']}")
    _notify_telegram(f"⚡ AgentMail — new email from {entry['from']}: {entry['subject']}")


def main():
    _load_seen()
    client = AgentMail(api_key=_api_key())
    print(f"[agentmail_listener] connecting, subscribing to {INBOX_ID} ...")
    with client.websockets.connect() as socket:
        socket.send_subscribe(Subscribe(inbox_ids=[INBOX_ID]))
        for event in socket:
            if isinstance(event, Subscribed):
                print(f"[agentmail_listener] subscribed: {event.inbox_ids}")
            elif isinstance(event, MessageReceivedEvent):
                _record(event)


if __name__ == "__main__":
    main()
