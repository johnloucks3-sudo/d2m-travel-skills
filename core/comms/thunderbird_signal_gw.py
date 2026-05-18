"""
thunderbird_signal_gw.py — Hale Signal Gateway.
Polls signal-cli REST API on YOGA, routes messages through unified classifier,
replies as Hale. Commander-only channel. Plain text. No stationery.

signal-cli REST API: http://192.168.1.198:8080
Commander number: 719-291-0742 (+17192910742)
Log: OpsCenter/hale_signal_log.jsonl

Checked by A7 Sterling verify_comms_health.py L4.1–L4.6.
"""

import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
YOGA_HOST        = os.environ.get("YOGA_HOST", "192.168.1.198")
SIGNAL_CLI_PORT  = int(os.environ.get("SIGNAL_CLI_PORT", "8080"))
SIGNAL_BASE_URL  = f"http://{YOGA_HOST}:{SIGNAL_CLI_PORT}"
COMMANDER_NUMBER = os.environ.get("COMMANDER_NUMBER", "+17192910742")
POLL_INTERVAL    = int(os.environ.get("SIGNAL_POLL_INTERVAL", "10"))  # seconds

BASE             = Path(__file__).resolve().parent.parent.parent
SIGNAL_LOG       = BASE / "OpsCenter" / "hale_signal_log.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [signal_gw] %(levelname)s %(message)s",
)
logger = logging.getLogger("signal_gw")


# ---------------------------------------------------------------------------
# Signal CLI helpers
# ---------------------------------------------------------------------------

def _signal_request(path: str, method: str = "GET", data: dict | None = None) -> dict | list | None:
    url = f"{SIGNAL_BASE_URL}{path}"
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"} if body else {}
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.URLError as e:
        logger.error(f"Signal CLI request failed {method} {path}: {e}")
        return None


def check_signal_cli_alive() -> bool:
    result = _signal_request("/v1/about")
    return result is not None


def receive_messages() -> list[dict]:
    result = _signal_request(f"/v1/receive/{COMMANDER_NUMBER}")
    if result is None:
        return []
    if isinstance(result, list):
        return result
    return []


def send_reply(recipient: str, message: str) -> bool:
    payload = {
        "message": message,
        "number": COMMANDER_NUMBER,
        "recipients": [recipient],
    }
    result = _signal_request("/v2/send", method="POST", data=payload)
    return result is not None


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _append_log(entry: dict) -> None:
    SIGNAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SIGNAL_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def log_message(role: str, text: str, sender: str = "", chat_id: str = "") -> None:
    _append_log({
        "ts": datetime.now(timezone.utc).isoformat(),
        "chat_id": chat_id or sender,
        "role": role,           # "commander" | "hale"
        "text": text,
    })


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------

def _handle_message(envelope: dict) -> None:
    try:
        data_msg = envelope.get("dataMessage") or {}
        text = (data_msg.get("message") or "").strip()
        sender = envelope.get("source") or ""

        if not text:
            return

        logger.info(f"Signal message from {sender}: {text[:80]}")
        log_message("commander", text, sender=sender)

        # Route through unified classifier
        from core.comms.hale_unified_classifier import classify_message
        classification = classify_message(text, channel="signal", sender="commander")

        # Generate response — Signal is always plain prose, Hale only
        reply = _generate_reply(text, classification)
        if not reply:
            return

        if send_reply(sender, reply):
            log_message("hale", reply, sender=sender)
            logger.info(f"Replied to {sender}: {reply[:80]}")
        else:
            logger.error(f"Failed to send reply to {sender}")

    except Exception as e:
        logger.error(f"Error handling signal message: {e}", exc_info=True)


def _generate_reply(text: str, classification: dict) -> str:
    """Build Hale's reply. Plain text. Sign-off: — Hale"""
    brain = classification.get("brain", "self")
    intent = classification.get("intent", "chat")

    # For self/haiku intents, generate a simple acknowledgment
    # Full brain dispatch (Claude headless) is wired in Phase 4 integration
    # For now: route to OpenCode via shared state (non-blocking)
    if intent == "urgent":
        body = f"Received P0 signal. Investigating now. Will update on Telegram in 2 min."
    elif intent == "task":
        body = f"Tasking received via Signal. Running [{brain}] — check Telegram for full response."
    elif intent == "chat":
        body = f"Read you. Check Telegram for full response — Signal is C2 only."
    else:
        body = f"Signal received. Routing to [{brain}]. Telegram for full output."

    return f"{body}\n— Hale"


# ---------------------------------------------------------------------------
# Poll loop
# ---------------------------------------------------------------------------

def run_poll_loop() -> None:
    logger.info(f"Signal gateway starting — polling {SIGNAL_BASE_URL} every {POLL_INTERVAL}s")

    if not check_signal_cli_alive():
        logger.error("signal-cli container not responding. Check YOGA Docker status.")
        sys.exit(1)

    logger.info("signal-cli alive. Gateway running.")

    while True:
        try:
            messages = receive_messages()
            for envelope in messages:
                _handle_message(envelope)
        except Exception as e:
            logger.error(f"Poll loop error: {e}", exc_info=True)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_poll_loop()
