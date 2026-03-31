"""
Thunderbird Groq MCP Connectors — Google Workspace via Groq Remote MCP
=======================================================================

Dreams2Memories Travel, LLC · Thunderbird OS

Wraps Groq's Remote MCP Connectors (Gmail, Calendar, Drive) as local MCP
tools.  Groq's Responses API handles the tool orchestration server-side —
we send a natural-language query plus connector config, Groq calls the
Google APIs, and we get structured results back.

OAuth tokens are auto-refreshed from the existing Thunderbird credential
files (gmail_token.json / credentials.json).

Architecture:
  Any MCP client (Claude, Goose, Cline)
      ↓  tool call
  travel_mcp_server.py  (this module registered here)
      ↓  HTTP POST
  Groq Responses API  (/openai/v1/responses)
      ↓  server-side MCP
  Google Workspace  (Gmail / Calendar / Drive)
      ↓
  Structured result returned

Requires: GROQ_API_KEY in environment or .env
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path(__file__).parent

# ── Configuration ────────────────────────────────────────────────────────────

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_RESPONSES_URL = "https://api.groq.com/openai/v1/responses"

# Default model for connector queries — must handle tool-use types correctly
# llama-4-scout has type coercion bugs (sends "5" not 5); qwen3-32b is reliable
GROQ_CONNECTOR_MODEL = os.environ.get(
    "GROQ_CONNECTOR_MODEL", "qwen/qwen3-32b"
)
GROQ_CONNECTOR_FALLBACK_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Google OAuth files (shared with thunderbird_gmail.py)
TOKEN_FILE = THUNDERBIRD_DIR / "gmail_token.json"
CREDENTIALS_FILE = THUNDERBIRD_DIR / "credentials.json"

# Connector definitions
CONNECTORS = {
    "gmail": {
        "connector_id": "connector_gmail",
        "server_label": "Gmail",
        "description": "Search and read emails from d2mconcierge@gmail.com",
        "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
    },
    "calendar": {
        "connector_id": "connector_googlecalendar",
        "server_label": "Google Calendar",
        "description": "View and search calendar events",
        "scopes": ["https://www.googleapis.com/auth/calendar.events"],
    },
    "drive": {
        "connector_id": "connector_googledrive",
        "server_label": "Google Drive",
        "description": "Search and access files in D2M Google Drive",
        "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
    },
}


# ── OAuth Token Management ───────────────────────────────────────────────────

_cached_token: Optional[str] = None
_token_expiry: float = 0


def _get_google_access_token() -> str:
    """
    Get a valid Google OAuth access token, refreshing if expired.

    Uses the same token file as thunderbird_gmail.py (gmail_token.json).
    """
    global _cached_token, _token_expiry

    # Return cached if still valid (with 5-min buffer)
    if _cached_token and time.time() < (_token_expiry - 300):
        return _cached_token

    if not TOKEN_FILE.exists():
        raise RuntimeError(
            f"Google OAuth token file not found: {TOKEN_FILE}. "
            "Run thunderbird_gmail.py first to authorize."
        )

    token_data = json.loads(TOKEN_FILE.read_text())

    # Parse expiry so Credentials knows when to refresh
    expiry = None
    expiry_str = token_data.get("expiry", "")
    if expiry_str:
        try:
            # Strip trailing Z, parse ISO
            expiry = datetime.fromisoformat(expiry_str.rstrip("Z"))
        except (ValueError, TypeError):
            pass

    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes"),
        expiry=expiry,
    )

    if creds.expired or not creds.valid:
        logger.info("Google OAuth token expired — refreshing...")
        creds.refresh(GoogleAuthRequest())

        # Write refreshed token back
        refreshed = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else token_data.get("scopes", []),
            "universe_domain": token_data.get("universe_domain", "googleapis.com"),
            "account": token_data.get("account", ""),
            "expiry": creds.expiry.isoformat() + "Z" if creds.expiry else "",
        }
        TOKEN_FILE.write_text(json.dumps(refreshed))
        logger.info("Google OAuth token refreshed and saved.")

    _cached_token = creds.token
    # Parse expiry for caching
    if creds.expiry:
        _token_expiry = creds.expiry.timestamp()
    else:
        _token_expiry = time.time() + 3500  # ~1 hour default

    return _cached_token


# ── Groq Responses API Client ───────────────────────────────────────────────

async def _call_groq_connector(
    connector_key: str,
    query: str,
    model: Optional[str] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Call a Groq Remote MCP Connector.

    Args:
        connector_key: One of 'gmail', 'calendar', 'drive'
        query: Natural language query for the connector
        model: Override the default Groq model
        timeout: Request timeout in seconds

    Returns:
        Parsed response with connector results
    """
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY not set. Add it to .env or environment."
        )

    connector = CONNECTORS.get(connector_key)
    if not connector:
        raise ValueError(
            f"Unknown connector: {connector_key}. "
            f"Available: {list(CONNECTORS.keys())}"
        )

    # Get fresh Google OAuth token
    access_token = _get_google_access_token()

    payload = {
        "model": model or GROQ_CONNECTOR_MODEL,
        "tools": [
            {
                "type": "mcp",
                "server_label": connector["server_label"],
                "connector_id": connector["connector_id"],
                "authorization": access_token,
                "require_approval": "never",
            }
        ],
        "input": query,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(GROQ_RESPONSES_URL, json=payload, headers=headers)

        if resp.status_code == 424:
            raise RuntimeError(
                f"Groq connector failed (424): credentials expired or server unavailable. "
                f"Response: {resp.text[:500]}"
            )

        # 400 with tool_use_failed = model type-coercion bug; retry with fallback
        if resp.status_code == 400 and "tool_use_failed" in resp.text:
            fallback = GROQ_CONNECTOR_FALLBACK_MODEL
            if payload["model"] != fallback:
                logger.warning(
                    f"Groq connector 400 (type bug) with {payload['model']}; "
                    f"retrying with {fallback}"
                )
                payload["model"] = fallback
                resp = await client.post(
                    GROQ_RESPONSES_URL, json=payload, headers=headers
                )

        resp.raise_for_status()
        result = resp.json()

    return _parse_connector_response(result, connector_key)


def _parse_connector_response(
    response: Dict[str, Any], connector_key: str
) -> Dict[str, Any]:
    """Extract structured data from Groq Responses API output."""
    output_items = response.get("output", [])

    parsed = {
        "connector": connector_key,
        "model": response.get("model", ""),
        "status": response.get("status", "unknown"),
        "tool_calls": [],
        "message": "",
        "raw_output_count": len(output_items),
    }

    for item in output_items:
        item_type = item.get("type", "")

        if item_type == "mcp_call":
            parsed["tool_calls"].append({
                "tool": item.get("name", ""),
                "server": item.get("server_label", ""),
                "arguments": item.get("arguments", ""),
                "output": item.get("output", ""),
            })

        elif item_type == "message":
            content = item.get("content", [])
            for block in content:
                if block.get("type") == "output_text":
                    parsed["message"] = block.get("text", "")

        elif item_type == "mcp_list_tools":
            parsed["available_tools"] = [
                t.get("name", "") for t in item.get("tools", [])
            ]

    return parsed


# ── Multi-Connector Query ────────────────────────────────────────────────────

async def _call_groq_multi_connector(
    connector_keys: List[str],
    query: str,
    model: Optional[str] = None,
    timeout: float = 90.0,
) -> Dict[str, Any]:
    """
    Call multiple Groq connectors in a single request.

    Groq supports multiple tools in one request — the LLM decides which
    connectors to use based on the query.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set.")

    access_token = _get_google_access_token()

    tools = []
    for key in connector_keys:
        connector = CONNECTORS.get(key)
        if not connector:
            continue
        tools.append({
            "type": "mcp",
            "server_label": connector["server_label"],
            "connector_id": connector["connector_id"],
            "authorization": access_token,
            "require_approval": "never",
        })

    if not tools:
        raise ValueError(f"No valid connectors in: {connector_keys}")

    payload = {
        "model": model or GROQ_CONNECTOR_MODEL,
        "tools": tools,
        "input": query,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(GROQ_RESPONSES_URL, json=payload, headers=headers)
        resp.raise_for_status()
        result = resp.json()

    return _parse_connector_response(result, "+".join(connector_keys))


# ── MCP Tool Registration ───────────────────────────────────────────────────

def register_groq_connector_tools(mcp_server):
    """Register Groq MCP Connector tools on the FastMCP server."""

    @mcp_server.tool(
        name="groq_gmail_query",
        annotations={"title": "Groq → Gmail Connector", "readOnlyHint": True},
    )
    async def groq_gmail_query(
        query: str,
    ) -> str:
        """Search or read Gmail via Groq's remote MCP connector.

        Uses Groq's server-side Gmail integration — bypasses local MCP for
        email reads. Good for quick lookups when local Gmail MCP is unavailable.

        Args:
            query: Natural language query, e.g. "Show unread emails from this week"
                   or "Find emails from Silversea about bookings"
        """
        try:
            result = await _call_groq_connector("gmail", query)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "connector": "gmail"}, indent=2)

    @mcp_server.tool(
        name="groq_calendar_query",
        annotations={"title": "Groq → Calendar Connector", "readOnlyHint": True},
    )
    async def groq_calendar_query(
        query: str,
    ) -> str:
        """Search or view Google Calendar via Groq's remote MCP connector.

        Uses Groq's server-side Calendar integration. Good for checking
        upcoming events, deadlines, and booking dates.

        Args:
            query: Natural language query, e.g. "What's on my calendar this week?"
                   or "Find events related to Furlow booking"
        """
        try:
            result = await _call_groq_connector("calendar", query)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "connector": "calendar"}, indent=2)

    @mcp_server.tool(
        name="groq_drive_query",
        annotations={"title": "Groq → Drive Connector", "readOnlyHint": True},
    )
    async def groq_drive_query(
        query: str,
    ) -> str:
        """Search or access Google Drive via Groq's remote MCP connector.

        Uses Groq's server-side Drive integration. Good for finding files,
        reading documents, and checking recent uploads.

        Args:
            query: Natural language query, e.g. "Find recent trip dossiers"
                   or "Search for Westbrook itinerary files"
        """
        try:
            result = await _call_groq_connector("drive", query)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "connector": "drive"}, indent=2)

    @mcp_server.tool(
        name="groq_workspace_query",
        annotations={"title": "Groq → Google Workspace (Multi)", "readOnlyHint": True},
    )
    async def groq_workspace_query(
        query: str,
        connectors: str = "gmail,calendar,drive",
    ) -> str:
        """Query multiple Google Workspace services in one shot via Groq.

        Sends your query to Groq with all specified connectors enabled.
        The LLM decides which services to call based on context.

        Args:
            query: Natural language query spanning multiple services, e.g.
                   "Do I have any emails about the meeting on Thursday?"
            connectors: Comma-separated list of connectors to enable.
                        Options: gmail, calendar, drive. Default: all three.
        """
        try:
            keys = [k.strip() for k in connectors.split(",") if k.strip()]
            result = await _call_groq_multi_connector(keys, query)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "connector": "multi"}, indent=2)

    @mcp_server.tool(
        name="groq_connector_status",
        annotations={"title": "Groq Connector Status", "readOnlyHint": True},
    )
    async def groq_connector_status() -> str:
        """Check Groq MCP connector health and OAuth token status.

        Verifies: GROQ_API_KEY present, Google OAuth token valid/refreshable,
        available connectors. Use to diagnose connector issues.
        """
        status = {
            "groq_api_key": "set" if GROQ_API_KEY else "MISSING",
            "groq_model": GROQ_CONNECTOR_MODEL,
            "groq_endpoint": GROQ_RESPONSES_URL,
            "token_file": str(TOKEN_FILE),
            "token_file_exists": TOKEN_FILE.exists(),
            "connectors": {},
        }

        # Check OAuth token
        try:
            token = _get_google_access_token()
            status["google_oauth"] = "valid"
            status["token_preview"] = token[:20] + "..." if token else "empty"
            status["token_expiry_utc"] = (
                datetime.utcfromtimestamp(_token_expiry).isoformat()
                if _token_expiry else "unknown"
            )
        except Exception as e:
            status["google_oauth"] = f"error: {e}"

        for key, cfg in CONNECTORS.items():
            status["connectors"][key] = {
                "connector_id": cfg["connector_id"],
                "server_label": cfg["server_label"],
                "description": cfg["description"],
            }

        return json.dumps(status, indent=2)

    logger.info("Groq MCP Connector tools registered (5 tools)")
