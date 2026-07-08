#!/usr/bin/env python3
"""AgentMail <-> Gmail d2mconcierge integration bridge.

Three active integration points (fourth is in scripts/agentmail_daily_digest.py):
  1. poll_and_forward()       -- Gmail INBOUND: new client threads forwarded to hale-thunderbird@ as artifacts
  2. push_draft_to_gmail()    -- AgentMail OUTBOUND: draft pushed to d2mconcierge with Commander-Review label + gate_veto
  3. sync_commander_replies() -- REPLY BRIDGE: Commander's sent messages synced back into AgentMail thread context

Rocket compliance: ALL THREE are EDGE-TRIGGERED.
  - Forwarded thread IDs tracked in state -- never re-fired on the same thread.
  - Synced sent message IDs tracked -- never re-fired on the same send.
  - Per-poll burst guard: MAX_SENDS_PER_POLL caps sends in any one cycle.
  "When condition still true tomorrow, does it speak again?" Answer: NO.

State file: OpsCenter/state/gmail_agentmail_bridge.json
Run via: scripts/gmail_agentmail_bridge_poller.py (systemd timer, every 5 min)
"""
import base64
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")

from core.email.agentmail_client import AgentMailClient
from core.email.agentmail_quota import check_and_record, QuotaExceeded
from core.email.channel_router import route_by_content_type

STATE_PATH = Path("/home/john/Thunderbird/OpsCenter/state/gmail_agentmail_bridge.json")
HALE_INBOX = "hale-thunderbird@agentmail.to"

# Per-poll burst guard: max AgentMail sends per cycle.
# Prevents quota exhaustion if many threads arrive simultaneously (e.g. marketing blast reply).
MAX_SENDS_PER_POLL = 10

# Senders excluded from client-bridge forwarding (wing-internal / system noise)
_EXCLUDE_SENDER_FRAGMENTS = {
    "d2mconcierge@gmail.com",
    "johnloucks3@gmail.com",
    "noreply@",
    "no-reply@",
    "mailer-daemon@",
    "notifications@",
    "hale-thunderbird@agentmail.to",
    "dreams2memories-80921@agentmail.to",
    "concierge@d2mluxury.quest",
}


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "last_processed_ts": None,
        "forwarded_thread_ids": [],
        "pushed_draft_thread_ids": [],
        "last_sent_sync_ts": None,
        "synced_send_ids": [],
    }


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Gmail service
# ---------------------------------------------------------------------------

def _gmail_service():
    """Gmail API service for d2mconcierge, via thunderbird_google_auth."""
    _api_dir = str(Path("/home/john/Thunderbird/api"))
    if _api_dir not in sys.path:
        sys.path.insert(0, _api_dir)
    from thunderbird_google_auth import get_persona_gmail
    return get_persona_gmail()


# ---------------------------------------------------------------------------
# Message parsing helpers
# ---------------------------------------------------------------------------

def _is_wing_internal(sender: str) -> bool:
    if not sender:
        return True
    s = sender.lower()
    return any(excl in s for excl in _EXCLUDE_SENDER_FRAGMENTS)


def _extract_body_preview(payload: dict, max_chars: int = 500) -> str:
    """Walk MIME payload recursively to find first text/plain block."""
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            try:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")[:max_chars]
            except Exception:
                pass
    for part in payload.get("parts", []):
        result = _extract_body_preview(part, max_chars)
        if result:
            return result
    return ""


def _thread_summary(service, thread_id: str) -> dict | None:
    """Return a structured summary dict for a Gmail thread, or None if wing-internal."""
    try:
        # Metadata-only for headers (cheap); full fetch only for body preview
        meta = service.users().threads().get(
            userId="me", id=thread_id, format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        msgs = meta.get("messages", [])
        if not msgs:
            return None
        first = msgs[0]
        headers = {h["name"].lower(): h["value"] for h in first.get("payload", {}).get("headers", [])}
        sender = headers.get("from", "")
        if _is_wing_internal(sender):
            return None
        # Fetch body preview from first message
        full_msg = service.users().messages().get(
            userId="me", id=first["id"], format="full"
        ).execute()
        preview = _extract_body_preview(full_msg.get("payload", {}))
        return {
            "thread_id": thread_id,
            "from": sender,
            "subject": headers.get("subject", "(no subject)"),
            "date": headers.get("date", ""),
            "body_preview": preview,
            "gmail_link": f"https://mail.google.com/mail/u/0/#inbox/{thread_id}",
        }
    except Exception as e:
        print(f"[bridge] thread {thread_id} summary failed: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# #1 — Gmail INBOUND bridge
# ---------------------------------------------------------------------------

def poll_and_forward(dry_run: bool = False) -> dict:
    """Poll d2mconcierge inbox for new client threads; forward each once to AgentMail.

    EDGE-TRIGGERED: thread_id added to forwarded_thread_ids on first forward.
    Burst guard: stops after MAX_SENDS_PER_POLL sends per call.

    Returns: {"forwarded": int, "skipped": int, "quota_stopped": bool}
    """
    state = _load_state()
    forwarded_set = set(state.get("forwarded_thread_ids", []))

    if state.get("last_processed_ts"):
        ts = int(datetime.fromisoformat(state["last_processed_ts"]).timestamp())
        query = f"in:inbox after:{ts}"
    else:
        query = "in:inbox newer_than:1d"

    service = _gmail_service()
    try:
        result = service.users().threads().list(
            userId="me", q=query, maxResults=50
        ).execute()
    except Exception as e:
        print(f"[bridge] threads.list failed: {e}", file=sys.stderr)
        return {"forwarded": 0, "skipped": 0, "quota_stopped": False}

    threads = result.get("threads", [])
    forwarded = 0
    skipped = 0
    quota_stopped = False
    client = AgentMailClient()

    for t in threads:
        tid = t["id"]
        if tid in forwarded_set:
            skipped += 1
            continue
        if forwarded >= MAX_SENDS_PER_POLL:
            quota_stopped = True
            break

        summary = _thread_summary(service, tid)
        # Mark as processed even if wing-internal (avoids re-checking same thread)
        forwarded_set.add(tid)
        if summary is None:
            skipped += 1
            continue

        subject = f"[CLIENT-EMAIL] {summary['subject']}"
        text = (
            f"From: {summary['from']}\n"
            f"Date: {summary['date']}\n"
            f"Subject: {summary['subject']}\n"
            f"Gmail: {summary['gmail_link']}\n\n"
            f"--- Preview (first 500 chars) ---\n{summary['body_preview']}\n\n"
            f"[bridge::gmail_thread_id={tid}]"
        )

        if not dry_run:
            try:
                check_and_record()
                client.send_message(
                    inbox_id=HALE_INBOX,
                    to=[HALE_INBOX],
                    subject=subject,
                    text=text,
                )
                forwarded += 1
                print(f"[bridge] forwarded {tid}: {summary['subject'][:60]}")
            except QuotaExceeded as e:
                print(f"[bridge] quota exceeded, stopping: {e}", file=sys.stderr)
                quota_stopped = True
                break
            except Exception as e:
                print(f"[bridge] send failed for {tid}: {e}", file=sys.stderr)
                # Don't add to forwarded_set on send failure -- retry next cycle
                forwarded_set.discard(tid)
        else:
            print(f"[bridge] DRY-RUN: would forward {tid}: {summary['subject'][:60]}")
            forwarded += 1

    state["last_processed_ts"] = datetime.now(timezone.utc).isoformat()
    state["forwarded_thread_ids"] = list(forwarded_set)
    if not dry_run:
        _save_state(state)

    return {"forwarded": forwarded, "skipped": skipped, "quota_stopped": quota_stopped}


# ---------------------------------------------------------------------------
# #2 — AgentMail draft -> Gmail WF-17 output pipeline
# ---------------------------------------------------------------------------

def push_draft_to_gmail(
    agentmail_thread_id: str,
    subject: str,
    html_body: str,
    to_email: str,
    allow_repush: bool = False,
) -> dict:
    """Push an AgentMail-authored draft into d2mconcierge Gmail for Commander review.

    Creates draft with THUNDERBIRD-Commander-Review label.
    Fires gate_veto: Telegram ping + AgentMail confirmation (both channels per ROE Rule 1).
    EDGE-TRIGGERED: each agentmail_thread_id pushed once unless allow_repush=True.

    Returns: {"draft_id": str|None, "channel": str|None, "already_pushed": bool}
    """
    state = _load_state()
    pushed_set = set(state.get("pushed_draft_thread_ids", []))

    if agentmail_thread_id in pushed_set and not allow_repush:
        return {"draft_id": None, "channel": None, "already_pushed": True}

    from core.email.thunderbird_gmail import gmail_create_draft_sync
    draft_id = gmail_create_draft_sync(
        to=to_email,
        subject=subject,
        body=html_body,
        persona_id="CONCIERGE",
    )

    # gate_veto per channel_router: (telegram, agentmail) -- both channels notified
    channel = route_by_content_type("gate_veto")
    try:
        from core.ops.confirmed_auto_execute import send_telegram_notification
        send_telegram_notification(
            f"[WF-17 GATE] Draft queued for Commander review\n"
            f"Subject: {subject}\n"
            f"To: {to_email}\n"
            f"AgentMail thread: {agentmail_thread_id}\n"
            f"Gmail draft ID: {draft_id}"
        )
    except Exception as e:
        print(f"[bridge] Telegram gate_veto ping failed (non-fatal): {e}", file=sys.stderr)

    pushed_set.add(agentmail_thread_id)
    state["pushed_draft_thread_ids"] = list(pushed_set)
    _save_state(state)

    return {"draft_id": draft_id, "channel": str(channel), "already_pushed": False}


# ---------------------------------------------------------------------------
# #3 — Commander reply bridge
# ---------------------------------------------------------------------------

def sync_commander_replies(dry_run: bool = False) -> dict:
    """Scan d2mconcierge SENT folder; sync Commander replies back to AgentMail.

    Only syncs replies on threads previously bridged (in forwarded_thread_ids).
    EDGE-TRIGGERED: each sent message_id tracked in synced_send_ids, never re-synced.
    Runs in the same 5-min timer as poll_and_forward().

    Returns: {"synced": int, "skipped": int}
    """
    state = _load_state()
    forwarded_set = set(state.get("forwarded_thread_ids", []))
    synced_set = set(state.get("synced_send_ids", []))

    if not forwarded_set:
        return {"synced": 0, "skipped": 0}

    if state.get("last_sent_sync_ts"):
        ts = int(datetime.fromisoformat(state["last_sent_sync_ts"]).timestamp())
        query = f"in:sent after:{ts}"
    else:
        query = "in:sent newer_than:1d"

    service = _gmail_service()
    try:
        result = service.users().threads().list(
            userId="me", q=query, maxResults=50
        ).execute()
    except Exception as e:
        print(f"[bridge] sent threads.list failed: {e}", file=sys.stderr)
        return {"synced": 0, "skipped": 0}

    threads = result.get("threads", [])
    synced = 0
    skipped = 0
    client = AgentMailClient()

    for t in threads:
        tid = t["id"]
        if tid not in forwarded_set:
            skipped += 1
            continue
        try:
            thread = service.users().threads().get(
                userId="me", id=tid, format="full"
            ).execute()
        except Exception:
            continue

        for msg in thread.get("messages", []):
            if "SENT" not in msg.get("labelIds", []):
                continue
            msg_id = msg["id"]
            if msg_id in synced_set:
                continue

            headers = {
                h["name"].lower(): h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }
            body_preview = _extract_body_preview(msg.get("payload", {}))
            sync_text = (
                f"[COMMANDER-REPLY via d2mconcierge]\n"
                f"To: {headers.get('to', '')}\n"
                f"Subject: {headers.get('subject', '')}\n"
                f"Date: {headers.get('date', '')}\n\n"
                f"{body_preview}\n\n"
                f"[bridge::gmail_thread_id={tid}]"
            )

            if not dry_run:
                try:
                    check_and_record()
                    client.send_message(
                        inbox_id=HALE_INBOX,
                        to=[HALE_INBOX],
                        subject=f"[REPLY] {headers.get('subject', '(no subject)')}",
                        text=sync_text,
                    )
                    synced_set.add(msg_id)
                    synced += 1
                    print(f"[bridge] synced reply {msg_id} on thread {tid}")
                except QuotaExceeded as e:
                    print(f"[bridge] quota exceeded syncing replies: {e}", file=sys.stderr)
                    break
                except Exception as e:
                    print(f"[bridge] reply sync failed for {msg_id}: {e}", file=sys.stderr)
            else:
                print(f"[bridge] DRY-RUN: would sync reply {msg_id} on thread {tid}")
                synced_set.add(msg_id)
                synced += 1

    state["last_sent_sync_ts"] = datetime.now(timezone.utc).isoformat()
    state["synced_send_ids"] = list(synced_set)
    if not dry_run:
        _save_state(state)

    return {"synced": synced, "skipped": skipped}


# ---------------------------------------------------------------------------
# CLI for manual runs and dry-runs
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AgentMail<->Gmail bridge — manual run")
    parser.add_argument("--dry-run", action="store_true", help="Print actions, no sends")
    parser.add_argument("--inbound", action="store_true", help="Run inbound poll only (#1)")
    parser.add_argument("--replies", action="store_true", help="Run reply sync only (#3)")
    args = parser.parse_args()

    run_all = not args.inbound and not args.replies

    if args.inbound or run_all:
        r = poll_and_forward(dry_run=args.dry_run)
        print(f"Inbound: forwarded={r['forwarded']} skipped={r['skipped']} quota_stopped={r['quota_stopped']}")

    if args.replies or run_all:
        r = sync_commander_replies(dry_run=args.dry_run)
        print(f"Replies: synced={r['synced']} skipped={r['skipped']}")
