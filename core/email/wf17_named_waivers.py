#!/usr/bin/env python3
"""WF-17 Named Waiver Guard — the ONLY code path that bypasses WF-17.

Generalizes the Nancy Lyons exception (previously a hand-rolled one-off
script per SO_LYONS_WF17_EXCEPTION_PIPELINE_20260705) into a single,
auditable allowlist + guard, per WF17_NAMED_WAIVER_EXPANSION_PLAN_20260706.md.

An inbox or send capability is NOT send authority — only a name on
config/wf17_named_waivers.json is. Every waived send still logs a
provenance stamp to hale_decisions.md and CCs johnloucks3.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")
sys.path.insert(0, "/home/john/Thunderbird/api")

WAIVERS_PATH = Path("/home/john/Thunderbird/config/wf17_named_waivers.json")
DECISIONS_LOG = Path("/home/john/Thunderbird/hale_decisions.md")


class NotWaivedError(RuntimeError):
    """Raised when the recipient is not on the named-waiver list — the send
    MUST NOT proceed; caller should fall back to the normal WF-17 draft path."""


def _bare_email(addr: str) -> str:
    m = re.search(r"<([^>]+)>", addr)
    return (m.group(1) if m else addr).strip().lower()


def load_waivers() -> list:
    return json.loads(WAIVERS_PATH.read_text())["waivers"]


def get_waiver(to_email: str) -> dict | None:
    """Return the waiver record if to_email is on the allowlist, else None."""
    bare = _bare_email(to_email)
    for w in load_waivers():
        if bare in {e.lower() for e in w["emails"]}:
            return w
    return None


def _log_provenance(waiver: dict, to_email: str, subject: str):
    now = datetime.now(timezone.utc).isoformat()
    entry = (
        f"\n## {now[:10]} — WF-17 waived send: {waiver['name']}\n"
        f"**Provenance:** waiver `{waiver['name']}`, granted {waiver['granted_date']}, "
        f"source `{waiver['source']}`. To: {to_email}. Subject: {subject}. "
        f"CC: {', '.join(waiver['cc'])}. Voice track: {waiver['voice_track']}.\n"
    )
    with DECISIONS_LOG.open("a") as f:
        f.write(entry)


def send_waived_client_email(to_email: str, subject: str, text: str, html: str | None = None) -> dict:
    """THE single send path for named-waiver correspondence. Checks the
    allowlist first — NotWaivedError if the recipient isn't on it, caller
    must fall back to the normal WF-17 draft-and-hold path. Routes to the
    correct voice/channel per the waiver record, CCs johnloucks3 always,
    logs a provenance stamp to hale_decisions.md on every send."""
    waiver = get_waiver(to_email)
    if waiver is None:
        raise NotWaivedError(
            f"{to_email} is not on the WF-17 named-waiver list — "
            "falling back to standard draft-and-hold, no exceptions."
        )

    if waiver["send_channel"] == "d2mconcierge_gmail":
        result = _send_via_d2mconcierge(to_email, waiver["cc"], subject, text, html)
    elif waiver["send_channel"] == "agentmail_hale_thunderbird":
        result = _send_via_agentmail(to_email, waiver["cc"], subject, text, html)
    else:
        raise NotWaivedError(f"Unknown send_channel {waiver['send_channel']!r} for {waiver['name']}")

    _log_provenance(waiver, to_email, subject)
    return {"waiver": waiver["name"], "channel": waiver["send_channel"], **result}


def _send_via_d2mconcierge(to_email, cc, subject, text, html):
    import base64
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from thunderbird_google_auth import get_persona_gmail

    svc = get_persona_gmail()
    msg = MIMEMultipart("alternative")
    msg["to"] = to_email
    msg["cc"] = ", ".join(cc)
    msg["subject"] = subject
    msg.attach(MIMEText(text, "plain"))
    if html:
        msg.attach(MIMEText(html, "html"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"gmail_message_id": sent["id"]}


def _send_via_agentmail(to_email, cc, subject, text, html):
    from core.email.agentmail_client import AgentMailClient
    client = AgentMailClient()
    sent = client.send_message(
        inbox_id="hale-thunderbird@agentmail.to",
        to=[to_email], cc=cc, subject=subject, text=text, html=html,
    )
    return {"agentmail_message_id": sent.message_id}
