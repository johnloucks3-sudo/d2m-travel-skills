"""
Thunderbird MCP Gateway — Domain Activation Server
Wake-on-call profile management. Controls which tool domain loads next session.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from mcp.server.fastmcp import FastMCP

GATEWAY_STATE_FILE = Path.home() / ".claude" / "gateway_state.json"
PROFILES_DIR = Path.home() / ".claude" / "profiles"
VALID_PROFILES = ["core", "intel", "travel", "ops", "full"]

mcp = FastMCP("thunderbird-gateway")

def _read_state() -> dict:
    if GATEWAY_STATE_FILE.exists():
        return json.loads(GATEWAY_STATE_FILE.read_text())
    return {"active_profile": "full", "requested_profile": None, "last_changed": None}

def _write_state(state: dict):
    GATEWAY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    GATEWAY_STATE_FILE.write_text(json.dumps(state, indent=2))

@mcp.tool()
def gateway_status() -> str:
    """Show current and requested MCP profile state."""
    state = _read_state()
    lines = [
        "🌐 Thunderbird MCP Gateway Status",
        f"Active profile:    {state.get('active_profile', 'full')}",
        f"Requested profile: {state.get('requested_profile') or '(none)'}",
        f"Last changed:      {state.get('last_changed') or 'never'}",
        "",
        "Available profiles:",
    ]
    profile_descriptions = {
        "core":   "~25 tools — drive, gmail, keep, dossiers, tasks, memory, personas, learning, commander inbox",
        "intel":  "core + ship intel, world intel, port/weather, cruise scraping, innovation scanner",
        "travel": "core + hotel/flight search, transfers, shore excursions, tours, dining, fare watch",
        "ops":    "core + commission recon, survey tools, quote rendering, booking sync, drive ops",
        "full":   "ALL tools — everything (120+ tools, high context cost)",
    }
    for p, desc in profile_descriptions.items():
        marker = "◀ ACTIVE" if p == state.get("active_profile") else ("◀ REQUESTED" if p == state.get("requested_profile") else "")
        lines.append(f"  {p:8} — {desc} {marker}".rstrip())

    if state.get("requested_profile") and state["requested_profile"] != state.get("active_profile"):
        lines.append("")
        lines.append(f"⚡ Profile change pending — start next session with: cc {state['requested_profile']}")

    return "\n".join(lines)

@mcp.tool()
def activate_domain(domain: str) -> str:
    """
    Request a domain profile for the next Claude session.

    This cannot change tools mid-session (FastMCP limitation), but records
    the requested profile so you can start the right session with: cc <domain>

    Args:
        domain: One of: core, intel, travel, ops, full
    """
    if domain not in VALID_PROFILES:
        return f"❌ Unknown domain '{domain}'. Valid: {', '.join(VALID_PROFILES)}"

    state = _read_state()
    prev = state.get("active_profile", "full")
    state["requested_profile"] = domain
    state["last_changed"] = datetime.now().isoformat()
    _write_state(state)

    config_path = PROFILES_DIR / f"mcp_{domain}.json"
    if not config_path.exists():
        return f"⚠️  Profile config missing: {config_path}\nRun the profile setup script to create it."

    if domain == prev:
        return f"ℹ️  Already on profile '{domain}'. No change needed."

    return (
        f"✅ Domain '{domain}' activated for next session.\n"
        f"Previous: {prev} → Requested: {domain}\n\n"
        f"To start a session with this profile:\n"
        f"  cc {domain}\n\n"
        f"Tool counts:\n"
        f"  core: ~25 tools  |  intel: ~60  |  travel: ~80  |  ops: ~55  |  full: 120+"
    )

@mcp.tool()
def list_profiles() -> str:
    """List all available MCP profiles and their tool domains."""
    state = _read_state()
    current = state.get("active_profile", "full")

    profiles = {
        "core":   {"tools": 25,  "domains": ["drive", "gmail", "keep", "dossiers", "tasks", "memory", "personas", "learning", "commander-inbox", "sss", "learning", "routing", "dani-email", "quotes", "voice", "health", "temporal", "bulletin", "anchors", "briefings"]},
        "intel":  {"tools": 60,  "domains": ["+ ship-intel", "world-intel", "port-weather", "cruise-scraping", "innovation", "tech-monitor", "competitive-surveillance"]},
        "travel": {"tools": 80,  "domains": ["+ hotels", "flights", "transfers", "shore-excursions", "tours-viator", "tours-musement", "dining", "fare-watch", "taap", "mozio", "blacklane", "welcome-pickups"]},
        "ops":    {"tools": 55,  "domains": ["+ commissions", "survey", "quotes-pdf", "booking-sync", "drive-ops", "excel-reader", "anchor-dates", "dossier-scanner"]},
        "full":   {"tools": 120, "domains": ["ALL of the above"]},
    }

    lines = ["📋 MCP Profile Directory\n"]
    for name, info in profiles.items():
        marker = " ◀ CURRENT" if name == current else ""
        lines.append(f"  cc {name}{marker}")
        lines.append(f"    Tools: ~{info['tools']}")
        lines.append(f"    Domains: {', '.join(info['domains'][:5])}{'...' if len(info['domains']) > 5 else ''}")
        lines.append("")

    lines.append("Usage:  cc core      # Start session with core profile")
    lines.append("        cc intel     # Start session with intel profile")
    lines.append("        cc full      # Start session with all tools")

    return "\n".join(lines)

@mcp.tool()
def set_active_profile(profile: str) -> str:
    """
    Mark a profile as the currently active one (call at session start).
    The cc launcher should call this via a startup hook.

    Args:
        profile: One of: core, intel, travel, ops, full
    """
    if profile not in VALID_PROFILES:
        return f"❌ Unknown profile '{profile}'"

    state = _read_state()
    state["active_profile"] = profile
    state["requested_profile"] = None
    state["last_changed"] = datetime.now().isoformat()
    _write_state(state)

    return f"✅ Active profile set to '{profile}'"

if __name__ == "__main__":
    import sys
    if "--stdio" in sys.argv:
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="stdio")
