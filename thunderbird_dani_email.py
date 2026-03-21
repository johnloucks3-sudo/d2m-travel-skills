"""
Thunderbird Dani Email Responder
=================================

Watches Gmail for client emails (read AND unread) and has Dani draft responses.
COS reviews before any draft is created. Commander is notified via Telegram.

Routing:
  - Emails FROM Commander's addresses → SKIP (handled by Star Protocol)
  - Emails FROM known clients or unknown senders → Dani drafts reply → COS reviews

Standing Order 2026-03-20 — Three-Phase Workflow:
  Phase 1 (AGGREGATE): Gather all data from specialists, dossier, sheets, memory.
                        Pure data — no client-facing prose.
  Phase 2 (ARTIST):    Craft the response with voice/tone/relationship rules.
                        Pull from voice ledger. Apply per-client rules.
  Phase 3 (ADVOCATE):  COS review gate, learning diff capture, draft creation,
                        Commander notification. Package and present.

Run modes:
  - Standalone sweep:  python3 thunderbird_dani_email.py --sweep
  - Cron/scheduler:    from thunderbird_dani_email import dani_email_sweep
  - MCP tool:          run_dani_email_sweep (registered in travel_mcp_server.py)

Dependencies: thunderbird_gmail.py, thunderbird_dani_engine.py, thunderbird_personas.py,
              thunderbird_voice_ledger.py
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
    mime_msg["from"] = "d2mconcierge@gmail.com"  # D2M ops account — not Commander personal
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
# Dani response engine — Standing Order 2026-03-20
# Three discrete phases: AGGREGATE → ARTIST → ADVOCATE
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Client tier resolution helpers
# ---------------------------------------------------------------------------

# Known client-to-tier mapping. Supplement with dossier/sheets lookups at runtime.
_CLIENT_TIER_MAP = {
    # Paying clients
    "furlow": "paying", "ely": "paying", "kuklinski": "paying",
    "nichols": "paying", "morton": "paying", "mcleod": "paying",
    # Friends & family
    "lyons": "friend", "loucks": "friend", "britan": "friend",
    "westbrook": "friend",
}


def _resolve_client_tier(sender_name: str, sender_email: str) -> str:
    """Determine the client tier from sender name/email for voice rule lookup.

    Returns one of: paying | friend | prospect | vendor | staff
    Falls back to 'prospect' when tier is unknown.
    """
    combined = f"{sender_name} {sender_email}".lower()
    for key, tier in _CLIENT_TIER_MAP.items():
        if key in combined:
            return tier
    return "prospect"


# ---------------------------------------------------------------------------
# Phase 1: AGGREGATE
# ---------------------------------------------------------------------------

def _phase_aggregate(sender_name: str, sender_email: str,
                     subject: str, body: str,
                     dossier_data: Optional[str] = None) -> Dict[str, Any]:
    """Phase 1 — Pure data collection. No client-facing prose.

    Gathers from: dossier, booking data, sheets, memory, Gmail history.
    Consults A2 (Dembe) if destination/intel is needed.
    Consults A9 (Harlan) if pricing/financial data is needed.
    A5, COS, and CH are available for Commander-side context only.

    Args:
        sender_name:   Display name from the From header.
        sender_email:  Bare email address of the sender.
        subject:       Email subject line.
        body:          Email body text (will be trimmed to 3000 chars).
        dossier_data:  Optional pre-loaded dossier content (reserved for future
                       direct injection; build_dani_context reads dossiers internally).

    Returns:
        Structured dict with all gathered data — NOT prose.
        {
            "query":        str,   # normalised query string
            "context":      str,   # full Dani context block from engine
            "sender_name":  str,
            "sender_email": str,
            "subject":      str,
            "body_excerpt": str,   # first 3000 chars
            "client_tier":  str,   # paying | friend | prospect | vendor | staff
            "clients":      list,  # detected client family names
            "error":        str | None,
        }
    """
    from thunderbird_dani_engine import build_dani_context, _detect_clients

    query = (
        f"EMAIL from {sender_name} ({sender_email}):\n"
        f"Subject: {subject}\n\n"
        f"{body[:3000]}"
    )

    detected_clients = _detect_clients(query)
    client_tier = _resolve_client_tier(sender_name, sender_email)

    try:
        # build_dani_context handles: KNOWN_BOOKINGS, dossiers, Sheets (Booking Master
        # + all tabs), Gmail history, anchor dates, client profile, shared memory,
        # specialist consults (A2 for research, A9 for financials), and the
        # data-confidence classifier. is_commander=False hides financial/A9 data.
        context = build_dani_context(query, is_commander=False)

        return {
            "query": query,
            "context": context,
            "sender_name": sender_name,
            "sender_email": sender_email,
            "subject": subject,
            "body_excerpt": body[:3000],
            "client_tier": client_tier,
            "clients": detected_clients,
            "error": None,
        }

    except Exception as e:
        logger.error(f"[AGGREGATE] Data gather failed for {sender_name}: {e}")
        return {
            "query": query,
            "context": "",
            "sender_name": sender_name,
            "sender_email": sender_email,
            "subject": subject,
            "body_excerpt": body[:3000],
            "client_tier": client_tier,
            "clients": detected_clients,
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Phase 2: ARTIST
# ---------------------------------------------------------------------------

def _phase_artist(aggregated_data: Dict[str, Any]) -> Optional[str]:
    """Phase 2 — Craft the response with voice/tone/relationship rules.

    This is where Dani's personality and warmth come through.
    Pulls from the voice ledger (global → tier → client-specific rules).
    Calls the A3 persona with: aggregated context + voice rules + email rules.

    Args:
        aggregated_data: Dict returned by _phase_aggregate().

    Returns:
        Crafted prose email response, or None if generation fails.
    """
    from thunderbird_personas import call_persona
    from thunderbird_voice_ledger import get_voice_rules

    if aggregated_data.get("error") and not aggregated_data.get("context"):
        logger.warning(
            f"[ARTIST] Skipping — aggregate phase had error and no context: "
            f"{aggregated_data['error']}"
        )
        return None

    sender_name = aggregated_data["sender_name"]
    client_tier = aggregated_data["client_tier"]
    clients = aggregated_data["clients"]

    # Pull voice rules: global + tier + per-client (most specific wins)
    client_key = clients[0] if clients else sender_name
    voice_rules = get_voice_rules(client_name=client_key, tier=client_tier)

    # Build the full prompt: aggregated data block + voice rules + email format rules
    context = aggregated_data["context"]

    # --- Auto-enrichment: inject client context from dossiers/Gmail/Drive ---
    try:
        from thunderbird_auto_enrich import enrich_client_context
        client_context = enrich_client_context(
            aggregated_data.get("sender_email")
            or aggregated_data.get("subject")
            or ""
        )
        if client_context:
            context = client_context + "\n\n" + context
    except Exception:
        pass

    if voice_rules:
        context += f"\n\n{voice_rules}"

    # Conversation state machine — detect phase, inject guidance
    try:
        from thunderbird_conversation_state import detect_and_guide
        body_excerpt = aggregated_data.get("body_excerpt", "")
        phase_guidance = detect_and_guide(body_excerpt, is_first_message=False)
        context += f"\n\n{phase_guidance.to_injection_block()}"

        # Response library — inject template structure if one matches
        try:
            from thunderbird_response_library import select_template
            template = select_template(body_excerpt, phase_hint=phase_guidance.template_hint)
            if template:
                context += f"\n\n{template.to_injection_block()}"
        except Exception:
            pass
    except Exception:
        pass

    email_format_rules = (
        "\n\nEMAIL RESPONSE RULES:\n"
        "- You are responding to a client EMAIL, not a chat message.\n"
        "- Use proper email formatting — greeting, body, warm sign-off.\n"
        "- Sign as: Dani Moreau, Luxury Travel Concierge, Dreams2Memories Travel\n"
        "- FROM address: concierge@d2mluxury.quest — never mention it in the body.\n"
        "- Keep the response focused and professional. No emojis.\n"
        "- If you need to reference John, say 'John Loucks, our owner' or 'John'.\n"
        "- Apply Commander's voice rules above before generating any output.\n"
    )
    context += email_format_rules

    try:
        # A3 = Dani. model_override=opus for all client-facing email (quality floor).
        result = call_persona("A3", context, max_tokens=800, model_override="opus")
        answer = result.get("answer", "")

        # Strip the model attribution tag that call_persona appends
        answer = re.sub(r"\n\n---\n_.*?_$", "", answer).strip()

        if not answer:
            logger.warning(f"[ARTIST] Empty response from A3 for {sender_name}")
            return None

        logger.debug(f"[ARTIST] Crafted {len(answer)} chars for {sender_name}")
        return answer

    except Exception as e:
        logger.error(f"[ARTIST] Persona call failed for {sender_name}: {e}")
        return None


# ---------------------------------------------------------------------------
# Phase 3: ADVOCATE
# ---------------------------------------------------------------------------

def _phase_advocate(crafted_response: str, aggregated_data: Dict[str, Any],
                    service, msg: Dict, thread_id: str,
                    processed_label_id: str) -> Dict[str, Any]:
    """Phase 3 — Package as concierge, COS review gate, draft creation, notify.

    Dani presents as advocate: she owns the response and puts it in front of
    the COS, then into Gmail, then tells the Commander.

    Args:
        crafted_response:    Prose from _phase_artist().
        aggregated_data:     Structured data from _phase_aggregate().
        service:             Authenticated Gmail API service object.
        msg:                 Full Gmail message dict.
        thread_id:           Gmail thread ID for the reply.
        processed_label_id:  Gmail label ID for DANI-Processed.

    Returns:
        {
            "status":    str,   # draft_created | cos_blocked | draft_error
            "draft_id":  str | None,
            "cos_note":  str,
            "final_response": str,  # what actually went into the draft (may be COS-revised)
            "sss_id":    str | None,  # populated if COS blocked and SSS was created
        }
    """
    from thunderbird_dani_engine import cos_review

    sender_name  = aggregated_data["sender_name"]
    sender_email = aggregated_data["sender_email"]
    subject      = aggregated_data["subject"]
    body_excerpt = aggregated_data["body_excerpt"]

    # --- Pre-send evaluator (zero-API-cost leak detection) ---
    try:
        from thunderbird_presend_evaluator import evaluate_draft
        eval_result = evaluate_draft(
            body=crafted_response,
            subject=subject,
            recipient=sender_email,
            is_client_facing=True,
        )
        if not eval_result.passed:
            logger.warning(
                f"[ADVOCATE] Pre-send evaluator FAILED for {sender_name}: "
                f"{eval_result.summary()}"
            )
            for v in eval_result.violations:
                logger.warning(f"  {v}")
            # Block if any BLOCK-severity violations found
            return {
                "status": "presend_blocked",
                "draft_id": None,
                "cos_note": eval_result.to_cos_report(),
                "final_response": crafted_response,
                "sss_id": None,
            }
        else:
            logger.debug(f"[ADVOCATE] Pre-send evaluator PASSED for {sender_name}")
    except Exception as _eval_err:
        logger.debug(f"[ADVOCATE] Pre-send eval skipped: {_eval_err}")

    # --- COS review gate ---
    cos_query = f"{sender_name} asked: {subject}\n{body_excerpt[:500]}"
    cos_result = cos_review(cos_query, crafted_response, is_client=True)
    cos_note   = cos_result.get("note", "")

    if not cos_result.get("approved", True):
        logger.warning(f"[ADVOCATE] COS BLOCKED reply to {sender_name}: {cos_note}")

        sss_id = None
        try:
            from thunderbird_sss import create_sss, coordinate_sss
            sss = create_sss(
                action_officer="A3",
                purpose=f"COS blocked Dani reply to {sender_name} re: {subject}",
                background=(
                    f"Dani drafted a response to {sender_name} ({sender_email}) "
                    f"regarding: {subject}. COS blocked with note: {cos_note}"
                ),
                discussion=f"Original draft:\n{crafted_response[:500]}",
                recommendation=(
                    "Revise draft per COS guidance and re-submit, "
                    "or override with Commander approval."
                ),
                scope="client",
                category="comms",
            )
            coordinate_sss(sss.sss_id)
            sss_id = sss.sss_id
            logger.info(f"[ADVOCATE] SSS {sss_id} created for COS-blocked email to {sender_name}")
        except Exception as _sss_err:
            logger.debug(f"[ADVOCATE] SSS escalation skipped: {_sss_err}")

        return {
            "status": "cos_blocked",
            "draft_id": None,
            "cos_note": cos_note,
            "final_response": crafted_response,
            "sss_id": sss_id,
        }

    # Use COS-revised version if Hale edited
    final_response = cos_result.get("revised") or crafted_response

    # --- Learning diff capture (Skill 1: Capture the Diff) ---
    # Layer 2: Semantic info delta analysis enriches the learning compiler
    if final_response != crafted_response:
        try:
            from thunderbird_info_delta import analyze_and_feed
            delta_result = analyze_and_feed(
                crafted_response, final_response,
                recipient=sender_name,
                topic=subject,
            )
            logger.info(
                f"[ADVOCATE] Info delta captured for {sender_name}: "
                f"{delta_result['delta_count']} deltas, "
                f"categories={delta_result['categories']}, "
                f"correction_id={delta_result['correction_id']}"
            )
        except Exception as _delta_err:
            # Fallback to plain capture if info delta fails
            logger.debug(f"[ADVOCATE] Info delta failed ({_delta_err}), falling back to plain capture")
            try:
                from thunderbird_learning import capture_email_diff
                capture_email_diff(
                    crafted_response, final_response,
                    context=f"COS review of Dani reply to {sender_name} re: {subject}",
                    source="cos_review",
                )
                logger.debug(f"[ADVOCATE] Learning diff captured for {sender_name}")
            except Exception as _learn_err:
                logger.debug(f"[ADVOCATE] Learning capture skipped: {_learn_err}")

    # --- Draft creation ---
    try:
        draft = _create_draft_reply(
            service, msg, sender_email, subject, final_response, thread_id
        )
        draft_id = draft.get("id", "unknown")

        # Label as processed
        try:
            service.users().messages().modify(
                userId="me", id=msg["id"],
                body={"addLabelIds": [processed_label_id]}
            ).execute()
        except Exception as _label_err:
            logger.warning(f"[ADVOCATE] Failed to label message: {_label_err}")

        # Notify Commander via Telegram
        _notify_commander_telegram(
            f"{sender_name} <{sender_email}>", subject,
            final_response, cos_note, draft_id
        )

        logger.info(f"[ADVOCATE] Draft created for {sender_name} — draft ID: {draft_id}")
        return {
            "status": "draft_created",
            "draft_id": draft_id,
            "cos_note": cos_note,
            "final_response": final_response,
            "sss_id": None,
        }

    except Exception as e:
        logger.error(f"[ADVOCATE] Draft creation failed for {sender_name}: {e}")
        return {
            "status": "draft_error",
            "draft_id": None,
            "cos_note": cos_note,
            "final_response": final_response,
            "sss_id": None,
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Phase chain — aggregate → artist → advocate
# ---------------------------------------------------------------------------

def _build_dani_email_response(sender_name: str, sender_email: str,
                                subject: str, body: str) -> Optional[str]:
    """Backward-compatible wrapper: aggregate → artist → return prose only.

    The sweep loop calls this to get Dani's crafted response text, then
    calls _phase_advocate() itself to control draft creation and logging.
    Callers that only need the prose (e.g. tests, external tools) use this.

    Returns the Artist-phase prose, or None if either phase fails.
    """
    aggregated = _phase_aggregate(sender_name, sender_email, subject, body)
    return _phase_artist(aggregated)


def _cos_review_email(query: str, dani_answer: str) -> Dict:
    """COS reviews Dani's email draft before it becomes a Gmail draft.

    Kept for backward compatibility. The sweep now goes through _phase_advocate().
    """
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

        # ----------------------------------------------------------------
        # Phase 1 — AGGREGATE: gather all data, consult A2/A9 as needed
        # ----------------------------------------------------------------
        aggregated = _phase_aggregate(sender_name, sender_email, subject, body)
        logger.debug(
            f"  [P1-AGGREGATE] clients={aggregated['clients']} "
            f"tier={aggregated['client_tier']} "
            f"context_len={len(aggregated['context'])}"
        )

        # ----------------------------------------------------------------
        # Phase 2 — ARTIST: craft prose with voice rules + Dani's warmth
        # ----------------------------------------------------------------
        crafted_response = _phase_artist(aggregated)
        if not crafted_response:
            entry["status"] = "dani_failed"
            _log_action(entry)
            processed_ids.add(msg_id)
            continue

        logger.debug(f"  [P2-ARTIST] crafted {len(crafted_response)} chars")

        # ----------------------------------------------------------------
        # Phase 3 — ADVOCATE: COS review, diff capture, draft, notify
        # ----------------------------------------------------------------
        advocate_result = _phase_advocate(
            crafted_response, aggregated,
            service, msg, thread_id, processed_label_id
        )

        entry["status"]   = advocate_result["status"]
        entry["cos_note"] = advocate_result.get("cos_note", "")
        if advocate_result.get("draft_id"):
            entry["draft_id"] = advocate_result["draft_id"]
        if advocate_result.get("sss_id"):
            entry["sss_id"] = advocate_result["sss_id"]
        if advocate_result.get("error"):
            entry["error"] = advocate_result["error"]

        if advocate_result["status"] == "draft_created":
            drafted += 1
            logger.info(
                f"  [P3-ADVOCATE] Draft created for {sender_name} "
                f"— draft ID: {advocate_result['draft_id']}"
            )
        elif advocate_result["status"] == "cos_blocked":
            logger.warning(
                f"  [P3-ADVOCATE] COS BLOCKED reply to {sender_name}: "
                f"{advocate_result['cos_note']}"
            )

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
