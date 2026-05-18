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
# SignalGateway — primary class (A7 Sterling L4.2)
# ---------------------------------------------------------------------------

class SignalGateway:
    """Hale Signal Gateway — polls signal-cli, classifies, replies as Hale."""

    def __init__(
        self,
        base_url: str = SIGNAL_BASE_URL,
        commander_number: str = COMMANDER_NUMBER,
        poll_interval: int = POLL_INTERVAL,
        log_path: Path = SIGNAL_LOG,
    ):
        self.base_url         = base_url
        self.commander_number = commander_number
        self.poll_interval    = poll_interval
        self.log_path         = log_path

    # -----------------------------------------------------------------------
    # Signal CLI helpers
    # -----------------------------------------------------------------------

    def _request(self, path: str, method: str = "GET", data: dict | None = None) -> dict | list | None:
        url  = f"{self.base_url}{path}"
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

    def alive(self) -> bool:
        return self._request("/v1/about") is not None

    def receive(self) -> list[dict]:
        result = self._request(f"/v1/receive/{self.commander_number}")
        if isinstance(result, list):
            return result
        return []

    def send(self, recipient: str, message: str) -> bool:
        payload = {
            "message":    message,
            "number":     self.commander_number,
            "recipients": [recipient],
        }
        return self._request("/v2/send", method="POST", data=payload) is not None

    # -----------------------------------------------------------------------
    # Logging (A7 Sterling L4.5 schema: {ts, sender, direction, text})
    # -----------------------------------------------------------------------

    def log(self, sender: str, direction: str, text: str) -> None:
        """Append one entry: direction = 'inbound' | 'outbound'."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts":        datetime.now(timezone.utc).isoformat(),
            "sender":    sender,
            "direction": direction,
            "text":      text,
        }
        with self.log_path.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    # -----------------------------------------------------------------------
    # Message handling
    # -----------------------------------------------------------------------

    def handle(self, envelope: dict) -> None:
        try:
            data_msg = envelope.get("dataMessage") or {}
            text     = (data_msg.get("message") or "").strip()
            sender   = envelope.get("source") or ""

            if not text:
                return

            logger.info(f"Signal message from {sender}: {text[:80]}")
            self.log(sender, "inbound", text)

            from core.comms.hale_unified_classifier import classify_message
            classification = classify_message(text, channel="signal", sender="commander")

            reply = self._build_reply(text, classification)
            if not reply:
                return

            if self.send(sender, reply):
                self.log(self.commander_number, "outbound", reply)
                logger.info(f"Replied to {sender}: {reply[:80]}")
            else:
                logger.error(f"Failed to send reply to {sender}")

        except Exception as e:
            logger.error(f"Error handling signal message: {e}", exc_info=True)

    def _build_reply(self, text: str, classification: dict) -> str:
        """Build Hale's reply. Plain text. Sign-off: — Hale"""
        brain  = classification.get("brain", "self")
        intent = classification.get("intent", "chat")

        if intent == "urgent":
            body = "Received P0 signal. Investigating now. Will update on Telegram in 2 min."
        elif intent == "task":
            body = f"Tasking received via Signal. Running [{brain}] — check Telegram for full response."
        elif intent == "chat":
            body = "Read you. Check Telegram for full response — Signal is C2 only."
        else:
            body = f"Signal received. Routing to [{brain}]. Telegram for full output."

        return f"{body}\n— Hale"

    # -----------------------------------------------------------------------
    # Poll loop
    # -----------------------------------------------------------------------

    def run(self) -> None:
        logger.info(f"Signal gateway starting — polling {self.base_url} every {self.poll_interval}s")

        if not self.alive():
            logger.error("signal-cli container not responding. Check YOGA Docker status.")
            sys.exit(1)

        logger.info("signal-cli alive. Gateway running.")

        while True:
            try:
                for envelope in self.receive():
                    self.handle(envelope)
            except Exception as e:
                logger.error(f"Poll loop error: {e}", exc_info=True)
            time.sleep(self.poll_interval)


# ---------------------------------------------------------------------------
# Module-level shims (backward compat + __main__ entry)
# ---------------------------------------------------------------------------

def run_poll_loop() -> None:
    SignalGateway().run()


if __name__ == "__main__":
    run_poll_loop()
