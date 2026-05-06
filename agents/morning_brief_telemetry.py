#!/usr/bin/env python3
"""
morning_brief_telemetry.py — Dispatch telemetry section for the Thunderbird morning brief.

Provides a pre-formatted string (plaintext and HTML) containing yesterday's
dispatch rollup so Hale's daily performance is visible at the top of each brief.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTEGRATION HOOK for agents/thunderbird_morning_briefing.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

In run_briefing(), after building executive summary and before calling
send_briefing_json() / render_briefing_html(), add:

    from agents.morning_brief_telemetry import telemetry_section, telemetry_section_html
    dispatch_summary = telemetry_section()          # plaintext for JSON sections
    dispatch_html    = telemetry_section_html()     # HTML for email embedding

For the JSON briefing path (send_briefing_json):
Insert as an extra section at the top of brief_json["sections"]:

    brief_json["sections"].insert(0, {
        "id": "dispatch-telemetry",
        "title": "YESTERDAY'S DISPATCH",
        "text": dispatch_summary,
    })

For the HTML email path (render_briefing_html):
Add dispatch_html near the top of the body, after the header block.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

_ROOT = Path("/home/john/Thunderbird")
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.ops.dispatch_telemetry import daily_rollup


def telemetry_section(target_date: Optional[date] = None) -> str:
    """Return a plaintext summary of yesterday's dispatch activity.

    Format (single line):
        📊 YESTERDAY'S DISPATCH: N tasks | MAX OAuth X% | Layer 3 escalations Y | Saved $Z vs API

    Args:
        target_date: The UTC date to pull rollup for. Defaults to yesterday.

    Returns:
        Single-line plaintext string. Returns a "no activity" sentinel if no events.
    """
    yesterday = target_date or (date.today() - timedelta(days=1))
    r = daily_rollup(target_date=yesterday)
    if r["total_dispatches"] == 0:
        return f"📊 YESTERDAY'S DISPATCH ({yesterday}): no activity logged"
    return (
        f"📊 YESTERDAY'S DISPATCH ({yesterday}): "
        f"{r['total_dispatches']} tasks | "
        f"MAX OAuth {r['max_oauth_pct']:.0f}% | "
        f"Layer 3 escalations {r['escalations']} | "
        f"Saved ${r['savings_total_usd']:.4f} vs API"
    )


def telemetry_section_html(target_date: Optional[date] = None) -> str:
    """Return an HTML block for embedding in the morning brief email.

    Styled to match D2M stationery: cream background, blue accent text.
    Safe to inject directly into the brief body HTML.

    Args:
        target_date: The UTC date to pull rollup for. Defaults to yesterday.

    Returns:
        HTML string with dispatch stats. Returns an empty <div> if no activity.
    """
    yesterday = target_date or (date.today() - timedelta(days=1))
    r = daily_rollup(target_date=yesterday)

    if r["total_dispatches"] == 0:
        return (
            f'<div style="font-family:Georgia,serif;font-size:12px;color:#888;'
            f'padding:6px 16px;border-left:3px solid #ccc;margin:8px 0;">'
            f'📊 DISPATCH: no activity {yesterday}'
            f'</div>'
        )

    savings_str = f"${r['savings_total_usd']:.4f}"
    return (
        f'<div style="font-family:Georgia,serif;font-size:13px;color:#0000ff;'
        f'background:#f7f3ea;padding:8px 16px;border-left:4px solid #0000ff;'
        f'margin:8px 0 16px 0;">'
        f'<strong>📊 YESTERDAY\'S DISPATCH ({yesterday})</strong><br>'
        f'{r["total_dispatches"]} tasks dispatched &nbsp;|&nbsp; '
        f'MAX OAuth {r["max_oauth_pct"]:.0f}% &nbsp;|&nbsp; '
        f'Layer 3 escalations: {r["escalations"]} &nbsp;|&nbsp; '
        f'<strong>Saved {savings_str} vs all-API</strong>'
        f'</div>'
    )
