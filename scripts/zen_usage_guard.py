#!/usr/bin/env python3
"""
zen_usage_guard.py — alert-only watchdog for DeepSeek v4 (ZEN free tier).

Built 2026-08-02 alongside the Claude-MAX-burn incident fix: report/routine
traffic was just moved off Claude MAX onto opencode/deepseek-v4-flash-free
(agent_runner.py, opencode.json). ZEN has its own cap (100/hr, 500/day) —
this exists so a second "safety net alert nobody saw" incident doesn't
repeat on the new lane. Alert-only by design: unlike the billing guard,
there's no safe auto-disable action for a free local rate limiter — the
right response to high ZEN usage is a human decision (spread load, wait,
or accept a temporary fallback), not an automated kill.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RATE_LOG = ROOT / "OpsCenter" / ".deepseek_rate_log"
LIMITS = {"req_hr": 100, "req_day": 500}
ALERT_THRESHOLD_PCT = 80
ALERT_LOG = ROOT / "logs" / "zen_usage_guard.log"


def count_calls(hours_back: float) -> int:
    if not RATE_LOG.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    count = 0
    with open(RATE_LOG) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ts = datetime.fromisoformat(line)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    count += 1
            except ValueError:
                continue
    return count


def log(msg: str) -> None:
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ALERT_LOG.open("a") as f:
        f.write(f"{msg}\n")
    print(msg)


def main() -> None:
    hourly = count_calls(1)
    daily = count_calls(24)
    hourly_pct = 100 * hourly / LIMITS["req_hr"]
    daily_pct = 100 * daily / LIMITS["req_day"]

    log(f"ZEN usage: hourly={hourly}/{LIMITS['req_hr']} ({hourly_pct:.0f}%) "
        f"daily={daily}/{LIMITS['req_day']} ({daily_pct:.0f}%)")

    if hourly_pct >= ALERT_THRESHOLD_PCT or daily_pct >= ALERT_THRESHOLD_PCT:
        msg = (f"⚡ ZEN (DeepSeek free tier) usage high: "
               f"hourly {hourly}/{LIMITS['req_hr']} ({hourly_pct:.0f}%), "
               f"daily {daily}/{LIMITS['req_day']} ({daily_pct:.0f}%). "
               f"Report/routine load was just moved onto this lane — "
               f"human call needed if this keeps climbing.")
        log(f"ALERT: {msg}")
        try:
            import os
            import urllib.request
            import urllib.parse

            for line in (ROOT / ".env.telegram").read_text().splitlines():
                if line.startswith("TELEGRAM_D2MC2C_TOKEN="):
                    os.environ["TELEGRAM_D2MC2C_TOKEN"] = line.split("=", 1)[1].strip()
            token = os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")
            chat_id = os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206")
            if token:
                data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg}).encode()
                req = urllib.request.Request(
                    f"https://api.telegram.org/bot{token}/sendMessage", data=data
                )
                urllib.request.urlopen(req, timeout=15)
            else:
                log("Telegram send skipped — no TELEGRAM_D2MC2C_TOKEN found")
        except Exception as e:
            log(f"Telegram send failed (non-fatal): {e!r}")


if __name__ == "__main__":
    sys.exit(main() or 0)
