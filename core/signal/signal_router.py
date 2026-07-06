"""Signal router — routes inbound Signal messages to Hale and replies in-channel.

Signal is Commander's exclusive C2 channel (Personas/hale_cos.md Channel
Registry: "Signal | ... | Commander only | Plain, concise — Hale only, no
Dani"). No activation word gating needed — unlike the shared Telegram bots,
this linked device only ever sees Commander's own Signal traffic, so every
inbound message is in-scope for Hale.

Reuses the existing Hale dispatch engine (OpsCenter/telegram_hale_router.py)
rather than building a second classifier — one dispatch brain, three channels,
per the plan's own "unified classifier" goal.
"""
import sys
from pathlib import Path

_ROOT = Path("/home/john/Thunderbird")
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "OpsCenter") not in sys.path:
    sys.path.insert(0, str(_ROOT / "OpsCenter"))

from telegram_hale_router import get_hale_response  # shared dispatch brain
from core.signal import signal_cli_adapter as adapter
from core.signal.signal_relay import notify_telegram_fallback

STATE_PATH = _ROOT / "OpsCenter" / "state" / "signal_router_seen.json"


def _load_seen() -> set:
    import json
    if STATE_PATH.exists():
        return set(json.loads(STATE_PATH.read_text()).get("seen_timestamps", []))
    return set()


def _save_seen(seen: set) -> None:
    import json
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({"seen_timestamps": sorted(seen)[-500:]}))


def poll_and_route(receive_timeout: int = 5) -> list[dict]:
    """One polling pass: pull new messages, dispatch each through Hale,
    reply to the same sender. Returns a list of {message, response, status}
    for logging/tests. Call this from a timer (deploy/signal-router.timer),
    same cadence pattern as hale_email_responder.py.
    """
    if not adapter.is_linked():
        return [{"status": "not_linked",
                 "note": "Run signal_cli_adapter.link_device() and complete the human linking step."}]

    results = []
    seen = _load_seen()
    messages = adapter.receive_messages(timeout=receive_timeout)

    for msg in messages:
        key = f"{msg['source']}:{msg['timestamp']}"
        if key in seen:
            continue
        seen.add(key)

        text = msg["message"].strip()
        if not text:
            continue

        response = get_hale_response(text, channel="signal")
        send_result = adapter.send_message(to=msg["source"], message=response)

        if send_result.get("status") != "sent":
            # Signal send failed — fall back to Telegram so nothing is silently lost.
            notify_telegram_fallback(
                f"Signal send failed (to {msg['source']}). Original: {text!r}. "
                f"Reply was: {response!r}"
            )

        results.append({
            "source": msg["source"],
            "message": text,
            "response": response,
            "send_status": send_result.get("status"),
        })

    _save_seen(seen)
    return results


if __name__ == "__main__":
    for r in poll_and_route():
        print(r)
