#!/usr/bin/env python3
"""Rich Incident Email — Bold Use #3 (Commander-approved 2026-07-06).

Telegram alerts are terse by necessity (4096 chars, no native attachments
without a separate photo/document API call). Most incidents (CI failure,
credential expiry, fare-watch drop) have supporting evidence — a log
excerpt, a screenshot, a diff — that's awkward to paste into a Telegram
message but trivial to attach to an email.

This is the reusable primitive: Telegram still carries the "look now"
ping (per the Telegram/AgentMail ROE), this carries the substance.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")

from core.email.agentmail_client import AgentMailClient

INCIDENT_INBOX = "hale-thunderbird@agentmail.to"
COMMANDER_EMAIL = "johnloucks3@gmail.com"


def send_incident_email(subject: str, summary: str, attachments: list[Path] | None = None,
                         to: str = COMMANDER_EMAIL) -> dict:
    """attachments: list of file paths — log excerpts, screenshots, diffs.
    Returns the AgentMail send result. Standing CC to johnloucks3 fires
    automatically via agentmail_client's _with_standing_cc()."""
    import base64

    client = AgentMailClient()
    am_attachments = None
    if attachments:
        am_attachments = []
        for path in attachments:
            path = Path(path)
            content_type = "image/png" if path.suffix.lower() == ".png" else \
                           "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else \
                           "text/plain"
            with open(path, "rb") as f:
                content_b64 = base64.b64encode(f.read()).decode()
            am_attachments.append({
                "filename": path.name,
                "content_type": content_type,
                "content_disposition": "attachment",
                "content": content_b64,
            })

    return client.send_message(
        inbox_id=INCIDENT_INBOX,
        to=[to],
        subject=f"[INCIDENT] {subject}",
        text=summary,
        attachments=am_attachments,
    )
