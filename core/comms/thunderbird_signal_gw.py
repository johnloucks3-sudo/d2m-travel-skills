"""
thunderbird_signal_gw.py — Hale Signal Gateway.
Uses the bbernhard/signal-cli-rest-api HTTP endpoints (port 8088 on YOGA).
Commander sends Signal "Note to Self" → Hale receives + replies.

REST API:
  Receive: GET  http://YOGA:8088/v1/receive/+17192910742
  Send:    POST http://YOGA:8088/v2/send  {message, number, recipients}
"""

import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import urllib.request
import urllib.error

ACCOUNT      = "+17192910742"
API_BASE     = "http://localhost:8088"
POLL_INTERVAL = 15  # seconds
SIGNAL_MAX_CHARS = 900  # truncate AI replies above this

# Commander's Signal number(s) — only these may dispatch commands
COMMANDER_NUMBERS = frozenset({
    "+17192910742",   # Commander John Loucks work/personal cell
})


def _is_authorized_sender(sender: str) -> bool:
    """Returns True only if sender is in the Commander allowlist."""
    return sender in COMMANDER_NUMBERS

BASE       = Path(__file__).resolve().parent.parent.parent
SIGNAL_LOG = BASE / "OpsCenter" / "hale_signal_log.jsonl"

sys.path.insert(0, str(BASE))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [signal_gw] %(levelname)s %(message)s",
)
log = logging.getLogger("signal_gw")


def _get(path: str, timeout: int = 20):
    url = f"{API_BASE}{path}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        log.error(f"GET {path} → HTTP {e.code}: {e.read().decode()[:120]}")
        return None
    except Exception as e:
        log.error(f"GET {path} failed: {e}")
        return None


def _post(path: str, body: dict, timeout: int = 15):
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode()
    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        log.error(f"POST {path} → HTTP {e.code}: {e.read().decode()[:120]}")
        return None
    except Exception as e:
        log.error(f"POST {path} failed: {e}")
        return None


def send(message: str, recipient: str = ACCOUNT) -> bool:
    result = _post("/v2/send", {
        "message": message,
        "number": ACCOUNT,
        "recipients": [recipient],
    })
    if result and "timestamp" in result:
        log.info(f"Sent to {recipient}: ts={result['timestamp']}")
        return True
    log.error(f"Send failed: {result}")
    return False


def receive() -> list[dict]:
    data = _get(f"/v1/receive/{ACCOUNT}")
    if not isinstance(data, list):
        return []
    return data


def _log(sender: str, direction: str, text: str) -> None:
    SIGNAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "sender": sender,
        "direction": direction,
        "text": text,
    }
    with SIGNAL_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _extract_text(msg: dict) -> str | None:
    """Extract body text from a signal-cli-rest-api message envelope."""
    try:
        body = (
            msg.get("envelope", {})
               .get("dataMessage", {})
               .get("message", "")
            or msg.get("envelope", {})
               .get("syncMessage", {})
               .get("sentMessage", {})
               .get("message", "")
        )
        return body.strip() or None
    except Exception:
        return None


def _is_sync_only(msg: dict) -> bool:
    """True if this is just a sync echo of something Commander sent, not an inbound command."""
    try:
        # syncMessage.sentMessage means Commander sent this — skip it
        if msg.get("envelope", {}).get("syncMessage", {}).get("sentMessage"):
            return True
        return False
    except Exception:
        return False


def _dispatch_to_hale(text: str) -> str:
    """Dispatch the Commander's message to headless Sonnet (Hale) and return the reply."""
    try:
        from OpsCenter.opencode_headless_claude_dispatch import spawn_sonnet_inline

        # Single source of truth — gates-guaranteed compact persona.
        # Replaces the prior one-line identity that left Signal-Hale blind to
        # the four gates (2026-06-10 audit / MISSION-179 parity build).
        channel_directive = (
            "Reply concisely — Signal is a C2 channel, not a full briefing room. "
            "For complex deliverables (emails, itineraries, reports), acknowledge the task and "
            "say you'll route the full output via Telegram or email. "
            "Keep your reply under 500 characters when possible. Lead with the answer."
        )
        try:
            from core.ai_infra.hale_persona_loader import wrap_with_persona, load_state_summary
            _state = load_state_summary()
            _state_block = f"\n\n{_state}\n" if _state else ""
            prompt = wrap_with_persona(
                f"{_state_block}Commander sent this via Signal C2: \"{text}\"\n\n{channel_directive}",
                channel="telegram",  # thin-channel hint; Signal shares the tight format
                compact=True,
            )
        except Exception as _e:
            log.warning(f"persona loader unavailable, minimal persona: {_e}")
            prompt = (
                f"Commander sent this via Signal C2: \"{text}\"\n\n"
                "You are Hale (Ms. Victoria 'Victory' Hale, SES-6, COS/COO Thunderbird Wing, D2M Travel). "
                "Four gates you cannot open without the Commander: client sends, financial commitments, "
                "new-client first contact, strategy direction. " + channel_directive
            )
        result = spawn_sonnet_inline(prompt, "signal_hale_reply")
        if result.get("status") == "SUCCESS":
            return result["output"].strip()
        log.error(f"Sonnet dispatch failed: {result.get('status')}")
        return "🦅 Received. Processing — check Telegram in 2 min.\n— Hale"
    except Exception as e:
        log.error(f"Dispatch error: {e}", exc_info=True)
        return "🦅 Signal received. Processing error — check Telegram.\n— Hale"


def _trim_for_signal(text: str) -> str:
    """Trim AI response to Signal-appropriate length, routing long content to Telegram."""
    if len(text) <= SIGNAL_MAX_CHARS:
        return text
    truncated = text[:SIGNAL_MAX_CHARS].rsplit("\n", 1)[0]
    return f"{truncated}\n\n[Full response → Telegram]"


def handle(msg: dict) -> None:
    # Skip sync echoes (messages Commander sent from their own phone)
    if _is_sync_only(msg):
        return

    text = _extract_text(msg)
    if not text:
        return

    sender = msg.get("envelope", {}).get("source", ACCOUNT)

    # Allowlist gate — silently drop unauthorized senders
    if not _is_authorized_sender(sender):
        log.warning("SIGNAL POLICY: message from unauthorized sender %s — dropped", sender)
        return  # Silently drop — do not reply (don't confirm the gateway is live)

    log.info(f"Inbound from {sender}: {text[:80]}")
    _log(sender, "inbound", text)

    raw_reply = _dispatch_to_hale(text)
    reply = _trim_for_signal(raw_reply)

    if send(reply, recipient=sender):
        _log(ACCOUNT, "outbound", reply)
        log.info(f"Replied: {reply[:80]}")
    else:
        log.error("Reply send failed.")


def run() -> None:
    log.info(f"Signal gateway starting — REST API at {API_BASE}, poll every {POLL_INTERVAL}s")

    # Startup health check
    probe = _get(f"/v1/receive/{ACCOUNT}")
    if probe is None:
        log.error(f"REST API unreachable at {API_BASE}. Exiting.")
        raise SystemExit(1)
    log.info("REST API reachable. Gateway online.")

    send("🦅 Hale Signal C2 online. Send me orders here, Commander.")

    while True:
        try:
            for msg in receive():
                handle(msg)
        except Exception as e:
            log.error(f"Poll error: {e}", exc_info=True)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
