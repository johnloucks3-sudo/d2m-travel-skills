#!/usr/bin/env python3
"""
Hale Phase 2 Visual Synthesis Daemon Setup & Verification
===========================================================

Manages the systemd service/timer for weekly visual brief generation (Sundays 18:00 MT).
Run this manually to:
  - Enable/disable the timer
  - Check timer status
  - Trigger immediate generation (for testing)
  - View logs

Usage:
  python3 hale_phase2_visuals_daemon.py enable      # Enable weekly generation
  python3 hale_phase2_visuals_daemon.py disable     # Disable weekly generation
  python3 hale_phase2_visuals_daemon.py status      # Check timer status
  python3 hale_phase2_visuals_daemon.py trigger     # Run immediately (for testing)
  python3 hale_phase2_visuals_daemon.py logs        # View recent logs
  python3 hale_phase2_visuals_daemon.py verify      # Verify systemd setup

Author: Col Victoria "Iron Vic" Hale, COS — 2026-04-28
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Paths
_ROOT = Path(__file__).resolve().parent.parent.parent
_SERVICE = "hale-phase2-visuals.service"
_TIMER = "hale-phase2-visuals.timer"
_LOGS = _ROOT / "logs"
_LOGS.mkdir(exist_ok=True)

MT = timezone(timedelta(hours=-6))


def run_cmd(cmd: str) -> tuple[int, str, str]:
    """Run shell command, return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "[TIMEOUT] Command took >10s"
    except Exception as e:
        return 1, "", str(e)


def enable_timer():
    """Enable the systemd timer."""
    print(f"[{datetime.now(MT).strftime('%H:%M:%S')}] Enabling Phase 2 visual synthesis timer...")

    # Reload systemd
    rc, out, err = run_cmd("systemctl --user daemon-reload")
    if rc != 0:
        print(f"  ❌ daemon-reload failed: {err}")
        return False

    # Enable timer
    rc, out, err = run_cmd(f"systemctl --user enable {_TIMER}")
    if rc != 0:
        print(f"  ❌ enable {_TIMER} failed: {err}")
        return False

    # Start timer
    rc, out, err = run_cmd(f"systemctl --user start {_TIMER}")
    if rc != 0:
        print(f"  ❌ start {_TIMER} failed: {err}")
        return False

    print(f"  ✅ Timer enabled and started")
    return True


def disable_timer():
    """Disable the systemd timer."""
    print(f"[{datetime.now(MT).strftime('%H:%M:%S')}] Disabling Phase 2 visual synthesis timer...")

    rc, out, err = run_cmd(f"systemctl --user stop {_TIMER}")
    if rc != 0:
        print(f"  ❌ stop {_TIMER} failed: {err}")
        return False

    rc, out, err = run_cmd(f"systemctl --user disable {_TIMER}")
    if rc != 0:
        print(f"  ❌ disable {_TIMER} failed: {err}")
        return False

    print(f"  ✅ Timer disabled and stopped")
    return True


def check_status():
    """Show current timer status."""
    print(f"\n[TIMER STATUS]")
    rc, out, err = run_cmd(f"systemctl --user status {_TIMER} --no-pager")
    print(out if out else err)

    print(f"\n[SERVICE STATUS]")
    rc, out, err = run_cmd(f"systemctl --user status {_SERVICE} --no-pager")
    print(out if out else err)

    print(f"\n[NEXT SCHEDULED EXECUTION]")
    rc, out, err = run_cmd(f"systemctl --user list-timers {_TIMER} --no-pager")
    print(out if out else "Timer not scheduled")


def trigger_now():
    """Trigger immediate execution (for testing)."""
    print(f"[{datetime.now(MT).strftime('%H:%M:%S')}] Triggering immediate Phase 2 visual synthesis...")

    rc, out, err = run_cmd(f"systemctl --user start {_SERVICE}")
    if rc != 0:
        print(f"  ❌ Trigger failed: {err}")
        return False

    print(f"  ✅ Service triggered. Check logs with: python3 {Path(__file__).name} logs")
    return True


def show_logs():
    """Display recent service logs."""
    print(f"\n[RECENT LOGS — Last 30 entries]")
    rc, out, err = run_cmd(f"journalctl --user -u {_SERVICE} -n 30 --no-pager")
    print(out if out else "[No logs found]")


def verify_setup():
    """Verify systemd files are in place."""
    print(f"\n[VERIFICATION]")

    config_dir = Path.home() / ".config" / "systemd" / "user"
    service_file = config_dir / f"{_SERVICE}"
    timer_file = config_dir / f"{_TIMER}"

    checks = [
        ("Service file exists", service_file.exists()),
        ("Timer file exists", timer_file.exists()),
        ("Dispatcher exists", (_ROOT / "OpsCenter" / "hale_dispatcher.py").exists()),
        ("Phase 2 generators exist", (_ROOT / "core" / "visual_synthesis" / "phase2_generators.py").exists()),
        ("Output directory exists", (_ROOT / "output" / "visuals" / "phase2").exists()),
    ]

    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")

    all_ok = all(result for _, result in checks)
    if all_ok:
        print(f"\n✅ All checks passed. Setup is ready.")
    else:
        print(f"\n⚠️  Some checks failed. Verify setup before enabling timer.")

    return all_ok


if __name__ == "__main__":
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "status"

    if cmd == "enable":
        enable_timer()
    elif cmd == "disable":
        disable_timer()
    elif cmd == "status":
        check_status()
    elif cmd == "trigger":
        trigger_now()
    elif cmd == "logs":
        show_logs()
    elif cmd == "verify":
        verify_setup()
    else:
        print(f"""Usage: python3 {Path(__file__).name} <command>

Commands:
  enable      Enable weekly generation (Sundays 18:00 MT)
  disable     Disable weekly generation
  status      Show current timer and service status
  trigger     Run immediately (for testing)
  logs        View recent execution logs
  verify      Verify systemd files and dependencies

Examples:
  python3 {Path(__file__).name} enable
  python3 {Path(__file__).name} status
  python3 {Path(__file__).name} trigger
  python3 {Path(__file__).name} logs
""")
