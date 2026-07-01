#!/usr/bin/env python3
"""CI probe — Evernote backup MX (weekly code archive).
Efficacy check: state file exists + last backup is within 10 days (allows 1 missed weekly cycle).
NOTE: Evernote uses email-in architecture — no live API token check possible.
      The backup is a oneshot systemd service; 'inactive' is its normal resting state.
Exit 0 = GREEN, exit 1 = RED.
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

ID = "evernote-mx"
# State file lives at Thunderbird root (not state/ subdir)
STATE_FILE = Path.home() / "Thunderbird" / "evernote_backup_state.json"
MAX_AGE_DAYS = 10  # Weekly cadence; RED after 1 missed cycle


def fail(m):
    print(f"RED {ID}: {m}")
    sys.exit(1)


def main():
    if not STATE_FILE.exists():
        fail(f"State file not found: {STATE_FILE}")

    try:
        data = json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        fail(f"Cannot read state file: {e}")

    backup = data.get("last_evernote_backup", {})
    status = backup.get("status", "")
    if status != "success":
        fail(f"Last backup status={status!r} (expected 'success')")

    # Date field is YYYYMMDD string
    date_str = backup.get("date", "")
    if not date_str:
        fail("No 'date' field in backup state")

    try:
        backup_dt = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
    except ValueError as e:
        fail(f"Cannot parse backup date {date_str!r}: {e}")

    now = datetime.now(tz=timezone.utc)
    age = now - backup_dt
    age_days = age.days

    if age_days > MAX_AGE_DAYS:
        fail(f"Last backup {age_days} days ago ({date_str}) — exceeds {MAX_AGE_DAYS}-day threshold")

    files_count = backup.get("files_count", "?")
    method = backup.get("method", "?")
    print(
        f"GREEN {ID}: last backup {date_str} ({age_days}d ago), "
        f"status={status}, method={method}, files={files_count}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
