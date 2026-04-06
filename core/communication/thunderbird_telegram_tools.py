"""
Thunderbird Telegram Tools — Claude Anthropic SDK + Full MCP Access
====================================================================

Gives the Telegram bot REAL operational capability via Claude Sonnet
tool use, backed by ALL 143 MCP tools plus local bonus tools.

Architecture:
  1. On load: auto-discovers all tools from the running MCP server
  2. Converts MCP inputSchemas → Claude-compatible tool format
  3. Adds local "bonus" tools (file access, web search, persona consult)
  4. Commander messages → Claude with tools → execute via MCP or local
  5. Multi-round tool calling loop until model has enough data to respond

Tool execution:
  - MCP tools → HTTP POST to localhost:8765/mcp (tools/call)
  - Local tools → direct Python execution (faster, no HTTP)

Cost: $0 (Max plan covers all Anthropic SDK usage)
"""

import glob
import json
import logging
import os
import re
import time
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("thunderbird_telegram_tools")

# ── Config ──
# Groq ELIMINATED — all calls route through Claude via Anthropic SDK ($0 on Max plan)
MCP_URL = "http://localhost:8765/mcp"
THUNDERBIRD_DIR = os.path.expanduser("~/Thunderbird")
MAX_TOOL_ROUNDS = 8  # generous for complex multi-step operations

# ── COS System Prompt ──
COS_SYSTEM_PROMPT = """You are Colonel Victoria "Iron Vic" Hale, Chief of Staff at Dreams2Memories Travel, LLC.

You are briefing the COMMANDER (John Loucks, callsign "Yoda") via Telegram.

RULES:
- You have REAL tools — over 140 of them. Use them to get REAL data before answering. NEVER fabricate data.
- If the Commander asks about bookings, dossiers, clients, hotels, flights, cruises — USE THE TOOLS.
- You have access to: Google Drive, Gmail, Sheets, Calendar, hotel search (Hotelbeds), flight search (Amadeus), cruise intelligence, tour search, browser automation, ship comparison, world intelligence, travel advisories, weather, and more.
- If you don't have a tool for something, say so honestly. Don't pretend.
- Present data in clean, scannable format. Include all relevant details.
- Be measured, authoritative, precise. You are COS — you brief with facts.
- Format for Telegram: use *bold* for emphasis, keep responses concise but complete.
- When multiple tools are needed, call them in sequence. You can call multiple tools per round.
- Currency is always USD. Dates in human-readable format.
- For web searches, use the web_search tool. For fetching specific pages, use fetch_webpage.
- For file operations, use read_file, write_file, list_files (local bonus tools — faster than Drive).
- To consult Wing personas (Naia, Dembe, Dani, Viper, Harlan, Padre, ELON), use consult_persona.

CURRENT DATE: """ + datetime.now().strftime("%Y-%m-%d") + """
WORKING DIRECTORY: ~/Thunderbird/
"""

# ── MCP tools to INCLUDE (curated for Telegram — most useful ops) ──
# Keep under ~60 to stay within Groq TPM limits
MCP_INCLUDE_TOOLS = {
    # Cruise intelligence
    "search_live_cruise_voyages", "check_cabin_availability",
    "run_ship_intelligence_sweep", "scrape_specific_cruise_line",
    "list_available_ships", "check_departure_prices",
    # World intel
    "run_world_intelligence_sweep", "get_travel_advisories",
    "get_port_weather_forecast", "get_cruise_industry_news",
    # Ship comparison
    "generate_ship_comparison_docx", "generate_ship_comparison_pdf",
    # Drive
    "drive_list_files", "drive_search", "drive_read_document",
    "drive_upload_file", "drive_create_folder",
    # Gmail
    "gmail_search_messages", "gmail_read_message", "gmail_read_thread",
    "gmail_create_draft", "draft_client_email", "send_client_email",
    # Hotels
    "search_hotels", "check_hotel_rates", "get_hotel_details", "compare_hotels",
    # Flights
    "search_flights", "verify_flight_price", "search_airports", "compare_flights",
    # Tours
    "search_tours", "search_tours_musement", "compare_tours",
    # Personas
    "run_staff_meeting", "list_personas",
    # Dossiers & bookings
    "create_trip_dossier_tool", "list_trip_dossiers",
    "compute_booking_anchors", "scan_anchor_dates",
    # Briefings & reports
    "send_morning_briefing", "generate_weekly_report",
    # OA / TESS
    "oa_scrape_bookings", "oa_scrape_commissions", "oa_status",
    "tess_list_trips", "tess_get_booking", "tess_search_bookings",
    "tess_get_commissions", "tess_list_clients",
    # Commission & finance
    "reconcile_commissions",
    # Fare watch
    "fare_watch_add", "fare_watch_check", "fare_watch_list",
    # Keep
    "keep_search_notes", "keep_list_notes", "keep_create_note",
    # Competitive & research
    "run_competitive_surveillance", "run_tech_monitor", "get_tech_news",
    # Calendar
    "sync_anchors_to_calendar",
    # Browser (fallback for web)
    "browse_url",
    # Client materials
    "generate_client_materials", "generate_destination_guide_tool",
}


# ====================================================================
# MCP Auto-Discovery — fetch all tools from running MCP server
# ====================================================================

def _fetch_mcp_tools() -> list[dict]:
    """Fetch tool list from the MCP server. Returns list of MCP tool defs."""
    try:
        resp = requests.post(
            MCP_URL,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        tools = data.get("result", {}).get("tools", [])
        logger.info(f"Discovered {len(tools)} MCP tools from server")
        return tools
    except Exception as e:
        logger.warning(f"MCP tool discovery failed (server may not be running): {e}")
        return []


def _clean_schema_for_groq(schema: dict) -> dict:
    """Clean MCP inputSchema for Claude tool use.

    Simplify anyOf/oneOf patterns and strip extra fields.
    Name kept for backward compat.
    """
    if not schema:
        return {"type": "object", "properties": {}}

    result = {}

    # Handle type
    raw_type = schema.get("type", "object")
    if isinstance(raw_type, list):
        raw_type = next((t for t in raw_type if t != "null"), "string")
    result["type"] = raw_type

    if "description" in schema:
        result["description"] = schema["description"][:300]
    if "enum" in schema:
        result["enum"] = [v for v in schema["enum"] if v is not None]

    if "properties" in schema:
        result["properties"] = {}
        for name, prop in schema["properties"].items():
            if "anyOf" in prop or "oneOf" in prop:
                options = prop.get("anyOf", prop.get("oneOf", []))
                simple = next((o for o in options if o.get("type") != "null"), {"type": "string"})
                simple["description"] = prop.get("description", simple.get("description", ""))
                result["properties"][name] = _clean_schema_for_groq(simple)
            else:
                result["properties"][name] = _clean_schema_for_groq(prop)

    if "required" in schema:
        result["required"] = schema["required"]
    if "items" in schema and result.get("type") == "array":
        result["items"] = _clean_schema_for_groq(schema["items"])
    if "default" in schema:
        result["description"] = result.get("description", "") + f" (default: {schema['default']})"

    return result


def _mcp_to_groq_tools(mcp_tools: list[dict]) -> list[dict]:
    """Convert MCP tool list → Claude tool format. Only includes curated tools. Name kept for backward compat."""
    tools = []
    for tool in mcp_tools:
        name = tool.get("name", "")
        if name not in MCP_INCLUDE_TOOLS:
            continue
        desc = tool.get("description", "No description")[:300]
        schema = _clean_schema_for_groq(tool.get("inputSchema", {}))
        if "type" not in schema:
            schema["type"] = "object"
        if "properties" not in schema:
            schema["properties"] = {}

        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": schema,
            }
        })
    return tools


def _call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Execute a tool via the MCP server HTTP endpoint."""
    try:
        resp = requests.post(
            MCP_URL,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=120,  # some tools (browser, API calls) take a while
        )
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            return f"MCP ERROR: {data['error'].get('message', 'Unknown error')}"

        result = data.get("result", {})
        # MCP returns content as list of {type, text} objects
        content_list = result.get("content", [])
        text_parts = [c.get("text", "") for c in content_list if c.get("type") == "text"]
        output = "\n".join(text_parts)

        if not output:
            # Try structuredContent fallback
            sc = result.get("structuredContent", {})
            if sc:
                output = json.dumps(sc, indent=2)

        return output or "Tool returned empty result."

    except requests.exceptions.Timeout:
        return f"MCP tool '{tool_name}' timed out after 120s."
    except Exception as e:
        return f"MCP tool execution failed: {e}"


# ====================================================================
# Local Bonus Tools — faster than MCP, plus capabilities MCP doesn't have
# ====================================================================

LOCAL_TOOL_DECLARATIONS = [
    {"type": "function", "function": {"name": "read_dossier", "description": "Read a client trip dossier by name or keyword", "parameters": {"type": "object", "properties": {"client_name": {"type": "string", "description": "Client name or trip keyword (e.g. 'Kuklinski', 'McLeod', 'Viking Panama')"}}, "required": ["client_name"]}}},
    {"type": "function", "function": {"name": "list_dossiers", "description": "List all trip dossiers", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read any file in ~/Thunderbird/", "parameters": {"type": "object", "properties": {"file_path": {"type": "string", "description": "Path relative to ~/Thunderbird/"}}, "required": ["file_path"]}}},
    {"type": "function", "function": {"name": "list_files", "description": "List files in a ~/Thunderbird/ directory", "parameters": {"type": "object", "properties": {"directory": {"type": "string", "description": "Directory relative to ~/Thunderbird/"}, "pattern": {"type": "string", "description": "Glob pattern e.g. '*.md'"}}}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write a file in ~/Thunderbird/", "parameters": {"type": "object", "properties": {"file_path": {"type": "string", "description": "Path relative to ~/Thunderbird/"}, "content": {"type": "string", "description": "Content to write"}}, "required": ["file_path", "content"]}}},
    {"type": "function", "function": {"name": "read_bookings", "description": "Read booking data from Sheets Booking Master", "parameters": {"type": "object", "properties": {"client_filter": {"type": "string", "description": "Client name filter (empty for all)"}}}}},
    {"type": "function", "function": {"name": "read_sheets_tab", "description": "Read a tab from the EARA Command Center sheet", "parameters": {"type": "object", "properties": {"tab_name": {"type": "string", "description": "Tab name (Booking Master, Clients, WAR_ROOM, etc.)"}, "row_limit": {"type": "integer", "description": "Max rows (default 50)"}}, "required": ["tab_name"]}}},
    {"type": "function", "function": {"name": "consult_persona", "description": "Consult a Wing persona for expert perspective", "parameters": {"type": "object", "properties": {"persona": {"type": "string", "description": "Persona ID: COS, EXEC, A2, A3, A5, A6, A9, CH, A12", "enum": ["COS", "EXEC", "A2", "A3", "A5", "A6", "A9", "CH", "A12"]}, "query": {"type": "string", "description": "Question or directive"}}, "required": ["persona", "query"]}}},
    {"type": "function", "function": {"name": "web_search", "description": "Search the web for current info — travel, cruise news, weather, etc.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "fetch_webpage", "description": "Fetch and read text content of a URL", "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "Full URL to fetch"}}, "required": ["url"]}}},
]


# ── Local tool execution functions ──

def _exec_read_dossier(client_name: str) -> str:
    dossier_dir = os.path.join(THUNDERBIRD_DIR, "dossiers")
    if not os.path.isdir(dossier_dir):
        return "ERROR: Dossier directory not found."
    pattern = os.path.join(dossier_dir, "DOSSIER_*.md")
    matches = []
    for f in sorted(glob.glob(pattern)):
        fname = os.path.basename(f).lower()
        search = client_name.lower().replace(" ", "")
        if search in fname.replace("_", ""):
            matches.append(f)
    if not matches:
        for f in sorted(glob.glob(pattern)):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    if client_name.lower() in fh.read(2000).lower():
                        matches.append(f)
            except Exception:
                pass
    if not matches:
        all_d = [os.path.basename(f) for f in glob.glob(pattern)]
        return f"No dossier matching '{client_name}'. Available: {', '.join(all_d)}"
    try:
        with open(matches[0], "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 15000:
            content = content[:15000] + "\n\n[TRUNCATED]"
        return f"FILE: {os.path.basename(matches[0])}\n\n{content}"
    except Exception as e:
        return f"ERROR: {e}"


def _exec_list_dossiers() -> str:
    pattern = os.path.join(THUNDERBIRD_DIR, "dossiers", "DOSSIER_*.md")
    files = sorted(glob.glob(pattern))
    if not files:
        return "No dossiers found."
    lines = ["Available trip dossiers:"]
    for f in files:
        lines.append(f"  - {os.path.basename(f)} ({os.path.getsize(f):,} bytes)")
    return "\n".join(lines)


def _exec_read_file(file_path: str) -> str:
    full = os.path.normpath(os.path.join(THUNDERBIRD_DIR, file_path))
    if not full.startswith(THUNDERBIRD_DIR):
        return "ERROR: Access denied."
    if not os.path.isfile(full):
        return f"ERROR: File not found: {file_path}"
    try:
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if len(content) > 15000:
            content = content[:15000] + "\n\n[TRUNCATED]"
        return content
    except Exception as e:
        return f"ERROR: {e}"


def _exec_list_files(directory: str = "", pattern: str = "") -> str:
    target = os.path.normpath(os.path.join(THUNDERBIRD_DIR, directory or ""))
    if not target.startswith(THUNDERBIRD_DIR):
        return "ERROR: Access denied."
    if not os.path.isdir(target):
        return f"ERROR: Directory not found: {directory}"
    if pattern:
        files = sorted(glob.glob(os.path.join(target, pattern)))
    else:
        files = [os.path.join(target, f) for f in sorted(os.listdir(target))]
    if not files:
        return f"No files in {directory or 'root'}."
    lines = [f"Files in {directory or '~/Thunderbird/'}:"]
    for f in files[:60]:
        name = os.path.basename(f)
        if os.path.isdir(f):
            lines.append(f"  [DIR] {name}/")
        else:
            lines.append(f"  {name} ({os.path.getsize(f):,} bytes)")
    if len(files) > 60:
        lines.append(f"  ... and {len(files) - 60} more")
    return "\n".join(lines)


def _exec_write_file(file_path: str, content: str) -> str:
    full = os.path.normpath(os.path.join(THUNDERBIRD_DIR, file_path))
    if not full.startswith(THUNDERBIRD_DIR):
        return "ERROR: Access denied."
    try:
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File written: {file_path} ({len(content)} chars)"
    except Exception as e:
        return f"ERROR: {e}"


def _exec_read_bookings(client_filter: str = "") -> str:
    try:
        from thunderbird_dani_engine import _gather_bookings, _fetch_all_tabs_summary
        if client_filter:
            return _gather_bookings([client_filter])
        else:
            return _fetch_all_tabs_summary()
    except Exception as e:
        return f"ERROR reading bookings: {e}"


def _exec_read_sheets_tab(tab_name: str, row_limit: int = 50) -> str:
    try:
        import gspread
        gc = gspread.service_account(filename=os.path.join(THUNDERBIRD_DIR, "credentials.json"))
        sh = gc.open_by_key("1RIOIFmmI4u4OSPA00HaBPPI9DnEftYBcS0TXWQ21ueU")
        try:
            ws = sh.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            tabs = [w.title for w in sh.worksheets()]
            return f"Tab '{tab_name}' not found. Available: {', '.join(tabs)}"
        rows = ws.get_all_values()
        if not rows:
            return f"Tab '{tab_name}' is empty."
        header = rows[0]
        data_rows = rows[1:row_limit + 1]
        lines = [f"Tab: {tab_name} ({len(rows) - 1} rows, showing {len(data_rows)})\n"]
        if header:
            lines.append("COLUMNS: " + " | ".join(str(h) for h in header[:15]))
            lines.append("")
        for i, row in enumerate(data_rows):
            lines.append(f"Row {i+1}: " + " | ".join(str(c)[:40] for c in row[:15]))
        if len(rows) - 1 > row_limit:
            lines.append(f"\n[{row_limit} of {len(rows)-1} rows shown]")
        result = "\n".join(lines)
        return result[:12000] if len(result) > 12000 else result
    except Exception as e:
        return f"ERROR: {e}"


def _exec_consult_persona(persona: str, query: str) -> str:
    try:
        from thunderbird_personas import call_persona, resolve_id
        pid = resolve_id(persona)
        result = call_persona(pid, query, max_tokens=800)
        return f"{result.get('icon','')} {result.get('name', persona)}:\n\n{result.get('answer', 'No response')}"
    except Exception as e:
        return f"ERROR consulting {persona}: {e}"


def _exec_web_search(query: str) -> str:
    """Web search using Google Custom Search API or fallback to Gemini grounding."""
    # Try Google Custom Search if available
    google_cse_key = os.environ.get("GOOGLE_CSE_API_KEY", "")
    google_cse_cx = os.environ.get("GOOGLE_CSE_CX", "")

    if google_cse_key and google_cse_cx:
        try:
            resp = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": google_cse_key, "cx": google_cse_cx, "q": query, "num": 5},
                timeout=10,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if items:
                lines = [f"Web search: '{query}'\n"]
                for item in items:
                    lines.append(f"  - {item.get('title', '?')}")
                    lines.append(f"    {item.get('link', '')}")
                    lines.append(f"    {item.get('snippet', '')}\n")
                return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Google CSE failed: {e}")

    # Fallback: use a simple DuckDuckGo HTML scrape
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
            timeout=10,
        )
        resp.raise_for_status()
        # Extract result snippets from the HTML
        results = []
        # Simple regex extraction of result titles and snippets
        titles = re.findall(r'class="result__a"[^>]*>([^<]+)</a>', resp.text)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</span>', resp.text, re.DOTALL)
        urls = re.findall(r'class="result__url"[^>]*>\s*(.*?)\s*</a>', resp.text, re.DOTALL)

        if titles:
            lines = [f"Web search: '{query}'\n"]
            for i in range(min(5, len(titles))):
                title = re.sub(r'<[^>]+>', '', titles[i]).strip()
                snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
                url = re.sub(r'<[^>]+>', '', urls[i]).strip() if i < len(urls) else ""
                lines.append(f"  {i+1}. {title}")
                if url:
                    lines.append(f"     {url}")
                if snippet:
                    lines.append(f"     {snippet}")
                lines.append("")
            return "\n".join(lines)
        return f"Web search for '{query}' returned no results."
    except Exception as e:
        return f"Web search failed: {e}. Try using the browse_stealth MCP tool instead."


def _exec_fetch_webpage(url: str) -> str:
    """Fetch a webpage and return text content."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
            timeout=15,
        )
        resp.raise_for_status()
        # Strip HTML tags for a rough text extraction
        text = re.sub(r'<script[^>]*>.*?</script>', '', resp.text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 10000:
            text = text[:10000] + "\n[TRUNCATED]"
        return f"URL: {url}\n\n{text}"
    except Exception as e:
        return f"ERROR fetching {url}: {e}"


# ── Local tool dispatch ──
LOCAL_TOOL_DISPATCH = {
    "read_dossier": lambda a: _exec_read_dossier(a.get("client_name", "")),
    "list_dossiers": lambda a: _exec_list_dossiers(),
    "read_file": lambda a: _exec_read_file(a.get("file_path", "")),
    "list_files": lambda a: _exec_list_files(a.get("directory", ""), a.get("pattern", "")),
    "write_file": lambda a: _exec_write_file(a.get("file_path", ""), a.get("content", "")),
    "read_bookings": lambda a: _exec_read_bookings(a.get("client_filter", "")),
    "read_sheets_tab": lambda a: _exec_read_sheets_tab(a.get("tab_name", ""), int(a.get("row_limit", 50))),
    "consult_persona": lambda a: _exec_consult_persona(a.get("persona", "COS"), a.get("query", "")),
    "web_search": lambda a: _exec_web_search(a.get("query", "")),
    "fetch_webpage": lambda a: _exec_fetch_webpage(a.get("url", "")),
}


# ====================================================================
# Tool Registry — built at module load
# ====================================================================

# Discover MCP tools
_mcp_tools_raw = _fetch_mcp_tools()
_mcp_groq_tools = _mcp_to_groq_tools(_mcp_tools_raw)
_mcp_tool_names = {t["function"]["name"] for t in _mcp_groq_tools}

# Local tool names (these override MCP if there's a name conflict)
_local_tool_names = set(LOCAL_TOOL_DISPATCH.keys())

# Filter out MCP tools that have a local override
_mcp_tools_filtered = [t for t in _mcp_groq_tools if t["function"]["name"] not in _local_tool_names]

# Combined tools: local first, then MCP
ALL_TOOLS = LOCAL_TOOL_DECLARATIONS + _mcp_tools_filtered

logger.info(
    f"Tool registry: {len(LOCAL_TOOL_DECLARATIONS)} local + "
    f"{len(_mcp_tools_filtered)} MCP = {len(ALL_TOOLS)} total"
)


def _execute_tool(tool_name: str, tool_args: dict) -> str:
    """Execute a tool — local dispatch first, then MCP."""
    if tool_name in LOCAL_TOOL_DISPATCH:
        try:
            return LOCAL_TOOL_DISPATCH[tool_name](tool_args)
        except Exception as e:
            logger.error(f"Local tool {tool_name} crashed: {e}")
            return f"ERROR: {e}"
    elif tool_name in _mcp_tool_names:
        return _call_mcp_tool(tool_name, tool_args)
    else:
        return f"ERROR: Unknown tool '{tool_name}'"


# ====================================================================
# Claude Tool-Calling Loop (Anthropic SDK)
# ====================================================================

def call_cos_with_tools(query: str, conversation_history: list[dict] = None) -> str:
    """Send a Commander query to Claude with ALL tools. Returns final text response.

    Main entry point called from thunderbird_telegram.py.
    Handles the full tool-calling loop: send → execute tools → return results → repeat.
    Groq ELIMINATED — uses Anthropic SDK ($0 on Max plan).
    """
    import anthropic

    # Convert OpenAI-style tool declarations to Claude tool format
    claude_tools = []
    for t in ALL_TOOLS:
        func = t.get("function", {})
        claude_tools.append({
            "name": func["name"],
            "description": func.get("description", ""),
            "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
        })

    # Build messages
    messages = []

    if conversation_history:
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["text"]})

    messages.append({"role": "user", "content": query})

    client = anthropic.Anthropic()

    for round_num in range(MAX_TOOL_ROUNDS):
        try:
            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                system=COS_SYSTEM_PROMPT,
                messages=messages,
                tools=claude_tools,
                temperature=0.3,
            )
        except Exception as e:
            logger.error(f"Anthropic SDK error: {e}")
            return f"COS reporting: API error — {e}"

        # Check if we got tool use blocks
        tool_use_blocks = [b for b in resp.content if b.type == "tool_use"]
        text_blocks = [b for b in resp.content if b.type == "text"]

        if not tool_use_blocks or resp.stop_reason == "end_turn":
            # Final text response
            final = " ".join(b.text for b in text_blocks).strip()
            if not final:
                return "COS reporting: No text in response."
            logger.info(f"COS response ready (round {round_num + 1})")
            return final

        # Execute tool calls
        logger.info(f"Round {round_num + 1}: {len(tool_use_blocks)} tool call(s)")

        # Add assistant message to conversation
        messages.append({"role": "assistant", "content": resp.content})

        # Execute each tool and add results
        tool_results = []
        for block in tool_use_blocks:
            tool_name = block.name
            tool_args = block.input or {}

            logger.info(f"  Tool: {tool_name}({json.dumps(tool_args)[:120]})")
            result = _execute_tool(tool_name, tool_args)

            # Truncate huge results
            if len(result) > 8000:
                result = result[:8000] + "\n\n[TRUNCATED]"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

    return "COS reporting: Max tool rounds reached."


# ====================================================================
# Quick test
# ====================================================================

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "List all dossiers"
    print(f"\nQuery: {query}\n{'=' * 50}")
    result = call_cos_with_tools(query)
    print(f"\n{result}")
