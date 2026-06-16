#!/usr/bin/env python3
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
D2M RELAY SEND — OC↔CC Bidirectional Communication
OpsCenter/relay_send.py

Usage:
    python3 OpsCenter/relay_send.py --to CC "message from OC"
    python3 OpsCenter/relay_send.py --to OC "message from CC"
    python3 OpsCenter/relay_send.py --to COMMANDER "urgent item needs Commander"
    python3 OpsCenter/relay_send.py --from OC --to CC --priority high "task description"

Both OC (OpenCode) and CC (Claude Code) use this to communicate.
D2M Channels shows every message — Commander observes the full conversation.

Message flow:
  OC → CC:  OC calls relay_send --to CC → writes to relay_queue.jsonl
             → posts to D2M Channels (Commander sees it)
             → CC gateway relay_poll_loop picks it up, processes, responds

  CC → OC:  CC calls relay_send --to OC → writes to relay_queue.jsonl
             → posts to D2M Channels (Commander sees it)
             → writes to opencode_inbox.md (OC polls this)

  Either → COMMANDER: posts to D2MC2C (genuine gate item — use sparingly)
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent
RELAY_QUEUE = THUNDERBIRD / "OpsCenter" / "relay_queue.jsonl"
OC_INBOX    = THUNDERBIRD / "OpsCenter" / "collaboration" / "opencode_inbox.md"
CC_INBOX    = THUNDERBIRD / "OpsCenter" / "collaboration" / "claude_inbox.md"
GW_SCRIPT   = THUNDERBIRD / "OpsCenter" / "thunderbird_telegram_gw.py"

# Telegram tokens (loaded from env)
def _expand_env_value(val: str, env: dict) -> str:
    """Expand shell-style ${VAR} and ${VAR:-default} against already-loaded
    values (then os.environ). Files like config/telegram_gw.env use the bash
    idiom ${TELEGRAM_RELAY_TOKEN:-PLACEHOLDER} to inherit from .env; without
    this expansion the literal placeholder string clobbers the real token and
    every Telegram POST 404s (api.telegram.org/bot${...}/sendMessage)."""
    import os, re

    def repl(m):
        name, default = m.group(1), m.group(3)
        return env.get(name) or os.environ.get(name) or (default if default is not None else m.group(0))

    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}", repl, val)


def _load_env():
    env = {}
    for f in [THUNDERBIRD / ".env", THUNDERBIRD / "config" / "telegram_gw.env"]:
        try:
            for line in f.read_text().splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    k, v = k.strip(), _expand_env_value(v.strip(), env)
                    # Never let an unresolved ${...} placeholder overwrite a real value.
                    if "${" in v and k in env:
                        continue
                    env[k] = v
        except Exception:
            pass
    return env


def _tg_send(token: str, chat_id: int | str, text: str) -> bool:
    """Send a message via Telegram API."""
    import urllib.request as _ur
    try:
        payload = json.dumps({
            "chat_id": chat_id,
            "text": text[:4096],
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }).encode()
        req = _ur.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        _ur.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"[relay_send] Telegram send failed: {e}", file=sys.stderr)
        return False


def enqueue(from_app: str, to_app: str, message: str, priority: str = "normal") -> str:
    """Write a relay message to relay_queue.jsonl. Returns the message ID."""
    msg_id = str(uuid.uuid4())[:8]
    entry = {
        "id":       msg_id,
        "from":     from_app.upper(),
        "to":       to_app.upper(),
        "ts":       datetime.now(timezone.utc).isoformat(),
        "priority": priority,
        "message":  message,
        "status":   "pending",
    }
    RELAY_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with open(RELAY_QUEUE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return msg_id


def send_relay(from_app: str, to_app: str, message: str, priority: str = "normal"):
    """
    Send a relay message from one app to another.
    1. Writes to relay_queue.jsonl (persistent, both apps can read)
    2. Posts to D2M Channels for Commander visibility
    3. For OC→CC: CC gateway loop drains it
       For CC→OC: also writes to opencode_inbox.md for OC pickup
       For either→COMMANDER: routes to D2MC2C (genuine gate only)
    """
    env = _load_env()
    msg_id = enqueue(from_app, to_app, message, priority)
    ts = datetime.now().strftime("%H:%M MT")
    from_tag  = from_app.upper()
    to_tag    = to_app.upper()
    prio_icon = {"high": "🔴", "normal": "📨", "low": "📋"}.get(priority, "📨")

    # ── Post to D2M Channels (Commander observes) ──────────────────────────
    relay_token   = env.get("TELEGRAM_RELAY_TOKEN", "")
    relay_chat_id = env.get("TELEGRAM_RELAY_CHAT_ID", "")

    if relay_token and relay_chat_id:
        channel_text = (
            f"{prio_icon} <b>[{from_tag}→{to_tag}]</b> {ts} #{msg_id}\n"
            f"{message[:3800]}"
        )
        _tg_send(relay_token, relay_chat_id, channel_text)

    # ── Write to recipient inbox ────────────────────────────────────────────
    if to_tag == "OC":
        # Also write to opencode_inbox.md so OC can pick it up via file polling
        _write_oc_inbox(from_tag, message, msg_id, priority)

    elif to_tag == "CC":
        # Gateway relay_poll_loop drains relay_queue.jsonl — no additional file needed
        # But also write to CC inbox for backward compat
        _write_cc_inbox(from_tag, message, msg_id, priority)

    elif to_tag == "COMMANDER":
        # Route to D2MC2C — genuine gate item only
        d2mc2c_token    = env.get("TELEGRAM_D2MC2C_TOKEN", "")
        commander_id_s  = env.get("TELEGRAM_COMMANDER_ID", "7554895206")
        if d2mc2c_token:
            gate_text = (
                f"🚨 <b>[{from_tag} → COMMANDER]</b>\n{message[:3800]}"
            )
            _tg_send(d2mc2c_token, int(commander_id_s), gate_text)

    print(f"[relay] {from_tag}→{to_tag} queued #{msg_id}: {message[:60]}...")
    return msg_id


def _write_oc_inbox(from_app: str, message: str, msg_id: str, priority: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    OC_INBOX.parent.mkdir(parents=True, exist_ok=True)
    with open(OC_INBOX, "a") as f:
        f.write(f"""
---
## RELAY-{msg_id} from {from_app} — {ts}
priority: {priority}
status: UNREAD
task: |
{chr(10).join('  ' + line for line in message.splitlines())}
""")


def _write_cc_inbox(from_app: str, message: str, msg_id: str, priority: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    CC_INBOX.parent.mkdir(parents=True, exist_ok=True)
    with open(CC_INBOX, "a") as f:
        f.write(f"""
---
## RELAY-{msg_id} from {from_app} — {ts}
priority: {priority}
status: UNREAD
task: |
{chr(10).join('  ' + line for line in message.splitlines())}
""")


# ── Read pending messages for a recipient ─────────────────────────────────────

def read_pending(for_app: str) -> list[dict]:
    """Return all pending relay messages addressed to for_app."""
    if not RELAY_QUEUE.exists():
        return []
    pending = []
    for line in RELAY_QUEUE.read_text().splitlines():
        try:
            entry = json.loads(line)
            if entry.get("to") == for_app.upper() and entry.get("status") == "pending":
                pending.append(entry)
        except Exception:
            continue
    return pending


def mark_processed(msg_id: str):
    """Mark a relay message as processed in relay_queue.jsonl."""
    if not RELAY_QUEUE.exists():
        return
    lines = RELAY_QUEUE.read_text().splitlines()
    updated = []
    for line in lines:
        try:
            entry = json.loads(line)
            if entry.get("id") == msg_id:
                entry["status"] = "processed"
                entry["processed_at"] = datetime.now(timezone.utc).isoformat()
            updated.append(json.dumps(entry))
        except Exception:
            updated.append(line)
    RELAY_QUEUE.write_text("\n".join(updated) + "\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="D2M Relay: send messages between OC and CC via D2M Channels"
    )
    parser.add_argument("message", nargs="?", help="Message to send")
    parser.add_argument("--from", dest="from_app", default="CC",
                        help="Sender: OC or CC (default: CC)")
    parser.add_argument("--to", dest="to_app", default="OC",
                        help="Recipient: OC, CC, or COMMANDER (default: OC)")
    parser.add_argument("--priority", choices=["high", "normal", "low"],
                        default="normal")
    parser.add_argument("--read", metavar="APP",
                        help="Read pending messages for APP (OC or CC)")
    args = parser.parse_args()

    if args.read:
        pending = read_pending(args.read)
        if not pending:
            print(f"No pending messages for {args.read.upper()}")
        for m in pending:
            print(f"#{m['id']} [{m['from']}→{m['to']}] {m['ts'][:16]} [{m['priority']}]")
            print(f"  {m['message'][:200]}")
        return

    if not args.message:
        parser.print_help()
        sys.exit(1)

    msg_id = send_relay(args.from_app, args.to_app, args.message, args.priority)
    sys.exit(0)


if __name__ == "__main__":
    main()
