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
Channel: "Yoda and D2M Channels Relay" | chat_id: -5248121475
Bot: @d2m_channels_bot

Usage:
    from core.relay.wing_relay import relay_send, relay_read
    relay_send("CC", "mission_board updated — 7 missions added (079-085)")
    messages = relay_read(since_id=0)
"""

import urllib.request
import urllib.parse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

_TOKEN = os.environ.get("TELEGRAM_RELAY_TOKEN") or "***REMOVED-SECRET***"
_CHAT_ID = -5248121475
_LAST_ID_FILE = Path(__file__).parent.parent.parent / "OpsCenter" / "relay_last_update_id.json"
_BASE = f"https://api.telegram.org/bot{_TOKEN}"


def relay_send(platform: str, message: str, tag: str = "INFO") -> int:
    """Post a relay message. Returns Telegram message_id."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = f"[{platform}→RELAY] {tag} | {ts}\n{message}"
    data = urllib.parse.urlencode({"chat_id": _CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(f"{_BASE}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=10) as r:
        result = json.loads(r.read())
    return result["result"]["message_id"]


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
