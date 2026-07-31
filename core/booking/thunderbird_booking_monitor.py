"""
D2M Booking Monitor — Playwright portal scraper
Checks Regent and Viking booking portals for status changes.
Runs every 6 hours via systemd timer. Alerts Commander on any change.

Credentials: ~/Thunderbird/config/portal_creds.json
State file:  ~/Thunderbird/config/monitor_state.json

Usage:
  python3 thunderbird_booking_monitor.py          # Run all monitors
  python3 thunderbird_booking_monitor.py --regent  # Regent only
  python3 thunderbird_booking_monitor.py --viking  # Viking only
  python3 thunderbird_booking_monitor.py --setup   # Test login, no state compare
"""
import asyncio
import json
import os
import sys
import argparse
import urllib.request
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout
    PW_OK = True
except ImportError:
    PW_OK = False

BASE = Path(__file__).parent
STATE_FILE = BASE / "config" / "monitor_state.json"
CREDS_FILE = BASE / "config" / "portal_creds.json"
BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "***REMOVED-SECRET***")  # D2MC2C_bot — Commander C2 channel
COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206")

# Regent booking numbers to monitor (pull from dossier frontmatter or hardcode)
REGENT_BOOKINGS = ["3071222", "3096289", "3078056"]

# Viking booking numbers
VIKING_BOOKINGS = ["9595029", "9596219", "9596220"]


# ── State management ──────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def load_creds() -> dict:
    if CREDS_FILE.exists():
        return json.loads(CREDS_FILE.read_text())
    return {}


# ── Telegram ─────────────────────────────────────────────────────────────────

_MUTE_FLAG = Path("/home/john/Thunderbird/config/d2mc2c_client_mute")

def send_telegram(msg: str):
    if _MUTE_FLAG.exists():
        return  # client/supplier push muted — SO 2026-05-05
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": COMMANDER_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15)


def diff_alert(booking_id: str, line: str, old: dict, new: dict):
    changes = []
    for k, v_new in new.items():
        v_old = old.get(k, "—")
        if v_new and v_new != v_old:
            changes.append(f"  *{k}:* `{v_old}` → `{v_new}`")
    if not changes:
        return
    msg = (f"*🔔 BOOKING CHANGE — {line} {booking_id}*\n"
           + "\n".join(changes)
           + f"\n\n_{datetime.now().strftime('%d %b %Y %H:%M')}_")
    send_telegram(msg)
    print(f"[monitor] Alert sent for {line} {booking_id}: {len(changes)} change(s)")


# ── Regent Seven Seas ─────────────────────────────────────────────────────────

async def check_regent(page, booking_id: str, creds: dict) -> dict | None:
    """Scrape RSSC booking portal for a single booking."""
    email = creds.get("regent", {}).get("email", "")
    password = creds.get("regent", {}).get("password", "")
    if not email or not password:
        print(f"[regent] No credentials for booking {booking_id} — skipping")
        return None

    try:
        await page.goto("https://rssc.com/my-reservation", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)

        # Login if needed
        if await page.locator("input[type='email'], input[name='email']").count() > 0:
            await page.fill("input[type='email'], input[name='email']", email)
            await page.fill("input[type='password']", password)
            await page.click("button[type='submit'], input[type='submit']")
            await page.wait_for_load_state("networkidle", timeout=20000)

        # Navigate to specific booking
        await page.goto(f"https://rssc.com/my-reservation/{booking_id}", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)

        state = {}

        # Payment status
        payment = await page.locator(
            "text=/payment status|balance due|amount due/i"
        ).first.text_content() if await page.locator(
            "text=/payment status|balance due|amount due/i"
        ).count() > 0 else ""
        if payment:
            state["payment_status"] = payment.strip()[:100]

        # Balance amount
        balance = await page.locator(
            "[class*='balance'], [class*='amount-due'], [data-testid*='balance']"
        ).first.text_content() if await page.locator(
            "[class*='balance'], [class*='amount-due']"
        ).count() > 0 else ""
        if balance:
            state["balance"] = balance.strip()[:50]

        # Stateroom
        cabin = await page.locator(
            "[class*='cabin'], [class*='stateroom'], [class*='suite']"
        ).first.text_content() if await page.locator(
            "[class*='cabin'], [class*='stateroom']"
        ).count() > 0 else ""
        if cabin:
            state["stateroom"] = cabin.strip()[:50]

        # Booking status
        status = await page.locator(
            "[class*='booking-status'], [class*='reservation-status']"
        ).first.text_content() if await page.locator(
            "[class*='booking-status']"
        ).count() > 0 else ""
        if status:
            state["booking_status"] = status.strip()[:50]

        print(f"[regent] {booking_id}: {state}")
        return state

    except PWTimeout:
        print(f"[regent] Timeout on booking {booking_id}")
        return None
    except Exception as e:
        print(f"[regent] Error on {booking_id}: {e}")
        return None


# ── Viking Ocean ──────────────────────────────────────────────────────────────

async def check_viking(page, booking_id: str, creds: dict) -> dict | None:
    """Scrape Viking booking portal for a single booking."""
    email = creds.get("viking", {}).get("email", "")
    password = creds.get("viking", {}).get("password", "")
    if not email or not password:
        print(f"[viking] No credentials for booking {booking_id} — skipping")
        return None

    try:
        await page.goto("https://www.vikingcruises.com/my-viking/", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)

        # Login if needed
        if await page.locator("input[type='email'], #username").count() > 0:
            await page.fill("input[type='email'], #username", email)
            await page.fill("input[type='password'], #password", password)
            await page.click("button[type='submit'], .login-btn, #login-submit")
            await page.wait_for_load_state("networkidle", timeout=20000)

        # Look for booking in list
        await page.goto(
            f"https://www.vikingcruises.com/my-viking/booking/{booking_id}",
            timeout=30000
        )
        await page.wait_for_load_state("networkidle", timeout=20000)

        state = {}

        # Payment/balance
        for selector in ["[class*='payment']", "[class*='balance']", "[class*='amount']"]:
            el = page.locator(selector).first
            if await el.count() > 0:
                txt = await el.text_content()
                if txt:
                    state["payment_info"] = txt.strip()[:100]
                    break

        # Stateroom assignment
        for selector in ["[class*='cabin']", "[class*='stateroom']", "[class*='category']"]:
            el = page.locator(selector).first
            if await el.count() > 0:
                txt = await el.text_content()
                if txt and any(c.isdigit() for c in txt):
                    state["stateroom"] = txt.strip()[:50]
                    break

        # Booking status
        for selector in ["[class*='status']", "[class*='booking-state']"]:
            el = page.locator(selector).first
            if await el.count() > 0:
                txt = await el.text_content()
                if txt:
                    state["status"] = txt.strip()[:50]
                    break

        print(f"[viking] {booking_id}: {state}")
        return state

    except PWTimeout:
        print(f"[viking] Timeout on booking {booking_id}")
        return None
    except Exception as e:
        print(f"[viking] Error on {booking_id}: {e}")
        return None


# ── Runner ────────────────────────────────────────────────────────────────────

async def run(args):
    if not PW_OK:
        send_telegram(
            "⚠️ Booking monitor failed — playwright not installed\n"
            "Run: `pip3 install playwright && playwright install chromium`"
        )
        return

    creds = load_creds()
    state = load_state()
    changed = 0

    async with async_playwright() as pw:
        # Chromium (not chromium_headless_shell — that SIGTRAPs on openSUSE).
        # Firefox juggler pipe broke after playwright updated firefox-1509→1522 (2026-07-04).
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        # Regent
        if not args.viking_only:
            for bid in REGENT_BOOKINGS:
                key = f"regent_{bid}"
                new_state = await check_regent(page, bid, creds)
                if new_state is None:
                    continue
                old_state = state.get(key, {})
                if old_state and old_state != new_state:
                    diff_alert(bid, "Regent", old_state, new_state)
                    changed += 1
                state[key] = new_state

        # Viking
        if not args.regent_only:
            for bid in VIKING_BOOKINGS:
                key = f"viking_{bid}"
                new_state = await check_viking(page, bid, creds)
                if new_state is None:
                    continue
                old_state = state.get(key, {})
                if old_state and old_state != new_state:
                    diff_alert(bid, "Viking", old_state, new_state)
                    changed += 1
                state[key] = new_state

        await browser.close()

    save_state(state)
    print(f"[monitor] Done — {changed} change(s) detected, state saved")

    if args.setup:
        send_telegram(
            f"*✅ Booking Monitor — Setup Check*\n"
            f"Regent bookings checked: {len(REGENT_BOOKINGS)}\n"
            f"Viking bookings checked: {len(VIKING_BOOKINGS)}\n"
            f"State file: `{STATE_FILE}`"
        )


def main():
    parser = argparse.ArgumentParser(description="D2M Booking Monitor")
    parser.add_argument("--regent", dest="regent_only", action="store_true")
    parser.add_argument("--viking", dest="viking_only", action="store_true")
    parser.add_argument("--setup", action="store_true",
                        help="Test login only, send confirmation to Telegram")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
