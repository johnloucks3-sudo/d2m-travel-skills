"""
Thunderbird SMS Monitor — Inbound SMS-to-Email Parser & Persona Router
======================================================================

Monitors Gmail for inbound SMS messages arriving via T-Mobile's email-to-SMS
gateway (7192910742@tmomail.net). Parses persona prefixes and routes commands
to the appropriate Wing persona via Groq.

Flow:
  1. Search Gmail for recent emails from T-Mobile SMS gateway patterns
  2. Skip already-processed message IDs (tracked in sms_monitor_state.json)
  3. Parse message body for persona prefix (A2--, A3--, COS--, etc.)
  4. If prefix found: route to persona via call_persona (Groq)
  5. Send truncated response back via SMS outbound
  6. If no prefix: log as general inbound, flag for COS review
  7. Label processed messages THUNDERBIRD-SMS-Processed

Standalone:  python3 thunderbird_sms_monitor.py
Scheduler:   from thunderbird_sms_monitor import check_inbound_sms
             (called every 10 minutes during business hours)

Dependencies: thunderbird_gmail.py (OAuth Gmail), thunderbird_personas.py,
              thunderbird_sms.py (outbound SMS)
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from googleapiclient.errors import HttpError

from thunderbird_gmail import _get_gmail_service, _decode_body, _extract_headers, USER_EMAIL
from thunderbird_personas import call_persona

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
STATE_FILE = THUNDERBIRD_DIR / "sms_monitor_state.json"
LOG_DIR = THUNDERBIRD_DIR / "logs"
LOG_FILE = LOG_DIR / "sms_inbound.log"

# T-Mobile SMS gateway (inbound parsing only — outbound via Telegram C2 since 2026-03-31)
JOHN_PHONE = "7192910742"

# Gmail labels for SMS tracking
SMS_DONE_LABEL = "THUNDERBIRD-SMS-Processed"

# Search query: emails from T-Mobile SMS gateway(s)
# T-Mobile uses tmomail.net for SMS and mms.tmomail.net for MMS
GMAIL_SMS_QUERY = (
    "from:tmomail.net OR from:mms.tmomail.net "
    "newer_than:1d"
)

# Persona prefix pattern: "A2--", "COS--", "STAFF--", etc.
# Accepts optional whitespace around the dashes
PREFIX_PATTERN = re.compile(
    r"^\s*(A2|A3|A5|A9|A10|A12|COS|EXEC|CH|STAFF)\s*--\s*(.+)",
    re.IGNORECASE | re.DOTALL,
)

# STAFF-- routes to COS for distribution
STAFF_ROUTE = "COS"

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)

# Also log to file
LOG_DIR.mkdir(parents=True, exist_ok=True)
_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter(
    "%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
))
logger.addHandler(_file_handler)


# ---------------------------------------------------------------------------
# State persistence — avoid reprocessing
# ---------------------------------------------------------------------------

def _load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "processed_ids": [],
        "last_check": None,
        "stats": {"total_processed": 0, "routed_to_persona": 0, "general": 0},
    }


def _save_state(state: Dict[str, Any]):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Gmail helpers
# ---------------------------------------------------------------------------

def _get_or_create_label(service, label_name: str) -> str:
    """Return the label ID for label_name, creating it if necessary."""
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


def _search_messages(service, query: str, max_results: int = 50) -> List[Dict]:
    """Search Gmail with a query string and return message stubs."""
    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    return results.get("messages", [])


def _read_full_message(service, msg_id: str) -> Dict[str, Any]:
    """Read a full message and return a clean dict."""
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=msg_id, format="full")
        .execute()
    )
    payload = msg.get("payload", {})
    headers = _extract_headers(
        payload.get("headers", []),
        {"From", "To", "Subject", "Date"},
    )
    body = _decode_body(payload)
    return {
        "id": msg["id"],
        "threadId": msg["threadId"],
        "labels": msg.get("labelIds", []),
        "snippet": msg.get("snippet", ""),
        "headers": headers,
        "body": body,
    }


def _label_message(service, msg_id: str, add_label_id: str):
    """Add a label to a message."""
    service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={"addLabelIds": [add_label_id]},
    ).execute()


# ---------------------------------------------------------------------------
# SMS body parsing
# ---------------------------------------------------------------------------

def _clean_sms_body(body: str) -> str:
    """Clean up SMS body from email gateway formatting.

    T-Mobile gateway emails often include signature lines, disclaimers,
    and extra whitespace. Strip those down to the actual message.
    """
    if not body:
        return ""

    # Remove common T-Mobile footer patterns
    for marker in [
        "Sent from my T-Mobile",
        "Sent via SMS",
        "This message was sent",
        "------",
    ]:
        idx = body.find(marker)
        if idx > 0:
            body = body[:idx]

    return body.strip()


def _parse_prefix(body: str) -> Tuple[Optional[str], str]:
    """Parse persona prefix from SMS body.

    Returns:
        (persona_id, command_text) if prefix found
        (None, full_body) if no prefix
    """
    cleaned = _clean_sms_body(body)
    match = PREFIX_PATTERN.match(cleaned)
    if match:
        prefix = match.group(1).upper()
        command = match.group(2).strip()
        # STAFF-- routes to COS
        if prefix == "STAFF":
            return STAFF_ROUTE, f"[STAFF broadcast] {command}"
        return prefix, command
    return None, cleaned


# ---------------------------------------------------------------------------
# SMS outbound — reply via gateway
# ---------------------------------------------------------------------------

def _load_env() -> dict:
    """Load .env file into a dict."""
    env = {}
    env_file = THUNDERBIRD_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def reply_via_sms(message: str, persona_id: Optional[str] = None) -> Dict[str, Any]:
    """Send a response back to John via Telegram C2 bot.
    (Replaced tmomail SMS gateway 2026-03-31.)

    Args:
        message: Response text
        persona_id: If set, prefix response with [PERSONA]

    Returns:
        Status dict with send result
    """
    try:
        import os
        import requests
        env = _load_env()
        token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_C2_BOT_TOKEN") or env.get("TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_C2_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_COMMANDER_ID") or env.get("TELEGRAM_COMMANDER_ID")
        if not token or not chat_id:
            logger.error("Telegram credentials not configured — reply not sent")
            return {"status": "error", "error": "Telegram credentials not configured"}

        # Format: "[A3] response text"
        if persona_id:
            body_text = f"<b>[{persona_id}]</b> {message}"
        else:
            body_text = message

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": body_text,
            "parse_mode": "HTML",
        }, timeout=10)

        if resp.status_code == 200:
            logger.info(f"Telegram reply sent: {body_text[:80]}...")
            return {
                "status": "sent",
                "channel": "telegram",
                "chars": len(body_text),
                "persona": persona_id,
            }
        else:
            logger.error(f"Telegram reply failed: {resp.status_code} {resp.text[:200]}")
            return {"status": "error", "error": f"Telegram API {resp.status_code}"}

    except Exception as e:
        logger.error(f"Telegram reply failed: {e}")
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Persona routing
# ---------------------------------------------------------------------------

def _route_to_persona(persona_id: str, command: str) -> Dict[str, Any]:
    """Route a command to a persona via Groq and return the result.

    Uses call_persona from thunderbird_personas.py which handles
    model selection, memory injection, and response attribution.
    """
    prompt = (
        f"INBOUND SMS COMMAND from Commander (Yoda):\n"
        f"{command}\n\n"
        f"Respond concisely — your answer will be sent back via SMS "
        f"(160 char limit). Be specific and actionable. Skip pleasantries."
    )

    try:
        result = call_persona(persona_id, prompt, max_tokens=200)
        if "error" in result:
            logger.error(f"Persona {persona_id} returned error: {result['error']}")
            return result

        # Extract the answer, strip the model attribution tag for SMS
        answer = result.get("answer", "")
        # Remove the trailing model tag (---\n_model_tag_)
        answer = re.sub(r"\n+---\n_[^_]+_\s*$", "", answer).strip()

        result["answer_clean"] = answer
        return result

    except Exception as e:
        logger.error(f"Persona routing failed for {persona_id}: {e}")
        return {"persona": persona_id, "error": str(e)}


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def check_inbound_sms(
    max_messages: int = 20,
    send_replies: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Poll Gmail for inbound SMS messages, parse, and route to personas.

    Args:
        max_messages: Max SMS emails to process per run
        send_replies: If True, send persona responses back via SMS
        dry_run: If True, parse but don't route or reply

    Returns:
        Summary dict with counts and per-message results
    """
    logger.info(f"=== SMS Monitor starting — dry_run: {dry_run} ===")

    # Load state
    state = _load_state()
    processed_ids = set(state.get("processed_ids", []))

    # Connect to Gmail
    try:
        service = _get_gmail_service()
    except Exception as e:
        logger.error(f"Gmail connection failed: {e}")
        return {"status": "error", "error": f"Gmail unreachable: {e}"}

    # Get/create done label
    done_label_id = _get_or_create_label(service, SMS_DONE_LABEL)

    # Search for SMS gateway emails
    message_stubs = _search_messages(service, GMAIL_SMS_QUERY, max_messages)
    logger.info(f"Found {len(message_stubs)} SMS gateway emails (last 24h)")

    results = []
    routed_count = 0
    general_count = 0
    skipped_count = 0

    for stub in message_stubs:
        msg_id = stub["id"]

        # Skip already processed
        if msg_id in processed_ids:
            skipped_count += 1
            continue

        # Read full message
        try:
            email_data = _read_full_message(service, msg_id)
        except HttpError as e:
            logger.error(f"Failed to read message {msg_id}: {e}")
            results.append({"id": msg_id, "status": "read_error", "error": str(e)})
            continue

        sender = email_data["headers"].get("From", "unknown")
        body = email_data["body"]
        logger.info(f"  SMS from: {sender}")
        logger.info(f"  Body: {body[:120]}")

        # Parse persona prefix
        persona_id, command = _parse_prefix(body)

        entry = {
            "id": msg_id,
            "timestamp": datetime.now().isoformat(),
            "from": sender,
            "raw_body": body[:500],
            "persona_prefix": persona_id,
            "command": command[:300] if command else None,
        }

        if persona_id and not dry_run:
            # Route to persona
            logger.info(f"  Routing to {persona_id}: {command[:80]}")
            persona_result = _route_to_persona(persona_id, command)

            answer = persona_result.get("answer_clean", persona_result.get("answer", ""))
            entry["persona_response"] = answer[:500]
            entry["status"] = "routed"

            if "error" in persona_result:
                entry["status"] = "route_error"
                entry["error"] = persona_result["error"]
            elif send_replies and answer:
                # Send reply via SMS
                reply_result = reply_via_sms(answer, persona_id)
                entry["reply_status"] = reply_result.get("status")

            routed_count += 1

        elif persona_id and dry_run:
            entry["status"] = "dry_run_would_route"
            routed_count += 1

        else:
            # No prefix — general inbound, flag for COS review
            logger.info(f"  No prefix — flagging for COS review")
            entry["status"] = "general"
            general_count += 1

            if not dry_run and send_replies:
                # Notify that message was received but needs a prefix
                reply_via_sms(
                    "Msg received. Use prefix to route: A2--, A3--, COS--, etc.",
                    None,
                )

        # Label as processed in Gmail
        if not dry_run:
            try:
                _label_message(service, msg_id, done_label_id)
            except HttpError as e:
                logger.error(f"Label failed for {msg_id}: {e}")

        # Track as processed
        processed_ids.add(msg_id)
        results.append(entry)

    # Save state
    state["processed_ids"] = list(processed_ids)[-500:]  # Keep last 500 to prevent unbounded growth
    state["last_check"] = datetime.now().isoformat()
    state["stats"]["total_processed"] += len(results)
    state["stats"]["routed_to_persona"] += routed_count
    state["stats"]["general"] += general_count
    if not dry_run:
        _save_state(state)

    summary = {
        "status": "success",
        "dry_run": dry_run,
        "found": len(message_stubs),
        "processed": len(results),
        "skipped": skipped_count,
        "routed": routed_count,
        "general": general_count,
        "results": results,
    }

    logger.info(
        f"=== SMS Monitor done — processed: {len(results)}, "
        f"routed: {routed_count}, general: {general_count}, "
        f"skipped: {skipped_count} ==="
    )
    return summary


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def get_sms_stats() -> Dict[str, Any]:
    """Return SMS monitor statistics.

    Returns:
        Dict with total_processed, routed_to_persona, general, last_check
    """
    state = _load_state()
    return {
        "last_check": state.get("last_check"),
        "stats": state.get("stats", {}),
        "tracked_message_count": len(state.get("processed_ids", [])),
    }


# ---------------------------------------------------------------------------
# MCP tool registration
# ---------------------------------------------------------------------------

def register_sms_monitor_tools(mcp):
    """Register SMS monitor tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """
    from pydantic import Field as PydanticField

    @mcp.tool(
        name="check_inbound_sms",
        annotations={"title": "Check Inbound SMS", "readOnlyHint": False},
    )
    async def check_inbound_sms_tool(
        max_messages: int = PydanticField(20, description="Max SMS emails to process"),
        send_replies: bool = PydanticField(True, description="Send persona responses back via SMS"),
        dry_run: bool = PydanticField(False, description="Parse only, no routing or replies"),
    ) -> str:
        """Poll Gmail for inbound SMS messages from T-Mobile gateway,
        parse persona prefixes, and route to the appropriate Wing persona.

        SMS format: 'A3-- check payment status' routes to Moreau (A3).
        Supported prefixes: A2, A3, A5, A9, A10, A12, COS, EXEC, CH, STAFF.
        """
        result = check_inbound_sms(
            max_messages=max_messages,
            send_replies=send_replies,
            dry_run=dry_run,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="sms_stats",
        annotations={"title": "SMS Monitor Stats", "readOnlyHint": True},
    )
    async def sms_stats_tool() -> str:
        """Return SMS monitor statistics: total processed, routed, general, last check time."""
        stats = get_sms_stats()
        return json.dumps(stats, indent=2, default=str)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv
    no_reply = "--no-reply" in sys.argv

    if "--stats" in sys.argv:
        stats = get_sms_stats()
        print(json.dumps(stats, indent=2, default=str))
        sys.exit(0)

    result = check_inbound_sms(
        dry_run=dry_run,
        send_replies=not no_reply,
    )
    print(json.dumps(result, indent=2, default=str))
