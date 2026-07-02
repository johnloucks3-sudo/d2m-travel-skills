#!/usr/bin/env python3
"""
email_ingestion_pipeline.py
============================
Dreams2Memories Travel, LLC — Thunderbird Wing

Fetches unread emails from johnloucks3@gmail.com (last 24h), classifies them,
and routes each to the appropriate handler:

  booking_confirmation → extracts booking ref + cruise line + amount → output/email_ingestion_log.json
  client_inquiry       → drafts a routing ticket to the mission board
  supplier_intel       → saves to intel/email_intel/<date>_<subject>.md
  invoice              → logged (financial category from hale_inbox_tools)
  spam/noise           → counted, not stored
  internal_wing        → counted, not stored

Outputs:
  output/email_ingestion_report.json  — summary by category per run
  output/email_ingestion_log.json     — cumulative booking/client events

Usage:
  python3 scripts/email_ingestion_pipeline.py
  python3 scripts/email_ingestion_pipeline.py --dry-run
  python3 scripts/email_ingestion_pipeline.py --hours 48

Author: Sterling (A7) — MISSION-431 · 2026-06-24
"""

import argparse
import base64
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
THUNDERBIRD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(THUNDERBIRD_DIR))
sys.path.insert(0, str(THUNDERBIRD_DIR / "api"))

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = THUNDERBIRD_DIR / "logs" / "email_ingestion_pipeline.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Output paths ──────────────────────────────────────────────────────────────
OUTPUT_DIR = THUNDERBIRD_DIR / "output"
INTEL_DIR = THUNDERBIRD_DIR / "intel" / "email_intel"
INGESTION_LOG = OUTPUT_DIR / "email_ingestion_log.json"
INGESTION_REPORT = OUTPUT_DIR / "email_ingestion_report.json"
MISSION_BOARD_PATH = THUNDERBIRD_DIR / "OpsCenter" / "mission_board.json"

# ── Gmail credentials ─────────────────────────────────────────────────────────
TOKEN_FILE = THUNDERBIRD_DIR / "creds" / "johnloucks3_token.json"
OAUTH_CREDS_FILE = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
USER_EMAIL = "johnloucks3@gmail.com"

# ── Wing sender domain (internal) ─────────────────────────────────────────────
WING_DOMAINS = {"d2mluxury.quest", "gmail.com"}
WING_ADDRESSES = {
    "d2mconcierge@gmail.com",
    "johnloucks3@gmail.com",
    "concierge@d2mluxury.quest",
}

# ── Booking extraction patterns ───────────────────────────────────────────────
_BOOKING_REF_RE = re.compile(
    r"\b(?:booking|reservation|confirmation|ref(?:erence)?|booking\s*#?)[:\s#]*([A-Z0-9]{5,12})\b",
    re.IGNORECASE,
)
_AMOUNT_RE = re.compile(r"\$\s?([\d,]+(?:\.\d{2})?)")
_CRUISE_LINES = [
    "Silversea", "Regent", "Viking", "Princess", "Celebrity", "Royal Caribbean",
    "Cunard", "Oceania", "Seabourn", "Holland America", "Carnival", "NCL",
    "Norwegian", "MSC", "Crystal", "Explora", "Scenic", "Scenic Eclipse",
]


# ── Gmail service ─────────────────────────────────────────────────────────────

def _build_gmail_service():
    """Build authenticated Gmail service using johnloucks3 token."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not TOKEN_FILE.exists():
        raise FileNotFoundError(f"Token not found: {TOKEN_FILE}")

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        log.info("Refreshing expired johnloucks3 token")
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ── Classifier ────────────────────────────────────────────────────────────────
#
# MISSION-431 DEFECT FIX (Sterling A7): the original classifier ended with a
# `return "client_inquiry"` DEFAULT. Any email that missed the narrow keyword
# lists fell through to client_inquiry → a P1 mission ticket + an auto-drafted
# junk reply. 326 newsletters/promos/self-sends/alerts polluted the board.
#
# New contract:
#   * Default fallthrough is "other" (non-actionable) — NEVER client_inquiry.
#   * client_inquiry is returned ONLY on a positive signal:
#       (a) sender is a KNOWN client (reuse thunderbird_commander_inbox tiering), OR
#       (b) client-inquiry body/subject signals present AND sender is NOT bulk noise.
#   * Bulk/newsletter/promo/noreply senders → "spam" via the canonical
#     _NOISE_PATTERNS regex (imported, single source of truth).
#
# We import — never reinvent — the noise regex + client tiering from the
# commander inbox module (read-only reuse).

# Positive-signal keyword list ported from classify_email() in
# core/email/thunderbird_commander_inbox.py (client_inquiry_signals, ~638-662).
_CLIENT_INQUIRY_SIGNALS = (
    "i want to book",
    "we are interested in",
    "looking for a quote",
    "can you help with",
    "do you have availability",
    "please send me",
    "i need a hotel",
    "we need flights",
    "our family wants to",
    "hello dani",
    "dear dani",
    "hi john",
    "dear john",
    "questions about",
    "can you recommend",
    "looking for recommendations",
    "what options",
    "would like to discuss",
    "can we schedule a call",
    "schedule a time",
)

# Import canonical noise regex + client tiering (read-only reuse — do NOT modify
# thunderbird_commander_inbox.py). CLIENT_ADDRESSES must be populated once before
# _determine_email_tier can report "CLIENT", so we prime it at import time.
try:
    from core.email.thunderbird_commander_inbox import (  # type: ignore
        _NOISE_PATTERNS,
        _determine_email_tier,
        _populate_client_addresses,
    )
    try:
        _populate_client_addresses()
    except Exception as e:  # pragma: no cover — defensive
        log.debug("client address population skipped: %s", e)
except Exception as e:  # pragma: no cover — module unavailable
    log.debug("commander inbox helpers unavailable: %s — noise/client reuse disabled", e)
    _NOISE_PATTERNS = re.compile(r"(?:no-?reply|noreply|newsletter|unsubscribe)", re.IGNORECASE)

    def _determine_email_tier(sender: str) -> str:  # type: ignore
        return "INTAKE"


def _is_noise_sender(from_lower: str) -> bool:
    """True if the sender matches the canonical bulk/newsletter/noreply regex."""
    try:
        return bool(_NOISE_PATTERNS.search(from_lower))
    except Exception:
        return False


def _classify_email(from_addr: str, subject: str, snippet: str,
                    registry: dict = None, use_ai: bool = False) -> str:
    """
    Classify an inbound email — delegates to the ZERO-MODEL rules_classifier.

    ELON incubator brief (2026-07-01): the live per-email Gemini call is REMOVED
    from the default/background path. rules_classifier.classify() is PURE (no
    network, no model). `registry` is loaded ONCE per run and threaded in here.

    Categories map to this pipeline's handlers via _map_category():
      financial → invoice handler; supplier_intel → supplier handler; etc.

    `use_ai=True` (CLI --ai) routes ONLY-`other` messages through the on-demand
    deep_classify() path. Off by default → background runs make ZERO model calls.
    """
    from core.email.rules_classifier import classify, deep_classify  # type: ignore

    cat = classify(from_addr, subject, snippet, registry=registry)
    if use_ai and cat == "other":
        cat = deep_classify(from_addr, subject, snippet)  # ON-DEMAND ONLY
    return _map_category(cat)


# rules_classifier categories → this pipeline's handler categories.
_CATEGORY_MAP = {
    "financial": "invoice",            # → _handle_invoice
    "supplier_intel": "supplier_intel",
    "booking_confirmation": "booking_confirmation",
    "client_inquiry": "client_inquiry",
    "internal_wing": "internal_wing",
    "commander_directive": "other",    # count-only (no mission)
    "direct_command": "other",         # count-only
    "intel": "other",                  # count-only
    "spam": "spam",
    "other": "other",
}


def _map_category(cat: str) -> str:
    """Map a rules_classifier category into the pipeline's handler categories."""
    return _CATEGORY_MAP.get(cat, "other")


# ── Handlers ──────────────────────────────────────────────────────────────────

def _extract_booking_data(subject: str, body: str, from_addr: str) -> dict:
    """Extract booking ref, cruise line, and amount from email text."""
    ref_match = _BOOKING_REF_RE.search(body) or _BOOKING_REF_RE.search(subject)
    booking_ref = ref_match.group(1) if ref_match else "UNKNOWN"

    cruise_line = "Unknown"
    combined = (subject + " " + body + " " + from_addr).lower()
    for cl in _CRUISE_LINES:
        if cl.lower() in combined:
            cruise_line = cl
            break

    amounts = _AMOUNT_RE.findall(body)
    amount = amounts[0].replace(",", "") if amounts else None

    return {
        "booking_ref": booking_ref,
        "cruise_line": cruise_line,
        "amount": float(amount) if amount else None,
    }


def _handle_booking_confirmation(msg: dict, body: str, dry_run: bool) -> dict:
    data = _extract_booking_data(msg["subject"], body, msg["from"])
    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "category": "booking_confirmation",
        "message_id": msg["id"],
        "from": msg["from"],
        "subject": msg["subject"],
        **data,
    }
    if not dry_run:
        _append_ingestion_log(log_entry)
    log.info("  BOOKING: ref=%s cruise=%s amount=%s", data["booking_ref"], data["cruise_line"], data["amount"])
    return log_entry


def _handle_client_inquiry(msg: dict, dry_run: bool) -> dict:
    """Draft a mission board routing ticket for client inquiries."""
    ticket = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "category": "client_inquiry",
        "message_id": msg["id"],
        "from": msg["from"],
        "subject": msg["subject"],
        "action": "ROUTE_TO_MISSION_BOARD",
        "mission_title": f"Client inquiry: {msg['subject'][:60]}",
        "description": f"Inbound client email from {msg['from']} — subject: {msg['subject']}",
    }
    if not dry_run:
        _append_ingestion_log(ticket)
        _create_mission_board_ticket(ticket)
    log.info("  CLIENT INQUIRY: from=%s subject=%s", msg["from"], msg["subject"][:60])
    return ticket


def _handle_supplier_intel(msg: dict, body: str, dry_run: bool) -> str:
    """Save supplier/vendor email to intel/email_intel/ with date-stamped filename."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_subject = re.sub(r"[^\w\s-]", "", msg["subject"])[:60].strip().replace(" ", "_")
    filename = f"{date_str}_{safe_subject}.md"
    filepath = INTEL_DIR / filename

    content = f"""# Supplier Intel — {msg['subject']}

**Date:** {date_str}
**From:** {msg['from']}
**Subject:** {msg['subject']}
**Message ID:** {msg['id']}

---

{body[:4000]}
"""
    if not dry_run:
        INTEL_DIR.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
    log.info("  SUPPLIER INTEL: saved to intel/email_intel/%s", filename)
    return str(filepath)


def _handle_invoice(msg: dict, body: str, dry_run: bool) -> dict:
    """Log financial/invoice emails."""
    data = _extract_booking_data(msg["subject"], body, msg["from"])
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "category": "invoice",
        "message_id": msg["id"],
        "from": msg["from"],
        "subject": msg["subject"],
        **data,
    }
    if not dry_run:
        _append_ingestion_log(entry)
    log.info("  INVOICE: from=%s amount=%s", msg["from"], data["amount"])
    return entry


# ── Storage helpers ───────────────────────────────────────────────────────────

def _append_ingestion_log(entry: dict):
    """Append a single event to the cumulative ingestion log (JSON lines)."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    existing = []
    if INGESTION_LOG.exists():
        try:
            existing = json.loads(INGESTION_LOG.read_text())
        except Exception:
            existing = []
    existing.append(entry)
    INGESTION_LOG.write_text(json.dumps(existing, indent=2))


def _create_mission_board_ticket(ticket: dict):
    """Add a P1 mission to the board for client inquiries."""
    try:
        mb = json.loads(MISSION_BOARD_PATH.read_text())
        missions = mb.get("missions", [])

        # Generate next mission ID
        numeric_ids = [
            int(re.search(r"\d+", m["id"]).group())
            for m in missions
            if re.search(r"\d+", m.get("id", ""))
        ]
        next_id = max(numeric_ids, default=400) + 1

        new_mission = {
            "id": f"MISSION-{next_id}",
            "title": ticket["mission_title"],
            "status": "active",
            "priority": "P1",
            "assigned_to": "Hale",
            "description": ticket["description"],
            "created_at": ticket["ts"],
            "updated_at": ticket["ts"],
            "logs": [f"[{ticket['ts']}] Auto-created by email_ingestion_pipeline — message_id={ticket['message_id']}"],
        }
        missions.append(new_mission)
        mb["missions"] = missions
        mb["last_updated"] = datetime.now(timezone.utc).isoformat()
        MISSION_BOARD_PATH.write_text(json.dumps(mb, indent=2))
        log.info("  → Created %s on mission board", new_mission["id"])
    except Exception as e:
        log.error("Failed to create mission board ticket: %s", e)


# ── Gmail fetch ───────────────────────────────────────────────────────────────

def _get_message_body(svc, msg_id: str) -> str:
    """Fetch and decode plain-text body from a Gmail message."""
    try:
        msg = svc.users().messages().get(userId="me", id=msg_id, format="full").execute()
        payload = msg.get("payload", {})

        def _extract(part):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            for sub in part.get("parts", []):
                result = _extract(sub)
                if result:
                    return result
            return ""

        return _extract(payload)
    except Exception as e:
        log.debug("Could not fetch body for %s: %s", msg_id, e)
        return ""


def _fetch_unread_messages(svc, hours: int) -> list:
    """Return list of message metadata dicts for unread emails in the last N hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    # Gmail uses Unix epoch seconds in after: query
    after_ts = int(cutoff.timestamp())
    query = f"is:unread after:{after_ts}"

    results = svc.users().messages().list(userId="me", q=query, maxResults=50).execute()
    message_refs = results.get("messages", [])

    messages = []
    for ref in message_refs:
        try:
            m = svc.users().messages().get(userId="me", id=ref["id"], format="metadata",
                                           metadataHeaders=["From", "Subject", "Date"]).execute()
            headers = {h["name"]: h["value"] for h in m.get("payload", {}).get("headers", [])}
            messages.append({
                "id": ref["id"],
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", "(no subject)"),
                "date": headers.get("Date", ""),
                "snippet": m.get("snippet", ""),
            })
        except Exception as e:
            log.warning("Could not fetch metadata for %s: %s", ref["id"], e)

    return messages


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(hours: int = 24, dry_run: bool = False, use_ai: bool = False) -> dict:
    """
    Fetch, classify, and route unread emails from johnloucks3 (last N hours).
    Returns the summary report dict.

    The client/supplier registry is loaded ONCE here (cache-backed, no network in
    the classify hot path) and threaded into every classify() call. use_ai only
    affects `other` messages and is OFF by default (zero model calls background).
    """
    mode = "DRY-RUN" if dry_run else "LIVE"
    log.info("=== EMAIL INGESTION PIPELINE [%s] — last %dh (ai=%s) ===", mode, hours, use_ai)

    # Load registry ONCE per run (cache-backed; refreshes from EARA only if stale).
    try:
        from core.email.rules_classifier import load_registry  # type: ignore
        registry = load_registry()
        log.info("Registry: %d clients, %d suppliers",
                 len(registry["client_emails"]), len(registry["supplier_domains"]))
    except Exception as e:
        log.warning("Registry load failed (%s) — classifier uses its own fallback", e)
        registry = None

    svc = _build_gmail_service()
    messages = _fetch_unread_messages(svc, hours)
    log.info("Fetched %d unread messages", len(messages))

    counts = {
        "booking_confirmation": 0,
        "client_inquiry": 0,
        "supplier_intel": 0,
        "invoice": 0,
        "internal_wing": 0,
        "spam": 0,
        "other": 0,
    }
    processed = []

    for msg in messages:
        category = _classify_email(msg["from"], msg["subject"], msg["snippet"],
                                   registry=registry, use_ai=use_ai)
        log.info("[%s] %s | %s", category.upper(), msg["from"][:40], msg["subject"][:60])

        counts[category] = counts.get(category, 0) + 1

        if category == "booking_confirmation":
            body = _get_message_body(svc, msg["id"])
            result = _handle_booking_confirmation(msg, body, dry_run)
            processed.append(result)

        elif category == "client_inquiry":
            result = _handle_client_inquiry(msg, dry_run)
            processed.append(result)

        elif category == "supplier_intel":
            body = _get_message_body(svc, msg["id"])
            filepath = _handle_supplier_intel(msg, body, dry_run)
            processed.append({"category": "supplier_intel", "file": filepath, "subject": msg["subject"]})

        elif category == "invoice":
            body = _get_message_body(svc, msg["id"])
            result = _handle_invoice(msg, body, dry_run)
            processed.append(result)

        # internal_wing, spam, and other: count only — no mission, no storage

    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "hours_scanned": hours,
        "total_messages": len(messages),
        "counts": counts,
        "processed_events": len(processed),
    }

    if not dry_run:
        OUTPUT_DIR.mkdir(exist_ok=True)
        INGESTION_REPORT.write_text(json.dumps(report, indent=2))
        log.info("Report written to %s", INGESTION_REPORT)
    else:
        log.info("DRY-RUN report (not written):\n%s", json.dumps(report, indent=2))

    log.info("=== DONE — %d messages processed | %s ===", len(messages), counts)
    return report


# ── Mission board completion helper ──────────────────────────────────────────

def _mark_mission_431_complete():
    """Update MISSION-431 to completed in mission_board.json."""
    try:
        mb = json.loads(MISSION_BOARD_PATH.read_text())
        for m in mb.get("missions", []):
            if m.get("id") == "MISSION-431":
                m["status"] = "completed"
                m["updated_at"] = datetime.now(timezone.utc).isoformat()
                m.setdefault("logs", []).append(
                    f"[{datetime.now(timezone.utc).isoformat()}] COMPLETED: "
                    "scripts/email_ingestion_pipeline.py built and deployed. "
                    "Systemd timer thunderbird-email-ingestion.timer runs every 4h. "
                    "Categories: booking_confirmation|client_inquiry|supplier_intel|invoice|internal_wing|spam. "
                    "Outputs: output/email_ingestion_log.json + output/email_ingestion_report.json. "
                    "Author: Sterling (A7) — MISSION-431 2026-06-24."
                )
                break
        mb["last_updated"] = datetime.now(timezone.utc).isoformat()
        MISSION_BOARD_PATH.write_text(json.dumps(mb, indent=2))
        log.info("MISSION-431 marked completed")
    except Exception as e:
        log.error("Failed to update MISSION-431: %s", e)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thunderbird Email Ingestion Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without writing files")
    parser.add_argument("--hours", type=int, default=24, help="Look-back window in hours (default: 24)")
    parser.add_argument("--ai", action="store_true",
                        help="ON-DEMAND ONLY: route only-'other'/ambiguous messages through "
                             "deep_classify (Gemini). OFF by default — background runs make ZERO model calls.")
    parser.add_argument("--mark-complete", action="store_true", help="Mark MISSION-431 complete and exit")
    args = parser.parse_args()

    if args.mark_complete:
        _mark_mission_431_complete()
        sys.exit(0)

    report = run_pipeline(hours=args.hours, dry_run=args.dry_run, use_ai=args.ai)
    print(json.dumps(report, indent=2))
