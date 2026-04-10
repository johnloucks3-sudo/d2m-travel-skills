#!/usr/bin/env python3
"""
Mythos Availability Monitor — Weekly intel sweep for Claude Mythos access.
Checks multiple channels for any change in availability status.
Sends alert to Commander (johnloucks3@gmail.com) if anything changes.

Run via systemd timer: mythos-monitor.timer (weekly)
"""

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("/home/john/Thunderbird/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "mythos_monitor.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

STATE_FILE = Path("/home/john/Thunderbird/state/mythos_monitor_state.json")
OUTBOX = Path("/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md")

# URLs to check for Mythos availability signals
WATCH_TARGETS = [
    {
        "name": "OpenRouter Mythos listing",
        "url": "https://openrouter.ai/anthropic/claude-mythos",
        # When Mythos goes live on OpenRouter, pricing info will appear
        "signal": "/million tokens",
        "invert": False,  # Alert when pricing appears (= model is live)
    },
    {
        "name": "Anthropic models — Mythos in model table",
        "url": "https://platform.claude.com/docs/en/about-claude/models/overview",
        # When Mythos leaves preview, it gets its own row with a model ID
        "signal": "claude-mythos",
        "invert": False,  # Alert when model ID appears in table (= GA)
    },
    {
        "name": "Anthropic models — invitation-only removed",
        "url": "https://platform.claude.com/docs/en/about-claude/models/overview",
        # Currently says "invitation-only" — alert when that disappears
        "signal": "invitation-only",
        "invert": True,
    },
    {
        "name": "AWS Bedrock — Mythos model ID",
        "url": "https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html",
        # Alert when actual Bedrock model ID appears
        "signal": "anthropic.claude-mythos",
        "invert": False,
    },
    {
        "name": "Anthropic Glasswing — self-serve access",
        "url": "https://anthropic.com/glasswing",
        # Currently invitation-only. Alert when self-serve language appears.
        "signal": "sign up",
        "invert": False,
    },
]


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"last_check": None, "alerts": [], "status": "WATCHING"}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def check_url(url: str, signal: str, invert: bool) -> dict:
    """Fetch URL and check for signal string. Returns result dict."""
    try:
        result = subprocess.run(
            ["curl", "-sL", "--max-time", "15", url],
            capture_output=True,
            text=True,
            timeout=20,
        )
        content = result.stdout.lower()
        signal_found = signal.lower() in content

        if invert:
            # Alert when signal DISAPPEARS
            triggered = not signal_found
            reason = f"'{signal}' no longer found (was blocking access)"
        else:
            # Alert when signal APPEARS
            triggered = signal_found
            reason = f"'{signal}' now appears (new availability)"

        return {
            "success": True,
            "triggered": triggered,
            "reason": reason,
            "content_length": len(content),
        }
    except Exception as e:
        return {"success": False, "triggered": False, "reason": str(e)}


def send_alert(alerts: list[dict]):
    """Write alert to outbox and create email draft via MCP bridge."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    alert_text = f"\n\n## MYTHOS AVAILABILITY ALERT — {timestamp}\n\n"
    for a in alerts:
        alert_text += f"- **{a['name']}**: {a['reason']}\n"
    alert_text += (
        "\n**ACTION:** Check https://anthropic.com/glasswing and "
        "https://openrouter.ai/anthropic/claude-mythos for access.\n"
        "\n---\n"
    )

    # Append to outbox
    with open(OUTBOX, "a") as f:
        f.write(alert_text)

    # Try to create email draft to Commander
    try:
        body = (
            f"Commander,\n\n"
            f"Mythos availability change detected at {timestamp}:\n\n"
        )
        for a in alerts:
            body += f"• {a['name']}: {a['reason']}\n"
        body += (
            f"\nCheck:\n"
            f"- https://anthropic.com/glasswing\n"
            f"- https://openrouter.ai/anthropic/claude-mythos\n"
            f"- https://platform.claude.com/docs/en/about-claude/models/overview\n"
            f"\n— Hale (Automated Mythos Monitor)"
        )

        draft_cmd = [
            "/home/john/Thunderbird/mcp_bridge.sh",
            "gmail_create_draft",
            json.dumps({
                "to": "johnloucks3@gmail.com",
                "subject": f"MYTHOS ALERT — Availability Change Detected {timestamp}",
                "body": body,
            }),
        ]
        subprocess.run(draft_cmd, capture_output=True, text=True, timeout=15)
        logging.info("Alert email drafted to Commander.")
    except Exception as e:
        logging.warning(f"Could not draft alert email: {e}")


def main():
    logging.info("=" * 60)
    logging.info("MYTHOS AVAILABILITY MONITOR — Weekly Check")
    logging.info("=" * 60)

    state = load_state()
    alerts = []

    for target in WATCH_TARGETS:
        logging.info(f"Checking: {target['name']} ({target['url']})")
        result = check_url(target["url"], target["signal"], target["invert"])

        if not result["success"]:
            logging.warning(f"  FAILED: {result['reason']}")
            continue

        if result["triggered"]:
            logging.info(f"  *** TRIGGERED: {result['reason']}")
            alerts.append({"name": target["name"], "reason": result["reason"]})
        else:
            logging.info(f"  No change: {result['reason']}")

    state["last_check"] = datetime.now().isoformat()
    state["check_count"] = state.get("check_count", 0) + 1

    if alerts:
        state["status"] = "ALERT"
        state["alerts"] = alerts
        state["last_alert"] = datetime.now().isoformat()
        logging.info(f"*** {len(alerts)} ALERT(S) — sending to Commander")
        send_alert(alerts)
    else:
        state["status"] = "WATCHING"
        logging.info("No changes detected. Mythos still invitation-only.")

    save_state(state)
    logging.info("Monitor complete.")


if __name__ == "__main__":
    main()
