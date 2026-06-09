#!/usr/bin/env python3
"""
Thunderbird Core MCP Server
JSON-RPC 2.0 over stdio — MCP protocol 2024-11-05
"""
import json
import sys
from typing import Any, Dict, List

TOOL_REGISTRY = {
    "travel": {
        "search_flights": "Search flights across providers",
        "search_hotels": "Search hotels worldwide",
        "search_tours": "Search shore excursions",
        "check_cabin_availability": "Check cruise cabin availability",
        "fare_watch_add": "Add price watch for flights/cruises",
        "fare_watch_check": "Check current watched prices",
        "fare_watch_history": "Get price history for watched fares",
    },
    "dossier": {
        "create_trip_dossier": "Create client trip dossier",
        "list_dossiers": "List all trip dossiers",
        "sync_dossier_files": "Sync dossier files to Drive",
        "scan_dossiers": "Scan for booking discrepancies",
    },
    "email": {
        "gmail_create_draft": "Create Gmail draft",
        "gmail_send_email": "Send email via Gmail",
        "draft_client_email": "Draft client-facing email with Dani chain",
        "send_client_email": "Send validated client email",
    },
    "itinerary": {
        "generate_itinerary": "Generate luxury itinerary",
        "trip_architect": "Run trip architecture pipeline",
        "generate_destination_guide": "Create destination guide",
        "run_itinerary_pipeline": "Full itinerary generation pipeline",
    },
    "quotes": {
        "render_flight_quote_pdf": "Render flight quote PDF",
        "render_hotel_quote_pdf": "Render hotel quote PDF",
        "email_quote": "Email quote to client",
    },
    "tess": {
        "tess_create_booking": "Create TESS booking",
        "tess_get_client": "Retrieve client from TESS",
        "tess_update_booking": "Update booking in TESS",
    },
    "system": {
        "system_health_check": "Check system health",
        "mcp_status": "Check MCP server status",
    },
}


def _build_tools() -> List[Dict[str, Any]]:
    tools = []
    for category, items in TOOL_REGISTRY.items():
        for name, description in items.items():
            tools.append({
                "name": name,
                "description": f"[{category}] {description}",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Tool input"}
                    }
                }
            })
    return tools


def _send(obj: Dict[str, Any]) -> None:
    print(json.dumps(obj), flush=True)


def main():
    """MCP server main loop — JSON-RPC 2.0 over stdio."""
    if len(sys.argv) > 1 and sys.argv[1] == "--list-tools":
        print(json.dumps({"tools": _build_tools()}, indent=2))
        return

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            continue

        method = req.get("method", "")
        req_id = req.get("id")

        # Notifications have no id — no response needed
        if req_id is None:
            continue

        if method == "initialize":
            _send({
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "thunderbird-core", "version": "1.0.0"}
                }
            })
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": req_id, "result": {"tools": _build_tools()}})
        elif method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name", "")
            args = params.get("arguments", {})
            _send({
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "status": "pending",
                            "message": f"Tool '{tool_name}' queued for execution",
                            "tool": tool_name, "args": args
                        })
                    }]
                }
            })
        else:
            _send({
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            })


if __name__ == "__main__":
    main()
