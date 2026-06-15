"""
hale_inbox_tools.py
====================
Dreams2Memories Travel, LLC — Thunderbird Wing

Hale expanded Gmail capabilities (SO 2026-06-06):
  Capability 1: d2mconcierge full inbox triage — ALL incoming, classified by type
  Capability 2: Cross-account unified search — both d2mconcierge + johnloucks3

Classifier: Gemini 2.0 Flash (primary) with regex pre-filter for obvious noise.
  - Obvious noise (noreply/unsubscribe patterns) → regex fast-exit, no API call
  - Everything else → Gemini 2.0 Flash, structured 1-token output
  - Added category: "financial" for payment/invoice/commission items
  - Fallback: regex heuristics if Gemini unavailable

These tools extend thunderbird_gmail.py without touching it.
Register with MCP server via register_hale_inbox_tools(mcp).

Author: Sterling (A7) — Hale directive 2026-06-06 (Gemini upgrade 2026-06-06)
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

from pydantic import Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini classifier — Gemini 2.0 Flash, structured 1-token output
# ---------------------------------------------------------------------------

_gemini_client = None
_GEMINI_MODEL = "gemini-2.5-flash"

_CLASSIFY_PROMPT = """You are an email classifier for Dreams2Memories Travel, a luxury travel agency.
Classify this email into exactly ONE of these categories:
  client_inquiry       — message from a client (question, request, reply, or feedback)
  vendor               — from a travel vendor, cruise line, airline, hotel, or supplier (not a booking confirmation)
  booking_confirmation — a confirmation, receipt, invoice, or itinerary from any source
  financial            — payment notification, commission statement, or billing requiring attention
  noise                — marketing, newsletter, automated system notification, or irrelevant

Respond with ONLY the category name, nothing else. No explanation.

From: {from_addr}
Subject: {subject}
Preview: {snippet}"""


def _get_gemini_client():
    """Lazy-init Gemini client. Returns None if unavailable."""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    try:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("Gemini API key not set — falling back to regex classifier")
            return None
        _gemini_client = genai.Client(api_key=api_key)
        logger.info("Gemini classifier initialized (model: %s)", _GEMINI_MODEL)
        return _gemini_client
    except Exception as e:
        logger.warning(f"Gemini client init failed: {e}")
        return None


def _classify_with_gemini(from_addr: str, subject: str, snippet: str) -> Optional[str]:
    """Call Gemini Flash to classify an email. Returns category string or None on failure."""
    client = _get_gemini_client()
    if not client:
        return None
    try:
        from google.genai import types
        prompt = _CLASSIFY_PROMPT.format(
            from_addr=from_addr[:200],
            subject=subject[:200],
            snippet=snippet[:400],
        )
        response = client.models.generate_content(
            model=_GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=80,
            ),
        )
        txt = response.text
        if txt is None:
            logger.debug("Gemini blocked response (safety filter) — falling back to regex")
            return None
        result = txt.strip().lower().replace("-", "_")
        valid = {"client_inquiry", "vendor", "booking_confirmation", "financial", "noise"}
        if result in valid:
            return result
        logger.debug(f"Gemini returned unexpected category '{result}' — falling back to regex")
        return None
    except Exception as e:
        logger.warning(f"Gemini classify failed: {e}")
        return None

# ---------------------------------------------------------------------------
# Classification config — regex pre-filter (fast, no API cost)
# ---------------------------------------------------------------------------

_HARD_NOISE_PATTERNS = [
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "mailer-daemon", "postmaster", "delivery status",
    "unsubscribe", "newsletter", "marketing", "promotional",
]

_VENDOR_DOMAINS = [
    "silversea.com", "rssc.com", "regentcruises.com", "vikingcruises.com",
    "crystalcruises.com", "seabourn.com", "oceania.com", "windstarcruises.com",
    "atlascruises.com", "unitedairlines.com", "aa.com", "delta.com",
    "icelandair.com", "lufthansa.com", "centrav.com", "kiwitaxi.com",
    "welcomepickups.com", "hotelbeds.com", "bedsonline.com",
    "hilton.com", "marriott.com", "accor.com", "ihg.com",
]

_BOOKING_KEYWORDS = [
    "confirmation", "booking", "reservation", "invoice", "receipt",
    "payment received", "deposit", "itinerary", "ticket",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify_message(from_addr: str, subject: str, snippet: str) -> str:
    """
    Classify an incoming message by type.

    Strategy:
      1. Hard-exit regex for obvious noise (no API call)
      2. Gemini 2.0 Flash for everything else (accurate, handles edge cases)
      3. Regex fallback if Gemini unavailable
    """
    from_lower = from_addr.lower()
    subject_lower = subject.lower()

    # Step 1 — Regex hard-exit for definitive noise (no API call needed)
    for pat in _HARD_NOISE_PATTERNS:
        if pat in from_lower or pat in subject_lower:
            return "noise"

    # Step 2 — Gemini primary classifier
    gemini_result = _classify_with_gemini(from_addr, subject, snippet)
    if gemini_result:
        return gemini_result

    # Step 3 — Regex fallback (Gemini unavailable)
    snippet_lower = snippet.lower()
    for domain in _VENDOR_DOMAINS:
        if domain in from_lower:
            for bkw in _BOOKING_KEYWORDS:
                if bkw in subject_lower or bkw in snippet_lower:
                    return "booking_confirmation"
            return "vendor"
    booking_hits = sum(1 for bkw in _BOOKING_KEYWORDS if bkw in subject_lower)
    if booking_hits >= 2:
        return "booking_confirmation"
    return "client_inquiry"


def _safe_get_service(account: str):
    """Get Gmail service for named account, return None on failure."""
    try:
        from thunderbird_gmail import _get_wing_gmail_service, _get_commander_gmail_service
        if account == "concierge":
            return _get_wing_gmail_service()
        else:
            return _get_commander_gmail_service()
    except Exception as e:
        logger.warning(f"Gmail service unavailable ({account}): {e}")
        return None


def _fetch_message_summary(service, msg_id: str) -> Optional[dict]:
    """Fetch a single message summary (metadata + snippet)."""
    try:
        from thunderbird_gmail import _decode_body, _extract_headers
        msg = service.users().messages().get(
            userId="me", id=msg_id, format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]
        ).execute()
        headers = _extract_headers(msg.get("payload", {}).get("headers", []))
        return {
            "message_id": msg["id"],
            "thread_id": msg.get("threadId", ""),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "labels": msg.get("labelIds", []),
        }
    except Exception as e:
        logger.error(f"Failed to fetch message {msg_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# Capability 1 — d2mconcierge full inbox triage
# ---------------------------------------------------------------------------

def concierge_inbox_triage(max_results: int = 30) -> dict:
    """
    Read ALL unread messages in d2mconcierge@gmail.com inbox.
    Classifies each message: client_inquiry | vendor | booking_confirmation | noise.
    Returns structured triage summary ready for morning brief.

    Does NOT filter by sender — picks up everything the Wing inbox receives.
    """
    service = _safe_get_service("concierge")
    if not service:
        return {"error": "d2mconcierge Gmail service unavailable", "messages": [], "summary": {}}

    try:
        results = service.users().messages().list(
            userId="me",
            q="is:unread in:inbox",
            maxResults=min(max_results, 50)
        ).execute()
    except Exception as e:
        logger.error(f"Concierge inbox list failed: {e}")
        return {"error": str(e), "messages": [], "summary": {}}

    stubs = results.get("messages", [])
    if not stubs:
        return {
            "account": "d2mconcierge@gmail.com",
            "checked_at": datetime.utcnow().isoformat() + "Z",
            "unread_count": 0,
            "messages": [],
            "summary": {"client_inquiry": 0, "financial": 0, "vendor": 0, "booking_confirmation": 0, "noise": 0},
        }

    messages = []
    summary = {"client_inquiry": 0, "vendor": 0, "booking_confirmation": 0, "financial": 0, "noise": 0}

    for stub in stubs:
        meta = _fetch_message_summary(service, stub["id"])
        if not meta:
            continue
        category = _classify_message(meta["from"], meta["subject"], meta["snippet"])
        meta["category"] = category
        summary[category] = summary.get(category, 0) + 1
        messages.append(meta)

    # Sort: client_inquiry first, then financial, then vendor, then booking, then noise
    order = {"client_inquiry": 0, "financial": 1, "vendor": 2, "booking_confirmation": 3, "noise": 4}
    messages.sort(key=lambda m: order.get(m["category"], 9))

    return {
        "account": "d2mconcierge@gmail.com",
        "checked_at": datetime.utcnow().isoformat() + "Z",
        "unread_count": len(messages),
        "summary": summary,
        "messages": messages,
    }


# ---------------------------------------------------------------------------
# Capability 2 — Cross-account unified search
# ---------------------------------------------------------------------------

def dual_inbox_search(query: str, max_results: int = 10) -> dict:
    """
    Search both d2mconcierge@gmail.com AND johnloucks3@gmail.com simultaneously.
    Returns combined results tagged by account.

    Useful for: finding a client email regardless of which inbox received it,
    tracking a thread across both accounts, or looking up a booking confirmation.
    """
    concierge_svc = _safe_get_service("concierge")
    commander_svc = _safe_get_service("commander")

    all_results = []
    account_status = {}

    for account_name, service, label in [
        ("d2mconcierge@gmail.com", concierge_svc, "concierge"),
        ("johnloucks3@gmail.com", commander_svc, "commander"),
    ]:
        if not service:
            account_status[account_name] = "unavailable"
            continue

        try:
            results = service.users().messages().list(
                userId="me", q=query, maxResults=min(max_results, 25)
            ).execute()
            stubs = results.get("messages", [])
            account_status[account_name] = f"{len(stubs)} results"

            for stub in stubs:
                meta = _fetch_message_summary(service, stub["id"])
                if meta:
                    meta["account"] = account_name
                    meta["account_label"] = label
                    all_results.append(meta)

        except Exception as e:
            logger.error(f"Dual search failed for {account_name}: {e}")
            account_status[account_name] = f"error: {e}"

    # Sort by date descending (best effort — Date header is a string)
    all_results.sort(key=lambda m: m.get("date", ""), reverse=True)

    return {
        "query": query,
        "searched_at": datetime.utcnow().isoformat() + "Z",
        "total_results": len(all_results),
        "account_status": account_status,
        "results": all_results,
    }


# ---------------------------------------------------------------------------
# MCP registration
# ---------------------------------------------------------------------------

def register_hale_inbox_tools(mcp):
    """Register Hale expanded Gmail tools with the MCP server."""

    @mcp.tool(
        name="gmail_concierge_triage",
        annotations={"title": "D2M Concierge Inbox Triage", "readOnlyHint": True},
    )
    async def _concierge_triage_tool(
        max_results: int = Field(30, description="Max unread messages to fetch (1-50)"),
    ) -> str:
        """
        Read ALL unread messages in d2mconcierge@gmail.com (the Wing ops inbox).
        Returns classified triage: client inquiries, vendor replies, booking confirmations, noise.
        Use for morning brief, session-start inbox sweep, or ad-hoc inbox check.
        """
        result = concierge_inbox_triage(max_results=max_results)
        return json.dumps(result, indent=2)

    @mcp.tool(
        name="gmail_dual_search",
        annotations={"title": "Search Both Gmail Inboxes", "readOnlyHint": True},
    )
    async def _dual_search_tool(
        query: str = Field(..., description="Gmail search query (same syntax as Gmail search bar). Searches both d2mconcierge and johnloucks3 simultaneously."),
        max_results: int = Field(10, description="Max results per account (1-25)"),
    ) -> str:
        """
        Search both d2mconcierge@gmail.com AND johnloucks3@gmail.com with a single query.
        Results are tagged by account. Useful for finding any email regardless of which inbox received it.
        """
        result = dual_inbox_search(query=query, max_results=max_results)
        return json.dumps(result, indent=2)
