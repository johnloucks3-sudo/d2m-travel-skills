"""
Thunderbird REST API Gateway
==============================

Lightweight FastAPI server that exposes Thunderbird tools as REST endpoints.
Designed for Google Workspace Add-on (Apps Script) to call via UrlFetchApp.

Endpoints:
  POST /api/tool/{name}          — Execute any registered tool
  POST /api/summarize-email      — Summarize a Gmail message/thread
  POST /api/draft-reply           — Draft a reply in John's voice
  GET  /api/briefing              — Get latest intel briefing
  GET  /api/fare-watches          — List active fare watches
  GET  /api/health                — Health check

Auth: X-API-Key header (shared secret)

Usage:
  python3 thunderbird_api.py                    # Default port 8766
  python3 thunderbird_api.py --port=9000        # Custom port
"""

import json
import logging
import secrets
import sys
import asyncio
import requests as http_requests
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
import uvicorn

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from thunderbird_gmail import _get_gmail_service, _decode_body, _extract_headers, gmail_create_draft_sync
from thunderbird_drive import _get_drive_service
from thunderbird_fare_watch import list_watches, check_fare, add_watch, get_fare_history
from thunderbird_ship_intel import run_ship_intelligence_sweep
from thunderbird_world_intel import run_world_intelligence_sweep
from thunderbird_tech_monitor import run_daily_tech_monitor
from thunderbird_personas import (
    PERSONA_REGISTRY, call_persona, run_staff_meeting, get_roster,
    get_persona, build_system_prompt,
)
from thunderbird_flight_search import _auth_headers as _flight_auth, _format_flight_offers, AmadeusConfig
from thunderbird_hotel_search import _auth_headers as _hotel_auth, _api_url as _hotel_api_url, _format_hotel_results
from thunderbird_hud_memory import HudMemory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIG
# ============================================================================

THUNDERBIRD_DIR = Path(__file__).parent
API_KEY_FILE = THUNDERBIRD_DIR / "api_key.txt"
# Groq ELIMINATED — all AI calls removed from intel pipeline (2026-03-16)
# Constants retained as comments for reference only:
# GROQ_API_KEY = "..."
# GROQ_MODEL = "llama-3.3-70b-versatile"
# GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
EVERNOTE_EMAIL = "yodainva.5d9fc@m.evernote.com"

VOICE_PROFILE = {
    "persona": "Owner, Dreams2Memories, LLC",
    "tone": "Sophisticated, Expert, and Empathetic",
    "vocabulary": "Professional (voyage, destination, logistics, immersion, concierge, end-game)",
    "sentence_structure": "Advisory; balances personal warmth with logistical precision",
    "signature_traits": {
        "value_anchoring": "Mentions research time to show dedication.",
        "advocacy": "Emphasizes being the advocate for the customer.",
        "contrast_logic": "Uses past personal experience to steer clients away from rough or rushed adventures.",
    },
    "standard_closers": ["Let me know what you think,", "Thanks, John", "John A Loucks III"],
    "signature": "John A Loucks III\nOwner, Dreams2Memories, LLC\n719-291-0742\njohnloucks3@gmail.com\nwww.d2mluxury.quest",
    "avoid": [
        "Corporate jargon or stiff formality",
        "Overselling or pressure tactics",
        "Generic greetings like 'Dear Valued Client'",
    ],
}


def _get_api_key() -> str:
    """Load or generate the API key."""
    if API_KEY_FILE.exists():
        return API_KEY_FILE.read_text(encoding="utf-8").strip()
    key = secrets.token_urlsafe(32)
    API_KEY_FILE.write_text(key, encoding="utf-8")
    API_KEY_FILE.chmod(0o600)
    logger.info(f"Generated new API key → {API_KEY_FILE}")
    return key


API_KEY = _get_api_key()
HUD_MEMORY = HudMemory()

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Thunderbird API",
    description="REST gateway for Dreams2Memories Thunderbird OS tools",
    version="1.0.0",
)


def _verify_key(x_api_key: Optional[str] = None):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ============================================================================
# HEALTH
# ============================================================================

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "thunderbird-api", "timestamp": datetime.now().isoformat()}


# ============================================================================
# GMAIL ENDPOINTS
# ============================================================================

@app.post("/api/summarize-email")
async def summarize_email(request: Request, x_api_key: str = Header(None)):
    """Summarize a Gmail message. Body: {"message_id": "..."} or {"thread_id": "..."}"""
    _verify_key(x_api_key)
    body = await request.json()

    try:
        service = _get_gmail_service()

        if "thread_id" in body:
            thread = service.users().threads().get(
                userId="me", id=body["thread_id"], format="full"
            ).execute()
            messages = thread.get("messages", [])
        elif "message_id" in body:
            msg = service.users().messages().get(
                userId="me", id=body["message_id"], format="full"
            ).execute()
            messages = [msg]
        else:
            raise HTTPException(400, "Provide message_id or thread_id")

        # Extract content from all messages
        email_data = []
        for msg in messages:
            payload = msg.get("payload", {})
            headers = _extract_headers(payload.get("headers", []))
            msg_body = _decode_body(payload)
            if len(msg_body) > 5000:
                msg_body = msg_body[:5000] + "..."

            email_data.append({
                "id": msg["id"],
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "body": msg_body,
                "snippet": msg.get("snippet", ""),
            })

        # Build a structured summary (no external AI call — just organized data)
        summary = {
            "status": "success",
            "message_count": len(email_data),
            "subject": email_data[0].get("subject", "") if email_data else "",
            "participants": list({m.get("from", "") for m in email_data}),
            "latest_date": email_data[-1].get("date", "") if email_data else "",
            "messages": [
                {
                    "from": m["from"],
                    "date": m["date"],
                    "snippet": m["snippet"],
                    "body_preview": m["body"][:500],
                }
                for m in email_data
            ],
            "voice_profile": VOICE_PROFILE,
        }

        return JSONResponse(summary)

    except Exception as e:
        logger.error(f"Summarize email error: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/draft-reply")
async def draft_reply(request: Request, x_api_key: str = Header(None)):
    """
    Prepare reply context for an email. Returns email data + voice profile
    for the add-on to compose a reply.
    Body: {"message_id": "...", "instructions": "optional guidance"}
    """
    _verify_key(x_api_key)
    body = await request.json()
    message_id = body.get("message_id")
    instructions = body.get("instructions", "")

    if not message_id:
        raise HTTPException(400, "Provide message_id")

    try:
        service = _get_gmail_service()
        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()

        payload = msg.get("payload", {})
        headers = _extract_headers(payload.get("headers", []))
        msg_body = _decode_body(payload)
        if len(msg_body) > 30000:
            msg_body = msg_body[:30000] + "..."

        # Return structured data for reply composition
        return JSONResponse({
            "status": "success",
            "original": {
                "id": msg["id"],
                "thread_id": msg["threadId"],
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "body": msg_body,
            },
            "reply_to": headers.get("From", ""),
            "subject": f"Re: {headers.get('Subject', '')}",
            "voice_profile": VOICE_PROFILE,
            "instructions": instructions,
        })

    except Exception as e:
        logger.error(f"Draft reply error: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/search-email")
async def search_email(request: Request, x_api_key: str = Header(None)):
    """Search Gmail. Body: {"query": "from:silversea", "max_results": 10}"""
    _verify_key(x_api_key)
    body = await request.json()
    query = body.get("query", "")
    max_results = min(body.get("max_results", 10), 50)

    try:
        service = _get_gmail_service()
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        summaries = []
        for msg_ref in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"]
            ).execute()
            headers = _extract_headers(msg.get("payload", {}).get("headers", []))
            summaries.append({
                "id": msg["id"],
                "threadId": msg["threadId"],
                "snippet": msg.get("snippet", ""),
                **headers,
            })

        return JSONResponse({"status": "success", "count": len(summaries), "messages": summaries})

    except Exception as e:
        raise HTTPException(500, str(e))


# ============================================================================
# INTEL ENDPOINTS
# ============================================================================

@app.get("/api/briefing")
async def get_briefing(x_api_key: str = Header(None)):
    """Get the latest saved briefing data, or run a fresh one."""
    _verify_key(x_api_key)

    # Check for most recent saved briefing
    intel_dir = THUNDERBIRD_DIR / "intel_reports"
    if intel_dir.exists():
        files = sorted(intel_dir.glob("world_intel_*.json"), reverse=True)
        if files:
            data = json.loads(files[0].read_text(encoding="utf-8"))
            return JSONResponse({
                "status": "success",
                "source": "cached",
                "file": files[0].name,
                "data": data,
            })

    return JSONResponse({"status": "empty", "message": "No briefings cached. Run scheduler or use /api/tool/run_world_intelligence_sweep"})


@app.get("/api/fare-watches")
async def get_fare_watches(x_api_key: str = Header(None)):
    """List all active fare watches."""
    _verify_key(x_api_key)
    result = list_watches(active_only=True)
    return JSONResponse(result)


# ============================================================================
# GENERIC TOOL EXECUTOR
# ============================================================================

# Registry of callable tools (name → async function)
TOOL_REGISTRY: Dict[str, Any] = {}


def _build_tool_registry():
    """Register available tools for generic execution."""
    async def _run_ship_intel(**kwargs):
        result = await run_ship_intelligence_sweep()
        return result

    async def _run_world_intel(**kwargs):
        result = await run_world_intelligence_sweep()
        return result

    async def _run_tech_monitor(**kwargs):
        result = await run_daily_tech_monitor()
        return result

    async def _fare_watch_list(**kwargs):
        return list_watches(kwargs.get("active_only", True))

    async def _fare_watch_check(**kwargs):
        return check_fare(kwargs["watch_id"], kwargs["new_price_pp"])

    async def _fare_watch_add(**kwargs):
        return add_watch(**kwargs)

    async def _fare_watch_history(**kwargs):
        return get_fare_history(kwargs["watch_id"], kwargs.get("limit", 30))

    async def _gmail_create_draft(**kwargs):
        """Create a Gmail draft and tag it THUNDERBIRD-Commander-Review."""
        return gmail_create_draft_sync(
            to=kwargs.get("to", "johnloucks3@gmail.com"),
            subject=kwargs.get("subject", "(no subject)"),
            body=kwargs.get("body", ""),
            from_address=kwargs.get("from_address", "concierge@d2mluxury.quest"),
            label_review=kwargs.get("label_review", True),
        )

    TOOL_REGISTRY.update({
        "run_ship_intelligence_sweep": _run_ship_intel,
        "run_world_intelligence_sweep": _run_world_intel,
        "run_daily_tech_monitor": _run_tech_monitor,
        "fare_watch_list": _fare_watch_list,
        "fare_watch_check": _fare_watch_check,
        "fare_watch_add": _fare_watch_add,
        "fare_watch_history": _fare_watch_history,
        "gmail_create_draft": _gmail_create_draft,
    })


_build_tool_registry()


@app.post("/api/tool/{tool_name}")
async def execute_tool(tool_name: str, request: Request, x_api_key: str = Header(None)):
    """Execute a registered Thunderbird tool by name. Body: tool parameters as JSON."""
    _verify_key(x_api_key)

    if tool_name not in TOOL_REGISTRY:
        available = sorted(TOOL_REGISTRY.keys())
        raise HTTPException(404, f"Tool '{tool_name}' not found. Available: {available}")

    body = await request.json() if await request.body() else {}

    try:
        result = await TOOL_REGISTRY[tool_name](**body)
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                result = {"result": result}
        return JSONResponse({"status": "success", "tool": tool_name, "data": result})

    except Exception as e:
        logger.error(f"Tool {tool_name} error: {e}")
        raise HTTPException(500, f"Tool execution failed: {str(e)}")


@app.get("/api/tools")
async def list_tools(x_api_key: str = Header(None)):
    """List all available tools."""
    _verify_key(x_api_key)
    return JSONResponse({
        "status": "success",
        "tools": sorted(TOOL_REGISTRY.keys()),
        "count": len(TOOL_REGISTRY),
    })


# ============================================================================
# AI ENGINE — Groq ELIMINATED (2026-03-16)
# Pass-through: returns original content without LLM summarization.
# Full content is what we want — no lossy summarization layer.
# ============================================================================

def _groq_complete(system_prompt: str, user_content: str, max_tokens: int = 2000) -> str:
    """Pass-through stub — Groq eliminated from intel pipeline.

    Returns the user content as-is. Callers that previously relied on
    Groq for summarization/drafting now get the raw text instead.
    """
    return user_content


VOICE_SYSTEM_PROMPT = f"""You are writing as John Loucks, owner of Dreams2Memories Travel, LLC.
Voice profile:
- Tone: {VOICE_PROFILE['tone']}
- Style: {VOICE_PROFILE['sentence_structure']}
- Traits: Value anchoring (mentions research effort), advocacy (customer's advocate), contrast logic (personal travel experience to guide)
- Closers: "Let me know what you think," / "Thanks, John"
- Signature: {VOICE_PROFILE['signature']}
- AVOID: Corporate jargon, overselling, generic greetings like "Dear Valued Client"
Keep replies warm, personal, and direct. Lead with value/reasoning before recommendations."""


@app.post("/api/ai/summarize")
async def ai_summarize(request: Request, x_api_key: str = Header(None)):
    """AI-powered email summarization. Body: {"message_id": "..."} or {"thread_id": "..."}"""
    _verify_key(x_api_key)
    body = await request.json()

    try:
        service = _get_gmail_service()

        if "thread_id" in body:
            thread = service.users().threads().get(
                userId="me", id=body["thread_id"], format="full"
            ).execute()
            messages = thread.get("messages", [])
        elif "message_id" in body:
            msg = service.users().messages().get(
                userId="me", id=body["message_id"], format="full"
            ).execute()
            messages = [msg]
        else:
            raise HTTPException(400, "Provide message_id or thread_id")

        # Build email text for AI
        email_text_parts = []
        for msg in messages:
            payload = msg.get("payload", {})
            headers = _extract_headers(payload.get("headers", []))
            msg_body = _decode_body(payload)
            if len(msg_body) > 10000:
                msg_body = msg_body[:10000] + "..."
            email_text_parts.append(
                f"FROM: {headers.get('From', '')}\n"
                f"DATE: {headers.get('Date', '')}\n"
                f"SUBJECT: {headers.get('Subject', '')}\n"
                f"BODY:\n{msg_body}"
            )

        full_text = "\n\n---\n\n".join(email_text_parts)

        system = """You are an executive briefing AI for a luxury travel advisor.
Produce a structured summary:
1. BOTTOM LINE UP FRONT (1-2 sentences)
2. KEY POINTS (bullet points, 5-10 items)
3. ACTION ITEMS (if any — what needs response/decision)
4. CLIENT CONTEXT (any relevant client details, dates, money mentioned)
Be concise, factual, and clinical. No fluff."""

        summary = _groq_complete(system, full_text)

        return JSONResponse({
            "status": "success",
            "ai_summary": summary,
            "message_count": len(messages),
            "subject": _extract_headers(messages[0].get("payload", {}).get("headers", [])).get("Subject", "") if messages else "",
        })

    except Exception as e:
        logger.error(f"AI summarize error: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/ai/draft-reply")
async def ai_draft_reply(request: Request, x_api_key: str = Header(None)):
    """AI-generated reply draft in John's voice. Body: {"message_id": "...", "instructions": "..."}"""
    _verify_key(x_api_key)
    body = await request.json()
    message_id = body.get("message_id")
    instructions = body.get("instructions", "Reply professionally and helpfully.")

    if not message_id:
        raise HTTPException(400, "Provide message_id")

    try:
        service = _get_gmail_service()
        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()

        payload = msg.get("payload", {})
        headers = _extract_headers(payload.get("headers", []))
        msg_body = _decode_body(payload)
        if len(msg_body) > 4000:
            msg_body = msg_body[:4000] + "..."

        email_context = (
            f"FROM: {headers.get('From', '')}\n"
            f"SUBJECT: {headers.get('Subject', '')}\n"
            f"DATE: {headers.get('Date', '')}\n"
            f"BODY:\n{msg_body}\n\n"
            f"INSTRUCTIONS: {instructions}"
        )

        draft_text = _groq_complete(VOICE_SYSTEM_PROMPT, f"Draft a reply to this email:\n\n{email_context}")

        return JSONResponse({
            "status": "success",
            "draft": draft_text,
            "reply_to": headers.get("From", ""),
            "subject": f"Re: {headers.get('Subject', '')}",
            "thread_id": msg.get("threadId", ""),
        })

    except Exception as e:
        logger.error(f"AI draft reply error: {e}")
        raise HTTPException(500, str(e))


# ============================================================================
# AI TOOL ROUTER — Natural language → MCP tool calls
# ============================================================================

TOOL_INTENT_PROMPT = """You are a query classifier for a travel agency AI system.
Analyze the user's query and determine if it requires calling a specific tool.

Available tools:
1. search_flights — Search for flights. Needs: origin (IATA), destination (IATA), departure_date (YYYY-MM-DD). Optional: return_date, adults, cabin_class (ECONOMY/BUSINESS/FIRST), nonstop_only.
2. search_hotels — Search for hotels. Needs: destination (city name or code), check_in (YYYY-MM-DD), check_out (YYYY-MM-DD). Optional: adults, rooms, min_category (1-5), max_rate.
3. search_gmail — Search email. Needs: query (Gmail search string).
4. search_drive — Search Google Drive. Needs: query (search terms).
5. fare_watches — List active fare watches. No params needed.
6. ship_intel — Run ship intelligence sweep. No params needed.
7. world_intel — Run world intelligence sweep. No params needed.
8. send_sms — Send SMS notification. Needs: message.
9. none — No tool needed, answer from general knowledge or provided context.

IMPORTANT:
- For dates, if the user says "June" without a year, assume 2026. If they say "next month" from March 2026, that's April 2026.
- For cities, convert to IATA codes: Denver=DEN, Oslo=OSL, London=LHR, Paris=CDG, New York=JFK, Tokyo=NRT, Rome=FCO, Barcelona=BCN, etc.
- If you can't determine required params, use tool "none" and the AI will ask for clarification.

Respond with ONLY valid JSON (no markdown, no explanation):
{"tool": "tool_name", "params": {"key": "value"}, "reason": "brief reason"}
"""


def _classify_intent(query: str) -> dict:
    """Classify query intent and extract tool params (Groq eliminated — pass-through)."""
    raw = _groq_complete(TOOL_INTENT_PROMPT, query, max_tokens=300)
    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"Intent classification failed to parse: {raw[:200]}")
        return {"tool": "none", "params": {}, "reason": "parse_error"}


async def _execute_tool_intent(tool: str, params: dict) -> str:
    """Execute a classified tool intent and return raw results as string."""
    try:
        if tool == "search_flights":
            flight_params = {
                    "originLocationCode": params.get("origin", "").upper(),
                    "destinationLocationCode": params.get("destination", "").upper(),
                    "departureDate": params.get("departure_date", ""),
                    "adults": params.get("adults", 1),
                    "max": 10,
                    "currencyCode": "USD",
                }
            if params.get("return_date"):
                flight_params["returnDate"] = params["return_date"]
            if params.get("cabin_class"):
                flight_params["travelClass"] = params["cabin_class"].upper()
            if params.get("nonstop_only"):
                flight_params["nonStop"] = "true"

            resp = http_requests.get(
                f"{AmadeusConfig.BASE_URL}/v2/shopping/flight-offers",
                headers=_flight_auth(),
                params=flight_params,
                timeout=30,
            )
            if resp.status_code == 200:
                result = _format_flight_offers(resp.json())
                return json.dumps(result, indent=2)
            return json.dumps({"error": f"Amadeus API {resp.status_code}", "detail": resp.text[:500]})

        elif tool == "search_hotels":
            dest = params.get("destination", "")
            check_in = params.get("check_in", "")
            check_out = params.get("check_out", "")
            payload = {
                "stay": {"checkIn": check_in, "checkOut": check_out},
                "occupancies": [{"rooms": params.get("rooms", 1), "adults": params.get("adults", 2), "children": 0}],
                "filter": {"maxHotels": 20, "maxRatesPerRoom": 3},
            }
            # Try destination as a code first
            if len(dest) <= 4:
                payload["destination"] = {"code": dest.upper()}
            else:
                # Use destination name — would need geocoding, fall back to code
                payload["destination"] = {"code": dest.upper()[:3]}

            resp = http_requests.post(
                _hotel_api_url("/hotels"),
                headers=_hotel_auth(),
                json=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                result = _format_hotel_results(resp.json())
                return json.dumps(result, indent=2)
            return json.dumps({"error": f"Hotelbeds API {resp.status_code}", "detail": resp.text[:500]})

        elif tool == "search_gmail":
            service = _get_gmail_service()
            q = params.get("query", "")
            results = service.users().messages().list(userId="me", q=q, maxResults=10).execute()
            messages = results.get("messages", [])
            snippets = []
            for msg_ref in messages[:8]:
                msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
                payload = msg.get("payload", {})
                headers = _extract_headers(payload.get("headers", []))
                body = _decode_body(payload)
                if len(body) > 1500:
                    body = body[:1500] + "..."
                snippets.append(f"From: {headers.get('From','')}\nDate: {headers.get('Date','')}\nSubject: {headers.get('Subject','')}\n{body}")
            return "\n---\n".join(snippets) if snippets else "No results found."

        elif tool == "search_drive":
            drive_service = _get_drive_service()
            q = params.get("query", "")
            escaped = q.replace("'", "\\'")
            results = drive_service.files().list(
                q=f"fullText contains '{escaped}'",
                pageSize=5,
                fields="files(id, name, mimeType)",
                orderBy="modifiedTime desc",
            ).execute()
            files = results.get("files", [])
            parts = []
            for f in files[:3]:
                try:
                    if "spreadsheet" in f.get("mimeType", ""):
                        content = drive_service.files().export(fileId=f["id"], mimeType="text/csv").execute().decode("utf-8", errors="replace")
                    else:
                        content = drive_service.files().export(fileId=f["id"], mimeType="text/plain").execute().decode("utf-8", errors="replace")
                    if len(content) > 15000:
                        content = content[:15000] + "... [truncated]"
                    parts.append(f"FILE: {f['name']}\n{content}")
                except Exception:
                    parts.append(f"FILE: {f['name']} (could not read)")
            return "\n\n".join(parts) if parts else "No results found."

        elif tool == "fare_watches":
            result = list_watches(active_only=True)
            return json.dumps(result, indent=2)

        elif tool == "ship_intel":
            result = await run_ship_intelligence_sweep()
            return json.dumps(result, indent=2) if isinstance(result, dict) else str(result)

        elif tool == "world_intel":
            result = await run_world_intelligence_sweep()
            return json.dumps(result, indent=2) if isinstance(result, dict) else str(result)

        elif tool == "send_sms":
            from thunderbird_payment_alerts import _send_sms
            msg = params.get("message", "")
            _send_sms(msg, "D2M HUD")
            return json.dumps({"status": "sent", "message": msg[:100]})

        else:
            return ""

    except Exception as e:
        logger.error(f"Tool execution error ({tool}): {e}")
        return json.dumps({"error": str(e), "tool": tool})


# ============================================================================
# CLIENT-AWARE QUERY ENGINE
# ============================================================================

# Known client names → search keywords for Gmail/Drive lookup
CLIENT_KEYWORDS = [
    "furlow", "missy", "melissa furlow", "john furlow",
    "ely", "al ely", "alfred ely", "darrow", "amy darrow",
    "nichols", "larry nichols", "heidi nichols",
    "kuklinski", "kyle kuklinski", "nick kuklinski", "roger kuklinski", "rosalie",
    "morton", "josh morton", "joshua morton", "erica dodge",
    "westbrook", "mcleod", "mc leod",
]


def _detect_client_query(query: str):
    """Check if a query mentions a known client. Returns matched name or None."""
    q_lower = query.lower()
    for name in CLIENT_KEYWORDS:
        if name in q_lower:
            return name
    return None


def _search_client_data(client_name: str, query: str) -> str:
    """Search Gmail and Drive for client-specific data. Returns context string."""
    context_parts = []

    # Search Gmail
    try:
        service = _get_gmail_service()
        results = service.users().messages().list(
            userId="me", q=f"{client_name}", maxResults=10
        ).execute()
        messages = results.get("messages", [])

        if messages:
            email_snippets = []
            for msg_ref in messages[:8]:
                msg = service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="full"
                ).execute()
                payload = msg.get("payload", {})
                headers = _extract_headers(payload.get("headers", []))
                subject = headers.get("Subject", "")
                from_addr = headers.get("From", "")
                date = headers.get("Date", "")
                body_text = _decode_body(payload)
                if len(body_text) > 1500:
                    body_text = body_text[:1500] + "..."

                email_snippets.append(
                    f"From: {from_addr}\nDate: {date}\nSubject: {subject}\n{body_text}"
                )

            context_parts.append(
                f"EMAIL DATA ({len(email_snippets)} messages):\n\n"
                + "\n---\n".join(email_snippets)
            )
    except Exception as e:
        logger.warning(f"Gmail search for '{client_name}' failed: {e}")

    # Search Drive
    try:
        drive_service = _get_drive_service()
        escaped = client_name.replace("'", "\\'")
        drive_results = drive_service.files().list(
            q=f"fullText contains '{escaped}' and (mimeType='application/vnd.google-apps.document' or mimeType='application/vnd.google-apps.spreadsheet')",
            pageSize=5,
            fields="files(id, name, mimeType)",
            orderBy="modifiedTime desc",
        ).execute()
        drive_files = drive_results.get("files", [])

        for f in drive_files[:3]:
            try:
                if "spreadsheet" in f["mimeType"]:
                    content = drive_service.files().export(
                        fileId=f["id"], mimeType="text/csv"
                    ).execute().decode("utf-8", errors="replace")
                else:
                    content = drive_service.files().export(
                        fileId=f["id"], mimeType="text/plain"
                    ).execute().decode("utf-8", errors="replace")
                if len(content) > 20000:
                    content = content[:20000] + "... [truncated]"
                context_parts.append(f"DRIVE DOC: {f['name']}\n{content}")
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Drive search for '{client_name}' failed: {e}")

    return "\n\n══════\n\n".join(context_parts) if context_parts else ""


@app.post("/api/ai/query")
async def ai_query(request: Request, x_api_key: str = Header(None)):
    """Free-form AI query with optional email context. Body: {"query": "...", "context": "..."}"""
    _verify_key(x_api_key)
    body = await request.json()
    query = body.get("query", "")
    context = body.get("context", "")

    if not query:
        raise HTTPException(400, "Provide query")

    # Auto-detect client queries and fetch real data
    client_match = _detect_client_query(query)
    if client_match and not context:
        logger.info(f"Client query detected: '{client_match}' — searching Gmail + Drive")
        client_data = _search_client_data(client_match, query)
        if client_data:
            context = client_data

    # AI Tool Router — classify intent if no context already provided
    tool_used = None
    if not context:
        intent = _classify_intent(query)
        tool = intent.get("tool", "none")
        params = intent.get("params", {})

        if tool != "none" and tool:
            logger.info(f"Tool intent: {tool} params={params} reason={intent.get('reason','')}")
            tool_data = await _execute_tool_intent(tool, params)
            if tool_data and "error" not in tool_data[:50].lower():
                context = f"TOOL RESULTS ({tool}):\n{tool_data}"
                tool_used = tool
            elif tool_data:
                # Tool returned an error — include it so AI can explain
                context = f"TOOL RESULTS ({tool}):\n{tool_data}"
                tool_used = tool

    system = """You are EARA, executive AI for Dreams2Memories Travel, LLC.
You serve John Loucks ("Yoda"), luxury travel advisor, Colorado Springs.
Be concise and direct. Answer the specific question asked.

You have CONVERSATION MEMORY — you can reference previous exchanges shown below.
If John asks "what did I just ask" or references something from earlier, check the conversation history.

RULES:
- Never say "use the Thunderbird tool" — you ARE Thunderbird.
- If given CONTEXT data (tool results, email, drive docs), analyze it and answer using ONLY that data.
- For flight results: present the best options clearly — airline, flight number, times, stops, price.
- For hotel results: present top options — name, star rating, price per night, board plan.
- Extract specific details: flight numbers, times, dates, stateroom numbers, booking IDs, costs.
- General travel knowledge: answer directly and briefly.
- If you lack data even after searching, say so honestly — do NOT fabricate.
- No bullet-point frameworks or template outlines. Just answer the question.
- NEVER fabricate data you don't have. A wrong answer is worse than no answer.
- When answering about bookings, include: booking number, stateroom, client names, payment dates.
- Format prices in USD.
- If the user references a previous conversation ("earlier", "before", "last time", "remember"), use the conversation history to answer."""

    # Inject conversation memory
    memory_context = HUD_MEMORY.get_recent_context(limit=10)

    user_msg = ""
    if memory_context:
        user_msg += f"{memory_context}\n\n"
    if context:
        user_msg += f"CONTEXT DATA:\n{context}\n\n"
    user_msg += f"CURRENT QUESTION:\n{query}"

    answer = _groq_complete(system, user_msg, max_tokens=1200)

    # Store this exchange in memory
    HUD_MEMORY.store(
        user_query=query,
        assistant_response=answer,
        tool_used=tool_used,
        client_detected=client_match,
    )

    result = {
        "status": "success",
        "answer": answer,
        "query": query,
    }
    if client_match:
        result["client_detected"] = client_match
    if tool_used:
        result["tool_used"] = tool_used

    return JSONResponse(result)


# ============================================================================
# MEMORY ENDPOINTS
# ============================================================================

@app.get("/api/memory/stats")
async def memory_stats(x_api_key: str = Header(None)):
    """Get HUD conversation memory statistics."""
    _verify_key(x_api_key)
    return JSONResponse({"status": "success", **HUD_MEMORY.get_stats()})


@app.get("/api/memory/recent")
async def memory_recent(x_api_key: str = Header(None), limit: int = 10):
    """Get recent conversation exchanges."""
    _verify_key(x_api_key)
    exchanges = HUD_MEMORY.get_recent(limit=min(limit, 50))
    return JSONResponse({"status": "success", "count": len(exchanges), "exchanges": exchanges})


@app.post("/api/memory/search")
async def memory_search(request: Request, x_api_key: str = Header(None)):
    """Search conversation memory. Body: {"query": "furlow", "limit": 10}"""
    _verify_key(x_api_key)
    body = await request.json()
    query = body.get("query", "")
    limit = min(body.get("limit", 10), 50)

    if not query:
        raise HTTPException(400, "Provide query")

    results = HUD_MEMORY.search_conversations(query, limit)
    return JSONResponse({"status": "success", "count": len(results), "results": results})


@app.post("/api/send-to-evernote")
async def send_to_evernote(request: Request, x_api_key: str = Header(None)):
    """Send content to Evernote via email. Body: {"subject": "...", "body": "..."}"""
    _verify_key(x_api_key)
    body = await request.json()
    subject = body.get("subject", "Thunderbird Note")
    content = body.get("body", "")

    try:
        service = _get_gmail_service()
        from email.mime.text import MIMEText
        import base64

        message = MIMEText(content)
        message["to"] = EVERNOTE_EMAIL
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

        return JSONResponse({"status": "sent", "to": EVERNOTE_EMAIL, "subject": subject})

    except Exception as e:
        logger.error(f"Evernote send error: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/save-to-drive")
async def save_to_drive(request: Request, x_api_key: str = Header(None)):
    """Save content to Google Drive. Body: {"filename": "...", "content": "...", "folder_id": "..."}"""
    _verify_key(x_api_key)
    body = await request.json()
    filename = body.get("filename", f"thunderbird_note_{datetime.now().strftime('%Y%m%d_%H%M')}.txt")
    content = body.get("content", "")
    folder_id = body.get("folder_id", "1MjjbqQVnzMYpHyAtNu-zZej-1mXhHkGk")  # Default: Knowledge Base

    try:
        drive_service = _get_drive_service()
        from googleapiclient.http import MediaInMemoryUpload

        media = MediaInMemoryUpload(content.encode("utf-8"), mimetype="text/plain")
        file_metadata = {"name": filename, "parents": [folder_id]}
        result = drive_service.files().create(
            body=file_metadata, media_body=media, fields="id,webViewLink"
        ).execute()

        return JSONResponse({
            "status": "saved",
            "file_id": result["id"],
            "link": result.get("webViewLink", ""),
            "filename": filename,
        })

    except Exception as e:
        logger.error(f"Drive save error: {e}")
        raise HTTPException(500, str(e))


# ============================================================================
# PERSONA ENDPOINTS
# ============================================================================

@app.post("/api/ai/persona")
async def ai_persona(request: Request, x_api_key: str = Header(None)):
    """Query a specific D2M staff persona. Body: {"persona_id": "A5", "query": "..."}"""
    _verify_key(x_api_key)
    body = await request.json()
    persona_id = body.get("persona_id", "COS")
    query = body.get("query", "")

    if not query:
        raise HTTPException(400, "Provide query")

    result = call_persona(persona_id, query)

    if "error" in result:
        return JSONResponse({"status": "error", **result})

    return JSONResponse({"status": "success", **result})


@app.post("/api/ai/staff-meeting")
async def ai_staff_meeting(request: Request, x_api_key: str = Header(None)):
    """Run all 9 personas against a query (war room). Body: {"query": "...", "persona_ids": "A2,A5,A9"}"""
    _verify_key(x_api_key)
    body = await request.json()
    query = body.get("query", "")
    persona_ids_str = body.get("persona_ids", "")

    if not query:
        raise HTTPException(400, "Provide query")

    ids = None
    if persona_ids_str:
        ids = [p.strip().upper() for p in persona_ids_str.split(",")]

    # ── Gather real data context for personas ──
    context_parts = []

    # Fare watches
    try:
        fw = list_watches(active_only=True)
        if fw.get("watches"):
            fw_lines = []
            for w in fw["watches"]:
                fw_lines.append(f"  {w.get('provider','')} | {w.get('label','')} | {w.get('price_pp','')}/pp | {w.get('vs_baseline','')}")
            context_parts.append("ACTIVE FARE WATCHES (" + str(fw.get("count", 0)) + "):\n" + "\n".join(fw_lines))
        else:
            context_parts.append("FARE WATCHES: None active.")
    except Exception:
        context_parts.append("FARE WATCHES: Unavailable.")

    # Cached briefing
    try:
        intel_dir = THUNDERBIRD_DIR / "intel_reports"
        if intel_dir.exists():
            files = sorted(intel_dir.glob("world_intel_*.json"), reverse=True)
            if files:
                briefing = json.loads(files[0].read_text(encoding="utf-8"))
                brief_text = json.dumps(briefing, indent=2)
                if len(brief_text) > 15000:
                    brief_text = brief_text[:15000] + "\n... [truncated]"
                context_parts.append("LATEST WORLD INTEL (" + files[0].name + "):\n" + brief_text)
            else:
                context_parts.append("WORLD INTEL: No cached reports.")
        else:
            context_parts.append("WORLD INTEL: No cached reports.")
    except Exception:
        context_parts.append("WORLD INTEL: Unavailable.")

    # Available tools
    context_parts.append("AVAILABLE TOOLS: " + ", ".join(sorted(TOOL_REGISTRY.keys())))

    # Roadmap status
    try:
        roadmap_file = THUNDERBIRD_DIR / "roadmap_status.md"
        if roadmap_file.exists():
            roadmap_text = roadmap_file.read_text(encoding="utf-8")
            if len(roadmap_text) > 20000:
                roadmap_text = roadmap_text[:20000] + "\n... [truncated]"
            context_parts.append("ROADMAP STATUS:\n" + roadmap_text)
    except Exception:
        context_parts.append("ROADMAP: Unavailable.")

    # Build enriched query with real data
    data_context = "\n\n".join(context_parts)
    enriched_query = (
        f"QUERY FROM JOHN:\n{query}\n\n"
        f"══════ REAL DATA (use ONLY this — do NOT invent data) ══════\n\n"
        f"{data_context}\n\n"
        f"══════ END REAL DATA ══════\n"
        f"Respond ONLY based on the real data above and your role's expertise. "
        f"If the data doesn't cover your area, say so honestly — do NOT fabricate numbers, "
        f"client names, metrics, or events."
    )

    result = run_staff_meeting(enriched_query, ids)
    return JSONResponse(result)


@app.get("/api/personas")
async def list_personas(x_api_key: str = Header(None)):
    """List all 12 D2M staff personas."""
    _verify_key(x_api_key)
    roster = []
    for pid, p in PERSONA_REGISTRY.items():
        roster.append({
            "id": pid,
            "name": p["name"],
            "role": p["role"],
            "icon": p["icon"],
            "voice": p.get("voice", ""),
        })
    return JSONResponse({"status": "success", "count": len(roster), "personas": roster})


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    port = 8766
    host = "0.0.0.0"

    for arg in sys.argv[1:]:
        if arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])
        elif arg.startswith("--host="):
            host = arg.split("=", 1)[1]

    logger.info(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    logger.info(f"Tools available: {len(TOOL_REGISTRY)}")
    logger.info(f"Starting Thunderbird API on {host}:{port}")

    uvicorn.run(app, host=host, port=port, log_level="info")
