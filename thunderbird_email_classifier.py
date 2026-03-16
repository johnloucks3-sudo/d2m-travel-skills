"""
Thunderbird Email Classifier
=============================

Auto-classifies incoming Gmail messages labeled THUNDERBIRD-Process using
Groq LLM and routes them to the appropriate client dossier.

Flow:
  1. Search Gmail for label:THUNDERBIRD-Process
  2. For each unprocessed message, read full content
  3. Call Groq (llama-3.1-8b-instant) to classify: category, client, priority, action
  4. Append summary to matching client dossier EMAIL LOG section
  5. If action needed, append to dossier OPEN ACTION ITEMS
  6. Relabel message THUNDERBIRD-Processed (remove Process label)
  7. Track processed IDs in email_classifier_state.json

Standalone:  python3 thunderbird_email_classifier.py
Scheduler:   from thunderbird_email_classifier import classify_and_route

Dependencies: thunderbird_gmail.py (OAuth Gmail), requests (Groq API)
"""

import json
import logging
import re
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests
from googleapiclient.errors import HttpError

from thunderbird_gmail import _get_gmail_service, _decode_body, _extract_headers

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
DOSSIERS_DIR = THUNDERBIRD_DIR / "Dossiers"
STATE_FILE = THUNDERBIRD_DIR / "email_classifier_state.json"

# Gmail labels
INBOX_LABEL = "THUNDERBIRD-Process"
DONE_LABEL = "THUNDERBIRD-Processed"

# Groq — mirrors thunderbird_personas.py pattern
GROQ_API_KEY = "***REMOVED-SECRET***"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

# Google Sheets (Booking Master)
SHEETS_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)


# ---------------------------------------------------------------------------
# State persistence — avoid reprocessing
# ---------------------------------------------------------------------------

def _load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"processed_ids": [], "last_run": None, "stats": {"total": 0, "routed": 0, "unmatched": 0}}


def _save_state(state: Dict[str, Any]):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Dossier discovery — build client map from filenames
# ---------------------------------------------------------------------------

def _build_client_map() -> Dict[str, Path]:
    """Parse dossier filenames into a lookup of lowercase last-name -> Path.

    Filenames follow pattern: LastName_Supplier_BookingID.md
    or LastName_Supplier_Destination.md
    """
    client_map: Dict[str, Path] = {}
    if not DOSSIERS_DIR.is_dir():
        logger.warning(f"Dossiers directory not found: {DOSSIERS_DIR}")
        return client_map

    for f in DOSSIERS_DIR.glob("*.md"):
        # First segment before underscore is the client last name
        parts = f.stem.split("_")
        if parts:
            last_name = parts[0].lower()
            client_map[last_name] = f
    return client_map


def _client_names_for_prompt(client_map: Dict[str, Path]) -> str:
    """Format known client names for the LLM prompt."""
    names = sorted(client_map.keys())
    return ", ".join(names) if names else "(no dossiers found)"


# ---------------------------------------------------------------------------
# Gmail label helpers
# ---------------------------------------------------------------------------

def _get_or_create_label(service, label_name: str) -> str:
    """Return the label ID for label_name, creating it if necessary."""
    results = service.users().labels().list(userId="me").execute()
    for label in results.get("labels", []):
        if label["name"] == label_name:
            return label["id"]

    # Create the label
    body = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = service.users().labels().create(userId="me", body=body).execute()
    logger.info(f"Created Gmail label: {label_name} ({created['id']})")
    return created["id"]


def _fetch_labeled_messages(service, label_id: str, max_results: int = 50) -> List[Dict]:
    """Fetch message stubs that carry the given label."""
    results = (
        service.users()
        .messages()
        .list(userId="me", labelIds=[label_id], maxResults=max_results)
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
    headers = _extract_headers(payload.get("headers", []),
                               {"From", "To", "Subject", "Date", "Cc"})
    body = _decode_body(payload)
    # Truncate for LLM context window (raised to 30K — Claude 1M context is GA)
    if len(body) > 30000:
        body = body[:30000] + "\n... [TRUNCATED]"
    return {
        "id": msg["id"],
        "threadId": msg["threadId"],
        "labels": msg.get("labelIds", []),
        "snippet": msg.get("snippet", ""),
        "headers": headers,
        "body": body,
    }


def _relabel_message(service, msg_id: str, remove_label_id: str, add_label_id: str):
    """Remove one label and add another on a message."""
    service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={
            "removeLabelIds": [remove_label_id],
            "addLabelIds": [add_label_id],
        },
    ).execute()


# ---------------------------------------------------------------------------
# Groq classification
# ---------------------------------------------------------------------------

CLASSIFY_SYSTEM_PROMPT = """You are an email classifier for Dreams2Memories Travel, LLC, a luxury travel agency.

Given an email, return a JSON object with EXACTLY these fields:
{
  "category": one of ["booking_confirmation", "payment_receipt", "client_inquiry", "supplier_update", "tour_confirmation", "marketing", "personal", "other"],
  "client_match": lowercase last name of the matched client or null if no match,
  "priority": one of ["urgent", "normal", "low"],
  "action_needed": true or false,
  "suggested_action": short description of what to do (or null if no action),
  "summary": 1-2 sentence summary of the email content
}

RULES:
- "urgent" priority: payment deadlines, cancellation notices, time-sensitive booking changes, embarkation issues
- "normal" priority: booking confirmations, client questions, supplier updates requiring response
- "low" priority: marketing, newsletters, informational
- Match client names against the KNOWN CLIENTS list. Use fuzzy matching (e.g. "Furlow" matches "furlow"). Return null if no match.
- Return ONLY valid JSON. No markdown fences, no explanation."""


def _classify_email(email_data: Dict, known_clients: str) -> Dict[str, Any]:
    """Send email to Groq for classification. Returns parsed JSON dict."""
    headers = email_data["headers"]
    user_prompt = f"""KNOWN CLIENTS: {known_clients}

EMAIL:
From: {headers.get('From', 'unknown')}
To: {headers.get('To', 'unknown')}
Cc: {headers.get('Cc', '')}
Date: {headers.get('Date', 'unknown')}
Subject: {headers.get('Subject', '(no subject)')}

Body:
{email_data['body']}"""

    try:
        resp = requests.post(
            GROQ_URL,
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 300,
                "temperature": 0.1,
            },
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown fences if the model added them
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        return json.loads(raw)

    except json.JSONDecodeError as e:
        logger.error(f"Groq returned invalid JSON: {e}\nRaw: {raw}")
        return {
            "category": "other",
            "client_match": None,
            "priority": "normal",
            "action_needed": False,
            "suggested_action": None,
            "summary": f"Classification failed — raw: {raw[:200]}",
        }
    except Exception as e:
        logger.error(f"Groq classification failed: {e}")
        return {
            "category": "other",
            "client_match": None,
            "priority": "normal",
            "action_needed": False,
            "suggested_action": None,
            "summary": f"Classification error: {e}",
        }


# ---------------------------------------------------------------------------
# Dossier writer
# ---------------------------------------------------------------------------

def _append_to_dossier(dossier_path: Path, classification: Dict, email_data: Dict):
    """Append an email summary to the dossier's EMAIL LOG and optionally OPEN ACTION ITEMS."""
    headers = email_data["headers"]
    date_str = headers.get("Date", "unknown date")
    # Try to parse into short format
    try:
        dt = _parse_email_date(date_str)
        short_date = dt.strftime("%b %d")
    except Exception:
        short_date = date_str[:10]

    sender = headers.get("From", "unknown")
    # Extract just the name/email before angle bracket
    sender_short = sender.split("<")[0].strip().strip('"') or sender
    subject = headers.get("Subject", "(no subject)")
    summary = classification.get("summary", "")
    priority_tag = ""
    if classification.get("priority") == "urgent":
        priority_tag = " **[URGENT]**"

    log_entry = f"\n**{short_date} — {sender_short}**{priority_tag} (Re: {subject})\n> {summary}\n"

    content = dossier_path.read_text(encoding="utf-8")

    # Insert into EMAIL LOG section (before the next --- or ### section)
    email_log_pattern = r"(### EMAIL LOG[^\n]*\n)"
    match = re.search(email_log_pattern, content)
    if match:
        # Find the end of the existing log entries — look for next section marker
        insert_pos = match.end()
        # Walk forward past existing log entries to find the next section
        rest = content[insert_pos:]
        next_section = re.search(r"\n---\n|\n### ", rest)
        if next_section:
            insert_pos = insert_pos + next_section.start()
        else:
            insert_pos = len(content)
        content = content[:insert_pos] + log_entry + content[insert_pos:]
    else:
        # No EMAIL LOG section — append at end
        content += f"\n\n### EMAIL LOG\n{log_entry}"

    # If action needed, append to OPEN ACTION ITEMS
    if classification.get("action_needed") and classification.get("suggested_action"):
        action_text = classification["suggested_action"]
        action_entry = f"\n- [ ] {action_text} (auto-classified {short_date})"

        action_pattern = r"(### OPEN ACTION ITEMS\n)"
        amatch = re.search(action_pattern, content)
        if amatch:
            # Find the end of the existing items list
            insert_pos = amatch.end()
            rest = content[insert_pos:]
            # Walk past numbered/bulleted items
            lines = rest.split("\n")
            offset = 0
            for line in lines:
                stripped = line.strip()
                if stripped.startswith(("- [", "* [")) or re.match(r"^\d+\.\s", stripped):
                    offset += len(line) + 1
                else:
                    break
            insert_pos += offset
            content = content[:insert_pos] + action_entry + "\n" + content[insert_pos:]
        else:
            content += f"\n\n### OPEN ACTION ITEMS{action_entry}\n"

    dossier_path.write_text(content, encoding="utf-8")
    logger.info(f"  -> Appended to dossier: {dossier_path.name}")


def _parse_email_date(date_str: str) -> datetime:
    """Best-effort parse of email Date header."""
    # Strip timezone abbreviation at the end (e.g. " (PST)")
    cleaned = re.sub(r"\s*\([A-Z]+\)\s*$", "", date_str)
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S",
        "%d %b %Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def classify_and_route(
    label: str = INBOX_LABEL,
    max_messages: int = 50,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Search Gmail for the processing label, classify each message via Groq,
    route to client dossiers, and relabel as processed.

    Args:
        label: Gmail label to search (default THUNDERBIRD-Process)
        max_messages: Max emails to process per run
        dry_run: If True, classify but don't modify dossiers or labels

    Returns:
        Summary dict with counts and per-message results
    """
    logger.info(f"=== Email Classifier starting — label: {label}, dry_run: {dry_run} ===")

    # Load state
    state = _load_state()
    processed_ids = set(state.get("processed_ids", []))

    # Build client map from dossiers
    client_map = _build_client_map()
    known_clients = _client_names_for_prompt(client_map)
    logger.info(f"Known clients: {known_clients}")

    # Connect to Gmail
    service = _get_gmail_service()

    # Get/create labels
    process_label_id = _get_or_create_label(service, label)
    done_label_id = _get_or_create_label(service, DONE_LABEL)

    # Fetch messages
    message_stubs = _fetch_labeled_messages(service, process_label_id, max_messages)
    logger.info(f"Found {len(message_stubs)} messages with label '{label}'")

    results = []
    routed_count = 0
    skipped_count = 0
    unmatched_count = 0

    for stub in message_stubs:
        msg_id = stub["id"]

        # Skip already processed
        if msg_id in processed_ids:
            logger.info(f"  Skipping already-processed: {msg_id}")
            skipped_count += 1
            continue

        # Read full message
        try:
            email_data = _read_full_message(service, msg_id)
        except HttpError as e:
            logger.error(f"  Failed to read message {msg_id}: {e}")
            results.append({"id": msg_id, "status": "read_error", "error": str(e)})
            continue

        subject = email_data["headers"].get("Subject", "(no subject)")
        sender = email_data["headers"].get("From", "unknown")
        logger.info(f"  Processing: {subject[:60]} from {sender[:40]}")

        # Classify via Groq
        classification = _classify_email(email_data, known_clients)
        logger.info(
            f"    Category: {classification.get('category')} | "
            f"Client: {classification.get('client_match')} | "
            f"Priority: {classification.get('priority')} | "
            f"Action: {classification.get('action_needed')}"
        )

        # Route to dossier
        client_key = classification.get("client_match")
        dossier_path = client_map.get(client_key) if client_key else None
        routed = False

        if dossier_path and dossier_path.exists():
            if not dry_run:
                _append_to_dossier(dossier_path, classification, email_data)
            routed = True
            routed_count += 1
        else:
            if client_key:
                logger.warning(f"    Client '{client_key}' not found in dossiers")
            unmatched_count += 1

        # Relabel in Gmail
        if not dry_run:
            try:
                _relabel_message(service, msg_id, process_label_id, done_label_id)
                logger.info(f"    Relabeled: {label} -> {DONE_LABEL}")
            except HttpError as e:
                logger.error(f"    Relabel failed for {msg_id}: {e}")

        # Track as processed
        processed_ids.add(msg_id)

        results.append({
            "id": msg_id,
            "subject": subject,
            "from": sender,
            "classification": classification,
            "routed_to": dossier_path.name if dossier_path and routed else None,
            "status": "routed" if routed else "unmatched",
        })

    # Save state
    state["processed_ids"] = list(processed_ids)
    state["last_run"] = datetime.now().isoformat()
    state["stats"]["total"] += len(results)
    state["stats"]["routed"] += routed_count
    state["stats"]["unmatched"] += unmatched_count
    if not dry_run:
        _save_state(state)

    summary = {
        "status": "success",
        "dry_run": dry_run,
        "label": label,
        "found": len(message_stubs),
        "processed": len(results),
        "skipped": skipped_count,
        "routed": routed_count,
        "unmatched": unmatched_count,
        "results": results,
    }

    logger.info(
        f"=== Classifier done — processed: {len(results)}, "
        f"routed: {routed_count}, unmatched: {unmatched_count}, "
        f"skipped: {skipped_count} ==="
    )
    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv
    label = INBOX_LABEL
    for arg in sys.argv[1:]:
        if arg.startswith("--label="):
            label = arg.split("=", 1)[1]

    result = classify_and_route(label=label, dry_run=dry_run)
    print(json.dumps(result, indent=2, default=str))
