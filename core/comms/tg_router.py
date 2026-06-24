"""Telegram channel routing — SO-TELEGRAM-ROUTING-20260622

D2MC2C (COMMANDER_CHAT_ID): Hale speaking TO Commander.
  Decisions, escalations, WF-17 notifications, briefs, Commander-actionable P0 alerts.

Relay (RELAY_CHAT_ID): all ops/status/error/automated pipeline output.
  Health checks, CI results, adopt counts, tool trim reports, error logs.
"""

COMMANDER_CHAT_ID = "7554895206"   # D2MC2C — Hale↔Commander only
RELAY_CHAT_ID     = "-5248121475"  # relay — all ops/status/automated output

_COMMANDER_TYPES = {"escalation", "wf17", "brief", "commander_action", "p0_alert"}


def route(message_type: str) -> str:
    """Return the correct chat_id for this message type."""
    return COMMANDER_CHAT_ID if message_type in _COMMANDER_TYPES else RELAY_CHAT_ID
