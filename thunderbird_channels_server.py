#!/usr/bin/env python3
"""
Thunderbird Channels Server — v2.1.81 --channels permission relay
Forwards Claude Code tool-approval prompts to Commander's Telegram phone.

Usage:
  1. Ensure TELEGRAM_C2_BOT_TOKEN and TELEGRAM_COMMANDER_ID are set in .env
  2. Register in mcp.json (done automatically by install script)
  3. Launch Claude Code with: claude --channels thunderbird-channels

Protocol Note (2026-03-22):
  Implements the MCP "permission" capability introduced in Claude Code v2.1.81.
  Claude Code connects via stdio; when a tool needs approval it calls the
  "request_permission" tool. This server forwards to Telegram, awaits Commander
  response, and returns allow/deny to Claude Code.

  TODO: Verify exact capability declaration name against Anthropic docs once
  published. Current implementation uses "permission" + "claude/channel" per
  v2.1.81 release notes.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests  # for Telegram Bot API (sync, no PTB needed for simple sends)
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ─── Config ──────────────────────────────────────────────────────────────────
_ENV = Path(__file__).parent / ".env"
if _ENV.exists():
    for _line in _ENV.read_text().splitlines():
        if "=" in _line and not _line.strip().startswith("#"):
            _k, _v = _line.strip().split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

BOT_TOKEN       = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "")
COMMANDER_ID    = int(os.environ.get("TELEGRAM_COMMANDER_ID", "0"))
TIMEOUT_SECS    = int(os.environ.get("CHANNELS_TIMEOUT_SECS", "120"))
THUNDERBIRD_DIR = Path(__file__).parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [channels] %(levelname)s %(message)s",
    handlers=[logging.FileHandler(THUNDERBIRD_DIR / "logs" / "channels_server.log")]
)
log = logging.getLogger("channels")

# ─── Telegram helpers ─────────────────────────────────────────────────────────

def tg_send(text: str, parse_mode: str = "Markdown", reply_markup: dict | None = None) -> int:
    """Send message to Commander. Returns message_id."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": COMMANDER_ID,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    r = requests.post(url, json=payload, timeout=10)
    data = r.json()
    if not data.get("ok"):
        log.error("Telegram send failed: %s", data)
        return 0
    return data["result"]["message_id"]


def tg_delete(message_id: int) -> None:
    """Delete a Telegram message (cleanup after approval)."""
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
        json={"chat_id": COMMANDER_ID, "message_id": message_id},
        timeout=10,
    )


def tg_poll_update(after_update_id: int, timeout: int = 5) -> list[dict]:
    """Long-poll for new updates."""
    r = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
        params={"offset": after_update_id + 1, "timeout": timeout},
        timeout=timeout + 5,
    )
    return r.json().get("result", [])


# ─── Permission Request Handler ───────────────────────────────────────────────

async def ask_commander(tool_name: str, tool_input: str, context: str = "") -> bool:
    """
    Forward a tool approval request to Commander via Telegram.
    Returns True = allow, False = deny.
    Blocks until Commander responds or TIMEOUT_SECS elapses.
    """
    if not BOT_TOKEN or not COMMANDER_ID:
        log.warning("No Telegram credentials — auto-allowing")
        return True

    # Build approval message
    short_input = tool_input[:400] + "…" if len(tool_input) > 400 else tool_input
    msg_text = (
        f"🔐 *PERMISSION REQUEST*\n\n"
        f"*Tool:* `{tool_name}`\n"
        f"*Input:* `{short_input}`\n"
        f"{f'*Context:* {context}' if context else ''}\n\n"
        f"Approve or deny within {TIMEOUT_SECS}s:"
    )
    reply_markup = {
        "inline_keyboard": [[
            {"text": "✅ ALLOW", "callback_data": f"channel_allow"},
            {"text": "❌ DENY",  "callback_data": f"channel_deny"},
        ]]
    }

    msg_id = tg_send(msg_text, reply_markup=reply_markup)
    if not msg_id:
        log.error("Failed to send approval request — auto-denying for safety")
        return False

    log.info("Approval request sent (msg_id=%d) for tool=%s", msg_id, tool_name)

    # Get current update_id baseline
    baseline = tg_poll_update(0, timeout=0)
    last_id = max((u["update_id"] for u in baseline), default=0) if baseline else 0

    deadline = time.monotonic() + TIMEOUT_SECS
    while time.monotonic() < deadline:
        updates = await asyncio.get_event_loop().run_in_executor(
            None, tg_poll_update, last_id, 5
        )
        for upd in updates:
            last_id = max(last_id, upd["update_id"])
            cb = upd.get("callback_query", {})
            if cb.get("data") in ("channel_allow", "channel_deny"):
                # Answer the callback so button stops spinning
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                    json={"callback_query_id": cb["id"], "text": "Received"},
                    timeout=5,
                )
                tg_delete(msg_id)
                decision = cb["data"] == "channel_allow"
                log.info("Commander %s tool=%s", "ALLOWED" if decision else "DENIED", tool_name)
                tg_send(
                    f"{'✅ Allowed' if decision else '❌ Denied'}: `{tool_name}`",
                    parse_mode="Markdown"
                )
                return decision

    # Timed out — deny for safety
    log.warning("Approval timed out for tool=%s — auto-denying", tool_name)
    tg_delete(msg_id)
    tg_send(f"⏱ *TIMED OUT* — auto-denied `{tool_name}`", parse_mode="Markdown")
    return False


# ─── MCP Server ───────────────────────────────────────────────────────────────

app = Server("thunderbird-channels")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="request_permission",
            description=(
                "Forward a tool permission request to the Commander's phone via Telegram. "
                "Returns 'allow' or 'deny' based on Commander's real-time decision."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "Name of the tool requesting permission"
                    },
                    "tool_input": {
                        "type": "string",
                        "description": "JSON-encoded tool input for display"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional session context for Commander"
                    }
                },
                "required": ["tool_name", "tool_input"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "request_permission":
        tool_name  = arguments.get("tool_name", "unknown")
        tool_input = arguments.get("tool_input", "{}")
        context    = arguments.get("context", "")

        allowed = await ask_commander(tool_name, tool_input, context)
        result  = "allow" if allowed else "deny"

        return [types.TextContent(type="text", text=result)]

    return [types.TextContent(type="text", text="error: unknown tool")]


# ─── Capability declaration ───────────────────────────────────────────────────
# Claude Code v2.1.81 --channels relay: declare "permission" capability
# so Claude Code routes tool-approval prompts to this server.
# Capability name to verify against Anthropic docs when published.
app.capabilities = {
    "permission": {},          # forward tool approvals to phone
    "claude/channel": {}       # inbound message push capability
}


# ─── Entry point ─────────────────────────────────────────────────────────────

async def main() -> None:
    log.info("Thunderbird Channels Server starting (commander=%d)", COMMANDER_ID)
    # Announce readiness to Commander
    tg_send(
        "🛰 *Thunderbird Channels Server ONLINE*\n"
        "Tool approval requests will route here.",
        parse_mode="Markdown"
    )
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
