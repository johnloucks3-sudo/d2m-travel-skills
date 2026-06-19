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
import sys
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


def send_email_brief(count: int, lines: list[str]) -> bool:
    """Route git dirty status to AM email brief — not D2MC2C (nightly hygiene, no immediate action)."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from core.comms.wing_sms import _load_env
        env = _load_env()
        import urllib.request, urllib.parse, json as _json
        token = env.get("GMAIL_JOHNLOUCKS3_TOKEN") or env.get("GMAIL_TOKEN", "")
        # If no token available, fall back to Telegram so alert isn't lost
        if not token:
            return False
        return False  # email send not yet wired — fall through to Telegram
    except Exception:
        return False


def main():
    count, lines = git_status()

    if count < 0:
        print(f"[git-commit-alert] git error: {lines}")
        return

    if count == 0:
        print("[git-commit-alert] Repo clean — no alert sent.")
        return

    print(f"[git-commit-alert] {count} uncommitted file(s) — logging (AM brief).")
    # Write to a brief-pickup file instead of paging Commander on Telegram
    brief_file = Path(__file__).parent.parent.parent / "OpsCenter" / "state" / "git_dirty_alert.txt"
    brief_file.parent.mkdir(parents=True, exist_ok=True)
    brief_file.write_text(f"{datetime.now().isoformat()}: {count} uncommitted files\n" + "\n".join(lines[:20]))
    print(f"[git-commit-alert] Written to {brief_file} — picked up by AM brief.")


if __name__ == "__main__":
    main()
