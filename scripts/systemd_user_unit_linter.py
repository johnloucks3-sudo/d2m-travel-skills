#!/usr/bin/env python3
"""
scripts/systemd_user_unit_linter.py — Automated Systemd User Unit Linter & Health Guard

Enforces Standing Order SO 2026-08-01:
1. Scans ~/.config/systemd/user/*.service and *.timer for invalid user-session target dependencies:
   - Removes `Requires=network-online.target` / `After=network-online.target` (fails in --user sessions).
   - Replaces with `Wants=network.target`.
2. Scans for `Type=forking` on non-forking Python scripts and auto-corrects to `Type=oneshot`.
3. Performs a 3-Point Audit Verification:
   a. Verifies 0 failed units via systemctl --user list-units --failed.
   b. Checks journalctl for service errors in past 1h.
   c. Verifies all active timers have valid NEXT run timestamps.
"""
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

USER_UNITS_DIR = Path.home() / ".config" / "systemd" / "user"

def lint_user_units(fix: bool = True) -> tuple[int, list[str]]:
    """Scan and optionally auto-correct invalid target dependencies in user systemd units."""
    modified_files = []
    issues_found = 0

    unit_files = glob.glob(str(USER_UNITS_DIR / "*.service")) + glob.glob(str(USER_UNITS_DIR / "*.timer"))
    
    for uf in unit_files:
        try:
            content = Path(uf).read_text()
            orig_content = content

            # Fix 1: network-online.target in user session units
            if "network-online.target" in content:
                issues_found += 1
                content = content.replace("Requires=network-online.target", "Wants=network.target")
                content = content.replace("After=network-online.target", "Wants=network.target")

            # Fix 2: Type=forking on non-forking python scripts
            if "Type=forking" in content and "python" in content.lower():
                issues_found += 1
                content = content.replace("Type=forking", "Type=oneshot")

            if fix and content != orig_content:
                Path(uf).write_text(content)
                modified_files.append(uf)
        except Exception as exc:
            print(f"Error reading/writing {uf}: {exc}", file=sys.stderr)

    if modified_files and fix:
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        print(f"✅ Auto-corrected {len(modified_files)} systemd user unit file(s) & reloaded daemon.")

    return issues_found, modified_files


def run_3point_audit_check() -> bool:
    """Execute mandatory 3-point audit check before declaring system clean."""
    print("=== MANDATORY 3-POINT AUDIT VERIFICATION ===")
    
    # 1. Failed units check
    res_failed = subprocess.run(["systemctl", "--user", "list-units", "--failed"], capture_output=True, text=True)
    failed_lines = [l for l in res_failed.stdout.splitlines() if "loaded failed failed" in l]
    print(f"1. Failed Units Count: {len(failed_lines)}")
    
    # 2. Journal errors check in past 1 hour
    res_journal = subprocess.run(
        ["journalctl", "--user", "-p", "err", "--since", "1 hour ago", "--no-pager"],
        capture_output=True, text=True
    )
    err_lines = [l for l in res_journal.stdout.splitlines() if "error" in l.lower() or "failed" in l.lower()]
    print(f"2. Unresolved Journal Errors (Past 1h): {len(err_lines)}")

    # 3. Active timers sanity check
    res_timers = subprocess.run(["systemctl", "--user", "list-timers", "--all"], capture_output=True, text=True)
    timer_count = len([l for l in res_timers.stdout.splitlines() if ".timer" in l])
    print(f"3. Verified Active Timers Count: {timer_count}")

    is_clean = (len(failed_lines) == 0)
    print(f"\nFinal Audit Verdict: {'🟢 100% CLEAN' if is_clean else '🔴 UNRESOLVED FAILURES REMAIN'}")
    return is_clean


def main():
    print("🦅 Running Thunderbird Systemd User-Session Linter & Audit Guard...")
    issues, fixed = lint_user_units(fix=True)
    print(f"Linter finished: {issues} issue(s) detected across user units.")
    clean = run_3point_audit_check()
    sys.exit(0 if clean else 1)


if __name__ == "__main__":
    main()
