#!/usr/bin/env python3
"""
DEPRECATED: superseded by thunderbird_evernote_backup.py (weekly zipped backup)
and thunderbird-gdrive-sync.timer (daily Drive mirror).

This script used mcp_bridge.sh which no longer exists.
Keeping for reference only — do not run.
"""
import sys

def pull_drive_backups_and_send_to_evernote():
    print("DEPRECATED: Use thunderbird_evernote_backup.py instead.")
    sys.exit(1)

if __name__ == "__main__":
    pull_drive_backups_and_send_to_evernote()
