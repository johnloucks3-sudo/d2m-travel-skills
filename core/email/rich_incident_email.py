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
import html as _html
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")

from core.email.agentmail_client import AgentMailClient

INCIDENT_INBOX = "hale-thunderbird@agentmail.to"
COMMANDER_EMAIL = "johnloucks3@gmail.com"
TEMPLATE_PATH = Path("/home/john/Thunderbird/scripts/agentmail_alert_template.html")

SEVERITY_COLORS = {"P0": "#b00020", "P1": "#cc7a00", "P2": "#8a8a00", "INFO": "#003087"}


def render_alert_html(subject: str, summary: str, severity: str = "P1",
                       details: dict | None = None, log_excerpt: str = "",
                       timestamp: str | None = None) -> str:
    """Fill scripts/agentmail_alert_template.html. `details` becomes the facts
    table (field -> value); values and log_excerpt are HTML-escaped here so
    callers can pass raw text/log content safely."""
    rows = "".join(
        f'<tr><td style="font-family:Georgia,serif;color:#003087;font-size:12px;'
        f'font-weight:bold;border:1px solid #dcd6c7;width:35%;">{_html.escape(str(k))}</td>'
        f'<td style="font-family:Georgia,serif;color:#1a1a1a;font-size:13px;'
        f'border:1px solid #dcd6c7;">{_html.escape(str(v))}</td></tr>'
        for k, v in (details or {}).items()
    )
    template = TEMPLATE_PATH.read_text()
    return (
        template
        .replace("{{SEVERITY}}", _html.escape(severity))
        .replace("{{SEVERITY_COLOR}}", SEVERITY_COLORS.get(severity, "#003087"))
        .replace("{{SUBJECT}}", _html.escape(subject))
        .replace("{{TIMESTAMP}}", timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
        .replace("{{SUMMARY}}", _html.escape(summary))
        .replace("{{DETAIL_ROWS}}", rows)
        .replace("{{LOG_EXCERPT}}", _html.escape(log_excerpt))
    )


def send_incident_email(subject: str, summary: str, attachments: list[Path] | None = None,
                         to: str = COMMANDER_EMAIL, severity: str = "P1",
                         details: dict | None = None, log_excerpt: str = "") -> dict:
    """attachments: list of file paths — log excerpts, screenshots, diffs.
    Returns the AgentMail send result. Standing CC to johnloucks3 fires
    automatically via agentmail_client's _with_standing_cc().

    Pass `details` (dict of facts, e.g. {"Credential": "regent_cookies_oa",
    "Expired": "41.3h ago"}) and/or `log_excerpt` to render the branded HTML
    template alongside the plain-text body — text stays the fallback/primary
    (already verified live), HTML is additive."""
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

    html = None
    if details or log_excerpt:
        html = render_alert_html(subject, summary, severity=severity,
                                  details=details, log_excerpt=log_excerpt)

    return client.send_message(
        inbox_id=INCIDENT_INBOX,
        to=[to],
        subject=f"[INCIDENT] {subject}",
        text=summary,
        html=html,
        attachments=am_attachments,
    )
