#!/usr/bin/env python3
"""
fare_watch_deadman.py — 48-hour dead-man switch for flight fare watching.
FIX-4 2026-06-27 (Wing Exercise — BURNING HOT CI).

Runs via supertimer every 3 hours. If fare-watch has been dark (0 checks) for
>48 hours, pages Commander immediately via Telegram. Does NOT wait for brief.

Exit codes:
  0  fare-watch is live (or no data yet)
  1  fare-watch DARK >48h — Telegram page sent
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
LAST_CHECK = ROOT / "OpsCenter" / "fare_watches" / "last_check.json"
ALERT_STATE = ROOT / "logs" / "fare_watch_deadman_alert.json"
DARK_THRESHOLD_HOURS = 48


def log(m: str) -> None:
    print(m, flush=True)


def _telegram_page(hours_dark: float, watches_total: int) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")
    if not token:
        log(f"[deadman] Telegram token missing — cannot page (dark {hours_dark:.0f}h)")
        return
    commander_id = 7554895206
    msg = (
        f"🚨 FARE-WATCH DARK {hours_dark:.0f} HOURS\n"
        f"{watches_total} flight watches have had ZERO price checks for {hours_dark:.0f}h.\n\n"
        "Root cause: Centrav session expired OR ITA Playwright binary missing.\n\n"
        "Fix options:\n"
        "  1. Centrav re-auth: .venv/bin/python scripts/centrav_serve.py\n"
        "  2. ITA binary: .venv/bin/playwright install chromium\n\n"
        "No client flight intelligence since last successful check."
    )
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": commander_id, "text": msg}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        urllib.request.urlopen(req, timeout=10)
        log(f"[deadman] Commander paged: fare-watch dark {hours_dark:.0f}h")
    except Exception as e:
        log(f"[deadman] Telegram page failed: {e}")


def main() -> int:
    if not LAST_CHECK.exists():
        log("[deadman] no last_check.json — fare-watch never ran, skipping")
        return 0

    try:
        data = json.loads(LAST_CHECK.read_text())
    except Exception as e:
        log(f"[deadman] failed to parse last_check.json: {e}")
        return 0

    checked = int(data.get("watches_checked", 0))
    total = int(data.get("watches_total", 0))
    started = data.get("started_at", "")

    if total == 0:
        log("[deadman] no watches registered — nothing to check")
        return 0

    now = datetime.now(timezone.utc)
    hours_since = 999.0
    try:
        ts = datetime.fromisoformat(started.replace("Z", "+00:00"))
        hours_since = (now - ts).total_seconds() / 3600
    except Exception:
        pass

    if checked > 0 and hours_since <= DARK_THRESHOLD_HOURS:
        log(f"[deadman] fare-watch OK — {checked}/{total} checked {hours_since:.1f}h ago")
        # Reset alert state on recovery
        if ALERT_STATE.exists():
            ALERT_STATE.unlink(missing_ok=True)
            log("[deadman] alert state cleared (recovery)")
        return 0

    # DARK — check if we already paged recently (don't spam every 3h)
    last_alert_hours = 999.0
    if ALERT_STATE.exists():
        try:
            alert_data = json.loads(ALERT_STATE.read_text())
            alert_ts = datetime.fromisoformat(alert_data.get("last_alert", "").replace("Z", "+00:00"))
            last_alert_hours = (now - alert_ts).total_seconds() / 3600
        except Exception:
            pass

    # Page once at 48h, then every 24h after that
    page_interval = 24.0 if last_alert_hours < 999 else 0.0
    if last_alert_hours >= page_interval:
        log(f"[deadman] DARK {hours_since:.0f}h — paging Commander")
        _telegram_page(hours_since, total)
        ALERT_STATE.write_text(json.dumps({
            "last_alert": now.isoformat(),
            "dark_hours": hours_since,
            "watches_total": total,
        }, indent=2))
        return 1
    else:
        log(f"[deadman] DARK {hours_since:.0f}h but paged {last_alert_hours:.0f}h ago — holding")
        return 1


if __name__ == "__main__":
    sys.exit(main())
