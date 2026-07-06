#!/usr/bin/env python3
"""Cross-Engine Native Mail — Bold Use #1 outbound compose helper.

wind_email_responder.py already handles the INBOUND half live (WIND replies
when CONDOR or the Commander emails it). This module is the missing OUTBOUND
convenience for CONDOR-initiated correspondence to WIND — "CONDOR: can you
research X" — so callers don't hand-roll the inbox_id/to pair every time.

Not a replacement for core/hale_bus/brain_bridge.py. Brain bridge is the
concurrency primitive (atomic claim, no double-work, queryable ownership) —
this is a conversation channel. Use brain bridge to ASSIGN/CLAIM work; use
this to discuss it, attach findings, or ask a question that doesn't need a
claim. See docs/AGENTMAIL_BOLD_USES_INFRASTRUCTURE.md Use Case 1.
"""
import sys

sys.path.insert(0, "/home/john/Thunderbird")

from core.email.agentmail_client import AgentMailClient

CONDOR_INBOX = "hale-thunderbird@agentmail.to"
WIND_INBOX = "dreams2memories-80921@agentmail.to"


def send_to_wind(subject: str, text: str, html: str | None = None) -> dict:
    """CONDOR (Claude Code / TALON) -> WIND (OpenCode / JET)."""
    client = AgentMailClient()
    return client.send_message(
        inbox_id=CONDOR_INBOX, to=[WIND_INBOX], subject=subject, text=text, html=html,
    )


def send_to_condor(subject: str, text: str, html: str | None = None) -> dict:
    """WIND (OpenCode / JET) -> CONDOR (Claude Code / TALON).
    Callable from Python on either engine; OpenCode's native AgentMail MCP
    tools (see opencode.json hale-oc prompt) are the preferred path when
    already inside an OpenCode session — this is for script/CLI contexts."""
    client = AgentMailClient()
    return client.send_message(
        inbox_id=WIND_INBOX, to=[CONDOR_INBOX], subject=subject, text=text, html=html,
    )
