"""
Thunderbird Dani Email Responder
=================================

Watches Gmail for client emails (read AND unread) and has Dani draft responses.
COS reviews before any draft is created. Commander is notified via Telegram.

Routing:
  - Emails FROM Commander's addresses → SKIP (handled by Star Protocol)
  - Emails FROM known clients or unknown senders → Dani drafts reply → COS reviews

Run modes:
  - Standalone sweep:  python3 thunderbird_dani_email.py --sweep
  - Cron/scheduler:    from thunderbird_dani_email import dani_email_sweep
  - MCP tool:          run_dani_email_sweep (registered in travel_mcp_server.py)

Dependencies: thunderbird_gmail.py, thunderbird_dani_engine.py, thunderbird_personas.py
"""

import base64
import json
import logging
import re
import time
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
STATE_FILE = THUNDERBIRD_DIR / "dani_email_state.json"
SWEEP_LOG = THUNDERBIRD_DIR / "dani_email_log.json"

# ---------------------------------------------------------------------------
# Commander email addresses — these are EXCLUDED from Dani responses.
# Emails from these go to Star Protocol / COS, not Dani.
# ---------------------------------------------------------------------------
COMMANDER_EMAILS = {
    "johnloucks3@gmail.com",
    "john@d2mluxury.quest",
    "johnloucks@d2mluxury.quest",
}

# How many emails to process per sweep
MAX_PER_SWEEP = 10

# Gmail label for tracking processed messages
DANI_PROCESSED_LABEL = "DANI-Processed"


# ---------------------------------------------------------------------------
# Gmail helpers
# ---------------------------------------------------------------------------

def _get_gmail_service():
    from thunderbird_gmail import _get_gmail_service as _get_svc
    return _get_svc()


def _decode_body(payload):
    """Extract plain text body from Gmail message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        if part.get("parts"):
            result = _decode_body(part)
            if result:
                return result
    return ""


def _extract_headers(headers):
    keys = {"From", "To", "Subject", "Date", "Cc", "Message-ID"}
    return {h["name"]: h["value"] for h in headers if h["name"] in keys}


def _extract_email_address(from_field: str) -> str:
    """Extract bare email address from 'Name <email>' format."""
    match = re.search(r'<([^>]+)>', from_field)
    return match.group(1).lower() if match else from_field.strip().lower()


def _extract_sender_name(from_field: str) -> str:
    """Extract display name from 'Name <email>' format."""
    match = re.match(r'^"?([^"<]+)"?\s*<', from_field)
    return match.group(1).strip() if match else from_field.split("@")[0]


def _is_commander_email(from_field: str) -> bool:
    """Check if the sender is the Commander."""
    addr = _extract_email_address(from_field)
    return addr in COMMANDER_EMAILS


def _get_or_create_label(service, label_name: str) -> str:
    """Return the label ID for label_name, creating if needed."""
    results = service.users().labels().list(userId="me").execute()
    for label in results.get("labels", []):
        if label["name"] == label_name:
            return label["id"]
    body = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = service.users().labels().create(userId="me", body=body).execute()
    logger.info(f"Created Gmail label: {label_name} ({created['id']})")
    return created["id"]


def _create_draft_reply(service, msg: Dict, to_email: str, subject: str,
                         reply_body: str, thread_id: str) -> Dict:
    """Create a Gmail draft reply on a thread."""
    mime_msg = MIMEText(reply_body, "plain")
    mime_msg["to"] = to_email
    mime_msg["from"] = "johnloucks3@gmail.com"
    mime_msg["subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject

    raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")
    draft_data = {
        "message": {
            "raw": raw,
            "threadId": thread_id,
        }
    }
    draft = service.users().drafts().create(userId="me", body=draft_data).execute()
    return draft


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def _load_state() -> Dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"processed_ids": [], "last_run": None, "stats": {"total": 0, "drafted": 0, "skipped": 0}}


def _save_state(state: Dict):
    # Keep processed_ids list manageable
    if len(state["processed_ids"]) > 500:
        state["processed_ids"] = state["processed_ids"][-500:]
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _log_action(entry: Dict):
    log_data = []
    if SWEEP_LOG.exists():
        try:
            log_data = json.loads(SWEEP_LOG.read_text())
        except Exception:
            log_data = []
    log_data.append(entry)
    if len(log_data) > 200:
        log_data = log_data[-200:]
    SWEEP_LOG.write_text(json.dumps(log_data, indent=2))


# ---------------------------------------------------------------------------
# Dani response engine
# ---------------------------------------------------------------------------

def _build_dani_email_response(sender_name: str, sender_email: str,
                                 subject: str, body: str) -> Optional[str]:
    """Build Dani's response to a client email using the full data engine.

    Returns the response text, or None if engine fails.
    """
    from thunderbird_dani_engine import build_dani_context
    from thunderbird_personas import call_persona

    # Build the query as Dani would see it
    query = (
        f"EMAIL from {sender_name} ({sender_email}):\n"
        f"Subject: {subject}\n\n"
        f"{body[:3000]}"
    )

    try:
        # Build full Dani context (client mode — hides financials)
        context = build_dani_context(query, is_commander=False)

        # Add email-specific rules
        email_rules = (
            "\n\nEMAIL RESPONSE RULES:\n"
            "- You are responding to a client EMAIL, not a chat message.\n"
            "- Use proper email formatting — greeting, body, warm sign-off.\n"
            "- Sign as: Dani Moreau, Luxury Travel Concierge, Dreams2Memories Travel\n"
            "- Keep the response focused and professional. No emojis.\n"
            "- If you need to reference John, say 'John Loucks, our owner' or 'John'.\n"
        )
        context += email_rules

        result = call_persona("A3", context, max_tokens=800)
        answer = result.get("answer", "")

        # Strip the model attribution tag for email drafts
        answer = re.sub(r"\n\n---\n_.*?_$", "", answer).strip()

        return answer if answer else None

    except Exception as e:
        logger.error(f"Dani email response failed: {e}")
        return None


def _cos_review_email(query: str, dani_answer: str) -> Dict:
    """COS reviews Dani's email draft before it becomes a Gmail draft."""
    from thunderbird_dani_engine import cos_review
    return cos_review(query, dani_answer, is_client=True)


# ---------------------------------------------------------------------------
# Telegram notification
# ---------------------------------------------------------------------------

def _notify_commander_telegram(sender: str, subject: str, dani_response: str,
                                 cos_note: str, draft_id: str):
    """Send Commander a Telegram notification about the email draft."""
    try:
        import os
        import requests as _requests

        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        commander_id = os.environ.get("TELEGRAM_COMMANDER_ID", "")

        if not bot_token or not commander_id:
            logger.warning("Telegram env vars not set — skipping notification")
            return

        notice = (
            f"📧 *DANI EMAIL DRAFT CREATED*\n\n"
            f"From: {sender}\n"
            f"Subject: {subject}\n\n"
            f"Dani's draft response (first 300 chars):\n"
            f"_{dani_response[:300]}_\n\n"
            f"COS: {cos_note}\n"
            f"Draft ID: `{draft_id}`\n\n"
            f"Review in Gmail before sending."
        )

        _requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": commander_id,
                "text": notice,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")


# ---------------------------------------------------------------------------
# Main sweep
# ---------------------------------------------------------------------------

def dani_email_sweep() -> Dict[str, Any]:
    """Scan Gmail for client emails (read AND unread), have Dani draft responses.

    Skips:
      - Emails from Commander's addresses
      - Already-processed messages (by ID state + DANI-Processed label)
      - Newsletters / marketing (no-reply senders)
      - Emails already in DANI-Processed label

    For each client email:
      1. Build Dani context with full data engine
      2. Get Dani's response
      3. COS reviews the response
      4. Create Gmail draft reply
      5. Label as DANI-Processed
      6. Notify Commander via Telegram
    """
    service = _get_gmail_service()
    state = _load_state()
    processed_ids = set(state.get("processed_ids", []))

    # Get/create tracking label
    processed_label_id = _get_or_create_label(service, DANI_PROCESSED_LABEL)

    # Search for recent emails in INBOX (read OR unread, not from Commander)
    # Exclude newsletters, no-reply, and already-processed
    # NOTE: Removed is:unread — rely on DANI-Processed label + processed_ids for dedup.
    # Commander's emails were being missed because opening them marked them as read.
    query = "in:inbox newer_than:2d -label:DANI-Processed"
    for addr in COMMANDER_EMAILS:
        query += f" -from:{addr}"

    results = service.users().messages().list(
        userId="me", q=query, maxResults=MAX_PER_SWEEP
    ).execute()

    messages = results.get("messages", [])
    actions = []
    drafted = 0

    logger.info(f"Dani email sweep: found {len(messages)} unread client emails")

    for msg_ref in messages:
        msg_id = msg_ref["id"]

        if msg_id in processed_ids:
            continue

        # Read full message
        try:
            msg = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
        except Exception as e:
            logger.error(f"Failed to read message {msg_id}: {e}")
            continue

        payload = msg.get("payload", {})
        headers = _extract_headers(payload.get("headers", []))
        from_field = headers.get("From", "")
        subject = headers.get("Subject", "(no subject)")
        body = _decode_body(payload)
        thread_id = msg.get("threadId", "")

        # Double-check: skip Commander emails
        if _is_commander_email(from_field):
            processed_ids.add(msg_id)
            continue

        # Skip no-reply / newsletter senders
        sender_email = _extract_email_address(from_field)
        if any(skip in sender_email for skip in ["noreply", "no-reply", "newsletter", "mailer-daemon", "postmaster"]):
            processed_ids.add(msg_id)
            continue

        sender_name = _extract_sender_name(from_field)
        logger.info(f"  Processing: {subject[:60]} from {sender_name}")

        entry = {
            "timestamp": datetime.now().isoformat(),
            "message_id": msg_id,
            "from": from_field,
            "subject": subject,
            "status": "pending",
        }

        # Get Dani's response
        dani_response = _build_dani_email_response(sender_name, sender_email, subject, body)
        if not dani_response:
            entry["status"] = "dani_failed"
            _log_action(entry)
            processed_ids.add(msg_id)
            continue

        # COS review
        cos_result = _cos_review_email(
            f"{sender_name} asked: {subject}\n{body[:500]}",
            dani_response
        )
        cos_note = cos_result.get("note", "")

        if not cos_result.get("approved", True):
            logger.warning(f"COS BLOCKED email response to {sender_name}: {cos_note}")
            entry["status"] = "cos_blocked"
            entry["cos_note"] = cos_note
            _log_action(entry)
            processed_ids.add(msg_id)
            continue

        # Use COS-revised version if available
        final_response = cos_result.get("revised") or dani_response

        # Create Gmail draft reply
        try:
            draft = _create_draft_reply(
                service, msg, sender_email, subject, final_response, thread_id
            )
            draft_id = draft.get("id", "unknown")
            entry["status"] = "draft_created"
            entry["draft_id"] = draft_id
            entry["cos_note"] = cos_note
            drafted += 1

            # Label as processed
            try:
                service.users().messages().modify(
                    userId="me", id=msg_id,
                    body={"addLabelIds": [processed_label_id]}
                ).execute()
            except Exception as e:
                logger.warning(f"Failed to label message: {e}")

            # Notify Commander
            _notify_commander_telegram(from_field, subject, final_response, cos_note, draft_id)

            logger.info(f"  Draft created for {sender_name} — draft ID: {draft_id}")

        except Exception as e:
            logger.error(f"Failed to create draft reply: {e}")
            entry["status"] = "draft_error"
            entry["error"] = str(e)

        _log_action(entry)
        processed_ids.add(msg_id)

    # Save state
    state["processed_ids"] = list(processed_ids)
    state["last_run"] = datetime.now().isoformat()
    state["stats"]["total"] += len(actions) + drafted
    state["stats"]["drafted"] += drafted
    _save_state(state)

    summary = {
        "status": "success",
        "sweep_time": datetime.now().isoformat(),
        "emails_found": len(messages),
        "drafts_created": drafted,
        "actions": [a for a in actions] if actions else [],
    }

    logger.info(f"Dani email sweep done — {drafted} drafts created from {len(messages)} emails")
    return summary


# ---------------------------------------------------------------------------
# MCP tool registration
# ---------------------------------------------------------------------------

def register_dani_email_tools(mcp_server):
    """Register Dani email responder MCP tools."""
    from pydantic import Field

    @mcp_server.tool(
        name="run_dani_email_sweep",
        annotations={"title": "Run Dani Email Sweep", "readOnlyHint": False},
    )
    async def run_dani_email_sweep_tool() -> str:
        """Scan Gmail for unread client emails and have Dani draft responses.

        Excludes Commander emails (johnloucks3@gmail.com, etc.).
        Each response is COS-reviewed before draft creation.
        Commander is notified via Telegram for each draft.
        """
        try:
            result = dani_email_sweep()
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Dani email sweep error: {e}")
            return json.dumps({"error": str(e), "type": "dani_email_error"})

    @mcp_server.tool(
        name="dani_email_log",
        annotations={"title": "View Dani Email Log", "readOnlyHint": True},
    )
    async def dani_email_log_tool(
        count: int = Field(10, description="Number of recent entries to show"),
    ) -> str:
        """View recent Dani email response results."""
        try:
            if not SWEEP_LOG.exists():
                return json.dumps({"status": "success", "count": 0, "entries": []})
            log_data = json.loads(SWEEP_LOG.read_text())
            recent = log_data[-count:] if len(log_data) > count else log_data
            return json.dumps({
                "status": "success",
                "total_entries": len(log_data),
                "showing": len(recent),
                "entries": recent,
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "type": "log_error"})

    logger.info("Dani Email Responder tools registered (run_dani_email_sweep, dani_email_log)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if "--sweep" in sys.argv:
        print("Running Dani email sweep...", file=sys.stderr)
        result = dani_email_sweep()
        print(json.dumps(result, indent=2))
    else:
        print("Usage:", file=sys.stderr)
        print("  python3 thunderbird_dani_email.py --sweep    # Run one sweep", file=sys.stderr)
        print("", file=sys.stderr)
        print("Scans Gmail for unread client emails (excludes Commander).", file=sys.stderr)
        print("Dani drafts responses, COS reviews, Gmail draft created.", file=sys.stderr)
        print("Commander notified via Telegram.", file=sys.stderr)
