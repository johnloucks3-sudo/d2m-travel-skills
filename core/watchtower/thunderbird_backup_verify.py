#!/usr/bin/env python3
"""
Thunderbird Backup Verification — Weekly Health Check
Monday 07:30 MDT (after weekly Evernote backup runs at 07:00)

Checks all 4 backup paths, flags failures, sends Telegram report.
Designed to run as the Monday-morning health confirmation to Commander.

Checks:
  1. Drive mirror      — thunderbird_sync_state.json timestamp (stale > 36h = WARN)
  2. Evernote weekly   — evernote_backup_state.json (stale > 8d = WARN)
  3. Monthly archive   — monthly_archive_state.json (not run this month = WARN if date > 5th)
  4. Git repo          — last commit age + uncommitted changes count
  5. Output file count — delta vs last week (unexpected large drops = WARN)

Usage:
    python3 thunderbird_backup_verify.py           # Run check + send Telegram report
    python3 thunderbird_backup_verify.py --quiet   # Only send Telegram if there are warnings
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
STATE_DIR = THUNDERBIRD_DIR / "state"
STATE_FILE = STATE_DIR / "backup_verify_state.json"

TELEGRAM_BOT = os.getenv("TELEGRAM_C2_BOT_TOKEN", "")
TELEGRAM_CHAT = os.getenv("TELEGRAM_COMMANDER_ID", "")

DRIVE_SYNC_STATE = STATE_DIR / "thunderbird_sync_state.json"
EVERNOTE_STATE = STATE_DIR / "evernote_backup_state.json"
MONTHLY_STATE = STATE_DIR / "monthly_archive_state.json"
RCLONE_LOG = THUNDERBIRD_DIR / ".rclone_sync.log"

DRIVE_STALE_HOURS = 36
EVERNOTE_STALE_DAYS = 8


# ─── State ────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ─── Individual checks ────────────────────────────────────────────────────────

def check_drive_mirror() -> dict:
    """Check Drive sync state — flag if last rclone sync > 36h ago."""
    # Primary check: rclone log timestamp (most reliable last-run indicator)
    if RCLONE_LOG.exists():
        log_mtime = RCLONE_LOG.stat().st_mtime
        sync_dt = datetime.fromtimestamp(log_mtime)
        age_hours = (datetime.now() - sync_dt).total_seconds() / 3600

        # Also check for last success line in the log
        try:
            log_tail = RCLONE_LOG.read_text()[-500:]
            last_exit_ok = "exit: 0" in log_tail or "Transferred:" in log_tail
        except Exception:
            last_exit_ok = True  # assume OK if can't read

        if age_hours > DRIVE_STALE_HOURS:
            return {
                "status": "WARN",
                "msg": f"Drive mirror stale — last rclone {age_hours:.0f}h ago ({sync_dt.strftime('%m/%d %H:%M')})",
                "age_hours": round(age_hours, 1),
            }

        status_note = "" if last_exit_ok else " (last run may have had errors)"
        return {
            "status": "OK",
            "msg": f"Drive mirror current — last rclone {age_hours:.0f}h ago{status_note}",
            "age_hours": round(age_hours, 1),
        }

    # Fallback: check sync state file
    if not DRIVE_SYNC_STATE.exists():
        return {"status": "WARN", "msg": "rclone log and thunderbird_sync_state.json both missing — Drive sync unverifiable"}

    try:
        state = json.loads(DRIVE_SYNC_STATE.read_text())
    except Exception:
        return {"status": "WARN", "msg": "Cannot parse thunderbird_sync_state.json"}

    # Use the file's own mtime as a proxy for last sync run
    file_mtime = DRIVE_SYNC_STATE.stat().st_mtime
    sync_dt = datetime.fromtimestamp(file_mtime)
    age_hours = (datetime.now() - sync_dt).total_seconds() / 3600

    if age_hours > DRIVE_STALE_HOURS:
        return {
            "status": "WARN",
            "msg": f"Drive mirror stale — last sync state updated {age_hours:.0f}h ago ({sync_dt.strftime('%m/%d %H:%M')})",
            "age_hours": round(age_hours, 1),
        }

    return {
        "status": "OK",
        "msg": f"Drive mirror current — state updated {age_hours:.0f}h ago",
        "age_hours": round(age_hours, 1),
    }


def check_evernote_backup() -> dict:
    """Check Evernote weekly backup — flag if > 8 days since last run."""
    if not EVERNOTE_STATE.exists():
        return {"status": "WARN", "msg": "evernote_backup_state.json not found — never backed up"}

    try:
        state = json.loads(EVERNOTE_STATE.read_text())
    except Exception:
        return {"status": "WARN", "msg": "Cannot parse evernote_backup_state.json"}

    last = state.get("last_evernote_backup", {})
    if not last:
        return {"status": "WARN", "msg": "No Evernote backup record found"}

    date_str = last.get("date", "")
    if not date_str:
        return {"status": "WARN", "msg": "Evernote backup date missing in state"}

    try:
        backup_dt = datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        return {"status": "WARN", "msg": f"Cannot parse backup date: {date_str}"}

    age_days = (datetime.now() - backup_dt).days
    files_count = last.get("files_count", 0)
    zip_kb = last.get("zip_size_kb", 0)

    if age_days > EVERNOTE_STALE_DAYS:
        return {
            "status": "WARN",
            "msg": f"Evernote backup stale — last run {age_days}d ago ({backup_dt.strftime('%m/%d')})",
            "age_days": age_days,
            "files_count": files_count,
        }

    return {
        "status": "OK",
        "msg": f"Evernote backup current — {age_days}d ago, {files_count} files ({zip_kb} KB)",
        "age_days": age_days,
        "files_count": files_count,
    }


def check_monthly_archive() -> dict:
    """Check monthly archive — flag if not run this month and today > 5th."""
    now = datetime.now()
    current_month = now.strftime("%Y%m")

    if not MONTHLY_STATE.exists():
        if now.day > 5:
            return {"status": "WARN", "msg": f"Monthly archive not yet run for {now.strftime('%B %Y')}"}
        return {"status": "OK", "msg": f"Monthly archive not yet due ({now.strftime('%B %Y')})"}

    try:
        state = json.loads(MONTHLY_STATE.read_text())
    except Exception:
        return {"status": "WARN", "msg": "Cannot parse monthly_archive_state.json"}

    last = state.get("last_archive", {})
    last_month = last.get("month", "")

    if last_month == current_month:
        files_count = last.get("files_count", 0)
        return {
            "status": "OK",
            "msg": f"Monthly archive complete — {now.strftime('%B %Y')}, {files_count} files",
            "files_count": files_count,
        }

    if now.day > 5:
        return {
            "status": "WARN",
            "msg": f"Monthly archive not run for {now.strftime('%B %Y')} (last: {last.get('month_display', 'unknown')})",
        }

    return {
        "status": "OK",
        "msg": f"Monthly archive pending (due 1st — today is {now.day}th)",
    }


def check_git_repo() -> dict:
    """Check git repo — last commit age + uncommitted changes."""
    try:
        # Last commit timestamp
        result = subprocess.run(
            ["git", "-C", str(THUNDERBIRD_DIR), "log", "-1", "--format=%ct"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return {"status": "WARN", "msg": "Git log failed — repo may not be initialized"}

        commit_ts = int(result.stdout.strip())
        commit_dt = datetime.fromtimestamp(commit_ts)
        age_days = (datetime.now() - commit_dt).days

        # Uncommitted changes count
        status_result = subprocess.run(
            ["git", "-C", str(THUNDERBIRD_DIR), "status", "--short"],
            capture_output=True, text=True, timeout=10
        )
        uncommitted = len([l for l in status_result.stdout.strip().splitlines() if l.strip()])

        msg = f"Last commit {age_days}d ago ({commit_dt.strftime('%m/%d')})"
        if uncommitted:
            msg += f" — {uncommitted} uncommitted changes"

        status = "WARN" if age_days > 3 or uncommitted > 20 else "OK"
        return {
            "status": status,
            "msg": msg,
            "age_days": age_days,
            "uncommitted_count": uncommitted,
        }

    except Exception as e:
        return {"status": "WARN", "msg": f"Git check failed: {e}"}


def check_output_files() -> dict:
    """Check output file count — flag unexpected large drops vs last week."""
    output_dir = THUNDERBIRD_DIR / "output"
    if not output_dir.exists():
        return {"status": "WARN", "msg": "output/ directory missing"}

    current_count = sum(1 for _ in output_dir.rglob("*") if _.is_file())

    state = load_state()
    last_count = state.get("last_output_count", 0)

    if last_count > 0 and current_count < last_count * 0.7:
        return {
            "status": "WARN",
            "msg": f"output/ file count dropped: {last_count} → {current_count} (>30% loss)",
            "current_count": current_count,
            "last_count": last_count,
        }

    # Update count in state (done after report)
    return {
        "status": "OK",
        "msg": f"output/ contains {current_count} files",
        "current_count": current_count,
    }


# ─── Report builder ──────────────────────────────────────────────────────────

def build_telegram_report(checks: dict, warnings: list, now: datetime) -> str:
    icon = "✅" if not warnings else "⚠️"
    lines = [
        f"<b>{icon} Backup Health Check — {now.strftime('%a %d %b %Y %H:%M MT')}</b>",
        "",
    ]

    status_icons = {"OK": "✅", "WARN": "⚠️", "ERROR": "❌"}

    for check_name, result in checks.items():
        icon_c = status_icons.get(result["status"], "❓")
        lines.append(f"{icon_c} <b>{check_name}</b>: {result['msg']}")

    if warnings:
        lines.append("")
        lines.append(f"<b>{len(warnings)} warning(s) need attention.</b>")
    else:
        lines.append("")
        lines.append("All backup paths healthy.")

    return "\n".join(lines)


def send_telegram(message: str):
    if not TELEGRAM_BOT or not TELEGRAM_CHAT:
        print("⚠️  TELEGRAM not configured — skipping send")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"Telegram send failed: {e}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_verify(quiet: bool = False) -> dict:
    now = datetime.now()

    checks = {
        "Drive Mirror": check_drive_mirror(),
        "Evernote Weekly": check_evernote_backup(),
        "Monthly Archive": check_monthly_archive(),
        "Git Repo": check_git_repo(),
        "Output Files": check_output_files(),
    }

    warnings = [name for name, r in checks.items() if r["status"] == "WARN"]
    has_issues = bool(warnings)

    # Update output count in state
    output_result = checks.get("Output Files", {})
    if output_result.get("status") == "OK":
        state = load_state()
        state["last_output_count"] = output_result.get("current_count", 0)
        state["last_run"] = now.isoformat()
        save_state(state)

    # Print to console
    print(f"\nBackup Health Check — {now.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    for name, result in checks.items():
        icon = "✅" if result["status"] == "OK" else "⚠️"
        print(f"  {icon} {name}: {result['msg']}")

    if warnings:
        print(f"\n⚠️  {len(warnings)} warning(s): {', '.join(warnings)}")
    else:
        print("\n✅ All backup paths healthy.")

    # Send Telegram — always unless --quiet and no issues
    if not quiet or has_issues:
        report = build_telegram_report(checks, warnings, now)
        send_telegram(report)
        print("\n📱 Telegram report sent.")
    else:
        print("\n⏭  Quiet mode — no issues, skipping Telegram.")

    return {
        "checks": checks,
        "warnings": warnings,
        "has_issues": has_issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Thunderbird backup verification — weekly health check")
    parser.add_argument("--quiet", action="store_true",
                        help="Only send Telegram if there are warnings")
    args = parser.parse_args()

    result = run_verify(quiet=args.quiet)
    sys.exit(0)  # warnings are informational; supertimer failure = crash, not stale backup


if __name__ == "__main__":
    main()
