#!/usr/bin/env python3
"""
Mission Health Check — Report only what needs action TODAY

Reads mission_board_live.yaml and surfaces:
1. P0 CRITICAL — blocking missions (hard dependencies or Commander decision awaited)
2. P1 ACTIVE — in-progress work with T-7 or sooner deadlines
3. P1 ON_HOLD — next action when suspense date arrives (preview for tomorrow)
4. BLOCKED — awaiting external action (Commander, portal auth, etc.)

Filters out: P2/P3, completed, historical.

Usage:
  python3 OpsCenter/mission_health_check.py                # brief report
  python3 OpsCenter/mission_health_check.py --telegram      # send Telegram alert
  python3 OpsCenter/mission_health_check.py --verbose       # full details
"""

import json
import sys
from datetime import datetime, timedelta
import yaml

MISSION_FILE = "/home/john/Thunderbird/OpsCenter/mission_board_live.yaml"
TODAY = datetime.now().date()

def days_until(date_str):
    """Return days until date string (YYYY-MM-DD). Return None if undated."""
    if not date_str or date_str == "null":
        return None
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (target - TODAY).days
    except:
        return None

def load_missions():
    """Load YAML mission board."""
    try:
        with open(MISSION_FILE, 'r') as f:
            data = yaml.safe_load(f)
        return data.get('active_missions', [])
    except Exception as e:
        print(f"❌ Failed to load {MISSION_FILE}: {e}")
        return []

def report_brief():
    """One-line status for Commander inbox."""
    missions = load_missions()

    p0_critical = [m for m in missions if m.get('priority') == 'P0' and m.get('status') != 'completed']
    p1_active = [m for m in missions if m.get('priority') == 'P1' and m.get('status') == 'active']
    blocked = [m for m in missions if m.get('status') == 'blocked']
    on_hold = [m for m in missions if m.get('status') == 'on_hold']

    lines = []
    if p0_critical:
        lines.append(f"🔴 {len(p0_critical)} P0 CRITICAL (action required)")
    if p1_active:
        lines.append(f"🟠 {len(p1_active)} P1 ACTIVE in progress")
    if blocked:
        lines.append(f"⏸️  {len(blocked)} BLOCKED (awaiting external)")
    on_hold_resume = sum(1 for m in on_hold if days_until(m.get('suspense_date')) and days_until(m.get('suspense_date')) <= 7)
    if on_hold_resume:
        lines.append(f"⏰ {on_hold_resume} on hold → resume T-7")

    if not lines:
        lines.append("✅ No P0/P1 action required TODAY")

    return " | ".join(lines)

def report_verbose():
    """Full status report."""
    missions = load_missions()

    print(f"\n🦅 MISSION HEALTH CHECK — {TODAY.isoformat()}")
    print("=" * 70)

    # P0 CRITICAL
    p0 = [m for m in missions if m.get('priority') == 'P0' and m.get('status') != 'completed']
    if p0:
        print(f"\n🔴 P0 CRITICAL ({len(p0)})\n")
        for m in p0:
            print(f"  {m['id']}: {m['title']}")
            print(f"    Status: {m.get('status')} | Assigned: {m.get('assigned_to')}")
            if m.get('blocker'):
                print(f"    BLOCKER: {m['blocker']}")
            print()

    # P1 ACTIVE (in_progress or active)
    p1_active = [m for m in missions if m.get('priority') == 'P1' and m.get('status') in ('active', 'in_progress')]
    if p1_active:
        print(f"\n🟠 P1 ACTIVE ({len(p1_active)})\n")
        for m in p1_active:
            days = days_until(m.get('suspense_date'))
            deadline = f" [T-{days}d]" if days else ""
            print(f"  {m['id']}: {m['title']}{deadline}")
            print(f"    Suspense: {m.get('suspense_date', 'N/A')} | Assigned: {m.get('assigned_to')}")
            if m.get('next_action'):
                print(f"    Next: {m['next_action']}")
            print()

    # BLOCKED (hard dependencies)
    blocked = [m for m in missions if m.get('status') == 'blocked']
    if blocked:
        print(f"\n⏸️  BLOCKED ({len(blocked)})\n")
        for m in blocked:
            print(f"  {m['id']}: {m['title']}")
            print(f"    Blocker: {m.get('blocker', 'unknown')}")
            print()

    # ON_HOLD (resuming T-7 or sooner)
    on_hold = [m for m in missions if m.get('status') == 'on_hold']
    resume_soon = [m for m in on_hold if days_until(m.get('suspense_date')) and days_until(m.get('suspense_date')) <= 7]
    if resume_soon:
        print(f"\n⏰ ON_HOLD → RESUMING SOON ({len(resume_soon)})\n")
        for m in resume_soon:
            days = days_until(m.get('suspense_date'))
            print(f"  {m['id']}: {m['title']}")
            print(f"    Resume: {m.get('suspense_date')} [T-{days}d] | Assigned: {m.get('assigned_to')}")
            print(f"    Next: {m.get('next_action')}")
            print()

    print("=" * 70)

def send_telegram(text):
    """Send to Telegram if token available."""
    try:
        import os
        token = os.environ.get('TELEGRAM_ALERT_BOT_TOKEN') or \
                open('/home/john/Thunderbird/config/telegram_token.txt').read().strip()
        import subprocess
        subprocess.run([
            'curl', '-s',
            f'https://api.telegram.org/bot{token}/sendMessage',
            '-d', f'chat_id=@thunderbird_ops',
            '-d', f'text={text}'
        ], check=False)
        print(f"✅ Telegram alert sent")
    except:
        print(f"⚠️  Telegram send failed (token not found)")

def main():
    if '--verbose' in sys.argv:
        report_verbose()
    elif '--telegram' in sys.argv:
        send_telegram(report_brief())
    else:
        print(report_brief())

if __name__ == '__main__':
    main()
