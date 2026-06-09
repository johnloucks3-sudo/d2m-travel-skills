#!/usr/bin/env python3
"""
Context Sniper MCP Server
==========================
Exposes Context Sniper as MCP tools for OpenCode/Claude Code.
Register in opencode.json as "context-sniper" server.

Tools:
  context_compress  — Build a persona-appropriate context brief from durable sources
  context_pin       — Pin an item (never dropped from future briefs)
  context_unpin     — Remove a pin by ID
  context_status    — Show token budget estimate, pins, calibration
  context_help      — Usage guide and persona reference
"""

import sys
import json
import os

# Ensure Thunderbird root is on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    try:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "mcp", "-q"], check=True)
        from mcp.server.fastmcp import FastMCP
    except Exception as e:
        print(json.dumps({"error": f"FastMCP not available: {e}"}), file=sys.stderr)
        sys.exit(1)

from pathlib import Path

BASE = Path(BASE_DIR)
sys.path.insert(0, str(BASE / "scripts"))

try:
    from context_sniper import ContextSniper
except ImportError as e:
    # Fallback: run subprocess
    pass

mcp = FastMCP("context-sniper")


def _get_sniper() -> "ContextSniper":
    from context_sniper import ContextSniper
    return ContextSniper()


@mcp.tool()
def context_compress(persona: str = "default", hint: str = "") -> str:
    """
    Build a compressed context brief from durable external sources.

    Call this when you feel context bloat slowing you down, or when
    starting a new sub-task and want a clean situational snapshot.

    Personas:
      hale     — Broad multi-mission view: overdue items, P0/P1 board, blackboard, relay
      sterling — Narrow build view: current mission, pins, git status
      intel    — Research view: fare watches, blackboard, active missions
      harlan   — Finance view: financial pulse, pins, P0 missions
      dani     — Client content view: pins, active P0/P1, blackboard
      default  — Balanced view (use when unsure)

    Args:
      persona: Which persona policy to apply (default: "default")
      hint:    Optional note about what you're currently working on

    Returns a structured brief built from: mission board, blackboard,
    wing relay, financial pulse, fare watches, and pinned items.
    Everything here is from persistent sources — it will still be
    accurate after a context reset.
    """
    try:
        sniper = _get_sniper()
        return sniper.build_brief(persona=persona, hint=hint)
    except Exception as e:
        return f"❌ context_compress error: {e}"


@mcp.tool()
def context_pin(item: str, category: str = "critical") -> str:
    """
    Pin an item so it always appears in future context_compress briefs.

    Use this for: current task spec, client constraint, standing order,
    financial figure being verified, or any fact that MUST survive a
    context reset.

    Args:
      item:     The text to pin (keep under 200 chars for readability)
      category: critical | plan | instruction | fact (default: critical)

    Returns the pin ID — use this with context_unpin when the item expires.
    """
    try:
        from context_sniper import PinManager
        pm = PinManager()
        pin = pm.add(item, category)
        return f"✅ Pinned #{pin['id']} [{pin['category']}]: {pin['item']}"
    except Exception as e:
        return f"❌ context_pin error: {e}"


@mcp.tool()
def context_unpin(pin_id: int) -> str:
    """
    Remove a pin by its ID (returned when you called context_pin).

    Call this when a task is complete and the pinned item is no longer
    critical — keeps the pin list clean so future briefs stay concise.

    Args:
      pin_id: The numeric ID of the pin to remove
    """
    try:
        from context_sniper import PinManager
        pm = PinManager()
        if pm.remove(pin_id):
            return f"✅ Unpinned #{pin_id}"
        else:
            return f"❌ Pin #{pin_id} not found or already inactive"
    except Exception as e:
        return f"❌ context_unpin error: {e}"


@mcp.tool()
def context_status() -> str:
    """
    Show Context Sniper status: active pins, calibration stats, and
    the token budget thresholds for each persona.

    Call this at session start or when wondering if you should compress.
    Rule of thumb: if a session has been running >2 hours on a complex
    build, calling context_compress is almost always worth it.
    """
    try:
        sniper = _get_sniper()
        return sniper.status()
    except Exception as e:
        return f"❌ context_status error: {e}"


@mcp.tool()
def context_help() -> str:
    """
    Usage guide for Context Sniper — when to use it, which persona to pick,
    and how pins work.
    """
    return """
╔══════════════════════════════════════════════════════════════╗
║           CONTEXT SNIPER — Token Budget Foreman              ║
╚══════════════════════════════════════════════════════════════╝

WHAT IT DOES
  Rebuilds your working context from durable external sources
  (mission board, blackboard, relay, fare watches, pins) so you
  can orient after context bloat without losing a beat.

WHEN TO CALL context_compress:
  • Session running >90 min on a complex build
  • Switching from one task to a very different one
  • After a long tool chain (Playwright, scrape, big file read)
  • After Commander gives new direction mid-session
  • Before drafting any WF-17 item (want clean context)

WHICH PERSONA:
  hale     — You're coordinating / tracking multiple threads
  sterling — You're writing code on a specific spec
  intel    — You're doing research / fare watch / scan
  harlan   — You're verifying $ figures or booking details
  dani     — You're writing a client email or product
  default  — Not sure — this is always safe

PINS:
  context_pin("Current task: wire thunderbird-core to travel_mcp_server.py", category="plan")
  → Returns pin ID (e.g. #7)
  context_unpin(7)  ← when done

  Pins survive sessions — they're in data/context_sniper_pins.json.
  Keep <10 pins active at once for best brief quality.

CALIBRATION:
  The system logs every brief call with its persona and estimated token
  size. Run context_status() to see calibration history and check whether
  your token thresholds are well-tuned.

CLI (for scripts):
  python3 scripts/context_sniper.py brief --persona hale
  python3 scripts/context_sniper.py pin "item" --category plan
  python3 scripts/context_sniper.py pins
  python3 scripts/context_sniper.py status
"""


if __name__ == "__main__":
    mcp.run(transport="stdio")
