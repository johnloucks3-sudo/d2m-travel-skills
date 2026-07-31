#!/usr/bin/env python3
"""
Hale → Telegram Reporter — Activity Updates to Commander via Telegram Bot

Hale sends real-time activity updates to Commander via Telegram.
- Decisions made
- Escalations handled
- System alerts
- What Hale is thinking/about to do

Format: Scannable, actionable, mobile-first. No walls of text.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger("hale_telegram_reporter")

# Telegram bot token and Commander ID
D2MC2C_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_C2_BOT_TOKEN", ""))
COMMANDER_TELEGRAM_ID = 7554895206  # John Loucks (@yodalife)


def send_to_commander(
    message: str,
    message_type: str = "update",
    urgent: bool = False,
    also_email: bool = False
) -> bool:
    """
    Send message to Commander via Telegram bot and optionally email.

    Args:
        message: The message text (markdown OK)
        message_type: "update", "decision", "alert", "escalation", "think"
        urgent: If True, add alert emoji and higher priority
        also_email: If True, also send to johnloucks3@gmail.com

    Returns:
        True if sent successfully, False if failed

    Example:
        send_to_commander(
            "Supplier approval decision: McLeod group → approved with 90-day gate",
            message_type="decision",
            also_email=True
        )
    """

    # Routed through the single gate (C2 RECALIBRATION task 8, Commander directive
    # 2026-07-29). This used to hit the bot API directly and, on also_email=True,
    # separately call the Gmail send API — two of the direct senders the gate
    # replaced. notify() is itself the delivery (email, plus Slack if configured),
    # so also_email no longer needs a second call — it is accepted for backward
    # compatibility and otherwise ignored.
    emoji_map = {
        "update": "📋",
        "decision": "✅",
        "alert": "⚠️",
        "escalation": "🔼",
        "think": "🤔"
    }
    emoji = emoji_map.get(message_type, "📌")
    prefix = "🚨 " if urgent else ""

    formatted = f"{prefix}{emoji} **[Hale]** {message}"

    try:
        from core.comms.commander_channel import notify
        kwargs = {"urgency": "NOW" if urgent else "WINDOW", "source": "hale_telegram_reporter"}
        if urgent:
            kwargs["reason"] = f"urgent Hale {message_type} report"
        result = notify(message_type, f"[Hale] {message_type.title()}", formatted, **kwargs)
        return result.get("status") in ("sent", "queued", "suppressed")
    except Exception as e:
        logger.error(f"notify() send failed: {e}")
        return False


def report_decision(decision: str, reasoning: str = "", next_step: str = ""):
    """
    Report a decision Hale made.

    Example:
        report_decision(
            decision="Approved Ponant supplier at 22% margin",
            reasoning="Strong reviews, EU-based logistics",
            next_step="Finance to cut PO, 30-day trial"
        )
    """
    msg = f"**Decision:** {decision}"
    if reasoning:
        msg += f"\n_Reasoning:_ {reasoning}"
    if next_step:
        msg += f"\n→ {next_step}"

    send_to_commander(msg, message_type="decision")


def report_escalation_complete(question: str, ruling: str):
    """
    Report that Hale escalated something and resolved it.

    Example:
        report_escalation_complete(
            question="Supplier approval at 40% margin?",
            ruling="No. Margin unsustainable. Counter at 28% or walk."
        )
    """
    msg = f"**Escalation Resolved**\n_Q:_ {question}\n_A:_ {ruling}"
    send_to_commander(msg, message_type="escalation")


def report_alert(alert_text: str, severity: str = "info"):
    """
    Report a system alert or anomaly.

    severity: "info", "warning", "critical"

    Example:
        report_alert("OpenCode escalation failed — token refresh daemon down", severity="critical")
    """
    urgent = severity == "critical"
    msg = f"**Alert [{severity.upper()}]** {alert_text}"
    send_to_commander(msg, message_type="alert", urgent=urgent)


def report_thinking(thought: str):
    """
    Report something Hale is considering or uncertain about.

    Example:
        report_thinking("Considering whether to approve McLeod's Grandeur upgrade. Need Commander input on price sensitivity.")
    """
    msg = f"{thought}"
    send_to_commander(msg, message_type="think")


def report_activity_summary(actions: list[str], decisions: list[str] = None, alerts: list[str] = None):
    """
    Send a brief activity summary to Commander.

    Example:
        report_activity_summary(
            actions=["Routed Furlow CAK to A8", "Escalated supplier approval to Hale"],
            decisions=["Approved Westbrook Perx booking"],
            alerts=["Culinary Arts Kitchen opens May 1 — 7 days"]
        )
    """
    msg = "**Activity Summary**\n"

    if actions:
        msg += "\n*Actions:*\n" + "\n".join([f"• {a}" for a in actions])

    if decisions:
        msg += "\n*Decisions:*\n" + "\n".join([f"✅ {d}" for d in decisions])

    if alerts:
        msg += "\n*Alerts:*\n" + "\n".join([f"⚠️ {a}" for a in alerts])

    send_to_commander(msg, message_type="update")


def audit_log_entry(action: str, details: str = "", outcome: str = ""):
    """
    Log an action to hale_activity_journal.md AND send brief to Telegram + email.

    Args:
        action: What Hale did (e.g., "Escalated supplier approval")
        details: Context/reasoning
        outcome: Result/next step
    """

    # Write to audit journal
    journal_path = Path("/home/john/Thunderbird/hale_activity_journal.md")
    journal_path.parent.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n### {timestamp}\n**Action:** {action}"
    if details:
        entry += f"\n**Details:** {details}"
    if outcome:
        entry += f"\n**Outcome:** {outcome}"

    with open(journal_path, "a") as f:
        f.write(entry + "\n")

    # Report to Telegram + email (brief version)
    telegram_msg = f"**{action}**"
    if outcome:
        telegram_msg += f"\n→ {outcome}"

    send_to_commander(telegram_msg, message_type="update", also_email=True)


if __name__ == "__main__":
    # Test reporter
    logging.basicConfig(level=logging.INFO)
    print("Testing Hale Telegram reporter...\n")

    # Test 1: Decision
    print("Test 1: Report decision")
    report_decision(
        decision="Approved Regent Grandeur upgrade for Furlow party",
        reasoning="High-value client, strong commission upside",
        next_step="Push to draft, await Commander approval"
    )

    # Test 2: Thinking
    print("\nTest 2: Report thinking")
    report_thinking("Should we consolidate hotel suppliers now or wait until Q3? Cost vs. operational overhead.")

    # Test 3: Alert
    print("\nTest 3: Report alert")
    report_alert("Culinary Arts Kitchen opens May 1 — 7 days for upsells", severity="info")

    # Test 4: Activity summary
    print("\nTest 4: Activity summary")
    report_activity_summary(
        actions=["Routed 5 lifecycle drafts to review queue", "Updated Westbrook dossier"],
        decisions=["Approved CAK excursion for Furlow party"],
        alerts=["FPD deadline: Lyons May 11 (14 days)"]
    )

    print("\n✅ Reporter tests complete")
