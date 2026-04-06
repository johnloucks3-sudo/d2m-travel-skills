"""
Dreams2Memories Notification MCP Module
========================================
Sends alerts via Telegram C2 bot (replaced tmomail SMS gateway 2026-03-31).
"""
import json
import logging
import os
import asyncio
from pathlib import Path

from pydantic import Field
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path(__file__).parent


def _load_env() -> dict:
    """Load .env file into a dict."""
    env = {}
    env_file = THUNDERBIRD_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _sync_send(message: str, subject: str) -> dict:
    """Send alert via Telegram C2 bot."""
    import requests
    env = _load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_C2_BOT_TOKEN") or env.get("TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_C2_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_COMMANDER_ID") or env.get("TELEGRAM_COMMANDER_ID")
    if not token or not chat_id:
        return {"status": "error", "error": "TELEGRAM_BOT_TOKEN or TELEGRAM_COMMANDER_ID not set"}

    text = f"<b>{subject}</b>\n{message}" if subject else message
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }, timeout=10)

    if resp.status_code == 200:
        return {"status": "sent", "channel": "telegram", "chars": len(text)}
    else:
        return {"status": "error", "error": f"Telegram API {resp.status_code}: {resp.text[:200]}"}


def register_sms_tools(mcp: FastMCP):

    @mcp.tool(name="send_sms_notification", annotations={"title": "Send SMS Notification", "readOnlyHint": False})
    async def send_sms_notification(
        message: str = Field(..., description="Alert message text"),
        subject: str = Field("D2M Alert", description="Alert subject/header"),
    ) -> str:
        """Send a notification to John's phone via Telegram C2 bot."""
        try:
            result = await asyncio.to_thread(_sync_send, message, subject)
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return json.dumps({"error": str(e), "type": "telegram_error"})
