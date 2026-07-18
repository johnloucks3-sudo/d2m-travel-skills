# ============================================================
# ⚠️  PROTECTED FILE — THUNDERBIRD WING STANDING ORDER
# ============================================================
# DO NOT MODIFY without explicit Commander authorization
# via Claude Code (Hale) session.
#
# SPECIFICALLY: DeepSeek v4 / any OpenCode non-Claude model
# MAY NOT edit this file autonomously. Any non-Claude AI
# operating in OpenCode MUST relay a change request to
# Claude Code and receive explicit "proceed" before touching
# this file or any protected scanner/email file.
#
# Full SO: standing_orders/SO_EMAIL_SCANNER_PROTECT_20260608.md
# ============================================================
"""
Wing Relay — CC↔OC Telegram bridge
Channels:
  D2M System  (chat_id: -5248121475 | bot: @d2m_channels_bot) — system alerts, write-only
  Wing Bridge (chat_id: -5159954387 | bot: @GooseD2M_bot)     — OC↔CC relay

Usage:
    from core.relay.wing_relay import relay_send, relay_send_wb, relay_read
    relay_send("CC", "mission_board updated — 7 missions added")
    relay_send_wb("CC", "Hale, what's the FPD status on Kuklinski?")
    messages = relay_read(since_id=0)
"""

import urllib.request
import urllib.parse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

_TOKEN = os.environ.get("TELEGRAM_RELAY_TOKEN") or "***REMOVED-SECRET***"
_CHAT_ID = -5248121475
_LAST_ID_FILE = Path(__file__).parent.parent.parent / "OpsCenter" / "relay_last_update_id.json"
_BASE = f"https://api.telegram.org/bot{_TOKEN}"

# Wing Bridge (OC↔CC relay via Goose bot)
_WB_TOKEN = os.environ.get("TELEGRAM_GOOSE_TOKEN") or "***REMOVED-SECRET***"
_WB_CHAT_ID = int(os.environ.get("TELEGRAM_HALE_CHAT_ID", "-5159954387"))
_WB_BASE = f"https://api.telegram.org/bot{_WB_TOKEN}"


# Durable queue for sends that exhaust all retries — a lost Telegram message is
# logged here instead of crashing the caller (MISSION-670). NEVER relay/notify
# about a queue write (that's the alert-on-alert infinite regress this avoids).
_FAILURE_QUEUE = Path(__file__).parent.parent.parent / "logs" / "wing_relay_failures.jsonl"
_MAX_RETRIES = 3
# Per-attempt socket timeout. The WHOLE retry budget (3*3s attempts + 1s+2s
# backoff = ~12s) MUST stay under the tightest caller's subprocess timeout —
# hale_notify invokes this via subprocess.run(timeout=15). A retry loop that
# ran long (the naive 3*10s) would itself be SIGKILLed mid-flight, which is
# exactly what produced the 213 empty crash reports. Keep this sized to fit.
_ATTEMPT_TIMEOUT = 3


def _post_send(base: str, chat_id: int, text: str, label: str) -> int:
    """POST sendMessage with bounded retries + exponential backoff (1s, 2s).
    Returns the Telegram message_id on success, or 0 on final failure — it
    NEVER raises (a crashed relay subprocess, with a mostly-empty crash report,
    was the entire 670 bug: 224 crashes/7d, 213 empty). On exhaustion the
    message is durably queued to _FAILURE_QUEUE for later inspection/replay."""
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            req = urllib.request.Request(f"{base}/sendMessage", data=data)
            with urllib.request.urlopen(req, timeout=_ATTEMPT_TIMEOUT) as r:
                return json.loads(r.read())["result"]["message_id"]
        except Exception as e:  # SSL, connection reset, HTTP 4xx/5xx, JSON, ...
            last_err = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    try:
        _FAILURE_QUEUE.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "label": label,
               "chat_id": chat_id, "text": text[:500], "error": str(last_err)[:300]}
        with open(_FAILURE_QUEUE, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass  # even the durable-log write must never crash the caller
    return 0


def relay_send(platform: str, message: str, tag: str = "INFO") -> int:
    """Post a system message to D2M System channel. Returns Telegram message_id
    (0 if all retries failed — the message is durably queued, not lost)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = f"[{platform}→RELAY] {tag} | {ts}\n{message}"
    return _post_send(_BASE, _CHAT_ID, text, "relay_send")


def relay_send_wb(platform: str, message: str, tag: str = "INFO") -> int:
    """Post an OC↔CC relay message to Wing Bridge. Returns Telegram message_id
    (0 if all retries failed — the message is durably queued, not lost)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = f"[{platform}→WB] {tag} | {ts}\n{message}"
    return _post_send(_WB_BASE, _WB_CHAT_ID, text, "relay_send_wb")


def relay_read(since_id: int = None) -> list[dict]:
    """Read relay messages since last known update_id. Updates persisted cursor."""
    if since_id is None:
        since_id = _load_cursor()

    params = f"?offset={since_id + 1}&limit=50&timeout=0"
    with urllib.request.urlopen(f"{_BASE}/getUpdates{params}", timeout=10) as r:
        data = json.loads(r.read())

    updates = data.get("result", [])
    messages = []
    max_id = since_id

    for u in updates:
        max_id = max(max_id, u["update_id"])
        for key in ("channel_post", "message"):
            if key in u:
                msg = u[key]
                if msg.get("chat", {}).get("id") == _CHAT_ID:
                    messages.append({
                        "update_id": u["update_id"],
                        "message_id": msg["message_id"],
                        "text": msg.get("text", ""),
                        "date": msg["date"],
                    })

    if max_id > since_id:
        _save_cursor(max_id)

    return messages


def relay_handoff(from_platform: str, to_platform: str, task: str, detail: str = "") -> int:
    """Structured task handoff between platforms."""
    msg = f"HANDOFF → {to_platform}\nTask: {task}"
    if detail:
        msg += f"\nDetail: {detail}"
    return relay_send(from_platform, msg, tag="HANDOFF")


def relay_ack(platform: str, mission_id: str, status: str = "received") -> int:
    """Acknowledge receipt of a mission or handoff."""
    return relay_send(platform, f"ACK {mission_id} — {status}", tag="ACK")


def relay_heartbeat(platform: str, status: str = "ONLINE") -> int:
    """Session-open heartbeat. Call once per session start."""
    return relay_send(platform, f"status={status} | session open", tag="HEARTBEAT")


def _load_cursor() -> int:
    if _LAST_ID_FILE.exists():
        try:
            return json.loads(_LAST_ID_FILE.read_text()).get("last_update_id", 0)
        except Exception:
            return 0
    return 0


def _save_cursor(update_id: int):
    _LAST_ID_FILE.write_text(json.dumps({
        "last_update_id": update_id,
        "updated": datetime.now(timezone.utc).isoformat()
    }))


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "heartbeat"
    platform = sys.argv[2] if len(sys.argv) > 2 else "CC"

    if cmd == "heartbeat":
        mid = relay_heartbeat(platform)
        print(f"Heartbeat sent | msg_id: {mid}")
    elif cmd == "read":
        msgs = relay_read()
        if not msgs:
            print("No new relay messages.")
        for m in msgs:
            print(f"[{m['update_id']}] {m['text'][:120]}")
    elif cmd == "send":
        msg = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "test"
        mid = relay_send(platform, msg)
        print(f"Sent | msg_id: {mid}")
