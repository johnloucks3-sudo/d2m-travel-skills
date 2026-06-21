#!/usr/bin/env python3
"""
centrav_serve.py — Serve a PERSISTENT, visible Centrav browser for the Commander to drive.

Unlike --centrav-login (throwaway context that re-triggers OTP every time), this uses a
persistent Firefox profile so "Remember this Browser" STICKS — after one full login the
trust cookie persists and future logins skip the OTP. Stays open ~45 min; captures the
session to centrav_session.json the moment you're authenticated, while you keep searching.

Usage: .venv/bin/python scripts/centrav_serve.py
"""
import asyncio, json, time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path("/home/john/Thunderbird")
SESSION_FILE = ROOT / "core" / "travel" / "data" / "centrav_session.json"
PROFILE_DIR = ROOT / "core" / "travel" / "data" / "centrav_ff_profile"   # persistent profile
CREDS_PATH = ROOT / "centrav_credentials.json"

if CREDS_PATH.exists():
    c = json.loads(CREDS_PATH.read_text())
    EMAIL, PASS = c["email"], c["password"]
else:
    EMAIL, PASS = "johnloucks3@gmail.com", "Falcons4me!"


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


async def main():
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        ctx = await p.firefox.launch_persistent_context(
            str(PROFILE_DIR), headless=False,
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://www.centrav.com/login", wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(1_500)
        # Prefill creds if the login form is present (skipped automatically if already trusted/logged in)
        try:
            await page.fill("#FormEmail", EMAIL, timeout=4_000)
            await page.fill("#FormPassword", PASS, timeout=4_000)
            log("Credentials pre-filled. Solve CAPTCHA + Login, then enter the email code on /trust.")
        except Exception:
            log("Login form not shown (already trusted?) — go straight to search.")

        log("Browser is YOURS. Drive it. I'll capture the session when you're in.")
        saved = False
        # Keep the browser open ~45 min; snapshot cookies whenever authenticated.
        for i in range(540):  # 540 * 5s = 45 min
            await page.wait_for_timeout(5_000)
            try:
                u = page.url.lower()
            except Exception:
                log("Browser closed by user. Done.")
                break
            if "login" not in u and "trust" not in u:
                cookies = await ctx.cookies()
                SESSION_FILE.write_text(json.dumps(cookies, indent=2))
                if not saved:
                    log(f"✅ AUTHENTICATED — session captured ({len(cookies)} cookies) → {SESSION_FILE}")
                    log("Keep searching; session is saved and will refresh as you browse.")
                    saved = True
        try:
            await ctx.close()
        except Exception:
            pass
        log("Serve session ended. " + ("Session saved." if saved else "No authenticated session captured."))


if __name__ == "__main__":
    asyncio.run(main())
