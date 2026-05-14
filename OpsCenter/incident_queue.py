#!/usr/bin/env python3
"""
Incident Queue — atomic append-only JSONL queue for watchdog events.
Watchdogs call enqueue_incident() instead of sending Telegram directly.
Hale's incident handler drains and triages the queue every 5 minutes.
"""
import json
import fcntl
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

QUEUE_PATH = Path("/home/john/Thunderbird/OpsCenter/hale_incident_queue.jsonl")
ARCHIVE_PATH = Path("/home/john/Thunderbird/OpsCenter/hale_incident_queue_archive.jsonl")

log = logging.getLogger(__name__)


def enqueue_incident(event: dict) -> None:
    """Atomic append to hale_incident_queue.jsonl. Never raises — logs errors silently."""
    try:
        if "event_id" not in event:
            event["event_id"] = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
        if "ts" not in event:
            event["ts"] = datetime.now(timezone.utc).isoformat()
        event.setdefault("consumed_by_brief", False)
        event.setdefault("consumed_at", None)

        QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(QUEUE_PATH, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(event) + "\n")
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        log.error(f"enqueue_incident failed: {e} — event: {event}")


def drain_queue() -> list[dict]:
    """Atomically read and clear the queue. Returns list of events."""
    if not QUEUE_PATH.exists():
        return []
    try:
        with open(QUEUE_PATH, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            content = f.read()
            f.seek(0)
            f.truncate()
            fcntl.flock(f, fcntl.LOCK_UN)
        events = []
        for line in content.splitlines():
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    log.warning(f"Skipping malformed queue entry: {line[:80]}")
        return events
    except Exception as e:
        log.error(f"drain_queue failed: {e}")
        return []


def archive_processed(events: list[dict]) -> None:
    """Append processed events to archive for audit trail."""
    if not events:
        return
    try:
        with open(ARCHIVE_PATH, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            for event in events:
                f.write(json.dumps(event) + "\n")
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        log.error(f"archive_processed failed: {e}")


def peek_queue() -> list[dict]:
    """Read queue without draining. For monitoring only."""
    if not QUEUE_PATH.exists():
        return []
    events = []
    try:
        with open(QUEUE_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        log.error(f"peek_queue failed: {e}")
    return events
