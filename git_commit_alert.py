#!/usr/bin/env python3
"""
Git Commit Alert — Uncommitted Changes Watchdog
Dreams2Memories Travel, LLC

Checks ~/Thunderbird/ for uncommitted changes.
If dirty: fires Telegram alert to Commander with file count + list.
If clean: silent (no spam).

Run: python3 git_commit_alert.py
Systemd: thunderbird-git-commit-alert.timer (daily 21:47 MDT)
"""

import os
import subprocess
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ── Config ──────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

BOT_TOKEN    = os.getenv("TELEGRAM_C2_BOT_TOKEN")
COMMANDER_ID = os.getenv("TELEGRAM_COMMANDER_ID")
REPO_DIR     = Path(__file__).parent  # ~/Thunderbird/

MAX_FILES_SHOWN = 20   # cap Telegram message length


def git_status() -> tuple[int, list[str]]:
    """Return (count_of_changed_files, list_of_status_lines)."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return -1, [f"git error: {result.stderr.strip()}"]

    lines = [l for l in result.stdout.splitlines() if l.strip()]
    return len(lines), lines


def build_message(count: int, lines: list[str]) -> str:
    now = datetime.now().strftime("%d %b %Y %H:%M MDT")
    if count == 0:
        return ""   # clean — no message sent

    shown = lines[:MAX_FILES_SHOWN]
    overflow = count - len(shown)

    file_block = "\n".join(f"  `{l}`" for l in shown)
    if overflow > 0:
        file_block += f"\n  _...and {overflow} more_"

    return (
        f"⚠️ *THUNDERBIRD — UNCOMMITTED CHANGES*\n"
        f"_{now}_\n\n"
        f"*{count} file(s)* not committed to git:\n\n"
        f"{file_block}\n\n"
        f"👉 Commit before session close to protect the wing."
    )


def send_telegram(message: str) -> bool:
    if not BOT_TOKEN or not COMMANDER_ID:
        print("❌ Missing bot token or commander ID in .env")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    COMMANDER_ID,
        "text":       message,
        "parse_mode": "Markdown",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print(f"✅ Alert sent — {len(message)} chars")
        return True
    except Exception as e:
        print(f"❌ Telegram send failed: {e}")
        return False


def main():
    count, lines = git_status()

    if count < 0:
        print(f"[git-commit-alert] git error: {lines}")
        return

    if count == 0:
        print("[git-commit-alert] Repo clean — no alert sent.")
        return

    print(f"[git-commit-alert] {count} uncommitted file(s) — alerting Commander.")
    msg = build_message(count, lines)
    send_telegram(msg)


if __name__ == "__main__":
    main()
