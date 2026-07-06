#!/usr/bin/env python3
"""
poe_points_check.py — scrape poe.com/api_key for points balance
Saves to data/poe_points.json and updates blackboard.

Source page: https://poe.com/api_key
Key element: "675,320 available  ≈ $20.46 value"

Run:   python3 scripts/poe_points_check.py
Timer: poe-points-check.timer (0600 MT daily)
Cookies: config/poe_cookies.json  (p-b auth token, valid ~1 year)
"""

import asyncio
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT           = Path(__file__).parent.parent
COOKIES_FILE   = ROOT / "config" / "poe_cookies.json"
POINTS_FILE    = ROOT / "data" / "poe_points.json"
POE_ENV        = ROOT / "config" / "poe.env"
BLACKBOARD     = ROOT / "OpsCenter" / "collaboration" / "blackboard.md"
TELEGRAM_ENV   = ROOT / "config" / "telegram_gw.env"
DOTENV         = ROOT / ".env"
POINTS_THRESHOLD = 10_000  # ~1 week of lite usage


def load_poe_env() -> dict:
    env = {}
    if POE_ENV.exists():
        for line in POE_ENV.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


async def scrape() -> dict:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: playwright not installed — run: pip install playwright && playwright install chromium")
        sys.exit(1)

    if not COOKIES_FILE.exists():
        return {"status": "no_cookies", "timestamp": datetime.now(timezone.utc).isoformat()}

    cookies = json.loads(COOKIES_FILE.read_text())

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            storage_state={"cookies": cookies, "origins": []}
        )
        page = await ctx.new_page()

        # ── Navigate to api_key page (shows balance) ──────────────────────
        await page.goto("https://poe.com/api_key", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        final_url = page.url
        text = await page.evaluate("() => document.body.innerText")

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "url": final_url,
            "points_available": None,
            "value_usd": None,
            "status": "unknown",
        }

        # Auth check
        if "login" in final_url or "sign" in final_url:
            result["status"] = "auth_required"
            await browser.close()
            return result

        # Parse: "675,320\navailable\n≈ $20.46 value"
        m = re.search(r'([\d,]+)\s*\n?\s*available', text)
        if m:
            result["points_available"] = int(m.group(1).replace(",", ""))

        m = re.search(r'≈\s*\$([0-9.]+)\s*value', text)
        if m:
            result["value_usd"] = float(m.group(1))

        # Refresh cookies
        fresh = await ctx.cookies()
        COOKIES_FILE.write_text(json.dumps(fresh, indent=2))

        result["status"] = "ok" if result["points_available"] is not None else "parse_failed"
        result["raw_sample"] = text[:500]

        await browser.close()
        return result


def _load_env_var(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return None


def send_telegram_alert(message: str) -> bool:
    """Send low-balance alert to Commander via D2MC2C bot. Returns True on success."""
    token = _load_env_var(DOTENV, "TELEGRAM_D2MC2C_TOKEN") or _load_env_var(DOTENV, "TELEGRAM_BOT_TOKEN")
    chat_id = _load_env_var(TELEGRAM_ENV, "TELEGRAM_COMMANDER_ID")
    if not token or not chat_id:
        print("  ⚠️  Telegram alert skipped — token/chat_id not found")
        return False
    try:
        payload = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }).encode()
        resp = urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            timeout=10,
        )
        body = json.loads(resp.read())
        return bool(body.get("ok"))
    except Exception as exc:
        print(f"  ⚠️  Telegram alert send failed: {exc}")
        return False


def update_blackboard(pts: int, usd: float):
    if not BLACKBOARD.exists():
        return
    pts_str = f"Poe:{pts:,}pts(${usd:.2f})" if usd else f"Poe:{pts:,}pts"
    text = BLACKBOARD.read_text()
    if "Poe:" in text:
        text = re.sub(r'Poe:[^\s|]+', pts_str, text)
    else:
        text = re.sub(r'(Budget:[^\n]+)', r'\1 | ' + pts_str, text)
    BLACKBOARD.write_text(text)
    print(f"  Blackboard → {pts_str}")


def save(data: dict):
    POINTS_FILE.parent.mkdir(exist_ok=True)
    POINTS_FILE.write_text(json.dumps(data, indent=2))


async def main():
    print("─" * 44)
    print("  Poe Points Check  — poe.com/api_key")
    print("─" * 44)

    data = await scrape()
    save(data)

    status = data.get("status")
    pts    = data.get("points_available")
    usd    = data.get("value_usd")

    if status == "ok" and pts is not None:
        print(f"  ✅  {pts:,} points available  ≈ ${usd:.2f}" if usd else f"  ✅  {pts:,} points available")
        update_blackboard(pts, usd or 0)
        if pts < POINTS_THRESHOLD:
            msg = (
                f"🔴 THUNDERBIRD ALERT\n"
                f"Poe points balance LOW: {pts:,} available (≈${usd:.2f})\n"
                f"Threshold: {POINTS_THRESHOLD:,}. Recharge or expect API interruptions."
            )
            if send_telegram_alert(msg):
                print(f"  📟  Low-balance Telegram alert sent to Commander")
    elif status == "auth_required":
        print("  ❌  Auth required — cookies expired")
        print("      Fix: copy fresh p-b cookie from browser → config/poe_cookies.json")
    elif status == "no_cookies":
        print("  ❌  No cookies file at config/poe_cookies.json")
    else:
        sample = data.get("raw_sample","")[:300]
        print(f"  ⚠️   Parse failed. Page sample:\n{sample}")

    print(f"  Saved → {POINTS_FILE}")
    print(f"  At   → {data['timestamp']}")
    print("─" * 44)


if __name__ == "__main__":
    asyncio.run(main())
