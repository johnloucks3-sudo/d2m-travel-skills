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
    """Send a DM to the Commander via D2MC2C bot.

    Args:
        text: Message text. Markdown supported (parse_mode=Markdown).

    Returns:
        True if at least one send succeeded, False otherwise.
    """
    if not _TOKEN:
        logger.error("telegram_c2: TELEGRAM_C2_BOT_TOKEN not set — DM skipped")
        return False

    url = f"https://api.telegram.org/bot{_TOKEN}/sendMessage"
    success = False

    for chat_id in _COMMANDER_IDS:
        try:
            r = requests.post(
                url,
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
            r.raise_for_status()
            success = True
        except Exception as e:
            logger.error(f"telegram_c2: Markdown send failed (id={chat_id}): {e}")
            try:
                plain = text.replace("*", "").replace("_", "")
                requests.post(
                    url,
                    json={"chat_id": chat_id, "text": plain},
                    timeout=10,
                )
                success = True
            except Exception as e2:
                logger.error(f"telegram_c2: Plain fallback also failed (id={chat_id}): {e2}")

    return success
