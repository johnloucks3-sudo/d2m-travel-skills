#!/usr/bin/env python3
"""
Hale Morning Brief Generator
Sends to johnloucks3@gmail.com at 0530 MT weekdays
Comprehensive operational status, priorities, and decisions needed
"""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import base64
import os

def get_nag_queue_alerts() -> str:
    """Return escalating action reminders from nag_queue.json."""
    try:
        result = subprocess.run(
            ['python3', '/home/john/Thunderbird/scripts/check_nag_queue.py'],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout.strip()
        if output and "clear" not in output.lower():
            return output
    except Exception:
        pass
    return ""


def get_mission_board_status():
    """Pull live mission board state"""
    try:
        result = subprocess.run(
            ['python3', '/home/john/Thunderbird/OpsCenter/mission_health_check.py', '--verbose'],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout if result.returncode == 0 else "Mission board unavailable"
    except Exception as e:
        return f"Error reading mission board: {str(e)}"

def get_hale_state():
    """Read latest Hale operational state"""
    state_file = Path('/home/john/Thunderbird/hale_state.json')
    if state_file.exists():
        try:
            with open(state_file) as f:
                return json.load(f)
        except:
            return {}
    return {}

def get_work_items_status():
    """Get status of 8 tracked work items"""
    try:
        result = subprocess.run(
            ['python3', '/home/john/Thunderbird/OpsCenter/work_item_tracker.py', 'brief'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}
    return {}

def get_recent_activity():
    """Check recent work and completions from executor logs"""
    from datetime import date
    import re

    activity = {
        'completed_yesterday': 0,
        'completed_detail': [],
        'failed_count': 0,
        'active_now': 0,
        'blockers': 0,
        'decisions_needed': 0,
        'last_run': 'Unknown'
    }

    # Read from executor logs and get last N runs
    executor_logs = [
        Path('/home/john/Thunderbird/logs/mission_executor_4h.log'),
        Path('/home/john/Thunderbird/logs/daily_executor.log'),
    ]

    all_lines = []
    for log_file in executor_logs:
        if log_file.exists():
            try:
                all_lines.extend(log_file.read_text().strip().split('\n'))
            except:
                continue

    if not all_lines:
        return activity

    # Search from the end backwards to find the most recent executor runs
    # Get the last 100 lines (covers multiple executor runs)
    recent_lines = all_lines[-100:]

    total_completed = 0
    total_failed = 0
    seen_missions = set()

    for line in recent_lines:
        # Track individual mission completions
        if '✅ MISSION-' in line:
            match = re.search(r'MISSION-(\d+)', line)
            if match:
                mission_id = f"MISSION-{match.group(1)}"
                if mission_id not in seen_missions:
                    seen_missions.add(mission_id)
                    total_completed += 1
                    if len(activity['completed_detail']) < 5:
                        # Extract mission title if available
                        title_part = line.split('—')[-1].strip() if '—' in line else ""
                        if not title_part and ':' in line:
                            title_part = line.split(':')[-1].strip()[:40]
                        activity['completed_detail'].append(f"{mission_id}{f': {title_part}' if title_part else ''}")
                    # Capture time
                    if line.startswith('['):
                        activity['last_run'] = line[1:9]

        # Track failures
        if '❌' in line or 'FAILED' in line:
            if 'MISSION-' in line:
                total_failed += 1

    # Look for summary line: "Executor complete: X/Y tasks succeeded"
    for line in reversed(recent_lines):
        if 'Executor complete:' in line and 'tasks' in line:
            match = re.search(r'(\d+)/(\d+)\s+tasks', line)
            if match:
                total_completed = int(match.group(1))
                break

    activity['completed_yesterday'] = total_completed
    activity['failed_count'] = total_failed

    return activity

def get_client_status():
    """Check active client dossiers and upcoming deadlines"""
    dossier_dir = Path('/home/john/Thunderbird/dossiers')
    clients = []

    if dossier_dir.exists():
        for client_dir in sorted(dossier_dir.iterdir())[:5]:  # Top 5
            if client_dir.is_dir():
                clients.append({
                    'name': client_dir.name,
                    'path': str(client_dir)
                })

    return clients

def get_financial_pulse():
    """Quick financial status"""
    pulse = {
        'pending_payments': 0,
        'unpaid_commissions': 0,
        'reconciled_this_week': 0
    }

    state = get_hale_state()
    if 'financial' in state:
        pulse.update(state['financial'])

    return pulse


def get_dossier_sweep_results():
    """Read latest dossier validation sweep results"""
    results_file = Path('/home/john/Thunderbird/logs/dossier_sweep_results.json')
    if not results_file.exists():
        return {'red': [], 'yellow': [], 'green_count': 0, 'total': 0}

    try:
        with open(results_file) as f:
            return json.load(f)
    except Exception:
        return {'red': [], 'yellow': [], 'green_count': 0, 'total': 0}

def get_staff_concerns() -> list:
    """Read staff concerns logged for this brief cycle."""
    concerns_file = Path('/home/john/Thunderbird/OpsCenter/staff_concerns.json')
    if not concerns_file.exists():
        return []
    try:
        import json
        with open(concerns_file) as f:
            data = json.load(f)
        return data.get('concerns', [])
    except Exception:
        return []


def get_tp_queue_item() -> dict:
    """Return the next TP/lifecycle draft pending Commander approval."""
    queue_file = Path('/home/john/Thunderbird/OpsCenter/tp_queue.json')
    if not queue_file.exists():
        return {}
    try:
        import json
        with open(queue_file) as f:
            data = json.load(f)
        pending = [item for item in data.get('queue', []) if item.get('status') == 'pending_approval']
        return pending[0] if pending else {}
    except Exception:
        return {}


def get_silver_activity() -> str:
    """CHIEF SILVER standing section — Overseer involvement, daily,
    non-negotiable (Commander 2026-07-16: 'I need more visibility')."""
    try:
        from core.silver.gate import brief_section
        return brief_section()
    except Exception as e:
        return f"## 🛡️ CHIEF SILVER — section unavailable: {e}"


def format_morning_brief(timestamp):
    """Generate formatted brief HTML"""
    mission_status = get_mission_board_status()
    activity = get_recent_activity()
    clients = get_client_status()
    financial = get_financial_pulse()
    work_items = get_work_items_status()
    nag_alerts = get_nag_queue_alerts()
    dossier_sweep = get_dossier_sweep_results()
    staff_concerns = get_staff_concerns()
    tp_item = get_tp_queue_item()
    silver_activity = get_silver_activity()

    # Calculate time until end of business
    now = datetime.now()
    eob = now.replace(hour=17, minute=30, second=0)
    hours_left = max(0, (eob - now).total_seconds() / 3600)

    html = f"""
<html>
<head>
    <style>
        body {{ font-family: Georgia, serif; color: #0000ff; background: #f7f3ea; margin: 20px; line-height: 1.6; }}
        .header {{ border-bottom: 2px solid #0000ff; padding-bottom: 10px; margin-bottom: 20px; }}
        .section {{ margin-bottom: 20px; padding: 10px; border-left: 3px solid #0000ff; padding-left: 15px; }}
        .section-title {{ font-weight: bold; font-size: 1.1em; margin-bottom: 8px; }}
        .metric {{ margin: 5px 0; }}
        .priority {{ color: #ff0000; font-weight: bold; }}
        .good {{ color: #008000; }}
        .footer {{ margin-top: 30px; border-top: 1px solid #0000ff; padding-top: 10px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🦅 Hale Morning Brief — {timestamp.strftime('%A, %B %d, %Y')}</h1>
        <p>Time: {timestamp.strftime('%H:%M MT')} | Hours until EOB: {hours_left:.1f}</p>
    </div>

    {f'''<div class="section" style="border-left:4px solid #ff0000; background:#fff0f0;">
        <div class="section-title" style="color:#cc0000;">⚠️ ACTION REMINDERS — CLEAR BEFORE DEPARTURE</div>
        <pre style="color:#cc0000; font-family:Georgia,serif; white-space:pre-wrap;">{nag_alerts}</pre>
    </div>''' if nag_alerts else ''}

    <div class="section">
        <div class="section-title">OPERATIONAL PRIORITY (Next 8 Hours)</div>
        <div class="metric">{mission_status}</div>
    </div>

    <div class="section" style="border-left:3px solid #708090;">
        <div class="section-title" style="color:#556;">🛡️ CHIEF SILVER — OVERSEER ACTIVITY</div>
        <pre style="font-family:Georgia,serif; white-space:pre-wrap;">{silver_activity}</pre>
    </div>

    <div class="section">
        <div class="section-title">STAFF CONCERNS — MISSION BOARD</div>
        {''.join([f'''<div class="metric" style="font-family:monospace; font-size:0.92em; white-space:pre-wrap; background:#fff8e8; padding:8px; border-radius:4px; margin-bottom:6px;"><strong>SOURCE:</strong> {c.get("source","?")}
<strong>PRIORITY:</strong> {c.get("priority","?")}
<strong>MISSION:</strong> {c.get("mission_id","—")}
<strong>CONCERN:</strong> {c.get("concern","")}
<strong>RESOLVED:</strong> {"Yes" if c.get("resolved") else "No — awaiting Commander assessment"}</div>''' for c in staff_concerns]) if staff_concerns else '<div class="metric good">No concerns submitted this cycle.</div>'}
        <div class="metric" style="font-size:0.85em; color:#555; margin-top:6px;">Reply with your assessment for each item. Staff will be notified.</div>
    </div>

    {f'''<div class="section" style="border-left:3px solid #9900cc;">
        <div class="section-title" style="color:#9900cc;">TP/LIFECYCLE DRAFT — PENDING YOUR APPROVAL</div>
        <div class="metric" style="font-family:monospace; font-size:0.95em; white-space:pre-wrap; background:#f0eaff; padding:10px; border-radius:4px;"><strong>TASK:</strong> {tp_item.get("phase","")} — {tp_item.get("voyage","")}
<strong>OWNER:</strong> Dani
<strong>PRIORITY:</strong> P1
<strong>DESCRIPTION:</strong> {tp_item.get("draft_preview","")}

<strong>SUBJECT LINE:</strong> {tp_item.get("subject_line","")}
<strong>TARGET SEND:</strong> {tp_item.get("target_send","")}
<strong>HOLDS:</strong> {tp_item.get("hold_notes","")}</div>
        <div class="metric" style="margin-top:8px; color:#555; font-size:0.88em;">Reply APPROVE or APPROVE WITH NOTES to release. One per day until completion.</div>
    </div>''' if tp_item else ''}

    <div class="section">
        <div class="section-title">ACTIVITY SNAPSHOT — Previous 24 Hours</div>
        <div class="metric"><strong>Completed Yesterday: {activity['completed_yesterday']} missions</strong> {f'(Failed: {activity["failed_count"]})' if activity.get('failed_count', 0) > 0 else ''}</div>
        {f'<div style="margin-left:20px; font-size:0.95em;">' + ''.join([f'<div class="metric">  • {m}</div>' for m in activity.get('completed_detail', [])]) + '</div>' if activity.get('completed_detail') else ''}
        <div class="metric">Last Executor Run: {activity.get('last_run', 'Unknown')}</div>
        <div class="metric">Active Right Now: {activity['active_now']} in progress</div>
        <div class="metric priority">Blockers: {activity['blockers']} (awaiting decision)</div>
        <div class="metric">Decisions Needed: {activity['decisions_needed']}</div>
    </div>

    <div class="section">
        <div class="section-title">DOSSIER VALIDATION SWEEP — Nightly Cache Check</div>
        <div class="metric">Total Dossiers Scanned: {dossier_sweep.get('total', 0)}</div>
        {f'<div class="metric priority">🔴 RED (Overdue FPD): {len(dossier_sweep.get("red", []))} clients</div>' if dossier_sweep.get('red') else '<div class="metric good">🟢 RED (Overdue FPD): 0</div>'}
        {f'<div class="metric">🟡 YELLOW (Due Soon): {len(dossier_sweep.get("yellow", []))} clients</div>' if dossier_sweep.get('yellow') else '<div class="metric good">🟡 YELLOW (Due Soon): 0</div>'}
        <div class="metric good">🟢 GREEN (On Track): {dossier_sweep.get('green_count', 0)}</div>
        {''.join([f'<div class="metric priority" style="margin-left:15px;">▸ {item["client_label"]}: {item["reasons"][0] if item["reasons"] else "—"}</div>' for item in dossier_sweep.get('red', [])[:3]]) if dossier_sweep.get('red') else ''}
    </div>

    <div class="section">
        <div class="section-title">WORK ITEM TRACKER — Autonomous Runner Action Items</div>
        {f'<div class="metric">Status: {work_items.get("summary", "Loading...")}</div>' if work_items else '<div class="metric">Work items unavailable</div>'}
        {f'<div class="metric">Progress: {work_items.get("percentage", 0)}% complete</div>' if work_items else ''}
        {f'<div class="metric priority">Red Items (Overdue): {len(work_items.get("red_items", []))} — See details below</div>' if work_items.get("red_items") else '<div class="metric good">No overdue items</div>'}
    </div>

    <div class="section">
        <div class="section-title">CLIENT STATUS — Active Dossiers</div>
        {''.join([f'<div class="metric">• {c["name"]}</div>' for c in clients]) if clients else '<div class="metric">No active dossiers</div>'}
    </div>

    <div class="section">
        <div class="section-title">FINANCIAL PULSE</div>
        <div class="metric">Pending Payments: {financial['pending_payments']}</div>
        <div class="metric">Unpaid Commissions: {financial['unpaid_commissions']}</div>
        <div class="metric good">Reconciled This Week: {financial['reconciled_this_week']}</div>
    </div>

    <div class="section">
        <div class="section-title">HALE STATUS</div>
        <div class="metric">Autonomous Runner: ACTIVE (every 2 hours, 0600-2200 MT weekdays)</div>
        <div class="metric">Last Status Update: {activity.get('last_update', 'Unknown')}</div>
        <div class="metric">Next Brief: Tomorrow 0530 MT</div>
    </div>

    <div class="footer">
        <p>Hale COS/COO — Thunderbird Wing, Dreams2Memories Travel, LLC</p>
        <p>Standing by for Commander direction. Alert: 🚨 Priority items flagged above.</p>
    </div>
</body>
</html>
"""
    return html

def send_brief_email(html_body, recipient='johnloucks3@gmail.com'):
    """Send brief as HTML email via Gmail API"""
    try:
        # Use the Thunderbird Gmail wrapper
        import sys
        sys.path.insert(0, '/home/john/Thunderbird')

        from core.email.thunderbird_gmail import gmail_create_draft_sync

        subject = f"🦅 Hale Morning Brief — {datetime.now().strftime('%a, %b %d')}"

        # Send via d2mconcierge (Hale persona)
        gmail_create_draft_sync(
            to=recipient,
            subject=subject,
            body=html_body,
            persona_id='HALE'
        )

        print(f"✅ Brief drafted to {recipient}")
        return True
    except Exception as e:
        print(f"❌ Error sending brief: {str(e)}")
        return False

def main():
    """Generate and send morning brief"""
    timestamp = datetime.now()

    # Only send on weekdays
    if timestamp.weekday() >= 5:  # Saturday/Sunday
        print("Weekend — skipping brief")
        return

    # Only send between 0530-0600
    if not (5 <= timestamp.hour < 6):
        print(f"Off-schedule (current: {timestamp.hour:02d}:{timestamp.minute:02d}) — running anyway for testing")

    print(f"Generating morning brief for {timestamp.strftime('%a, %b %d at %H:%M MT')}")

    html = format_morning_brief(timestamp)

    # Save to file for reference
    log_path = Path('/home/john/Thunderbird/OpsCenter/hale_brief.log')
    with open(log_path, 'a') as f:
        f.write(f"\n--- Brief generated {timestamp.isoformat()} ---\n{html}\n")

    # Send email
    send_brief_email(html)

if __name__ == '__main__':
    main()
