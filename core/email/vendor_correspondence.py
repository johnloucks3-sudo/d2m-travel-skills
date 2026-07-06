#!/usr/bin/env python3
"""Vendor Correspondence via AgentMail — Bold Use #4 (Commander: "may be as well").

Within Hale's existing standing authority: "Hale owns all vendor/supplier
contact that is transactional or informational." Bright line unchanged —
anything that could change a number or make a commitment still goes to
the Commander first.

NOT exercised against a real vendor as part of building this — the
capability is ready; sending to an actual supplier needs a real reason,
same discipline as not test-emailing Bryana/Susan's real inboxes.
"""
import sys

sys.path.insert(0, "/home/john/Thunderbird")

from core.email.agentmail_client import AgentMailClient

VENDOR_SEND_INBOX = "hale-thunderbird@agentmail.to"


def send_vendor_inquiry(vendor_email: str, subject: str, text: str, html: str | None = None) -> dict:
    """Transactional/informational vendor contact only — a rate check, an
    availability question, a documentation request. If the reply could
    result in a number changing or a commitment being made, this is the
    wrong function; escalate to the Commander before sending anything."""
    client = AgentMailClient()
    return client.send_message(
        inbox_id=VENDOR_SEND_INBOX,
        to=[vendor_email],
        subject=subject,
        text=text,
        html=html,
    )
