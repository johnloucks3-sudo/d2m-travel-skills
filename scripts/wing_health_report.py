#!/usr/bin/env python3
"""
wing_health_report.py — On-demand Wing health report.
Pulls latest state from dead code scan, Drive health, Evernote backup,
and supertimer status. Commander can run any time for instant readout.

Usage: python3 scripts/wing_health_report.py [--telegram]
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
STATE = ROOT / "OpsCenter/state"


def _age(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    delta = datetime.now(tz=timezone.utc) - mtime
    h = int(delta.total_seconds() // 3600)
    m = int((delta.total_seconds() % 3600) // 60)
    if h >= 24:
        return f"{h // 24}d {h % 24}h ago"
    return f"{h}h {m}m ago"


def _read(path: Path, max_lines: int = 10) -> str:
    if not path.exists():
        return "(not found)"
    lines = path.read_text(errors="ignore").splitlines()
    return "\n".join(lines[:max_lines])


def build_report() -> str:
    lines = [
        f"╔══ WING HEALTH REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')} MT ══╗",
        "",
    ]

    # 1. Dead Code
    dead_report = STATE / "dead_code_report.txt"
    lines.append("━━ DEAD CODE SCAN ━━")
    if dead_report.exists():
        header = dead_report.read_text(errors="ignore").splitlines()[:3]
        lines += header
        lines.append(f"   [{_age(dead_report)}]")
    else:
        lines.append("   No scan yet — runs weekly via audit_bot")
    lines.append("")

    # 2. Drive Health
    drive_report = STATE / "drive_health_latest.txt"
    lines.append("━━ DRIVE HEALTH ━━")
    if drive_report.exists():
        dh = _read(drive_report, 12)
        lines.append(dh)
        lines.append(f"   [{_age(drive_report)}]")
    else:
        lines.append("   No scan yet — runs daily via backup_bot")
    lines.append("")

    # 3. Evernote
    lines.append("━━ EVERNOTE BACKUP ━━")
    # Check supertimer state for backup_bot evernote-backup
    bot_state = ROOT / "OpsCenter/supertimer_backup_bot_state.json"
    if bot_state.exists():
        try:
            st = json.loads(bot_state.read_text())
            ev = st.get("tasks", {}).get("evernote-backup", {})
            last_status = ev.get("last_status", "unknown")
            last_run = ev.get("last_run", 0)
            if last_run:
                dt = datetime.fromtimestamp(last_run, tz=timezone.utc)
                ago = _age(Path(bot_state))
                lines.append(f"   Last run: {dt.strftime('%Y-%m-%d %H:%M')} UTC | Status: {last_status.upper()}")
            else:
                lines.append("   Not yet run this session")
        except Exception as e:
            lines.append(f"   State parse error: {e}")
    else:
        lines.append("   backup_bot state not found")
    lines.append("")

    # 4. Supertimer bot summary
    lines.append("━━ SUPERTIMER BOTS ━━")
    bot_names = ["ops_bot", "comms_bot", "infra_bot", "client_bot", "metrics_bot",
                 "intel_bot", "mission_bot", "finance_bot", "ai_exec_bot", "backup_bot", "audit_bot"]
    for bot in bot_names:
        sf = ROOT / f"OpsCenter/supertimer_{bot}_state.json"
        if sf.exists():
            try:
                st = json.loads(sf.read_text())
                consec = st.get("consecutive_failures", 0)
                last = st.get("last_run", 0)
                tasks = st.get("tasks", {})
                ok = sum(1 for t in tasks.values() if t.get("last_status") == "ok")
                fail = sum(1 for t in tasks.values() if t.get("last_status") == "fail")
                symbol = "🟢" if consec == 0 else ("🟡" if consec < 3 else "🔴")
                lines.append(f"   {symbol} {bot}: ok={ok} fail={fail} consec={consec} [{_age(sf)}]")
            except Exception:
                lines.append(f"   ⚪ {bot}: state unreadable")
        else:
            lines.append(f"   ⚪ {bot}: no state")
    lines.append("")

    # 5. Financial pulse
    fp = STATE / "financial_pulse_latest.txt"
    lines.append("━━ FINANCIAL PULSE ━━")
    if fp.exists():
        lines.append(_read(fp, 6))
        lines.append(f"   [{_age(fp)}]")
    else:
        lines.append("   No pulse on file")
    lines.append("")

    lines.append("╚══ END REPORT ══╝")
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    try:
        gw = ROOT / "OpsCenter/thunderbird_telegram_gw.py"
        subprocess.run(
            [sys.executable, str(gw), "send", text[:4000]],
            timeout=15, capture_output=True,
        )
    except Exception as e:
        print(f"Telegram send failed: {e}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--telegram", action="store_true", help="Also send to D2MC2C")
    args = parser.parse_args()

    report = build_report()
    print(report)

    # Always write to file
    out = ROOT / "OpsCenter/state/wing_health_latest.txt"
    out.write_text(report)
    print(f"\n[Saved to {out}]")

    if args.telegram:
        send_telegram(report)
        print("[Sent to Telegram]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
