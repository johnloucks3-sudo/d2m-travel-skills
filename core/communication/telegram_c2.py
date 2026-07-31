"""
telegram_c2.py — Lightweight C2 Telegram sender for Thunderbird Wing.

Pure requests, no PTB bot lifecycle. Safe to import from any script.
Used by airline monitor, hale_enforcer, and any non-bot caller that needs
to DM the Commander via D2MC2C bot.

Env vars (same as thunderbird_telegram.py):
    TELEGRAM_C2_BOT_TOKEN  — C2 bot token from BotFather
    TELEGRAM_COMMANDER_ID  — Commander's Telegram user ID (default: 7554895206)
"""

import logging
import os

import requests

logger = logging.getLogger("telegram_c2")

_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "")
_COMMANDER_IDS = [
    uid.strip()
    for uid in os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206").split(",")
    if uid.strip()
]


def dm_commander(text: str) -> bool:
    """Send a message to the Commander.

    Routed through the single gate (C2 RECALIBRATION task 8, Commander directive
    2026-07-29). This used to hit the bot API directly — one of the direct senders
    the gate replaced. notify() dedups, renders, and batches to the 06:30/18:30
    windows.

    Args:
        text: Message text. Markdown supported.

    Returns:
        True if notify() accepted the message (sent, queued, or suppressed as a
        duplicate), False otherwise.
    """
    try:
        from core.comms.commander_channel import notify
        result = notify("c2", text.splitlines()[0][:80] if text.strip() else "telegram_c2",
                        text, urgency="WINDOW", source="telegram_c2")
        return result.get("status") in ("sent", "queued", "suppressed")
    except Exception as e:
        logger.error(f"telegram_c2: notify() send failed: {e}")
        return False
