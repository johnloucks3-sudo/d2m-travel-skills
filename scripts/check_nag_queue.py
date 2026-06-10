#!/usr/bin/env python3
"""
check_nag_queue.py — Persistent action reminders for Commander.
Reads nag_queue.json, outputs escalating alerts based on days remaining.
Called by hale_morning_brief.py and hale_state_updater.py.

Exit 0 always. Prints markdown-safe alert lines for AM brief injection.
"""
import json
import sys
from datetime import date, datetime
from pathlib import Path

TB = Path("/home/john/Thunderbird")
NAG_FILE = TB / "OpsCenter" / "nag_queue.json"


def urgency(days_to_deadline: int) -> tuple[str, str]:
    """Return (emoji, label) based on days remaining to order deadline."""
    if days_to_deadline < 0:
        return "🔴🔴", "OVERDUE"
    elif days_to_deadline == 0:
        return "🔴🔴", "DUE TODAY"
    elif days_to_deadline <= 2:
        return "🔴", f"T-{days_to_deadline} CRITICAL"
    elif days_to_deadline <= 7:
        return "🟠", f"T-{days_to_deadline} URGENT"
    elif days_to_deadline <= 14:
        return "🟡", f"T-{days_to_deadline}"
    else:
        return "🔵", f"T-{days_to_deadline}"


def check() -> list[str]:
    """Return list of alert lines for open nags."""
    try:
        data = json.loads(NAG_FILE.read_text())
    except Exception:
        return []

    today = date.today()
    alerts = []

    for nag in data.get("nags", []):
        if nag.get("status") == "CLEARED":
            continue

        deadline_str = nag.get("order_deadline") or nag.get("embark_date", "")
        try:
            deadline = date.fromisoformat(deadline_str)
        except Exception:
            continue

        days_left = (deadline - today).days
        icon, label = urgency(days_left)
        client = nag.get("client", "?")
        nag_label = nag.get("label", nag.get("type", "action"))
        mission = nag.get("mission_id", "")
        note = nag.get("note", "")

        line = f"{icon} **{label}** — {client}: {nag_label}"
        if mission:
            line += f" [{mission}]"
        if note:
            line += f"\n    → {note}"
        alerts.append(line)

    return alerts


def main():
    alerts = check()
    if not alerts:
        print("NAG QUEUE: clear")
        return

    print("=" * 44)
    print("⚠️  ACTION REMINDERS — CLEAR BEFORE DEPARTURE")
    print("=" * 44)
    for a in alerts:
        print(a)
    print("=" * 44)
    print(f"To clear: edit OpsCenter/nag_queue.json → status: CLEARED")


if __name__ == "__main__":
    main()
