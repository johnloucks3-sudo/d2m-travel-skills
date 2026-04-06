"""
goose_mcp_server.py — Slim MCP server for Goose
================================================
Exposes ONLY the tools Goose needs:
- Google Workspace (Gmail, Drive, Keep, Calendar, Tasks)
- Dossier management
- Intel scans (innovation, world, ship)
- Morning briefing
- System health

~57 tools instead of 120+. Fast handshake. No import bloat.

Transport: stdio (Goose uses stdio MCP)

Author: Claude Sonnet 4.6 | Date: 2026-03-31
"""

import os
import sys
import logging

from pydantic import Field

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

# Suppress noisy registration logs from imported modules during stdio handshake
for noisy in ["thunderbird_gmail", "thunderbird_drive", "thunderbird_keep",
              "thunderbird_calendar_sync", "thunderbird_world_intel",
              "thunderbird_ship_intel", "thunderbird_health",
              "thunderbird_morning_briefing", "__main__"]:
    logging.getLogger(noisy).setLevel(logging.ERROR)

mcp = FastMCP("D2M Goose Slim")

# ── Google Workspace ──
from thunderbird_gmail import register_gmail_tools      # 18 tools
from thunderbird_gmail import (                         # sync tools for Goose
    gmail_get_message_sync,
    gmail_list_drafts_sync,
    gmail_get_draft_sync,
    gmail_create_draft_sync,
)
from thunderbird_drive import register_drive_tools      # 9 tools
from thunderbird_keep import register_keep_tools        # 5 tools
from thunderbird_calendar_sync import register_calendar_tools  # 3 tools
from thunderbird_tasks import register_tasks_tools      # 6 tools

# ── Dossier & Client ──
from thunderbird_dossier import register_dossier_tools  # 2 tools

# ── Intel & Search ──
from thunderbird_innovation_scanner import register_innovation_tools  # 2 tools
from thunderbird_world_intel import register_world_intel_tools        # 8 tools
from thunderbird_ship_intel import register_ship_intel_tools          # 2 tools

# ── Ops ──
from thunderbird_morning_briefing import register_briefing_tools  # 1 tool
from thunderbird_health import register_health_tools              # 1 tool

# ── Goose-specific Gmail extras (sync wrappers exposed as MCP tools) ──
def register_goose_gmail_extras(mcp_inst):
    """Register Goose-specific Gmail tools: explicit create_draft override + read helpers."""

    # ── Override gmail_create_draft ──────────────────────────────────────────
    # The bulk-registered version buries draft_id in a large nested JSON blob.
    # Goose needs draft_id surfaced as a top-level "id" field for reliable
    # chaining to gmail_send_draft. Remove the existing registration first,
    # then register this slim, explicit version.
    try:
        mcp_inst._tool_manager.remove_tool("gmail_create_draft")
    except Exception:
        pass  # Not yet registered — no-op

    @mcp_inst.tool(
        name="gmail_create_draft",
        annotations={"title": "Create Gmail Draft (Slim)", "readOnlyHint": False},
    )
    async def _gmail_create_draft(
        to: str = Field(..., description="Recipient email address"),
        subject: str = Field(..., description="Email subject line"),
        body: str = Field(..., description="Email body (HTML or plain text)"),
        from_address: str = Field(
            "concierge@d2mluxury.quest",
            description="Sender address — default is D2M concierge alias",
        ),
    ) -> str:
        """Create a Gmail draft. Returns 'id' (the Google draft_id) for chaining to gmail_send_draft."""
        import json
        try:
            result = gmail_create_draft_sync(
                to=to,
                subject=subject,
                body=body,
                from_address=from_address,
                label_review=False,
            )
            # Explicitly surface the Google draft ID as top-level "id" so Goose
            # can pass it directly to gmail_send_draft without nested JSON parsing.
            draft_id = result.get("draft_id", "")
            return json.dumps({
                "status": "success",
                "id": draft_id,
                "draft_id": draft_id,
                "message_id": result.get("message_id", ""),
                "to": to,
                "subject": subject,
            }, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})

    @mcp_inst.tool(
        name="gmail_get_message",
        annotations={"title": "Get Gmail Message by ID", "readOnlyHint": True},
    )
    async def _gmail_get_message(
        message_id: str = Field(..., description="Gmail message ID"),
    ) -> str:
        """Retrieve the full content of a Gmail message by ID (sent or received)."""
        import json
        try:
            result = gmail_get_message_sync(message_id)
            return json.dumps({"status": "success", **result}, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})

    @mcp_inst.tool(
        name="gmail_list_drafts_sync",
        annotations={"title": "List Gmail Drafts (Sync)", "readOnlyHint": True},
    )
    async def _gmail_list_drafts(
        max_results: int = Field(10, description="Max drafts to return (1-50)"),
    ) -> str:
        """List Gmail drafts with metadata summaries."""
        import json
        try:
            result = gmail_list_drafts_sync(max_results)
            return json.dumps({"status": "success", "count": len(result), "drafts": result}, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})

    @mcp_inst.tool(
        name="gmail_get_draft",
        annotations={"title": "Get Gmail Draft by ID", "readOnlyHint": True},
    )
    async def _gmail_get_draft(
        draft_id: str = Field(..., description="Gmail draft ID"),
    ) -> str:
        """Retrieve the full content of a Gmail draft by ID."""
        import json
        try:
            result = gmail_get_draft_sync(draft_id)
            return json.dumps({"status": "success", **result}, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})


# ── Register all ──
TOOL_GROUPS = [
    ("Google Workspace", [
        register_gmail_tools,
        register_drive_tools,
        register_keep_tools,
        register_calendar_tools,
        register_tasks_tools,
    ]),
    ("Client Management", [
        register_dossier_tools,
    ]),
    ("Intel & Search", [
        register_innovation_tools,
        register_world_intel_tools,
        register_ship_intel_tools,
    ]),
    ("Operations", [
        register_briefing_tools,
        register_health_tools,
    ]),
]

total = 0
for group_name, registrars in TOOL_GROUPS:
    for reg_fn in registrars:
        try:
            reg_fn(mcp)
        except Exception as e:
            log.warning(f"Failed to register {reg_fn.__name__}: {e}")
    log.info(f"Registered group: {group_name}")

# Register Goose-specific Gmail extras
register_goose_gmail_extras(mcp)
log.info("Registered Goose-specific Gmail extra tools.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Run as streamable-HTTP server (port 8766)")
    parser.add_argument("--port", type=int, default=8766)
    args, _ = parser.parse_known_args()

    if args.http:
        mcp.settings.host = "127.0.0.1"
        mcp.settings.port = args.port
        log.info(f"Goose Slim MCP ready — streamable-HTTP on 127.0.0.1:{args.port}/mcp")
        mcp.run(transport="streamable-http")
    else:
        log.info("Goose Slim MCP ready — stdio transport")
        mcp.run(transport="stdio")
