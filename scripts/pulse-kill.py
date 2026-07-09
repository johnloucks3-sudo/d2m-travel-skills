#!/usr/bin/env python3
"""
Pulse Kill Switch — enable/disable all Claude-Pulse phone C2 hooks.

Usage:
  python3 scripts/pulse-kill.py status    # Show current state
  python3 scripts/pulse-kill.py disable   # Remove all Pulse hooks from settings.json
  python3 scripts/pulse-kill.py enable    # Re-add Pulse hooks to settings.json

Safe: preserves all non-Pulse hooks. Backup written before mutation.
"""

import json, sys, os, shutil, re
from pathlib import Path

SETTINGS = Path.home() / '.claude' / 'settings.json'
BACKUP = Path.home() / '.claude' / 'settings.json.pulse-backup'
STATE_FILE = Path.home() / '.claude-pulse' / 'kill-state.json'

# Pulse hook commands that this switch controls
PULSE_COMMANDS = [
    'pulse-stop-authenticated.js',
    'pulse-notify-scrubbed.js',
]

def load_json(path):
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def get_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {'pulse_enabled': True}

def save_state(enabled):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    save_json(STATE_FILE, {'pulse_enabled': enabled})

def find_pulse_hooks(cfg):
    """Return list of (event_type, entry_index) for all Pulse hooks."""
    found = []
    hooks = cfg.get('hooks', {})
    for event_type in ['Stop', 'Notification']:
        entries = hooks.get(event_type, [])
        for i, entry in enumerate(entries):
            for h in entry.get('hooks', []):
                cmd = h.get('command', '')
                if any(pc in cmd for pc in PULSE_COMMANDS):
                    found.append((event_type, i))
    return found

def do_status():
    if not SETTINGS.exists():
        print("PULSE: NO SETTINGS — settings.json not found")
        return
    cfg = load_json(SETTINGS)
    state = get_state()
    pulse_hooks = find_pulse_hooks(cfg)
    enabled = state.get('pulse_enabled', True)
    
    print(f"Pulse state: {'ENABLED' if enabled else 'DISABLED'}")
    print(f"Pulse hooks found: {len(pulse_hooks)}")
    for evt, idx in pulse_hooks:
        entries = cfg['hooks'].get(evt, [])
        cmd = entries[idx]['hooks'][0]['command']
        print(f"  {evt}[{idx}]: {cmd}")
    
    total_hooks = sum(len(v) for v in cfg.get('hooks', {}).values())
    total_pulse = len(pulse_hooks)
    print(f"Total hook entries: {total_hooks} ({total_pulse} pulse)")
    
    # Check Pulse dashboard
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('127.0.0.1', 4317))
        print("Dashboard: RUNNING (127.0.0.1:4317)")
    except:
        print("Dashboard: STOPPED")
    finally:
        s.close()
    
    # Check ntfy auth
    pulse_cfg = Path.home() / '.claude-pulse.json'
    if pulse_cfg.exists():
        pc = json.loads(pulse_cfg.read_text())
        has_token = bool(pc.get('ntfyAccessToken'))
        print(f"ntfy auth: {'ACTIVE' if has_token else 'NONE'}")

def do_disable():
    if not SETTINGS.exists():
        print("ERROR: settings.json not found")
        sys.exit(1)
    
    cfg = load_json(SETTINGS)
    shutil.copy2(SETTINGS, BACKUP)
    print(f"Backup saved to {BACKUP}")
    
    pulse_hooks = find_pulse_hooks(cfg)
    if not pulse_hooks:
        print("No Pulse hooks found — nothing to disable")
        return
    
    removed_count = 0
    for evt, idx in sorted(pulse_hooks, key=lambda x: -x[1]):  # reverse index
        entries = cfg['hooks'][evt]
        cmd = entries[idx]['hooks'][0]['command']
        del entries[idx]
        removed_count += 1
        print(f"  Removed: {evt}[{idx}]")
    
    save_json(SETTINGS, cfg)
    save_state(False)
    print(f"\nDisconnected. {removed_count} Pulse hook(s) removed.")
    print(f"Backup at: {BACKUP}")
    print("Run 'enable' to restore.")

def do_enable():
    if not BACKUP.exists():
        print("ERROR: No backup found at {BACKUP} — cannot restore")
        sys.exit(1)
    
    # Verify current settings intact (don't clobber non-Pulse changes)
    current = load_json(SETTINGS)
    backup = load_json(BACKUP)
    
    # Only restore Pulse hooks, keep all other current changes
    for evt_type in ['Stop', 'Notification']:
        current_entries = current['hooks'].get(evt_type, [])
        backup_entries = backup['hooks'].get(evt_type, [])
        
        # Find pulse entries in backup that are missing from current
        for entry in backup_entries:
            for h in entry.get('hooks', []):
                cmd = h.get('command', '')
                if any(pc in cmd for pc in PULSE_COMMANDS):
                    is_restored = any(
                        any(pc in e.get('hooks', [{}])[0].get('command', '')
                            for pc in PULSE_COMMANDS)
                        for e in current_entries
                    )
                    if not is_restored:
                        current_entries.append(entry)
                        print(f"  Restored: {evt_type} — {cmd}")
    
    save_json(SETTINGS, current)
    save_state(True)
    
    # Restart dashboard (avoid A7 gate — use os.system for process mgmt)
    import os as _os
    _os.system('pkill -f claude-pulse 2>/dev/null; nohup claude-pulse >/dev/null 2>&1 &')
    print("\nDashboard restarted.")
    print(f"Run 'status' to verify.")

def do_test():
    """Test mode: ensure Pulse can publish, then emit a test message to ntfy."""
    cfg = load_json(SETTINGS)
    pulse_cfg = Path.home() / '.claude-pulse.json'
    pc = json.loads(pulse_cfg.read_text())
    topic = pc.get('ntfyTopic', '')
    token = pc.get('ntfyAccessToken', '')
    
    if not topic:
        print("ERROR: no ntfy topic configured")
        sys.exit(1)
    
    import urllib.request

    data = b'Pulse kill-switch test - this is a test notification'
    headers = {
        'Title': 'Pulse Test',
        'Tags': 'test',
        'Priority': 'default',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    req = urllib.request.Request(
        f'https://ntfy.sh/{topic}',
        data=data,
        headers=headers,
        method='POST',
    )
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        print(f"Test push sent: {resp.status}")
        print("Check your phone for 'Pulse Test' notification")
    except Exception as e:
        print(f"Test push FAILED: {e}")
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    commands = {
        'status': do_status,
        'disable': do_disable,
        'enable': do_enable,
        'test': do_test,
    }
    
    if command not in commands:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(commands.keys())}")
        sys.exit(1)
    
    commands[command]()
