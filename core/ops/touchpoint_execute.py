#!/usr/bin/env python3
"""
d2m-touchpoint-execute — Daily scan of lifecycle queue; surfaces ready touchpoints to Commander.
Does NOT send emails. Relays queue summary to blackboard for Hale review → WF-17 gate.
Schedule: Daily 07:00 MDT
"""
import json
import logging
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
LOG_FILE = THUNDERBIRD / "logs" / "touchpoint_execute.log"
QUEUE_CANDIDATES = [
    THUNDERBIRD / "OpsCenter" / "lifecycle_queue.json",
    THUNDERBIRD / "OpsCenter" / "logs" / "lifecycle_scheduler.log",
]
BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "***REMOVED-SECRET***")
COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)


def tg(msg: str):
    try:
        payload = json.dumps({"chat_id": COMMANDER_ID, "text": msg}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=payload, headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        log.warning(f"Telegram send failed: {e}")


def scan_lifecycle_queue() -> list[dict]:
    """Read lifecycle queue JSON if present."""
    for path in QUEUE_CANDIDATES:
        if path.suffix == ".json" and path.exists():
            try:
                data = json.loads(path.read_text())
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "queue" in data:
                    return data["queue"]
            except Exception as e:
                log.warning(f"Could not parse {path}: {e}")
    return []


def relay(msg: str):
    try:
        subprocess.run(
            ["python3", str(THUNDERBIRD / "core" / "relay" / "wing_relay.py"), "send", "OC", msg],
            capture_output=True, timeout=15
        )
    except Exception as e:
        log.warning(f"Relay failed: {e}")


def main():
    log.info("=== Touchpoint Execute starting ===")
    queue = scan_lifecycle_queue()

    today = datetime.now().date()
    ready = [t for t in queue if t.get("send_date") and str(today) <= t.get("send_date", "9999")]

    log.info(f"Queue: {len(queue)} total, {len(ready)} ready/upcoming")

    if ready:
        summary_lines = []
        for t in ready[:5]:
            client = t.get("client", "Unknown")
            type_ = t.get("type", "touchpoint")
            send_date = t.get("send_date", "?")
            summary_lines.append(f"  {send_date} | {client} | {type_}")
        msg = (
            f"Touchpoint Queue — {today}\n"
            f"{len(ready)} ready:\n" + "\n".join(summary_lines) +
            ("\n  ..." if len(ready) > 5 else "") +
            "\n\nAll at WF-17 — Commander sends."
        )
        tg(msg)
        relay(f"Touchpoint queue: {len(ready)} ready for {today}")
    else:
        log.info("No touchpoints due today.")
        relay(f"Touchpoint queue: 0 ready for {today}")

    log.info("=== Touchpoint Execute complete ===")


if __name__ == "__main__":
    main()
