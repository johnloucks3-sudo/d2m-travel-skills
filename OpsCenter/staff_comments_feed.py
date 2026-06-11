"""Realtime Staff-Comments Feed — Thunderbird Wing.

Commander directive 2026-06-11: "fold staff comments into REALTIME."

PROBLEM (first principles): staff/persona/agent comments were only visible via a
manual `STAFF COMMENTS?` query (staff_comments_handler.py). A human (Hale) had to
*ask*. Comments that landed between queries were invisible to the OODA loop and to
the brief. Why is a human polling a queue?

SOLUTION: one append-only live feed (`staff_comments_live.jsonl`). Every producer
appends a line the instant it has a comment. The OODA loop reads "what's new since
last cycle" every cycle. The brief reads the same feed and renders a section — no
manual query.

DESIGN PRINCIPLES:
- Append-only JSONL. No DB, no daemon, no lock contention. tail-able by a human.
- Idempotent: dedup by content hash so re-peeking RabbitMQ never double-writes.
- Cursor-based reads: the loop asks unread_since(cursor) and advances its own cursor.
- Zero new infrastructure. If RabbitMQ is down, the feed still works for any other
  producer (notifications dir, direct append_comment calls).

LANE: OpsCenter only. Does NOT touch Telegram gateway, core/email/*, qdrant, or the
6 protected files. RabbitMQ is read-only (non-destructive peek).
"""

from __future__ import annotations

import json
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

OPS_DIR = Path(__file__).resolve().parent
FEED_PATH = OPS_DIR / "staff_comments_live.jsonl"
CURSOR_PATH = OPS_DIR / ".staff_comments_feed_cursor.json"
NOTIFICATIONS_DIR = OPS_DIR / "notifications"

# Priority mapping by comment type. Dissents are the loud ones.
_TYPE_PRIORITY = {
    "dissent": "P0",
    "alternative": "P1",
    "observation": "P1",
    "confirmation": "P2",
    "notification": "P2",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _comment_hash(source: str, author: str, msg_type: str, content: str) -> str:
    """Stable dedup key. Same comment from the same source hashes identically,
    so re-syncing a peeked RabbitMQ queue does not create duplicate feed lines."""
    raw = f"{source}|{author}|{msg_type}|{content}".encode("utf-8", "replace")
    return hashlib.sha256(raw).hexdigest()[:16]


def _load_existing_hashes() -> set:
    """All hashes already in the feed — for idempotent appends."""
    hashes = set()
    if not FEED_PATH.exists():
        return hashes
    with FEED_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                h = rec.get("hash")
                if h:
                    hashes.add(h)
            except json.JSONDecodeError:
                continue
    return hashes


# ---------------------------------------------------------------------------
# WRITER — any producer calls this the instant it has a comment.
# ---------------------------------------------------------------------------

def append_comment(
    source: str,
    author: str,
    msg_type: str,
    content: str,
    to: Optional[list] = None,
    priority: Optional[str] = None,
    context: Optional[dict] = None,
    _known_hashes: Optional[set] = None,
) -> Optional[dict]:
    """Append one staff comment to the live feed. Idempotent.

    Args:
        source: where it came from ('rabbitmq', 'notifications', 'sterling-agent', ...)
        author: persona/agent that produced it
        msg_type: 'dissent' | 'observation' | 'alternative' | 'confirmation' | 'notification'
        content: the comment text
        to: optional list of intended recipients
        priority: override; otherwise derived from msg_type
        context: optional dict of structured context (mission id, client, etc.)
        _known_hashes: optional pre-loaded hash set (batch-append optimization)

    Returns:
        The written record dict, or None if it was a duplicate (already in feed).
    """
    h = _comment_hash(source, author, msg_type, content)
    known = _known_hashes if _known_hashes is not None else _load_existing_hashes()
    if h in known:
        return None  # idempotent: already recorded

    record = {
        "hash": h,
        "ts": _now_iso(),
        "source": source,
        "author": author,
        "type": msg_type,
        "priority": priority or _TYPE_PRIORITY.get(msg_type, "P2"),
        "content": content,
        "to": to or [],
        "context": context or {},
        "read": False,
    }

    FEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FEED_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    if _known_hashes is not None:
        _known_hashes.add(h)
    return record


# ---------------------------------------------------------------------------
# READER — the OODA loop and the brief consume from here.
# ---------------------------------------------------------------------------

def read_live_feed(limit: Optional[int] = None) -> list:
    """Return all feed records (newest last). Optionally cap to last `limit`."""
    records = []
    if not FEED_PATH.exists():
        return records
    with FEED_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if limit is not None:
        return records[-limit:]
    return records


def _load_cursor() -> str:
    if CURSOR_PATH.exists():
        try:
            return json.loads(CURSOR_PATH.read_text()).get("last_read_ts", "")
        except (json.JSONDecodeError, OSError):
            return ""
    return ""


def _save_cursor(ts: str) -> None:
    CURSOR_PATH.write_text(json.dumps({"last_read_ts": ts, "updated": _now_iso()}))


def unread_since(cursor_ts: Optional[str] = None, advance_cursor: bool = False) -> list:
    """Return feed records newer than cursor_ts (the OODA-loop primitive).

    Args:
        cursor_ts: ISO timestamp; if None, uses the persisted cursor.
        advance_cursor: if True, persist the newest ts so the next call only
                        returns comments that arrived after this cycle.

    Returns:
        List of records with ts > cursor_ts, oldest first.
    """
    cursor = cursor_ts if cursor_ts is not None else _load_cursor()
    records = read_live_feed()
    fresh = [r for r in records if r.get("ts", "") > cursor]
    if advance_cursor and records:
        _save_cursor(records[-1]["ts"])
    return fresh


# ---------------------------------------------------------------------------
# SOURCE SYNC — pull from RabbitMQ peek + notifications dir into the feed.
# Called by staff_comments_handler so the manual query also *populates* the feed,
# and callable standalone by the OODA loop each cycle.
# ---------------------------------------------------------------------------

def sync_from_rabbitmq() -> int:
    """Non-destructive peek of all persona inboxes; append new comments to feed.

    Returns number of new comments appended. Safe if RabbitMQ is offline (0)."""
    appended = 0
    try:
        from core.messaging.rabbitmq_client import PersonaMessaging
    except Exception:
        return 0

    try:
        messaging = PersonaMessaging()
    except Exception:
        return 0

    known = _load_existing_hashes()
    personas = ["sterling", "dembe", "reyes", "dani", "harlan", "washington"]
    try:
        for p in personas:
            try:
                inbox = messaging.consume(p)  # auto_ack=False → non-destructive peek
            except Exception:
                continue
            for msg in inbox:
                rec = append_comment(
                    source="rabbitmq",
                    author=getattr(msg, "from_persona", "unknown"),
                    msg_type=getattr(msg, "msg_type", "observation"),
                    content=getattr(msg, "content", ""),
                    to=getattr(msg, "to_personas", []),
                    context={
                        "inbox": p,
                        "message_id": getattr(msg, "message_id", None),
                        "requires_ack": getattr(msg, "requires_ack", False),
                    },
                    _known_hashes=known,
                )
                if rec:
                    appended += 1
    finally:
        try:
            messaging.close()
        except Exception:
            pass
    return appended


def sync_from_notifications() -> int:
    """Scan OpsCenter/notifications/*.json; append any new deliverable notices.

    Returns number of new comments appended."""
    appended = 0
    if not NOTIFICATIONS_DIR.exists():
        return 0
    known = _load_existing_hashes()
    for nf in sorted(NOTIFICATIONS_DIR.glob("*.json")):
        try:
            data = json.loads(nf.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        subject = data.get("subject") or data.get("client") or nf.stem
        rec = append_comment(
            source="notifications",
            author=data.get("client_id") or "timer-engine",
            msg_type="notification",
            content=subject,
            priority="P2" if data.get("priority", "INFO") == "INFO" else "P1",
            context={
                "file": nf.name,
                "client": data.get("client"),
                "to": data.get("to"),
                "orig_priority": data.get("priority"),
            },
            _known_hashes=known,
        )
        if rec:
            appended += 1
    return appended


def sync_sources() -> dict:
    """Pull every known source into the live feed. The OODA-loop entrypoint.

    Returns a small summary dict."""
    rmq = sync_from_rabbitmq()
    notif = sync_from_notifications()
    return {
        "rabbitmq_new": rmq,
        "notifications_new": notif,
        "total_new": rmq + notif,
    }


# ---------------------------------------------------------------------------
# BRIEF RENDERER — the brief consumes this. No manual query.
# ---------------------------------------------------------------------------

def format_brief_section(window_hours: int = 24, max_items: int = 8) -> str:
    """Render the live feed as a brief section. Auto-syncs first.

    Surfaces P0 (dissents) prominently, P1 below, count of older items."""
    sync_sources()
    records = read_live_feed()
    if not records:
        return "### STAFF COMMENTS (LIVE)\n\n✅ Feed clear — no staff comments logged."

    cutoff = datetime.now(timezone.utc).timestamp() - window_hours * 3600

    def _in_window(r):
        try:
            return datetime.fromisoformat(r["ts"]).timestamp() >= cutoff
        except (ValueError, KeyError):
            return True

    recent = [r for r in records if _in_window(r)]
    p0 = [r for r in recent if r.get("priority") == "P0"]
    p1 = [r for r in recent if r.get("priority") == "P1"]

    lines = [f"### STAFF COMMENTS (LIVE) — last {window_hours}h"]
    lines.append(f"\nFeed: `OpsCenter/staff_comments_live.jsonl` · {len(recent)} in window · {len(records)} total\n")

    if p0:
        lines.append(f"🚨 **{len(p0)} CRITICAL (dissent)** — response required:")
        for r in p0[:max_items]:
            lines.append(f"   - **{r['author']}** ({r['source']}): {r['content'][:140]}")
        lines.append("")

    if p1:
        lines.append(f"⚠️  **{len(p1)} observations/alternatives/notices:**")
        for r in p1[:max_items]:
            lines.append(f"   - {r['author']} ({r['type']}): {r['content'][:120]}")
        lines.append("")

    if not p0 and not p1:
        lines.append("All recent comments are low-priority (P2). No action flagged.")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    summary = sync_sources()
    print(f"sync_sources → {summary}")
    print("\n" + format_brief_section())
    sys.exit(0)
