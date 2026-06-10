#!/usr/bin/env python3
"""
Loucks Guinea Pig Lifecycle — One-Day Advance Notice System
Runs daily at 06:00 MT. For each event where fire_date == tomorrow:
  1. Sends Telegram D2MC2C page to Commander
  2. Writes alert to OpsCenter/loucks_advance_alerts.json (read by morning brief)

Standing order: Commander directive 2026-06-10. Every TP, both channels.
"""

import json
import os
import sys
import requests
from pathlib import Path
from datetime import date, timedelta, datetime

ROOT = Path("/home/john/Thunderbird")
SCHEDULE_FILE = ROOT / "OpsCenter" / "loucks_guinea_pig_schedule.json"
ALERTS_FILE   = ROOT / "OpsCenter" / "loucks_advance_alerts.json"
INBOX_FILE    = ROOT / "OpsCenter" / "collaboration" / "claude_inbox.md"
ENV_FILE      = ROOT / ".env"


def load_env(env_path: Path) -> dict:
    env = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip()
    return env


def tg_send(token: str, chat_id: int, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=20)
        data = r.json()
        if not data.get("ok"):
            print(f"[TG ERROR] {data.get('description', '?')}", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"[TG EXCEPTION] {e}", file=sys.stderr)
        return False


def build_message(event: dict, fire_date_str: str) -> str:
    urgency_emoji = {"P0": "🚨", "P1": "⚡", "P2": "📋"}.get(event.get("urgency", "P1"), "📋")
    trip_short = {
        "Door County": "🌲 DOOR COUNTY",
        "Grandeur Panama Canal": "🚢 GRANDEUR PANAMA",
        "Silver Nova Mediterranean": "⚓ SILVER NOVA MED"
    }.get(event.get("trip", ""), event.get("trip", ""))

    lines = [
        f"🦅 <b>LIFECYCLE ALERT — T-1</b>",
        f"",
        f"{urgency_emoji} <b>{trip_short}</b>",
        f"<b>{event.get('tp', '')} — {event.get('label', '')}</b>",
        f"",
        f"📅 Fires tomorrow: <b>{fire_date_str}</b>",
    ]

    if event.get("notes"):
        lines.extend(["", f"📌 {event['notes']}"])

    lines.extend([
        "",
        f"<i>— Hale · Thunderbird Wing · {date.today().isoformat()}</i>"
    ])

    return "\n".join(lines)


def main():
    # Load env for Telegram credentials
    env = load_env(ENV_FILE)
    # Fallback: also check os.environ (in case set by systemd unit)
    token = env.get("TELEGRAM_C2_BOT_TOKEN") or \
            env.get("TELEGRAM_BOT_TOKEN") or \
            os.environ.get("TELEGRAM_C2_BOT_TOKEN") or \
            os.environ.get("TELEGRAM_BOT_TOKEN", "")
    commander_id = int(
        env.get("TELEGRAM_COMMANDER_ID") or
        os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206")
    )

    if not token:
        print("[ERROR] No Telegram token found. Check .env TELEGRAM_C2_BOT_TOKEN.", file=sys.stderr)
        sys.exit(1)

    if not SCHEDULE_FILE.exists():
        print(f"[ERROR] Schedule file not found: {SCHEDULE_FILE}", file=sys.stderr)
        sys.exit(1)

    schedule = json.loads(SCHEDULE_FILE.read_text())
    tomorrow = date.today() + timedelta(days=1)
    tomorrow_str = tomorrow.isoformat()

    matching = [
        e for e in schedule.get("events", [])
        if e.get("fire_date") == tomorrow_str
    ]

    if not matching:
        print(f"[OK] No events on {tomorrow_str}. Nothing to send.")
        # Clear any stale alerts for today
        _write_alerts([], tomorrow_str)
        return

    print(f"[INFO] {len(matching)} event(s) fire on {tomorrow_str}:")
    sent_count = 0
    failed = []

    for event in matching:
        print(f"  → {event['id']}: {event['label']}")
        msg = build_message(event, tomorrow_str)
        ok = tg_send(token, commander_id, msg)
        if ok:
            sent_count += 1
        else:
            failed.append(event["id"])

    # Write alerts file for morning brief pickup
    _write_alerts(matching, tomorrow_str)
    # Pre-staging doctrine: write Wing prep request to claude_inbox.md
    _write_inbox_request(matching, tomorrow_str)

    if failed:
        print(f"[WARN] Failed to send: {failed}", file=sys.stderr)
    print(f"[DONE] Sent {sent_count}/{len(matching)} alerts for {tomorrow_str}.")

    if failed:
        sys.exit(1)


def _write_alerts(events: list, for_date: str) -> None:
    """Write/update the loucks_advance_alerts.json for morning brief pickup."""
    alerts = {
        "generated": datetime.now().isoformat(),
        "for_date": for_date,
        "count": len(events),
        "events": [
            {
                "id": e.get("id"),
                "trip": e.get("trip"),
                "tp": e.get("tp"),
                "label": e.get("label"),
                "fire_date": e.get("fire_date"),
                "urgency": e.get("urgency"),
                "notes": e.get("notes"),
            }
            for e in events
        ]
    }
    ALERTS_FILE.write_text(json.dumps(alerts, indent=2))


def _write_inbox_request(events: list, for_date: str) -> None:
    """Append Wing prep requests to claude_inbox.md for morning session pickup.

    Pre-staging doctrine (Commander directive 2026-06-10):
    Wing prepares support items BEFORE the TP fires — not reactively during Commander's session.
    """
    if not events:
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"\n---",
        f"## GUINEA PIG PRE-STAGE — {ts} MT",
        f"*{len(events)} TP(s) fire tomorrow ({for_date}). Hale: assess and prep Wing support before Commander's session.*\n",
    ]

    for e in events:
        urgency = e.get("urgency", "P1")
        lines.append(f"**[{urgency}] {e.get('tp', '')} — {e.get('label', '')}**")
        lines.append(f"- Trip: {e.get('trip', '')}")
        lines.append(f"- Fire date: {e.get('fire_date', '')}")
        if e.get("notes"):
            lines.append(f"- Context: {e.get('notes')}")
        lines.append(f"- **Hale action**: Review what Wing can pre-complete, stage, or surface so Commander's session is execution-ready, not discovery-mode.")
        lines.append("")

    lines.append("*— loucks_guinea_pig_notifier · pre-staging doctrine 2026-06-10*\n")

    if INBOX_FILE.exists():
        with open(INBOX_FILE, "a") as f:
            f.write("\n".join(lines))
    else:
        INBOX_FILE.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
