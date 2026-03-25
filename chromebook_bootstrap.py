#!/usr/bin/env python3
"""
Chromebook Bootstrap — YOGA MCP Tool Discovery
================================================
Run this on the Chromebook to discover all 154+ tools available
on YOGA's MCP Streamable HTTP server. Outputs a categorized
tool catalog that can be fed to Claude as context.

Usage:
  python3 chromebook_bootstrap.py                    # Auto-detect YOGA
  python3 chromebook_bootstrap.py --host 100.69.222.124  # Tailscale IP
  python3 chromebook_bootstrap.py --host mcp.d2mluxury.quest  # Tunnel
  python3 chromebook_bootstrap.py --dump             # Full JSON dump
  python3 chromebook_bootstrap.py --claude            # Output for Claude context
"""

import json
import sys
import requests

# YOGA connection options (tried in order)
YOGA_ENDPOINTS = [
    "http://100.69.222.124:8765/mcp",      # Tailscale (fastest, Japan-ready)
    "http://192.168.1.198:8765/mcp",           # LAN
    "https://mcp.d2mluxury.quest/mcp",     # Cloudflare tunnel (fallback)
]


def connect_mcp(base_url: str) -> tuple:
    """Initialize MCP session and return (session_id, headers)."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # Step 1: initialize
    init = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "chromebook-bootstrap", "version": "1.0"},
        },
    }
    r = requests.post(base_url, json=init, headers=headers, timeout=10)
    r.raise_for_status()
    session_id = r.headers.get("mcp-session-id", "")
    headers["mcp-session-id"] = session_id

    # Step 2: initialized notification
    notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    requests.post(base_url, json=notif, headers=headers, timeout=5)

    return session_id, headers


def list_tools(base_url: str, headers: dict) -> list:
    """Get all available tools from MCP server."""
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    r = requests.post(base_url, json=req, headers=headers, timeout=15)
    data = r.json()
    return data.get("result", {}).get("tools", [])


def categorize_tools(tools: list) -> dict:
    """Group tools by category prefix."""
    groups = {}
    for t in tools:
        name = t["name"]
        desc = t.get("description", "")[:80]
        # Use first word before underscore as category
        prefix = name.split("_")[0] if "_" in name else name
        groups.setdefault(prefix, []).append({"name": name, "description": desc})
    return dict(sorted(groups.items()))


def format_for_claude(tools: list, endpoint: str) -> str:
    """Format tool catalog as Claude-ready context block."""
    groups = categorize_tools(tools)

    lines = [
        "# YOGA MCP Server — Tool Catalog",
        f"**Endpoint:** `{endpoint}`",
        f"**Total tools:** {len(tools)}",
        f"**Categories:** {len(groups)}",
        "",
        "You have access to ALL of these tools via the MCP Streamable HTTP server on YOGA.",
        "Use them freely — they are your tools. Key categories:",
        "",
    ]

    for prefix, tool_list in groups.items():
        names = ", ".join(t["name"] for t in tool_list)
        lines.append(f"**{prefix}** ({len(tool_list)}): {names}")

    lines.extend([
        "",
        "## High-Value Tool Groups",
        "",
        "### Client Operations",
        "- `dani_*` — Dani concierge engine (client-facing)",
        "- `send_client_email`, `draft_client_email` — client comms",
        "- `create_trip_dossier_tool`, `list_trip_dossiers` — trip dossiers",
        "- `oa_*` — Outside Agents portal (bookings, commissions, invoices)",
        "- `tess_*` — TESS CRM (trips, clients, commissions)",
        "",
        "### Research & Intel",
        "- `search_flights`, `search_hotels`, `search_tours` — supplier search",
        "- `compare_flights`, `compare_hotels`, `compare_tours` — side-by-side",
        "- `get_travel_advisories`, `get_port_weather_forecast` — destination intel",
        "- `run_ship_intelligence_sweep`, `scrape_specific_cruise_line` — cruise intel",
        "- `fare_watch_*` — flight price monitoring",
        "",
        "### Wing Personas (AI Staff)",
        "- `consult_persona` — query any of 8 Wing personas (COS, EXEC, A2, A3, A5, A9, CH, A12)",
        "- `run_staff_meeting` — all personas analyze a topic",
        "- `crew_*` — CrewAI multi-agent orchestration (staff meeting, research, client, innovation)",
        "- `a2a_*` — Agent-to-Agent direct persona queries, chains, broadcasts",
        "- `wing_memory_*` — shared memory across all personas (Mem0)",
        "",
        "### Google Workspace",
        "- `drive_*` — Google Drive (list, search, upload, download, read docs)",
        "- `gmail_*` — Gmail (search, read, draft)",
        "- `keep_*` — Google Keep (notes, checklists)",
        "",
        "### Automation",
        "- `run_*` — scheduled sweeps (intel, email, tech, world, competitive)",
        "- `generate_*` — report generation (weekly, itinerary, ship comparison)",
        "- `shell_exec` — run shell commands on YOGA",
    ])

    return "\n".join(lines)


def main():
    host_override = None
    dump_mode = False
    claude_mode = False

    args = sys.argv[1:]
    if "--host" in args:
        idx = args.index("--host")
        host_override = args[idx + 1] if idx + 1 < len(args) else None
    dump_mode = "--dump" in args
    claude_mode = "--claude" in args

    # Build endpoint list
    if host_override:
        endpoints = [f"http://{host_override}:8765/mcp"]
    else:
        endpoints = YOGA_ENDPOINTS

    # Try each endpoint
    connected = False
    for endpoint in endpoints:
        try:
            print(f"Trying {endpoint}...", end=" ", flush=True)
            session_id, headers = connect_mcp(endpoint)
            tools = list_tools(endpoint, headers)
            print(f"CONNECTED — {len(tools)} tools")
            connected = True
            break
        except Exception as e:
            print(f"FAILED ({e})")
            continue

    if not connected:
        print("\nCould not connect to YOGA MCP server.")
        print("Make sure YOGA is running and reachable:")
        print("  - Tailscale: tailscale ping 100.69.222.124")
        print("  - LAN: ping 192.168.1.198")
        print("  - Tunnel: curl https://mcp.d2mluxury.quest/mcp")
        sys.exit(1)

    if dump_mode:
        print(json.dumps(tools, indent=2))
        return

    if claude_mode:
        print(format_for_claude(tools, endpoint))
        return

    # Default: categorized summary
    groups = categorize_tools(tools)
    print(f"\n{'='*60}")
    print(f"  YOGA MCP Server — {len(tools)} Tools Available")
    print(f"  Endpoint: {endpoint}")
    print(f"  Categories: {len(groups)}")
    print(f"{'='*60}\n")

    for prefix, tool_list in groups.items():
        print(f"  {prefix} ({len(tool_list)}):")
        for t in tool_list:
            print(f"    - {t['name']}")
        print()

    print(f"{'='*60}")
    print("  Run with --claude to get Claude-ready context block")
    print("  Run with --dump for full JSON tool definitions")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
