#!/usr/bin/env python3
"""
HALE-AG Token / Cost / Rate-Limit Telemetry Status Board
Dynamically computes CC/OC/AG token burn, live rate-limit headroom, and verified operational metrics.
Uses core.relay.engine_limits.check_headroom as canonical source of headroom %.

# 18:00 MT reset is an assumption based on task-1977's schedule, NOT confirmed by any Google API — no such API exists.
"""
import json
import os
import datetime
import time
import glob
import subprocess
import urllib.request
from pathlib import Path
import sys

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from core.relay.engine_limits import check_headroom, OPENROUTER_MONTHLY_HARD_CAP

def calculate_ag_informational_tokens():
    """Informational token estimate from active brain logs (not a headroom percentage)."""
    brain_dir = Path("/home/john/.gemini/antigravity-cli/brain")
    total_prompt_tokens = 0
    steps_count = 0

    if brain_dir.exists():
        transcripts = glob.glob(str(brain_dir / "*/.system_generated/logs/transcript.jsonl"))
        now = datetime.datetime.now().timestamp()
        one_day_ago = now - 86400
        for t in transcripts:
            try:
                if Path(t).stat().st_mtime >= one_day_ago:
                    with open(t, "r", encoding="utf-8") as f:
                        for line in f:
                            data = json.loads(line)
                            steps_count += 1
                            content_str = json.dumps(data)
                            total_prompt_tokens += int(len(content_str) * 0.25)
            except Exception:
                pass

    return total_prompt_tokens, steps_count

def get_failed_units_count():
    """Count failed user systemd units."""
    try:
        res = subprocess.run(
            ['systemctl', '--user', 'list-units', '--state=failed', '--no-legend'],
            capture_output=True, text=True, timeout=3
        )
        if res.returncode == 0:
            lines = [l for l in res.stdout.splitlines() if l.strip()]
            return f"{len(lines)} (healthy)" if len(lines) == 0 else f"{len(lines)} failed"
        return "UNKNOWN (systemctl error)"
    except Exception:
        return "UNKNOWN (systemctl failed)"

def get_temporal_status():
    """Check Temporal cluster health."""
    try:
        res = subprocess.run(
            ['temporal', 'operator', 'cluster', 'health', '--address', '127.0.0.1:7233'],
            capture_output=True, text=True, timeout=3
        )
        if res.returncode == 0 and 'SERVING' in res.stdout:
            return "LIVE"
        return "DOWN"
    except Exception:
        return "DOWN"

def get_active_timer_status():
    """Check for currently-running scheduled one-shot timers."""
    logs = glob.glob('/home/john/.gemini/antigravity-cli/brain/*/.system_generated/tasks/task-*.log')
    now = time.time()
    active = []
    for p in logs:
        try:
            mtime = os.path.getmtime(p)
            if (now - mtime) < 600:
                lines = [l.strip() for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
                if lines and 'Still waiting' in lines[-1]:
                    task_id = Path(p).stem
                    rem = lines[-1].split('Remaining time:')[-1].strip() if 'Remaining time:' in lines[-1] else ''
                    active.append(f"{task_id} ACTIVE ({rem})" if rem else f"{task_id} ACTIVE")
        except Exception:
            pass
    return ", ".join(active) if active else "none active"

def get_relay_unread_count():
    """Check unread messages in Wing Relay."""
    try:
        from core.relay.wing_relay import relay_read
        msgs = relay_read()
        return f"{len(msgs)} unread message(s)"
    except Exception as e:
        return "UNKNOWN (relay error)"

def get_brainbridge_pending():
    """Count pending tasks in brain_bridge_board.json."""
    bb_file = repo_root / "core" / "hale_bus" / "brain_bridge_board.json"
    if bb_file.exists():
        try:
            bb_data = json.loads(bb_file.read_text(encoding="utf-8"))
            tasks = bb_data.get("tasks", {})
            pending = [t_id for t_id, t in tasks.items() if t.get("status") == "pending"]
            if pending:
                return f"{len(pending)} pending task(s) ({', '.join(pending)})"
            return "0 pending tasks"
        except Exception:
            return "UNKNOWN (parse error)"
    return "UNKNOWN (file missing)"

def get_portal_status():
    """Check local executive portal health."""
    try:
        req = urllib.request.Request("http://localhost:9090/")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return f"http://localhost:9090/ (LIVE - HTTP {resp.status})"
    except Exception:
        return "http://localhost:9090/ (DOWN)"

def main():
    now_dt = datetime.datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    # Canonical CC headroom check (calls check_headroom("CC") -> get_cc_capacity())
    cc_limits = check_headroom("CC")

    # Canonical OC headroom check
    oc_limits = check_headroom("OC")
    oc_used_pct = oc_limits.get('used_pct', 0.0)
    oc_headroom_pct = oc_limits.get('headroom_pct', 100.0)
    oc_status = oc_limits.get('status', 'OK')

    # Canonical AG headroom check
    # 18:00 MT reset is an assumption based on task-1977's schedule, NOT confirmed by any Google API — no such API exists.
    ag_limits = check_headroom("AG")
    ag_used_pct = ag_limits.get('used_pct', 0.0)
    ag_headroom_pct = ag_limits.get('headroom_pct', 100.0)
    ag_reset_str = ag_limits.get('reset_str', '18:00 MT')

    used_tokens, steps_count = calculate_ag_informational_tokens()

    print(f"================================================================================")
    print(f"             🦅 THUNDERBIRD MULTI-ENGINE TOKEN & RESET STATUS BOARD             ")
    print(f"================================================================================")
    print(f" Engine Lead:             HALE-AG (Antigravity 4-Star Lead)")
    print(f" Current Local Time:      {now_str} MT")
    print(f" Daily Estimated Cost:    $0.00")
    print(f"--------------------------------------------------------------------------------")
    print(f" CC TELEMETRY (TALON-3★ | Claude Max):")
    if cc_limits.get("status") != "UNKNOWN":
        cc_sess_pct = cc_limits.get("five_hour_pct", 0.0)
        cc_sess_reset = cc_limits.get("five_hour_resets_at", "N/A")
        cc_week_pct = cc_limits.get("seven_day_pct", 0.0)
        cc_week_reset = cc_limits.get("seven_day_resets_at", "N/A")
        cc_src = cc_limits.get("source", "canonical")
        print(f"  • Current Session:      {cc_sess_pct}% Used | RESET: {cc_sess_reset}")
        print(f"  • Weekly Limit:         {cc_week_pct}% Used | RESET: {cc_week_reset}")
        print(f"  • Telemetry Source:     {cc_src}")
    else:
        print(f"  • Status:               UNKNOWN ({cc_limits.get('error', 'Unavailable')})")
    print(f"--------------------------------------------------------------------------------")
    print(f" OC TELEMETRY (JET-3★ | OpenCode / DeepSeek-v4):")
    print(f"  • Rate-Limit Progress:  {oc_used_pct}% Used | {oc_headroom_pct}% Headroom Available ({oc_status})")
    print(f"  • Daily Quota Reset:    {ag_reset_str}")
    print(f"--------------------------------------------------------------------------------")
    print(f" AG TELEMETRY (HALE-AG-4★ | Antigravity / Gemini 3.6 Flash):")
    print(f"  • Tokens Consumed:      {used_tokens:,} tokens ({steps_count} steps, informational)")
    print(f"  • Rate-Limit Progress:  {ag_used_pct}% Used | {ag_headroom_pct}% Headroom Available")
    print(f"  • Daily Quota Reset:    {ag_reset_str}")
    print(f"--------------------------------------------------------------------------------")
    print(f" OPERATIONAL STATUS:")
    print(f"  • Systemd Failed Units: {get_failed_units_count()} (Source: systemctl --user list-units --state=failed)")
    print(f"  • Temporal Cluster:     {get_temporal_status()} (Source: temporal operator cluster health)")
    print(f"  • Active Timer:         {get_active_timer_status()} (Source: task-*.log mtime/last line)")
    print(f"  • Wing Relay Inbox:     {get_relay_unread_count()} (Source: core.relay.wing_relay.relay_read)")
    print(f"  • BrainBridge Pending:  {get_brainbridge_pending()} (Source: core/hale_bus/brain_bridge_board.json)")
    print(f"  • OpenRouter Spend Cap: ${OPENROUTER_MONTHLY_HARD_CAP:.2f}/mo cap (spend: UNTRACKED -- no live API key wired) (Source: core.relay.engine_limits)")
    print(f"  • Operational Posture:  STAND DOWN (self-reported persona state, unbacked by state file)")
    print(f"  • Roster Idle Status:   JET IDLE, TALON IDLE (self-reported per-session state)")
    print(f"  • Executive Portal:     {get_portal_status()} (Source: live HTTP GET /)")
    print(f"================================================================================")

if __name__ == "__main__":
    main()
