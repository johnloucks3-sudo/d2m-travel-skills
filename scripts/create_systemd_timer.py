#!/usr/bin/env python3
"""
create_systemd_timer.py — Hale autonomously creates new systemd user timers.

Authority: SO-2026-05-04 §XII — Hale has authority to create/enable/start
           new systemd timers without Commander confirmation.

Usage:
    python3 scripts/create_systemd_timer.py \
        --name "d2m-fare-watch" \
        --description "D2M daily fare watch sweep" \
        --command "python3 /home/john/Thunderbird/core/travel/thunderbird_fare_watch.py" \
        --on-calendar "daily 06:30 MT" \
        --enable

    python3 scripts/create_systemd_timer.py --list
    python3 scripts/create_systemd_timer.py --status d2m-fare-watch
    python3 scripts/create_systemd_timer.py --disable d2m-fare-watch

Note: Creates user-level timers (systemctl --user). Does NOT require sudo.
      Log output goes to: /home/john/Thunderbird/logs/<timer_name>.log
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

SYSTEMD_USER_DIR = Path.home() / ".config/systemd/user"
LOG_DIR = Path("/home/john/Thunderbird/logs")
D2M_UNIT_PREFIX = "d2m-"


def create_timer(
    name: str,
    description: str,
    command: str,
    on_calendar: str = "daily",
    on_boot_sec: str = None,
    randomized_delay_sec: int = 300,
    enable: bool = True,
    start_now: bool = False,
) -> str:
    """Create a systemd user service + timer pair.

    Args:
        name: Timer name (e.g. "d2m-fare-watch" — will be prefixed with d2m- if not already)
        description: Human-readable description for the unit
        command: Full command to run (ExecStart)
        on_calendar: Systemd calendar expression (e.g. "daily", "*-*-* 06:30:00")
        on_boot_sec: Optional OnBootSec delay (e.g. "5min") for boot-triggered timers
        randomized_delay_sec: Jitter to avoid thundering herd
        enable: Enable and start the timer immediately
        start_now: Also trigger an immediate run after enabling

    Returns:
        Status message
    """
    if not name.startswith(D2M_UNIT_PREFIX):
        name = D2M_UNIT_PREFIX + name
    name = name.replace(" ", "-").lower()

    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{name}.log"

    # Service unit
    service_content = f"""[Unit]
Description={description}
After=network-online.target

[Service]
Type=oneshot
ExecStart={command}
StandardOutput=append:{log_file}
StandardError=append:{log_file}
Environment=PYTHONPATH=/home/john/Thunderbird
WorkingDirectory=/home/john/Thunderbird

[Install]
WantedBy=multi-user.target
"""

    # Timer unit
    timer_lines = [
        "[Unit]",
        f"Description=Timer — {description}",
        "",
        "[Timer]",
    ]
    if on_calendar:
        timer_lines.append(f"OnCalendar={on_calendar}")
    if on_boot_sec:
        timer_lines.append(f"OnBootSec={on_boot_sec}")
    timer_lines.append(f"RandomizedDelaySec={randomized_delay_sec}")
    timer_lines.append("Persistent=true")
    timer_lines.extend(["", "[Install]", "WantedBy=timers.target"])
    timer_content = "\n".join(timer_lines) + "\n"

    service_path = SYSTEMD_USER_DIR / f"{name}.service"
    timer_path = SYSTEMD_USER_DIR / f"{name}.timer"

    service_path.write_text(service_content)
    timer_path.write_text(timer_content)
    print(f"✅ Wrote: {service_path}")
    print(f"✅ Wrote: {timer_path}")

    # Reload daemon
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    print("✅ daemon-reload OK")

    if enable:
        subprocess.run(["systemctl", "--user", "enable", f"{name}.timer"], check=True)
        subprocess.run(["systemctl", "--user", "start", f"{name}.timer"], check=True)
        print(f"✅ Enabled and started: {name}.timer")

    if start_now:
        subprocess.run(["systemctl", "--user", "start", f"{name}.service"], check=False)
        print(f"✅ Triggered immediate run: {name}.service")

    # Verify
    result = subprocess.run(
        ["systemctl", "--user", "status", f"{name}.timer", "--no-pager", "-l"],
        capture_output=True, text=True
    )
    return result.stdout + result.stderr


def list_d2m_timers() -> str:
    result = subprocess.run(
        ["systemctl", "--user", "list-timers", "--all", "--no-pager"],
        capture_output=True, text=True
    )
    lines = [l for l in result.stdout.splitlines() if D2M_UNIT_PREFIX in l or "NEXT" in l or "LEFT" in l]
    return "\n".join(lines) or "No D2M timers found."


def timer_status(name: str) -> str:
    if not name.startswith(D2M_UNIT_PREFIX):
        name = D2M_UNIT_PREFIX + name
    result = subprocess.run(
        ["systemctl", "--user", "status", f"{name}.timer", "--no-pager", "-l"],
        capture_output=True, text=True
    )
    return result.stdout + result.stderr


def disable_timer(name: str) -> str:
    if not name.startswith(D2M_UNIT_PREFIX):
        name = D2M_UNIT_PREFIX + name
    subprocess.run(["systemctl", "--user", "stop", f"{name}.timer"], check=False)
    subprocess.run(["systemctl", "--user", "disable", f"{name}.timer"], check=False)
    return f"Disabled: {name}.timer"


def main():
    parser = argparse.ArgumentParser(description="Create/manage D2M systemd user timers")
    parser.add_argument("--name", help="Timer name (d2m- prefix added automatically)")
    parser.add_argument("--description", help="Timer description", default="D2M automated task")
    parser.add_argument("--command", help="Full command to run")
    parser.add_argument("--on-calendar", default="daily", help="Calendar expression (e.g. '*-*-* 06:30:00')")
    parser.add_argument("--on-boot-sec", help="OnBootSec delay")
    parser.add_argument("--randomized-delay", type=int, default=300, help="Jitter in seconds")
    parser.add_argument("--enable", action="store_true", help="Enable and start timer immediately")
    parser.add_argument("--start-now", action="store_true", help="Also trigger an immediate run")
    parser.add_argument("--list", action="store_true", help="List all D2M timers")
    parser.add_argument("--status", help="Show status of a named timer")
    parser.add_argument("--disable", help="Disable a named timer")
    args = parser.parse_args()

    if args.list:
        print(list_d2m_timers())
    elif args.status:
        print(timer_status(args.status))
    elif args.disable:
        print(disable_timer(args.disable))
    elif args.name and args.command:
        print(create_timer(
            name=args.name,
            description=args.description,
            command=args.command,
            on_calendar=args.on_calendar,
            on_boot_sec=args.on_boot_sec,
            randomized_delay_sec=args.randomized_delay,
            enable=args.enable,
            start_now=args.start_now,
        ))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
