"""
Thunderbird Star Protocol v3.0
===============================

Scans Gmail for colored superstars AND self-addressed persona emails,
then routes to the appropriate D2M staff personas.

Star Mapping:
  RED_CIRCLE    -> COMMAND: Extract intent, route to action (COS)
  GREEN_CIRCLE  -> APPROVED/EXECUTE: Ship it, send it (EXEC + COS)
  BLUE_STAR     -> DRAFT REPLY: Write response in Yoda's voice (EXEC)
  YELLOW_STAR   -> Personal / ignored by system

Self-Email Routing (replaces old Green Star):
  Yoda emails himself with subject: [PERSONA] <topic>
  Examples:
    [COS] Should we push the Ely call?
    [A2] Research Michelin restaurants in Stockholm
    [STAFF] Thoughts on adding a Rome extension?
    [EXEC] Draft thank you note to Kyle

  Response is created as a Gmail draft reply on the self-email thread.

After processing, star is removed / email is marked read.

Can run as:
  - Cron job (every 15 min): python3 thunderbird_star_protocol.py --sweep
  - MCP tool: run_star_sweep
  - One-off: python3 thunderbird_star_protocol.py --sweep
"""

import base64
import json
import logging
import re
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
SWEEP_LOG = THUNDERBIRD_DIR / "star_protocol_log.json"

# Commander's personal inbox — used to search for self-addressed command emails
YODA_EMAIL = "johnloucks3@gmail.com"
# D2M ops account — all draft From headers use this (gmail_token.json is d2mconcierge)
OPS_EMAIL = "d2mconcierge@gmail.com"

# Star -> Action mapping (3 stars only — Green Star retired)
STAR_ACTIONS = {
    "RED_CIRCLE": {
        "action": "COMMAND",
        "description": "Extract intent, route to action",
        "handler": "COS",
        "persona_id": "A1",
    },
    "GREEN_CIRCLE": {
        "action": "APPROVED",
        "description": "Approved — execute, ship it, send it",
        "handler": "EXEC + COS",
        "persona_id": "A1",
    },
    "BLUE_STAR": {
        "action": "DRAFT_REPLY",
        "description": "Draft reply in Yoda's voice",
        "handler": "EXEC",
        "persona_id": "A2",
    },
}

# Ignore these — personal use
IGNORE_STARS = {"YELLOW_STAR", "STARRED", "GREEN_STAR"}

# Persona name -> ID mapping for self-email routing
PERSONA_LOOKUP = {
    "COS": "COS", "HALE": "COS", "VIC": "COS",
    "EXEC": "EXEC", "NAIA": "EXEC",
    "A1": "COS",
    "A2": "A2", "DEMBE": "A2", "WRAITH": "A2", "INTEL": "A2",
    "A3": "A3", "MOREAU": "A3", "DANI": "A3",
    "A5": "A5", "CASTILLO": "A5", "VIPER": "A5",
    "A9": "A9", "HARLAN": "A9", "SHARK": "A9",
    "A10": "A10", "IKEDA": "A10", "TOMMY": "A10",
    "CH": "CH", "PADRE": "CH", "WASHINGTON": "CH", "CHAPLAIN": "CH",
    "A12": "A12", "ELON": "A12",
    "STAFF": "ALL", "ALL": "ALL", "TEAM": "ALL", "EVERYONE": "ALL",
}

# All active persona IDs for full staff meeting
ALL_PERSONA_IDS = ["COS", "EXEC", "A2", "A3", "A5", "A9", "A10", "CH", "A12"]


def _get_gmail_service():
    """Get cached Gmail service from thunderbird_gmail module."""
    from thunderbird_gmail import _get_gmail_service as _get_svc
    return _get_svc()


def _get_star_type(label_ids: List[str]) -> Optional[str]:
    """Extract the actionable star type from a message's labelIds."""
    for label in label_ids:
        if label in STAR_ACTIONS:
            return label
    return None


def _parse_persona_tag(subject: str) -> Optional[tuple]:
    """Parse [PERSONA] tag from subject line.

    Returns (persona_key, clean_subject) or None if no tag found.
    Examples:
        "[COS] Should we push?" -> ("COS", "Should we push?")
        "[STAFF] Thoughts?" -> ("STAFF", "Thoughts?")
        "[A12] Build this" -> ("A12", "Build this")
    """
    match = re.match(r'^\[([A-Za-z0-9]+)\]\s*(.*)', subject)
    if match:
        tag = match.group(1).upper()
        clean_subject = match.group(2).strip()
        if tag in PERSONA_LOOKUP:
            return (tag, clean_subject)
    return None


def _parse_action_command(subject: str) -> Optional[tuple]:
    """Parse [A3] DONE: or [A3] SNOOZE: commands from briefing mailto links.

    Returns (command, booking_key, anchor_label) or None.
    Examples:
        "[A3] DONE: Furlow_Regent_3071222 — Passport validity check" -> ("DONE", "Furlow_Regent_3071222", "Passport validity check")
        "[A3] SNOOZE: McLeod_Princess_8X6PGQ — E-90..." -> ("SNOOZE", "McLeod_Princess_8X6PGQ", "E-90...")
    """
    match = re.match(r'^\[A3\]\s*(DONE|SNOOZE):\s*(.+?)\s*(?:—|--|-)\s*(.+)', subject)
    if match:
        return (match.group(1).upper(), match.group(2).strip(), match.group(3).strip())
    return None


def _handle_action_command(service, msg_id: str, command: str, booking_key: str, anchor_label: str) -> Dict:
    """Write DONE or SNOOZE status to Action_Tracker sheet, mark email read."""
    import gspread
    from google.oauth2 import service_account as sa

    creds = sa.Credentials.from_service_account_file(
        str(THUNDERBIRD_DIR / "credentials.json"),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(creds)
    sheet_id = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
    ws = gc.open_by_key(sheet_id).worksheet("Action_Tracker")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if command == "DONE":
        status = "DONE"
    elif command == "SNOOZE":
        from datetime import timedelta
        snooze_until = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        status = f"SNOOZED until {snooze_until}"
    else:
        status = command

    # Check if this item already exists in tracker
    existing = ws.get_all_values()
    found = False
    for i, row in enumerate(existing[1:], start=2):
        if len(row) >= 2 and row[0].strip() == booking_key and row[1].strip() == anchor_label:
            # Update existing row
            ws.update(f"E{i}:H{i}", [[status, "Commander", now, ""]])
            found = True
            break

    if not found:
        # Append new row
        ws.append_row(
            [booking_key, anchor_label, "", "", status, "Commander", now, ""],
            value_input_option="USER_ENTERED",
        )

    # Mark email as read
    _mark_read(service, msg_id)

    logger.info(f"Action Tracker: {command} — {booking_key} / {anchor_label}")
    return {"command": command, "booking_key": booking_key, "anchor_label": anchor_label, "status": status}


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
    """Extract key headers from Gmail message."""
    keys = {"From", "To", "Subject", "Date", "Cc"}
    return {h["name"]: h["value"] for h in headers if h["name"] in keys}


def _remove_star(service, message_id: str, star_label: str):
    """Remove the colored star from a message and mark as read."""
    try:
        labels_to_remove = [star_label, "UNREAD"]
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": labels_to_remove}
        ).execute()
    except Exception as e:
        logger.error(f"Failed to remove star from {message_id}: {e}")


def _mark_read(service, message_id: str):
    """Mark a message as read."""
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
    except Exception as e:
        logger.error(f"Failed to mark read {message_id}: {e}")


def _create_draft_reply(service, msg: Dict, to_email: str, subject: str, reply_body: str) -> Dict:
    """Create a Gmail draft reply on a thread."""
    mime_msg = MIMEText(reply_body, "plain")
    mime_msg["to"] = to_email
    mime_msg["from"] = OPS_EMAIL  # D2M ops sends drafts — not Commander personal
    mime_msg["subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject

    raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")
    draft_data = {
        "message": {
            "raw": raw,
            "threadId": msg.get("threadId", ""),
        }
    }

    draft = service.users().drafts().create(userId="me", body=draft_data).execute()
    return draft


def _notify_commander_telegram(action_type: str, subject: str, from_addr: str,
                                response_preview: str, draft_id: str = None,
                                extra_note: str = None):
    """Send Commander a Telegram notification about a Star Protocol action."""
    try:
        import os
        import requests as _requests

        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        commander_id = os.environ.get("TELEGRAM_COMMANDER_ID", "")

        if not bot_token or not commander_id:
            logger.warning("Telegram env vars not set — skipping notification")
            return

        # Format header based on action type
        headers_map = {
            "RED_COMMAND": "\U0001f534 *STAR PROTOCOL \u2014 COMMAND*",
            "GREEN_APPROVED": "\U0001f7e2 *STAR PROTOCOL \u2014 APPROVED*",
            "BLUE_DRAFT": "\U0001f535 *STAR PROTOCOL \u2014 DRAFT REPLY*",
            "STAFF_MEETING": "\U0001f465 *STAR PROTOCOL \u2014 STAFF MEETING*",
            "ACTION_COMMAND": "\u2705 *STAR PROTOCOL \u2014 ACTION TRACKED*",
        }

        # PERSONA_EMAIL variants: action_type may be "PERSONA_EMAIL:A2" etc.
        if action_type.startswith("PERSONA_EMAIL"):
            persona_label = action_type.split(":", 1)[1] if ":" in action_type else ""
            header = f"\U0001f4e7 *STAR PROTOCOL \u2014 {persona_label} RESPONSE*"
        else:
            header = headers_map.get(action_type, f"*STAR PROTOCOL \u2014 {action_type}*")

        lines = [
            header,
            "",
            f"Subject: {subject}",
            f"From: {from_addr}",
            "",
            f"_{response_preview[:300]}_",
        ]

        if draft_id:
            lines.append(f"\nDraft ID: `{draft_id}`")

        if extra_note:
            lines.append(f"\n{extra_note}")

        if action_type in ("BLUE_DRAFT", "STAFF_MEETING") or action_type.startswith("PERSONA_EMAIL"):
            lines.append("\nReview in Gmail.")

        notice = "\n".join(lines)

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


def _log_action(entry: Dict):
    """Append to sweep log file."""
    log_data = []
    if SWEEP_LOG.exists():
        try:
            log_data = json.loads(SWEEP_LOG.read_text())
        except Exception:
            log_data = []

    log_data.append(entry)

    # Keep last 200 entries
    if len(log_data) > 200:
        log_data = log_data[-200:]

    SWEEP_LOG.write_text(json.dumps(log_data, indent=2))


# ============================================================================
# STAR HANDLERS
# ============================================================================

def _handle_command(subject: str, body: str, from_addr: str, headers: Dict) -> Dict:
    """RED CIRCLE: Extract intent, route to action via COS."""
    from thunderbird_personas import call_persona

    query_text = f"From: {from_addr}\nSubject: {subject}\n{body}"
    enriched = _build_enriched_query(query_text, "COS")

    prompt = (
        f"STAR PROTOCOL — COMMAND (Red Bang)\n"
        f"Yoda starred this email as a COMMAND. Extract the intent and recommend the action.\n\n"
        f"{enriched}\n\n"
        f"What is the actionable command here? Who on staff should handle it? "
        f"What specific steps should be taken? Be concise."
    )

    result = call_persona("COS", prompt, max_tokens=1500)
    response_text = result.get("answer", result.get("message", ""))
    _notify_commander_telegram("RED_COMMAND", subject, from_addr, response_text)
    return {"handler": "COS", "response": response_text}


def _handle_approved(subject: str, body: str, from_addr: str, headers: Dict, message_id: str) -> Dict:
    """GREEN CIRCLE: Approved — execute. EXEC + COS acknowledge."""
    from thunderbird_personas import call_persona

    query_text = f"From: {from_addr}\nSubject: {subject}\n{body}"
    enriched = _build_enriched_query(query_text, "COS")

    prompt = (
        f"STAR PROTOCOL — APPROVED (Green Check)\n"
        f"Yoda approved this for execution. Confirm what needs to be done and flag any blockers.\n\n"
        f"{enriched}\n\n"
        f"What is being approved? What's the execution checklist? Any risks?"
    )

    result = call_persona("COS", prompt, max_tokens=1500)
    response_text = result.get("answer", result.get("message", ""))
    _notify_commander_telegram("GREEN_APPROVED", subject, from_addr, response_text)
    return {"handler": "EXEC + COS", "response": response_text}


def _handle_draft_reply(service, msg: Dict, subject: str, body: str, from_addr: str, headers: Dict) -> Dict:
    """BLUE STAR: Draft a reply in Yoda's voice."""
    from thunderbird_personas import call_persona

    prompt = (
        f"STAR PROTOCOL — DRAFT REPLY (Blue Star)\n"
        f"Yoda wants a reply drafted in his voice. Write the reply.\n\n"
        f"YODA'S VOICE RULES:\n"
        f"- Never use 'Hey' as salutation\n"
        f"- Short sentences, conversational, dashes freely\n"
        f"- Warm but precise. USAF background shows.\n"
        f"- Never salesy. Present info, leave decision to them.\n"
        f"- Sign as: John\\n\\nJohn A Loucks III\\nOwner, Dreams2Memories, LLC\\n719-291-0742\\njohnloucks3@gmail.com\n\n"
        f"EMAIL TO REPLY TO:\n"
        f"From: {from_addr}\n"
        f"Subject: {subject}\n"
        f"Body:\n{body}\n\n"
        f"Write ONLY the reply body. No meta-commentary."
    )

    result = call_persona("EXEC", prompt)
    draft_body = result.get("answer", result.get("message", ""))

    if draft_body:
        try:
            reply_to = headers.get("From", from_addr)
            email_match = re.search(r'<([^>]+)>', reply_to)
            to_email = email_match.group(1) if email_match else reply_to

            draft = _create_draft_reply(service, msg, to_email, subject, draft_body)

            _notify_commander_telegram(
                "BLUE_DRAFT", subject, from_addr, draft_body,
                draft_id=draft["id"],
            )

            return {
                "handler": "EXEC",
                "draft_id": draft["id"],
                "to": to_email,
                "response": draft_body[:500],
                "note": "Draft created in Gmail — review before sending",
            }
        except Exception as e:
            logger.error(f"Failed to create draft: {e}")
            return {
                "handler": "EXEC",
                "response": draft_body,
                "draft_error": str(e),
                "note": "Persona drafted reply but Gmail draft creation failed",
            }

    return {"handler": "EXEC", "response": "No draft generated", "error": True}


# ============================================================================
# SELF-EMAIL HANDLER (replaces Green Star)
# ============================================================================

def _build_enriched_query(query: str, persona_id: str) -> str:
    """Build data-enriched query for a persona using the Dani data engine.

    COS gets COS-specific rules (present all data, structured briefing).
    Other personas get the raw data context without Dani's persona rules.
    """
    try:
        from thunderbird_dani_engine import build_dani_context
        context = build_dani_context(query, is_commander=True)

        # Strip Dani's persona rules — each persona has their own system prompt
        if "DANI'S RULES:" in context:
            context = context[:context.index("DANI'S RULES:")]

        if persona_id == "COS":
            context += (
                "\n\nCOS DATA PRESENTATION RULES:\n"
                "- You are briefing the COMMANDER via email. Present ALL data from above.\n"
                "- Format as a clean briefing: structured, scannable, complete.\n"
                "- Include: names, booking IDs, confirmation numbers, dates, costs, phone numbers, emails, addresses.\n"
                "- Include: anchor date timelines, cancellation penalties, payment status.\n"
                "- If data is missing, say so explicitly. NEVER fabricate details.\n"
                "- If you determine another staff member should handle part of this, say so clearly:\n"
                "  'DELEGATE TO [A2/A3/A5/A9/A10]: <specific task>'\n"
                "  The system will automatically consult that persona and append their response."
            )
        else:
            context += (
                "\n\nRULES:\n"
                "- Answer from the data above. Be specific and actionable.\n"
                "- If data is missing, say so. NEVER fabricate details.\n"
            )

        return f"{context}\n\nCOMMANDER QUERY: {query}"
    except Exception as e:
        logger.warning(f"Data engine failed for {persona_id}: {e}")
        return query


def _check_cos_delegation(cos_answer: str, original_query: str) -> list:
    """Check if COS delegated to other personas. Returns list of (persona_id, task) tuples."""
    import re as _re
    delegations = []
    # Match patterns like "DELEGATE TO A2: research Mediterranean ports"
    pattern = r'DELEGATE\s+TO\s+\[?([A-Z0-9]+)\]?\s*:\s*(.+?)(?:\n|$)'
    for match in _re.finditer(pattern, cos_answer):
        tag = match.group(1).upper()
        task = match.group(2).strip()
        pid = PERSONA_LOOKUP.get(tag)
        if pid and pid != "COS" and pid != "ALL":
            delegations.append((pid, task))
    return delegations


def _handle_self_email(service, msg: Dict, persona_tag: str, clean_subject: str, body: str) -> Dict:
    """Handle self-addressed [PERSONA] email. Creates draft reply with persona response.

    Enhanced features:
    - COS and all personas get the full data engine context (bookings, dossiers, Sheets, Gmail)
    - COS can delegate: if her response includes 'DELEGATE TO [A2]: task', A2 is auto-consulted
    - Delegated responses are appended to the draft
    - Uses Gemini 2.5 Flash primary, Groq fallback (via call_persona)
    """
    from thunderbird_personas import call_persona, run_staff_meeting

    persona_id = PERSONA_LOOKUP.get(persona_tag, "COS")

    if persona_id == "ALL":
        # Full staff meeting — all 9 personas weigh in, each with data context
        enriched = _build_enriched_query(f"{clean_subject}\n{body}", "COS")
        prompt = (
            f"STAR PROTOCOL — STAFF MEETING\n"
            f"Yoda sent himself a note addressed to the full staff.\n\n"
            f"{enriched}"
        )
        result = run_staff_meeting(prompt, persona_ids=ALL_PERSONA_IDS)
        responses = result.get("responses", [])
        reply_parts = []
        for r in responses:
            if "answer" in r:
                reply_parts.append(f"{r.get('icon', '')} {r['persona']}-{r['name'].upper()}:\n{r['answer']}")
            elif "error" in r:
                reply_parts.append(f"{r.get('icon', '')} {r['persona']}-{r['name'].upper()}: [ERROR]")
        reply_body = "\n\n---\n\n".join(reply_parts)

        try:
            draft = _create_draft_reply(service, msg, YODA_EMAIL, f"[STAFF] {clean_subject}", reply_body)

            _notify_commander_telegram(
                "STAFF_MEETING", f"[STAFF] {clean_subject}", YODA_EMAIL,
                reply_body, draft_id=draft["id"],
            )

            return {
                "handler": "STAFF_MEETING",
                "addressees": ALL_PERSONA_IDS,
                "draft_id": draft["id"],
                "persona_count": len(responses),
                "note": "Staff meeting results drafted as reply — review in Gmail",
            }
        except Exception as e:
            logger.error(f"Failed to create staff meeting draft: {e}")
            return {
                "handler": "STAFF_MEETING",
                "addressees": ALL_PERSONA_IDS,
                "responses": [{"persona": r.get("persona"), "answer": r.get("answer", "")[:200]} for r in responses],
                "draft_error": str(e),
            }
    else:
        # Single persona with full data engine context
        query_text = f"{clean_subject}\n{body}" if body.strip() else clean_subject
        enriched = _build_enriched_query(query_text, persona_id)

        prompt = (
            f"STAR PROTOCOL — STAFF DIRECTIVE\n"
            f"Yoda sent himself a note addressed to you.\n\n"
            f"{enriched}"
        )

        # COS and data-heavy personas get more tokens
        tokens = 1500 if persona_id in ("COS", "A2", "A3", "A9") else 800
        result = call_persona(persona_id, prompt, max_tokens=tokens)
        reply_body = result.get("answer", result.get("message", ""))

        # COS delegation — check if she's handing off to another persona
        delegated_responses = []
        if persona_id == "COS" and reply_body:
            delegations = _check_cos_delegation(reply_body, query_text)
            for delegate_pid, delegate_task in delegations:
                logger.info(f"COS delegated to {delegate_pid}: {delegate_task[:60]}")
                delegate_enriched = _build_enriched_query(delegate_task, delegate_pid)
                delegate_prompt = (
                    f"STAR PROTOCOL — COS DELEGATION\n"
                    f"COS (Hale) has delegated this task to you.\n\n"
                    f"{delegate_enriched}"
                )
                try:
                    d_result = call_persona(delegate_pid, delegate_prompt, max_tokens=1500)
                    d_answer = d_result.get("answer", "")
                    if d_answer:
                        delegated_responses.append(
                            f"\n\n{'='*40}\n"
                            f"DELEGATED TO {delegate_pid} ({d_result.get('name', '')}):\n"
                            f"{'='*40}\n{d_answer}"
                        )
                except Exception as e:
                    logger.error(f"Delegation to {delegate_pid} failed: {e}")
                    delegated_responses.append(
                        f"\n\n[Delegation to {delegate_pid} failed: {e}]"
                    )

        if delegated_responses:
            reply_body += "\n" + "\n".join(delegated_responses)

        if reply_body:
            try:
                original_subject = f"[{persona_tag}] {clean_subject}"
                draft = _create_draft_reply(service, msg, YODA_EMAIL, original_subject, reply_body)

                _notify_commander_telegram(
                    f"PERSONA_EMAIL:{persona_tag}", original_subject, YODA_EMAIL,
                    reply_body, draft_id=draft["id"],
                )

                return {
                    "handler": "DIRECT" + (" + DELEGATION" if delegated_responses else ""),
                    "persona": persona_id,
                    "persona_name": result.get("name", ""),
                    "draft_id": draft["id"],
                    "delegations": len(delegated_responses),
                    "response": reply_body[:500],
                    "note": f"{result.get('name', persona_id)} replied — draft in Gmail",
                }
            except Exception as e:
                logger.error(f"Failed to create persona draft: {e}")
                return {
                    "handler": "DIRECT",
                    "persona": persona_id,
                    "response": reply_body,
                    "draft_error": str(e),
                }

        return {"handler": "DIRECT", "persona": persona_id, "response": "No response generated", "error": True}


# ============================================================================
# MAIN SWEEP
# ============================================================================

def run_star_sweep() -> Dict[str, Any]:
    """Scan Gmail for colored superstars AND self-addressed persona emails.

    Returns a summary of actions taken.
    """
    service = _get_gmail_service()
    actions_taken = []

    # ── PHASE 1: Starred messages (Red Bang, Green Check, Blue Star) ──
    results = service.users().messages().list(
        userId="me", q="is:starred", maxResults=50
    ).execute()

    starred_msgs = results.get("messages", [])

    for msg_ref in starred_msgs:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        label_ids = msg.get("labelIds", [])
        star_type = _get_star_type(label_ids)

        if not star_type:
            continue

        payload = msg.get("payload", {})
        headers = _extract_headers(payload.get("headers", []))
        body = _decode_body(payload)
        subject = headers.get("Subject", "")
        from_addr = headers.get("From", "")
        body_short = body[:3000] if len(body) > 3000 else body

        star_config = STAR_ACTIONS[star_type]
        action = star_config["action"]

        action_entry = {
            "timestamp": datetime.now().isoformat(),
            "message_id": msg_ref["id"],
            "star": star_type,
            "action": action,
            "subject": subject,
            "from": from_addr,
            "status": "pending",
            "result": None,
        }

        try:
            if action == "COMMAND":
                result = _handle_command(subject, body_short, from_addr, headers)
            elif action == "APPROVED":
                result = _handle_approved(subject, body_short, from_addr, headers, msg_ref["id"])
            elif action == "DRAFT_REPLY":
                result = _handle_draft_reply(service, msg, subject, body_short, from_addr, headers)
            else:
                result = {"error": f"Unknown action: {action}"}

            action_entry["status"] = "completed"
            action_entry["result"] = result
            _remove_star(service, msg_ref["id"], star_type)

        except Exception as e:
            logger.error(f"Star protocol error for {msg_ref['id']}: {e}")
            action_entry["status"] = "error"
            action_entry["result"] = str(e)

        _log_action(action_entry)
        actions_taken.append(action_entry)

    # ── PHASE 2: Self-addressed [PERSONA] emails ──
    # Search for unread emails from Yoda to Yoda with bracket tags
    self_query = f"from:{YODA_EMAIL} to:{YODA_EMAIL} is:unread subject:["
    results = service.users().messages().list(
        userId="me", q=self_query, maxResults=20
    ).execute()

    self_msgs = results.get("messages", [])

    for msg_ref in self_msgs:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        payload = msg.get("payload", {})
        headers = _extract_headers(payload.get("headers", []))
        subject = headers.get("Subject", "")
        body = _decode_body(payload)
        body_short = body[:3000] if len(body) > 3000 else body

        # Check for action commands (DONE/SNOOZE) from briefing mailto links
        action_cmd = _parse_action_command(subject)
        if action_cmd:
            command, bkey, alabel = action_cmd
            action_entry = {
                "timestamp": datetime.now().isoformat(),
                "message_id": msg_ref["id"],
                "star": "SELF_EMAIL",
                "action": f"ACTION_COMMAND [{command}]",
                "subject": subject,
                "from": YODA_EMAIL,
                "status": "pending",
                "result": None,
            }
            try:
                result = _handle_action_command(service, msg_ref["id"], command, bkey, alabel)
                action_entry["status"] = "completed"
                action_entry["result"] = result
                _notify_commander_telegram(
                    "ACTION_COMMAND", subject, YODA_EMAIL,
                    f"{command}: {bkey} — {alabel}",
                )
            except Exception as e:
                logger.error(f"Action command error: {e}")
                action_entry["status"] = "error"
                action_entry["result"] = str(e)
            _log_action(action_entry)
            actions_taken.append(action_entry)
            continue  # Skip persona handling for action commands

        parsed = _parse_persona_tag(subject)
        if not parsed:
            continue

        persona_tag, clean_subject = parsed

        action_entry = {
            "timestamp": datetime.now().isoformat(),
            "message_id": msg_ref["id"],
            "star": "SELF_EMAIL",
            "action": f"PERSONA_DIRECTIVE [{persona_tag}]",
            "subject": subject,
            "from": YODA_EMAIL,
            "status": "pending",
            "result": None,
        }

        try:
            result = _handle_self_email(service, msg, persona_tag, clean_subject, body_short)
            action_entry["status"] = "completed"
            action_entry["result"] = result

            # Mark as read after processing
            _mark_read(service, msg_ref["id"])

        except Exception as e:
            logger.error(f"Self-email error for {msg_ref['id']}: {e}")
            action_entry["status"] = "error"
            action_entry["result"] = str(e)

        _log_action(action_entry)
        actions_taken.append(action_entry)

    return {
        "status": "success",
        "sweep_time": datetime.now().isoformat(),
        "starred_scanned": len(starred_msgs),
        "self_emails_scanned": len(self_msgs),
        "actions_taken": len(actions_taken),
        "actions": actions_taken,
    }


# ============================================================================
# MCP TOOLS
# ============================================================================

def register_star_protocol_tools(mcp_server):
    """Register Star Protocol MCP tools."""
    from pydantic import Field

    @mcp_server.tool(
        name="run_star_sweep",
        annotations={"title": "Run Star Protocol Sweep", "readOnlyHint": False},
    )
    async def run_star_sweep_tool() -> str:
        """Scan Gmail for colored superstars and self-addressed persona emails.

        Stars:
          Red Bang (RED_CIRCLE) -> COMMAND: COS extracts intent, routes action
          Green Check (GREEN_CIRCLE) -> APPROVED: EXEC + COS execute
          Blue Star (BLUE_STAR) -> DRAFT REPLY: EXEC drafts in Yoda's voice
          Yellow Star -> Ignored (personal)

        Self-Emails:
          [COS] subject -> COS responds, draft reply created
          [A2] subject -> A2-Dembe responds, draft reply created
          [STAFF] subject -> All 9 personas weigh in, consolidated draft reply
          Any persona tag works: COS, EXEC, A2, A3, A5, A9, A10, CH, A12, STAFF
        """
        try:
            result = run_star_sweep()
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Star sweep error: {e}")
            return json.dumps({"error": str(e), "type": "star_sweep_error"})

    @mcp_server.tool(
        name="star_protocol_log",
        annotations={"title": "View Star Protocol Log", "readOnlyHint": True},
    )
    async def star_protocol_log_tool(
        count: int = Field(10, description="Number of recent entries to show"),
    ) -> str:
        """View recent Star Protocol sweep results."""
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

    logger.info("Star Protocol v3 tools registered (run_star_sweep, star_protocol_log)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if "--sweep" in sys.argv:
        print("Running Star Protocol v3 sweep...", file=sys.stderr)
        result = run_star_sweep()
        print(json.dumps(result, indent=2))
    else:
        print("Usage:", file=sys.stderr)
        print("  python3 thunderbird_star_protocol.py --sweep    # Run one sweep", file=sys.stderr)
        print("", file=sys.stderr)
        print("Stars: Red Bang=COMMAND, Green Check=APPROVED, Blue Star=DRAFT REPLY", file=sys.stderr)
        print("Self-Email: Send to yourself with [COS], [A2], [STAFF], etc. in subject", file=sys.stderr)
