"""
Thunderbird Telegram MCP Tools — Hale's universal Telegram access

Hale (COS) can read and write to ALL Telegram bots/channels:
  - D2MC2C (@D2MC2C_bot) — Hale identity, Commander only
  - GooseD2M (@GooseD2M_bot) — Hale identity, Commander only
  - Dani (@d2m_dani_bot) — Dani Moreau, clients + Commander
  - Relay (@d2m_channels_bot) — System relay, Commander observer

Registered via register_telegram_mcp_tools(mcp).
"""

import os
import json
import logging
import requests
from pathlib import Path
from typing import Optional

logger = logging.getLogger("thunderbird_telegram_mcp")

CONFIG_PATH = Path(__file__).parent.parent / "config" / "telegram_gw.env"

BOT_MAP = {}

def _load_tokens():
    if not CONFIG_PATH.exists():
        logger.warning(f"Telegram config not found at {CONFIG_PATH}")
        return {}
    tokens = {}
    with open(CONFIG_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith("TELEGRAM_D2MC2C_TOKEN="):
                tokens["d2mc2c"] = line.split("=", 1)[1]
            elif line.startswith("TELEGRAM_GOOSE_TOKEN="):
                tokens["goose"] = line.split("=", 1)[1]
            elif line.startswith("TELEGRAM_DANI_TOKEN="):
                tokens["dani"] = line.split("=", 1)[1]
            elif line.startswith("TELEGRAM_RELAY_TOKEN="):
                tokens["relay"] = line.split("=", 1)[1]
            elif line.startswith("TELEGRAM_RELAY_CHAT_ID="):
                tokens["relay_chat_id"] = line.split("=", 1)[1]
            elif line.startswith("TELEGRAM_COMMANDER_ID="):
                tokens["commander_id"] = line.split("=", 1)[1]
    return tokens

_TOKENS = None

def _get_token(bot_name: str) -> Optional[str]:
    global _TOKENS
    if _TOKENS is None:
        _TOKENS = _load_tokens()
    return _TOKENS.get(bot_name.lower())

def _bot_api_url(bot_name: str, method: str) -> Optional[str]:
    token = _get_token(bot_name)
    if not token:
        return None
    return f"https://api.telegram.org/bot{token}/{method}"


# ── BOT INFO ────────────────────────────────────────────────────────────────

BOT_LABELS = {
    "d2mc2c": "@D2MC2C_bot — Hale identity, Commander-only bot",
    "goose": "@GooseD2M_bot — Hale identity (Goose), Commander-only",
    "dani": "@d2m_dani_bot — Dani Moreau (A3), clients + Commander",
    "relay": "@d2m_channels_bot — System relay, Commander observer",
}

BOT_DESCRIPTIONS = {
    "d2mc2c": "Hale's primary bot. Commander-only. Use this for Hale's own communications.",
    "goose": "Hale's secondary bot (Goose engine). Commander-only.",
    "dani": "Dani Moreau's bot. Clients AND Commander can message here. Use to read client conversations.",
    "relay": "System relay bot. Posts automated system messages to a private channel.",
}


# ── MCP TOOLS ──────────────────────────────────────────────────────────────

def register_telegram_mcp_tools(mcp):
    """Register all Telegram MCP tools for Hale's universal access."""

    @mcp.tool(
        name="telegram_get_bots",
        annotations={"title": "List Telegram bots", "readOnlyHint": True},
    )
    def telegram_get_bots() -> str:
        """List all available Telegram bots that Hale can access with descriptions."""
        bots = []
        for name, label in BOT_LABELS.items():
            token = _get_token(name)
            bots.append({
                "name": name,
                "label": label,
                "configured": token is not None,
                "token_preview": token[:12] + "..." if token else None,
            })
        return json.dumps({"bots": bots, "count": len(bots)})

    @mcp.tool(
        name="telegram_send_message",
        annotations={"title": "Send Telegram message"},
    )
    def telegram_send_message(
        bot_name: str,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
        disable_notification: bool = False,
    ) -> str:
        """Send a message via a Telegram bot to any chat/user.
        
        Args:
            bot_name: Bot identity — 'd2mc2c', 'goose', 'dani', or 'relay'
            chat_id: Target chat ID (numeric string, e.g. '7554895206' for Commander)
            text: Message text (supports Markdown formatting)
            parse_mode: 'Markdown', 'HTML', or '' for plain text
            disable_notification: If True, send silently
        """
        url = _bot_api_url(bot_name, "sendMessage")
        if not url:
            return json.dumps({"error": f"Bot '{bot_name}' not configured. Check telegram_gw.env"})

        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_notification": disable_notification,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            resp = requests.post(url, json=payload, timeout=10)
            data = resp.json()
            if data.get("ok"):
                result = data["result"]
                return json.dumps({
                    "status": "sent",
                    "message_id": result["message_id"],
                    "chat_id": str(result["chat"]["id"]),
                    "bot": bot_name,
                    "from_bot": result.get("from", {}).get("first_name", bot_name),
                })
            else:
                return json.dumps({"error": data.get("description", "Unknown error"), "ok": False})
        except requests.RequestException as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="telegram_get_updates",
        annotations={"title": "Read Telegram messages", "readOnlyHint": True},
    )
    def telegram_get_updates(
        bot_name: str,
        limit: int = 20,
        offset: Optional[int] = None,
        timeout: int = 5,
    ) -> str:
        """Read recent messages/conversations from a Telegram bot.
        
        Args:
            bot_name: Bot identity — 'd2mc2c', 'goose', 'dani', or 'relay'
            limit: Max messages to return (1-100)
            offset: Update ID offset for pagination. Omit for most recent.
            timeout: Long-poll timeout in seconds (0=no wait, max 30)
        """
        url = _bot_api_url(bot_name, "getUpdates")
        if not url:
            return json.dumps({"error": f"Bot '{bot_name}' not configured"})

        params = {
            "limit": min(max(limit, 1), 100),
            "timeout": min(max(timeout, 0), 30),
        }
        if offset is not None:
            params["offset"] = offset

        try:
            resp = requests.post(url, json=params, timeout=timeout + 5)
            data = resp.json()
            if not data.get("ok"):
                return json.dumps({"error": data.get("description", "Unknown error")})

            messages = []
            for update in data.get("result", []):
                msg = update.get("message") or update.get("channel_post") or {}
                message_data = {
                    "update_id": update["update_id"],
                    "message_id": msg.get("message_id"),
                    "date": msg.get("date"),
                    "text": msg.get("text", ""),
                    "from": {
                        "id": str(msg.get("from", {}).get("id", "")),
                        "first_name": msg.get("from", {}).get("first_name", ""),
                        "username": msg.get("from", {}).get("username", ""),
                        "is_bot": msg.get("from", {}).get("is_bot", False),
                    } if msg.get("from") else None,
                    "chat": {
                        "id": str(msg.get("chat", {}).get("id", "")),
                        "type": msg.get("chat", {}).get("type", ""),
                        "title": msg.get("chat", {}).get("title", ""),
                        "username": msg.get("chat", {}).get("username", ""),
                    },
                    "has_media": any(k in msg for k in ["photo", "document", "video", "audio"]),
                }
                messages.append(message_data)

            return json.dumps({
                "bot": bot_name,
                "bot_label": BOT_LABELS.get(bot_name, bot_name),
                "count": len(messages),
                "updates": messages,
                "next_offset": data["result"][-1]["update_id"] + 1 if data.get("result") else None,
            })
        except requests.RequestException as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="telegram_read_dani",
        annotations={"title": "Read Dani's conversations", "readOnlyHint": True},
    )
    def telegram_read_dani(limit: int = 20) -> str:
        """Read Dani bot's recent client conversations (convenience wrapper).
        
        Dani (@d2m_dani_bot) handles inbound messages from clients + Commander.
        Use this to see what clients are asking Dani.
        """
        return telegram_get_updates("dani", limit=limit)

    @mcp.tool(
        name="telegram_read_commander",
        annotations={"title": "Read Commander conversations", "readOnlyHint": True},
    )
    def telegram_read_commander(limit: int = 20) -> str:
        """Read Commander's recent messages across all Hale bots (D2MC2C + Goose).
        
        Returns messages from Hale's Commander-only bots combined.
        """
        all_messages = []
        for bot in ["d2mc2c", "goose"]:
            result = telegram_get_updates(bot, limit=limit)
            data = json.loads(result)
            if "updates" in data:
                for msg in data["updates"]:
                    msg["_bot"] = bot
                all_messages.extend(data["updates"])

        all_messages.sort(key=lambda m: m.get("date", 0), reverse=True)
        all_messages = all_messages[:limit]

        return json.dumps({
            "bot": "commander",
            "bot_label": "Commander channels (D2MC2C + GooseD2M)",
            "count": len(all_messages),
            "updates": all_messages,
        })

    @mcp.tool(
        name="telegram_get_chat",
        annotations={"title": "Get Telegram chat info", "readOnlyHint": True},
    )
    def telegram_get_chat(bot_name: str, chat_id: str) -> str:
        """Get information about a Telegram chat/user/group.
        
        Args:
            bot_name: Bot identity to query with
            chat_id: Chat ID to look up
        """
        url = _bot_api_url(bot_name, "getChat")
        if not url:
            return json.dumps({"error": f"Bot '{bot_name}' not configured"})

        try:
            resp = requests.post(url, json={"chat_id": chat_id}, timeout=10)
            data = resp.json()
            if data.get("ok"):
                chat = data["result"]
                return json.dumps({
                    "id": str(chat.get("id")),
                    "type": chat.get("type"),
                    "title": chat.get("title"),
                    "username": chat.get("username"),
                    "first_name": chat.get("first_name"),
                    "last_name": chat.get("last_name"),
                    "description": chat.get("description"),
                    "invite_link": chat.get("invite_link"),
                    "photo": chat.get("photo") is not None,
                    "permissions": {
                        "can_send_messages": chat.get("permissions", {}).get("can_send_messages"),
                        "can_send_media": chat.get("permissions", {}).get("can_send_media_messages"),
                    },
                })
            else:
                return json.dumps({"error": data.get("description", "Chat not found")})
        except requests.RequestException as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="telegram_send_to_commander",
        annotations={"title": "Send message to Commander"},
    )
    def telegram_send_to_commander(
        bot_name: str = "d2mc2c",
        text: str = "",
        urgent: bool = False,
    ) -> str:
        """Send a message directly to Commander (John Loucks).
        
        Args:
            bot_name: Bot identity to send from (default: d2mc2c)
            text: Message text
            urgent: If True, prefix with urgency indicator
        """
        commander_id = _TOKENS.get("commander_id", "7554895206") if _TOKENS else "7554895206"
        prefix = "[URGENT]" if urgent else ""
        full_text = f"{prefix} {text}".strip()
        return telegram_send_message(bot_name, commander_id, full_text)

    @mcp.tool(
        name="telegram_send_to_dani",
        annotations={"title": "Send message via Dani bot"},
    )
    def telegram_send_to_dani(chat_id: str, text: str) -> str:
        """Send a message as the Dani bot to any chat/user.
        
        This lets Hale respond to client conversations as Dani.
        
        Args:
            chat_id: Target chat ID
            text: Message text to send
        """
        return telegram_send_message("dani", chat_id, text)

    logger.info(f"Telegram MCP tools registered for {len(BOT_LABELS)} bots")
