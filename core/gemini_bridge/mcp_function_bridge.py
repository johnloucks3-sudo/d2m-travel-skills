"""
Gemini MCP Function-Calling Bridge
===================================
2026-07-12 — Commander directive: "using gemini to do the MCP work, claude
code still owns and manages python."

Gemini becomes an ADDITIONAL caller of the same tool implementations Claude
Code already calls via MCP — it does not replace Claude Code, and Claude
Code remains the sole author/maintainer of this bridge and the tools
themselves. Runs on the existing AI-Studio free-tier GEMINI_API_KEY by
default (see core/ai_infra/gemini_client.py — same allowlist + cost-gate
chokepoint every other Gemini call in this codebase goes through). A Vertex
AI mode is a later, separate switch (needs `gcloud auth application-default
login` — a human step, deferred until the Commander wants that path).

SAFETY: only a narrow, explicit allowlist of read-only/research tools is
exposed to Gemini's function-calling. Anything that sends, books, pays,
deletes, or writes client-facing content stays OFF by default — those match
the same Three Gates that already bind Claude Code (client send, financial
commitment, strategic >90d/>$5K are Commander-only). Expand the allowlist
deliberately, tool by tool, not by relaxing the filter.
"""
import asyncio
import json
import logging
from pathlib import Path

from core.ai_infra.gemini_client import call_gemini_with_tools

logger = logging.getLogger("thunderbird.gemini_bridge")

ROOT = Path(__file__).resolve().parent.parent.parent
CATALOG_PATH = ROOT / "docs" / "mcp_tool_catalog.json"

# ---------------------------------------------------------------------------
# Safe allowlist — read-only / research tools only. Starting narrow on
# purpose; expand by adding names here, never by weakening the mechanism.
# ---------------------------------------------------------------------------
SAFE_ALLOWLIST = {
    # Flights (read/search/compare/track only)
    "search_flights", "google_flights_search_airport",
    "search_centrav_flights", "compare_flights", "track_flight_flightaware",
    "track_flight_fr24", "get_airport_flights_fr24", "get_airport_info_flightaware",
    "search_airports", "verify_flight_price", "get_most_tracked_fr24",
    # Tours / excursions / hotels / dining / transfers (search only)
    "search_tours", "compare_tours", "search_tours_musement",
    "search_viator_excursions", "search_getyourguide_excursions",
    "search_shore_excursions_group", "search_taap_hotels", "get_taap_hotel_rates",
    "search_opentable_restaurants", "get_opentable_reservation_link",
    "search_blacklane_transfers", "search_mozio_transfers", "search_welcome_pickups",
    "search_live_cruise_voyages",
    # Intel / research
    "get_country_intel", "get_port_city_intel", "dossier_alert_digest",
    "scan_dossiers", "list_trip_dossiers", "list_dossier_files",
    "academic_scan", "run_innovation_scan", "innovation_daily_scan",
    "innovation_weekly_scan", "get_innovation_digest", "innovation_briefing_digest",
    "data_confidence_report", "query_decision_log",
    # Memory (search only — no set/write)
    "search_memory_semantic", "memory_search", "memory_stats",
    "recall_by_context", "wing_memory_search",
    # Calendar / Drive / Sheets (read only — no create/upload/delete/write)
    "calendar_list_events", "calendar_sync_status",
    "drive_search", "drive_list_files", "drive_get_file_info", "drive_read_document",
    "sheets_read_data", "sheets_list_sheets", "sheets_get_spreadsheet_info",
    # Gmail (read only — no send/trash/modify/create_draft)
    "gmail_search_messages", "gmail_read_message", "gmail_read_thread",
    "gmail_list_labels", "gmail_list_drafts", "gmail_get_profile", "gmail_dual_search",
    # System / ops visibility
    "system_health_check", "mcp_connector_status", "mcp_connector_tools_list",
    "check_oauth_health",
    # Maps
    "maps_geocode", "maps_place_details", "maps_places_search",
    "maps_distance_matrix", "maps_static_map_url",
    # Personas / skills metadata
    "list_personas", "get_persona", "list_available_skills_tool", "get_skill_metadata_tool",
}

_TYPE_MAP = {
    "str": "STRING", "int": "INTEGER", "float": "NUMBER", "bool": "BOOLEAN",
    "list": "ARRAY", "dict": "OBJECT",
}


def _normalize_type(raw: str) -> str:
    """Python type-hint string ('Optional[List[str]]', 'int', ...) -> Gemini
    JSON-Schema type string. Optional[] is stripped — required-ness already
    comes from the catalog's own `required` field."""
    t = raw or "str"
    t = t.replace("Optional[", "").rstrip("]") if t.startswith("Optional[") else t
    if t.startswith("List[") or t == "list":
        return "ARRAY"
    return _TYPE_MAP.get(t, "STRING")


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text())["tools"]


def _tool_to_function_declaration(name: str, spec: dict) -> dict:
    properties = {}
    required = []
    for p in spec.get("parameters", []):
        properties[p["name"]] = {
            "type": _normalize_type(p["type"]),
            "description": p.get("description") or "",
        }
        if p.get("required"):
            required.append(p["name"])
    decl = {
        "name": name,
        "description": (spec.get("description") or "")[:1000],
        "parameters": {"type": "OBJECT", "properties": properties},
    }
    if required:
        decl["parameters"]["required"] = required
    return decl


def build_function_declarations(names: set | None = None) -> list:
    """Gemini functionDeclarations for the given tool names (default: the
    safe allowlist). Silently skips any name not in the catalog or not on
    the allowlist — this is the enforcement point, not just documentation."""
    catalog = load_catalog()
    allowed = names if names is not None else SAFE_ALLOWLIST
    allowed = allowed & SAFE_ALLOWLIST  # allowlist always wins, even if caller passes more
    return [
        _tool_to_function_declaration(n, catalog[n])
        for n in sorted(allowed) if n in catalog
    ]


_SERVER = None  # lazy singleton — importing travel_mcp_server takes ~5s and
                # has real side effects (Telegram/Google auth wiring), so it
                # must happen at most once per process, not once per call.


def _get_server():
    """The SAME live FastMCP object Claude Code's own MCP tools call into —
    not a reimplementation. Tools here are registered as closures inside
    register_*_tools(mcp) at module import time, not as plain module
    attributes, so this is the only correct way to invoke one by name."""
    global _SERVER
    if _SERVER is None:
        import core.mcp.travel_mcp_server as srv
        _SERVER = srv.mcp
    return _SERVER


def dispatch_tool_call(name: str, args: dict) -> dict:
    """Execute a Gemini-requested tool call against the real, live MCP tool
    implementation (the identical one Claude Code calls). Refuses anything
    off the safe allowlist even if a caller somehow got Gemini to name it —
    the allowlist is enforced here too, not just at declaration-build time."""
    if name not in SAFE_ALLOWLIST:
        return {"error": f"'{name}' is not on the Gemini bridge safe allowlist — refused."}

    try:
        server = _get_server()
        raw = asyncio.run(server.call_tool(name, args))
        content = raw[0] if isinstance(raw, tuple) else raw
        if isinstance(content, dict):
            return {"result": content}
        texts = [getattr(block, "text", str(block)) for block in content]
        return {"result": "\n".join(texts)}
    except Exception as e:
        logger.error("gemini_bridge: dispatch failed for %s: %s", name, e)
        return {"error": f"{type(e).__name__}: {e}"}


def run(
    user_prompt: str,
    system_prompt: str | None = None,
    model: str = "gemini-2.5-flash",
    allowlist_names: set | None = None,
    caller: str = "gemini_bridge",
) -> dict:
    """One user turn, one round of Gemini function-calling. If Gemini calls a
    tool, dispatches it and makes a second call so Gemini can produce a final
    answer grounded in the real result. Returns an audit-friendly dict —
    never silently swallows which tool ran."""
    system_prompt = system_prompt or (
        "You are a research assistant with access to read-only travel/ops "
        "tools. Call a tool when it would answer the question; otherwise "
        "answer directly. You cannot send anything, book anything, or "
        "modify any record — those tools are not available to you."
    )
    declarations = build_function_declarations(allowlist_names)
    contents = [{"role": "user", "parts": [{"text": user_prompt}]}]

    first = call_gemini_with_tools(
        system_prompt, contents, declarations, model=model,
        caller=caller, task_hint=user_prompt[:80],
    )

    if "text" in first:
        return {"final_text": first["text"], "tool_calls": []}

    fc = first["function_call"]
    logger.info("gemini_bridge: tool call requested: %s(%s)", fc["name"], fc["args"])
    tool_result = dispatch_tool_call(fc["name"], fc["args"])

    contents.append({"role": "model", "parts": [{"functionCall": {"name": fc["name"], "args": fc["args"]}}]})
    contents.append({"role": "user", "parts": [{"functionResponse": {"name": fc["name"], "response": tool_result}}]})

    second = call_gemini_with_tools(
        system_prompt, contents, declarations, model=model,
        caller=caller, task_hint=f"[round2] {user_prompt[:70]}",
    )

    final_text = second.get("text", "")
    return {
        "final_text": final_text,
        "tool_calls": [{"name": fc["name"], "args": fc["args"], "result": tool_result}],
    }
