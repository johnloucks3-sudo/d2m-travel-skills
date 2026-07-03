#!/usr/bin/env python3
"""
check_deps.py — Binary dependency validator for Thunderbird Wing.
FIX-6 2026-06-27 (Wing Exercise — BURNING HOT CI).

Checks that required binaries exist. Pages Commander via Telegram on any miss.
Run at session open and as a supertimer task (daily).

Exit codes:
  0  all dependencies present
  1  one or more missing — Telegram page sent
"""
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")

REQUIRED = [
    {
        "name": "Playwright chromium headless shell",
        "paths": [
            Path.home() / ".cache/ms-playwright/chromium_headless_shell-1208/chrome-headless-shell-linux64/chrome-headless-shell",
            Path.home() / ".local/share/ms-playwright/chromium_headless_shell-1208/chrome-headless-shell-linux64/chrome-headless-shell",
        ],
        "fix": ".venv/bin/playwright install chromium",
        "affects": "ITA Matrix fare watch",
    },
    {
        "name": "Playwright Firefox binary",
        "paths": [
            Path.home() / ".cache/ms-playwright/firefox-1509/firefox/firefox",
            Path.home() / ".local/share/ms-playwright/firefox-1509/firefox/firefox",
        ],
        "fix": ".venv/bin/playwright install firefox",
        "affects": "Centrav session warm (centrav_session_warm.py)",
    },
    {
        "name": "SQLite3",
        "paths": [Path("/usr/bin/sqlite3"), Path("/bin/sqlite3")],
        "fix": "sudo zypper install sqlite3",
        "affects": "fare_watch.db — all flight/cruise watches",
    },
    {
        "name": "Python venv",
        "paths": [ROOT / ".venv/bin/python3"],
        "fix": "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt",
        "affects": "all Wing scripts",
    },
]


def _telegram_page(missing: list[dict]) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")
    if not token:
        print("[check_deps] no Telegram token — cannot page", flush=True)
        return
    lines = ["🔴 MISSING BINARY DEPENDENCIES\n"]
    for m in missing:
        lines.append(f"❌ {m['name']}")
        lines.append(f"   Affects: {m['affects']}")
        lines.append(f"   Fix: {m['fix']}\n")
    msg = "\n".join(lines)
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": 7554895206, "text": msg}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        urllib.request.urlopen(req, timeout=10)
        print(f"[check_deps] Commander paged: {len(missing)} missing deps", flush=True)
    except Exception as e:
        print(f"[check_deps] Telegram failed: {e}", flush=True)


def main() -> int:
    missing = []
    for dep in REQUIRED:
        found = any(p.exists() for p in dep["paths"])
        if found:
            print(f"[check_deps] ✅ {dep['name']}", flush=True)
        else:
            print(f"[check_deps] ❌ MISSING: {dep['name']} — affects: {dep['affects']}", flush=True)
            missing.append(dep)

    if missing:
        _telegram_page(missing)
        return 1
    print(f"[check_deps] All {len(REQUIRED)} dependencies present.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
