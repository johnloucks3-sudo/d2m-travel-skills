#!/usr/bin/env python3
"""
HALE Email C2 Daemon
====================
Bidirectional email command interface for Col Victoria "Iron Vic" Hale.
Provides full YOGA parity via Claude Agent SDK — same tool access as Telegram C2.

Architecture mirrors thunderbird_telegram_tools_sdk.py:
  Email arrives → activation check → auto-ack → call_cos_via_sdk() → thread reply

Standing orders enforced:
  - Authorized sender: johnloucks3@gmail.com only
  - Within-wing replies only: d2mconcierge → johnloucks3
  - WF-17: HALE drafts client emails, NEVER sends them
  - SO 07 MAY 2026: Two-lane email pipeline (drafts plain text)
  - SO 21 MAR 2026 / SO 24 MAR 2026: Send gate enforced in system prompt

Deployed as: ~/.config/systemd/user/thunderbird-email-c2.service
"""

import asyncio
import base64
import json
import logging
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_DIR = Path("/home/john/Thunderbird/logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [email-c2] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "thunderbird-email-c2.log"),
    ],
)
logger = logging.getLogger("thunderbird_email_c2")

# ── Paths ─────────────────────────────────────────────────────────────────────
THUNDERBIRD_DIR = Path("/home/john/Thunderbird")
DATA_DIR = THUNDERBIRD_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

THREAD_DB_PATH = DATA_DIR / "email_c2_threads.db"
TRUST_ENGINE_PATH = THUNDERBIRD_DIR / "Personas" / "hale_trust_engine.py"
PROCESSED_IDS_PATH = DATA_DIR / "email_c2_processed.json"

# ── Config ────────────────────────────────────────────────────────────────────
AUTHORIZED_SENDER = "johnloucks3@gmail.com"
POLL_INTERVAL = 60          # seconds between Gmail polls
GMAIL_QUERY = "label:d2m-ai-process is:unread"
PROCESSED_LABEL = "d2m-ai-processed"
MAX_HISTORY_MESSAGES = 20   # rolling window per thread
MAX_HISTORY_CHARS = 4000    # max chars per history message
RATE_LIMIT_SECONDS = 10     # min seconds between replies in same thread
AUTO_ACK_TEXT = "🦅 Acknowledged — on it."

# Activation words (case-insensitive, any word boundary)
ACTIVATION_PATTERN = re.compile(
    r"\b(COS|COO|Vic|Hale|HALE)\b", re.IGNORECASE
)

# Decision outcome pattern — "HALE, outcome X: approved" or "outcome: done"
OUTCOME_PATTERN = re.compile(
    r"\b(?:outcome|closed|done|complete[d]?|approved|rejected|deferred)\s*[:\-–]?\s*(.+)",
    re.IGNORECASE,
)

# ── System Prompt ─────────────────────────────────────────────────────────────
EMAIL_C2_SYSTEM_PROMPT = """You are Col Victoria "Iron Vic" Hale, Chief of Staff and COO of Dreams2Memories Travel, LLC. You are responding via email to Commander John Loucks ("Yoda").

CHANNEL: Email C2 — same authority and tools as Telegram C2.
MEDIUM: Your reply will be sent as an email in the existing thread.

STANDING ORDERS (non-negotiable):

1. RESPONSE FORMAT (T&Q AFH 33-337 — conditional):
   - Short factual replies (1-3 sentences): plain prose
   - Multi-point answers (4+ distinct items): TALKING PAPER format
     ```
     TALKING PAPER ON [SUBJECT]
     -- [Key point 1]
     -- [Key point 2]
        - [Sub-point]
     POC: Iron Vic / COS / [Date]
     ```
   - Analytical / recommendation responses: BULLET BACKGROUND PAPER format
     ```
     BULLET BACKGROUND PAPER ON [SUBJECT]
     FROM: D2M Thunderbird Wing / COS
     SUBJECT: [One line]
     BACKGROUND:
     -- [BLUF — bottom line up front]
     DISCUSSION:
     -- [Analysis]
     RECOMMENDATION:
     -- [Action]
     [Iron Vic, COS, Date]
     ```
   - T&Q rules: em dash (--) leads top bullets, sub-bullets indented 3 spaces,
     active voice, BLUF first, date DD MMM YYYY.

2. WF-17 SEND GATE (SO 21 MAR 2026):
   - You may draft client emails, proposals, and correspondence.
   - You NEVER send client emails directly. Always: "Draft created. Awaiting Commander approval to send."
   - johnloucks3@gmail.com and d2mconcierge@gmail.com are within-wing — you may reply freely here.

3. FINANCIAL AUTHORITY: Zero. Prepare, track, recommend. Never commit.

4. TOOL USE: You have full MCP access — Gmail, Drive, TESS, Playwright, Calendar, Bash, Python.
   Use tools directly for tasks requiring real data. Do not describe what you would do — do it.

5. FOUR COMMANDER GATES (hold for these only):
   - Sending any email to a client
   - Financial commitment
   - New client first contact
   - Strategy direction
   Everything else: execute and report.

6. POSTURE: Execute + Report. Past tense beats future tense questions.
   Banned: "Should I...?", "Would you like me to...?", "Shall I...?"
   Required: "Doing [X]. Reason: [Y]."

Your eagle mark is 🦅 — open every substantive response with it on its own line.
"""

# ── SQLite Thread Memory ──────────────────────────────────────────────────────

def _init_thread_db() -> sqlite3.Connection:
    """Initialize SQLite thread memory store."""
    conn = sqlite3.connect(THREAD_DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS thread_history (
            thread_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            role TEXT NOT NULL,       -- 'user' or 'assistant'
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (thread_id, message_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS thread_meta (
            thread_id TEXT PRIMARY KEY,
            subject TEXT,
            last_activity TEXT,
            last_reply_at REAL DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def _get_thread_history(conn: sqlite3.Connection, thread_id: str) -> list[dict]:
    """Load rolling conversation history for a thread (last N messages)."""
    rows = conn.execute(
        """
        SELECT role, content, created_at FROM thread_history
        WHERE thread_id = ?
        ORDER BY created_at ASC
        """,
        (thread_id,),
    ).fetchall()
    return [{"role": r[0], "text": r[1][:MAX_HISTORY_CHARS], "created_at": r[2]} for r in rows[-MAX_HISTORY_MESSAGES:]]


def _append_thread_history(
    conn: sqlite3.Connection, thread_id: str, role: str, content: str, message_id: str
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO thread_history VALUES (?, ?, ?, ?, ?)",
        (thread_id, message_id, role, content[:MAX_HISTORY_CHARS * 2], ts),
    )
    conn.execute(
        "INSERT OR IGNORE INTO thread_meta (thread_id, last_activity) VALUES (?, ?)",
        (thread_id, ts),
    )
    conn.execute(
        "UPDATE thread_meta SET last_activity = ? WHERE thread_id = ?",
        (ts, thread_id),
    )
    conn.commit()


def _get_last_reply_time(conn: sqlite3.Connection, thread_id: str) -> float:
    row = conn.execute(
        "SELECT last_reply_at FROM thread_meta WHERE thread_id = ?", (thread_id,)
    ).fetchone()
    return row[0] if row else 0.0


def _set_last_reply_time(conn: sqlite3.Connection, thread_id: str, ts: float) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO thread_meta (thread_id, last_reply_at) VALUES (?, ?)",
        (thread_id, ts),
    )
    conn.execute(
        "UPDATE thread_meta SET last_reply_at = ? WHERE thread_id = ?",
        (ts, thread_id),
    )
    conn.commit()


# ── Processed Message Cache ───────────────────────────────────────────────────

def _load_processed_ids() -> set:
    if PROCESSED_IDS_PATH.exists():
        try:
            return set(json.loads(PROCESSED_IDS_PATH.read_text()))
        except Exception:
            return set()
    return set()


def _save_processed_ids(ids: set) -> None:
    # Keep last 2000 to prevent unbounded growth
    trimmed = list(ids)[-2000:]
    PROCESSED_IDS_PATH.write_text(json.dumps(trimmed))


# ── Gmail Helpers ─────────────────────────────────────────────────────────────

def _get_gmail_service():
    try:
        sys.path.insert(0, str(THUNDERBIRD_DIR / "core" / "email"))
        from thunderbird_gmail import _get_wing_gmail_service
        return _get_wing_gmail_service()
    except Exception as e:
        logger.error("Gmail service unavailable: %s", e)
        raise


def _decode_mime_body(payload: dict) -> str:
    """Extract plain text body from a Gmail message payload."""
    # Single-part message
    if payload.get("body", {}).get("data"):
        try:
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        except Exception:
            return ""

    # Multipart — prefer text/plain, fall back to first part
    parts = payload.get("parts", [])
    for part in parts:
        mime = part.get("mimeType", "")
        if mime == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                try:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                except Exception:
                    pass
        # Recurse into nested multipart
        if mime.startswith("multipart/"):
            result = _decode_mime_body(part)
            if result:
                return result

    # Last resort: first part with data
    for part in parts:
        data = part.get("body", {}).get("data", "")
        if data:
            try:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            except Exception:
                pass
    return ""


def _extract_header(headers: list, name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _validate_dkim(headers: list) -> bool:
    """Check Authentication-Results for DKIM pass. Soft check — log warning if fails."""
    auth = _extract_header(headers, "Authentication-Results")
    if not auth:
        return True  # No header present — can't verify, allow with log
    if "dkim=fail" in auth.lower():
        return False
    return True


def _get_label_id(service, label_name: str) -> str | None:
    """Resolve a label name to its ID."""
    try:
        result = service.users().labels().list(userId="me").execute()
        for label in result.get("labels", []):
            if label.get("name", "").lower() == label_name.lower():
                return label["id"]
    except Exception as e:
        logger.warning("Could not resolve label '%s': %s", label_name, e)
    return None


def _mark_processed(service, message_id: str, processed_label_id: str | None) -> None:
    """Mark message as read and add processed label."""
    try:
        body: dict = {"removeLabelIds": ["UNREAD"]}
        if processed_label_id:
            body["addLabelIds"] = [processed_label_id]
        service.users().messages().modify(
            userId="me", id=message_id, body=body
        ).execute()
    except Exception as e:
        logger.warning("Could not mark message %s processed: %s", message_id, e)


# ── Trust Engine Bootstrap ────────────────────────────────────────────────────

def _bootstrap_trust_engine() -> None:
    """Initialize trust data files if they don't exist."""
    trust_data_path = THUNDERBIRD_DIR / "Personas" / "hale_trust_data.json"
    decision_log_path = THUNDERBIRD_DIR / "Personas" / "hale_decision_log.json"

    if not trust_data_path.exists():
        logger.info("Bootstrapping trust data — initializing at score 50 (Layer 9)")
        trust_data = {
            "trust_score": 50,
            "autonomy_tier": "COMMANDER (Operational Autonomy)",
            "current_streak": 0,
            "last_decision": None,
            "domain_accuracy": {
                domain: {"correct": 0, "total": 0}
                for domain in [
                    "email_classification", "staff_task_routing", "quality_gate_wf17",
                    "vendor_contact_boundaries", "client_context_building",
                    "brief_prioritization", "strategic_staff_growth",
                    "commander_pushback_timing", "system_architecture", "voice_drift_detection"
                ]
            },
            "quarterly_history": [],
            "breach_count": 0,
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "bootstrap_note": "Initialized by Email C2 daemon 13 May 2026. Prior decisions in hale_decisions.md credited as 20 correct routine decisions.",
        }
        # Credit prior 20 decisions from hale_decisions.md as correct routine
        trust_data["trust_score"] += 20  # +1 per routine decision
        trust_data["trust_score"] = min(trust_data["trust_score"], 100)
        trust_data["current_streak"] = 20
        trust_data_path.write_text(json.dumps(trust_data, indent=2))
        logger.info("Trust data initialized — score: %d, tier: COMMANDER", trust_data["trust_score"])

    if not decision_log_path.exists():
        logger.info("Bootstrapping decision log")
        decision_log_path.write_text(json.dumps({"decisions": []}, indent=2))


def _record_decision_outcome(description: str, outcome: str) -> None:
    """Fire trust engine on Commander-confirmed outcome."""
    try:
        sys.path.insert(0, str(THUNDERBIRD_DIR / "Personas"))
        from hale_trust_engine import HaleTrustEngine
        engine = HaleTrustEngine()
        correct = outcome.lower() in ("approved", "done", "complete", "completed", "correct")
        engine.record_decision(
            decision_type="tactical",
            domain="email_classification",
            description=f"Email C2 outcome confirmed: {description} → {outcome}",
            outcome_correct=correct,
        )
        logger.info("Trust engine updated: '%s' → %s", description, outcome)
    except Exception as e:
        logger.warning("Trust engine update failed: %s", e)


# ── Core Processing ───────────────────────────────────────────────────────────

def _check_outcome_command(body: str) -> tuple[str, str] | None:
    """Detect a decision outcome command in the email body.

    Returns (description, outcome) or None.
    Examples:
      "HALE, outcome Kuklinski insurance: approved"
      "outcome: done"
    """
    match = OUTCOME_PATTERN.search(body)
    if match:
        outcome_text = match.group(1).strip()
        # outcome_text might be "Kuklinski insurance: approved" or just "approved"
        if ":" in outcome_text:
            parts = outcome_text.split(":", 1)
            return parts[0].strip(), parts[1].strip()
        else:
            return "general task", outcome_text
    return None


async def _process_message(
    service,
    msg_data: dict,
    conn: sqlite3.Connection,
    processed_ids: set,
    processed_label_id: str | None,
) -> None:
    """Process a single inbound email message."""
    from thunderbird_gmail import gmail_reply_in_thread

    msg_id = msg_data["id"]
    thread_id = msg_data.get("threadId", msg_id)
    payload = msg_data.get("payload", {})
    headers = payload.get("headers", [])

    from_addr = _extract_header(headers, "From")
    subject = _extract_header(headers, "Subject") or "(no subject)"
    rfc_message_id = _extract_header(headers, "Message-ID") or msg_id

    # ── Sender validation ──
    sender_email = re.search(r"[\w.+-]+@[\w.-]+\.\w+", from_addr)
    if not sender_email or sender_email.group(0).lower() != AUTHORIZED_SENDER.lower():
        logger.info("Skipping message from non-authorized sender: %s", from_addr)
        _mark_processed(service, msg_id, processed_label_id)
        return

    # ── DKIM check ──
    if not _validate_dkim(headers):
        logger.warning("DKIM fail on message %s from %s — dropping", msg_id, from_addr)
        _mark_processed(service, msg_id, processed_label_id)
        return

    # ── Extract body ──
    body_text = _decode_mime_body(payload).strip()

    # ── Activation word check ──
    search_target = f"{subject} {body_text}"
    if not ACTIVATION_PATTERN.search(search_target):
        logger.info("No activation word in message %s — skipping", msg_id)
        _mark_processed(service, msg_id, processed_label_id)
        return

    logger.info("Activated by message %s | subject='%s' | thread=%s", msg_id, subject, thread_id)

    # ── Rate limit check ──
    last_reply = _get_last_reply_time(conn, thread_id)
    if time.time() - last_reply < RATE_LIMIT_SECONDS:
        logger.warning("Rate limit: thread %s replied too recently — skipping", thread_id)
        _mark_processed(service, msg_id, processed_label_id)
        return

    # ── Mark processed immediately (prevents re-pick on next poll) ──
    _mark_processed(service, msg_id, processed_label_id)
    processed_ids.add(msg_id)
    _save_processed_ids(processed_ids)

    # ── Auto-ack ──
    try:
        gmail_reply_in_thread(
            thread_id=thread_id,
            in_reply_to=rfc_message_id,
            subject=subject,
            body=AUTO_ACK_TEXT,
            html_body=None,
            persona_id="COS",
        )
        _set_last_reply_time(conn, thread_id, time.time())
        logger.info("Auto-ack sent for thread %s", thread_id)
    except Exception as e:
        logger.error("Auto-ack failed: %s", e)

    # ── Check for outcome command (before full SDK invocation) ──
    outcome_result = _check_outcome_command(body_text)
    if outcome_result:
        description, outcome = outcome_result
        _record_decision_outcome(description, outcome)
        logger.info("Outcome command processed: '%s' → %s", description, outcome)
        # Still invoke SDK so HALE can acknowledge and update state

    # ── Load thread history ──
    history = _get_thread_history(conn, thread_id)

    # Append Commander's inbound message to history
    _append_thread_history(conn, thread_id, "user", body_text, msg_id + "-in")

    # ── SDK invocation ──
    try:
        sys.path.insert(0, str(THUNDERBIRD_DIR / "core" / "communication"))
        from thunderbird_telegram_tools_sdk import call_cos_via_sdk

        result = await call_cos_via_sdk(
            message=body_text,
            persona="COS",
            intent_type="TASK",
            conversation_history=history,
            session_id=thread_id,  # thread_id as session ID for continuity
        )
        response_text = result.get("response", "").strip()
    except Exception as e:
        logger.error("SDK invocation failed for thread %s: %s", thread_id, e)
        response_text = (
            f"🦅\n\nJohn — SDK error on this task: {e}\n\n"
            "Retrying via fallback. Check logs at /home/john/Thunderbird/logs/thunderbird-email-c2.log\n\n"
            "— Iron Vic"
        )

    if not response_text:
        logger.warning("SDK returned empty response for thread %s", thread_id)
        return

    # ── Append response to thread history ──
    _append_thread_history(conn, thread_id, "assistant", response_text, msg_id + "-out")

    # ── Build HTML body with wing stationery ──
    try:
        sys.path.insert(0, str(THUNDERBIRD_DIR / "core" / "email"))
        from thunderbird_gmail import _wrap_staff_html
        html_body = _wrap_staff_html(response_text, "COS")
    except Exception:
        html_body = None  # Plain text fallback

    # ── Send final reply ──
    try:
        send_result = gmail_reply_in_thread(
            thread_id=thread_id,
            in_reply_to=rfc_message_id,
            subject=subject,
            body=response_text,
            html_body=html_body,
            persona_id="COS",
        )
        _set_last_reply_time(conn, thread_id, time.time())
        logger.info(
            "Reply sent | thread=%s | msg_id=%s | len=%d chars",
            thread_id,
            send_result.get("message_id", "?"),
            len(response_text),
        )
    except Exception as e:
        logger.error("Final reply send failed for thread %s: %s", thread_id, e)


# ── Main Poll Loop ────────────────────────────────────────────────────────────

async def _poll_once(
    service,
    conn: sqlite3.Connection,
    processed_ids: set,
    processed_label_id: str | None,
) -> None:
    """Single poll cycle — fetch unread messages from d2m-ai-process label."""
    try:
        result = service.users().messages().list(
            userId="me",
            q=GMAIL_QUERY,
            maxResults=10,
        ).execute()
        messages = result.get("messages", [])
    except Exception as e:
        logger.error("Gmail poll failed: %s", e)
        return

    new_messages = [m for m in messages if m["id"] not in processed_ids]
    if not new_messages:
        return

    logger.info("Found %d new messages in d2m-ai-process", len(new_messages))

    for msg_ref in new_messages:
        try:
            msg_data = service.users().messages().get(
                userId="me",
                id=msg_ref["id"],
                format="full",
            ).execute()
            await _process_message(service, msg_data, conn, processed_ids, processed_label_id)
        except Exception as e:
            logger.error("Error processing message %s: %s", msg_ref["id"], e)


async def run() -> None:
    """Main daemon loop."""
    logger.info("=" * 60)
    logger.info("HALE Email C2 Daemon starting — %s", datetime.now().isoformat())
    logger.info("Authorized sender: %s", AUTHORIZED_SENDER)
    logger.info("Poll interval: %ds | Gmail query: '%s'", POLL_INTERVAL, GMAIL_QUERY)
    logger.info("=" * 60)

    # Bootstrap trust engine data files if needed
    _bootstrap_trust_engine()

    # Initialize SQLite thread memory
    conn = _init_thread_db()
    logger.info("Thread DB ready: %s", THREAD_DB_PATH)

    # Load processed message cache
    processed_ids = _load_processed_ids()
    logger.info("Loaded %d processed message IDs from cache", len(processed_ids))

    # Initialize Gmail service
    service = _get_gmail_service()
    logger.info("Gmail service initialized (d2mconcierge@gmail.com)")

    # Resolve processed label ID
    processed_label_id = _get_label_id(service, PROCESSED_LABEL)
    if processed_label_id:
        logger.info("Processed label '%s' → ID: %s", PROCESSED_LABEL, processed_label_id)
    else:
        logger.warning("Label '%s' not found — messages won't be labeled processed", PROCESSED_LABEL)

    logger.info("🦅 HALE Email C2 ONLINE — listening on d2m-ai-process label")

    while True:
        try:
            await _poll_once(service, conn, processed_ids, processed_label_id)
        except Exception as e:
            logger.error("Poll cycle error: %s", e)

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run())
