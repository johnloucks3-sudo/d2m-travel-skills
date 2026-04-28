#!/usr/bin/env python3
"""
Hale Brief Email Sender — MCP Gmail Integration
Composes and sends daily brief email to Commander (johnloucks3@gmail.com).
Sends from d2mconcierge@gmail.com.
"""

import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("hale_brief_email_sender")

MT = timezone(timedelta(hours=-6))
BRIEFS_DOMAIN = "itinerary.d2mluxury.quest"
FROM_EMAIL = "d2mconcierge@gmail.com"
TO_EMAIL = "johnloucks3@gmail.com"


def compose_brief_email(date_str: str) -> tuple[str, str]:
    """
    Compose brief email subject and body.
    Returns: (subject, html_body)
    """
    brief_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    brief_time = datetime.now(MT).strftime("%H:%M")

    subject = f"HALE — DAILY BRIEF | {date_str} 06:00 MT"

    html_body = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.6; color: #1a1a1a; }}
            .container {{ max-width: 900px; margin: 0 auto; background: #f7f3ea; padding: 20px; }}
            .header {{ text-align: center; padding: 20px 0; border-bottom: 3px solid #0000ff; margin-bottom: 30px; }}
            .header h1 {{ color: #0000ff; margin: 0; font-size: 24px; }}
            .header p {{ color: #666; margin: 5px 0 0 0; font-size: 13px; }}
            .visual-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 30px; }}
            .visual-card {{
                background: white;
                border-radius: 8px;
                padding: 20px;
                border: 1px solid #ddd;
                text-align: center;
            }}
            .visual-card h3 {{ margin: 0 0 10px 0; color: #0000ff; font-size: 16px; }}
            .visual-card p {{ margin: 0 0 15px 0; color: #666; font-size: 13px; }}
            .visual-link {{
                display: inline-block;
                background: #0000ff;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                text-decoration: none;
                font-weight: bold;
                font-size: 13px;
            }}
            .visual-link:hover {{ background: #0000cc; }}
            .decisions {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #ffa500; }}
            .decisions h3 {{ margin: 0 0 15px 0; color: #ffa500; font-size: 14px; }}
            .decision-item {{ margin-bottom: 12px; font-size: 13px; padding-left: 20px; position: relative; }}
            .decision-item:before {{ content: "→"; position: absolute; left: 0; color: #0000ff; font-weight: bold; }}
            .footer {{ text-align: center; padding: 20px 0; border-top: 1px solid #ddd; color: #999; font-size: 11px; margin-top: 20px; }}
            .footer p {{ margin: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 HALE — DAILY OPERATIONAL BRIEF</h1>
                <p>Generated {date_str} · 06:00 MT · Commander John Loucks</p>
            </div>

            <div class="visual-grid">
                <div class="visual-card">
                    <h3>📊 Client Lifecycle Wheel</h3>
                    <p>7 active clients, urgency-coded segments, FPD countdown arcs. Click segment for detail panel.</p>
                    <a href="https://{BRIEFS_DOMAIN}/briefs/{date_str}/lifecycle-wheel/" class="visual-link">View Lifecycle Wheel →</a>
                </div>

                <div class="visual-card">
                    <h3>💰 Financial Waterfall</h3>
                    <p>Commission pipeline flow: Prospects → Booked → At-Risk → Projected. Allianz claim divergence shown.</p>
                    <a href="https://{BRIEFS_DOMAIN}/briefs/{date_str}/financial-waterfall/" class="visual-link">View Waterfall →</a>
                </div>

                <div class="visual-card">
                    <h3>🔥 Task Heat Map</h3>
                    <p>Clients × Task Types grid. Urgency-colored, effort-encoded. Hover for task roster by cell.</p>
                    <a href="https://{BRIEFS_DOMAIN}/briefs/{date_str}/task-heatmap/" class="visual-link">View Heat Map →</a>
                </div>

                <div class="visual-card">
                    <h3>⚠️ Risk Matrix</h3>
                    <p>Likelihood × Disruption scatter. Quadrants: Escalate (red), Mitigate (yellow), Monitor, Accept. Action registry below.</p>
                    <a href="https://{BRIEFS_DOMAIN}/briefs/{date_str}/risk-matrix/" class="visual-link">View Risk Matrix →</a>
                </div>
            </div>

            <div class="decisions">
                <h3>⚡ DECISIONS NEEDED FROM COMMANDER</h3>
                <div class="decision-item">
                    <strong>Approve 11 Gmail Drafts?</strong> Kuklinski (validation), McLeod (Silver Muse 60-day + Grandeur TP0.5/TP0.6), Westbrook (Perx + SkyLux), Furlow/Nichols/Ely (CAK). All staged in d2mconcierge drafts folder.
                </div>
                <div class="decision-item">
                    <strong>Initiate Lyons FPD Outreach?</strong> Nancy & Ken Lyons — FPD May 11 (14 days remaining). Direct Commander action required.
                </div>
                <div class="decision-item">
                    <strong>Chase Furlow $15,486 Payment?</strong> Final payment was due Apr 1. Confirm received or authorize A9 follow-up.
                </div>
                <div class="decision-item">
                    <strong>Re-Auth TESS?</strong> Financial feed is blind. Run: <code>python3 thunderbird_tess.py --authorize</code> to restore commission visibility.
                </div>
            </div>

            <div class="footer">
                <p><strong>HALE — Col Victoria "Iron Vic" Hale | Chief of Staff | Dreams2Memories Travel, LLC</strong></p>
                <p>This brief is generated automatically at 05:50 MT daily and sent at 06:00 MT.</p>
                <p style="margin-top: 10px; color: #ccc;">Link expires in 90 days. Briefs archived locally + Google Drive.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return subject, html_body


def send_brief_email(date_str: str) -> bool:
    """
    Send brief email via MCP Gmail.
    Requires mcp__claude_ai_Gmail__create_draft tool.
    """
    try:
        subject, html_body = compose_brief_email(date_str)

        # Import MCP Gmail tool
        # NOTE: This is a placeholder. Actual implementation via MCP gateway.
        logger.info(f"Composing brief email for {date_str}...")
        logger.info(f"Subject: {subject}")
        logger.info(f"To: {TO_EMAIL}")
        logger.info(f"From: {FROM_EMAIL}")

        # TODO: Call MCP mcp__claude_ai_Gmail__create_draft with:
        # - to=[TO_EMAIL]
        # - subject=subject
        # - htmlBody=html_body
        # - (optional: bcc or cc)

        logger.warning("Brief email composition complete; actual send via MCP not yet integrated")
        return True

    except Exception as e:
        logger.error(f"Failed to send brief email: {e}")
        return False


if __name__ == "__main__":
    # Test email composition
    logging.basicConfig(level=logging.INFO)
    today_str = datetime.now(MT).strftime("%Y-%m-%d")
    subject, html_body = compose_brief_email(today_str)
    print(f"Subject: {subject}")
    print(f"\nHTML Body (first 500 chars):\n{html_body[:500]}...")
