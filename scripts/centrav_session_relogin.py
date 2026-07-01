#!/usr/bin/env python3
"""
centrav_session_relogin.py — Headless Centrav re-login via trusted persistent Firefox profile.

WHY THIS WORKS (and centrav_session_auto_keepalive.py --headless doesn't):
  auto_keepalive creates a FRESH browser context → reCAPTCHA fires immediately.
  This script uses launch_persistent_context() with the profile at
  core/travel/data/centrav_ff_profile — which carries the _GRECAPTCHA cookie
  (valid ~180 days) that marks this browser as CAPTCHA-trusted. Combined with
  Centrav's "Remember this Browser" server-side state, login succeeds with
  just email + password — no CAPTCHA, no OTP.

Exit codes:
  0  success — session restored, cookies written to BOTH cookie files
  2  needs human — OTP required or login hard-failed (Telegram fired)
  3  skip — profile locked or missing (retry next cycle)

Usage:
  .venv/bin/python scripts/centrav_session_relogin.py
  .venv/bin/python scripts/centrav_session_relogin.py --force   # skip expiry check
  .venv/bin/python scripts/centrav_session_relogin.py --status  # check only

Dreams2Memories Travel, LLC · Thunderbird Wing · 2026-07-01
"""
import argparse
import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
PROFILE_DIR  = ROOT / "core" / "travel" / "data" / "centrav_ff_profile"
SESSION_FILE = ROOT / "core" / "travel" / "data" / "centrav_session.json"   # scraper primary
ALT_COOKIES  = ROOT / "creds" / "centrav_cookies.json"                       # portal-probe alt
CONFIG_FILE  = ROOT / "config" / "portal_creds.json"
FARE_WATCH_STATE = ROOT / "OpsCenter" / "fare_watches" / "last_check.json"
LOG_FILE     = ROOT / "logs" / "centrav_relogin.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CENTRAV-RELOGIN] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_FILE), mode="a"),
    ],
)
log = logging.getLogger("centrav_relogin")

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
LOGIN_URL  = "https://www.centrav.com/login"
NAV_TIMEOUT = 30_000


def _load_creds() -> tuple[str, str]:
    try:
        cfg = json.loads(CONFIG_FILE.read_text())
        c = cfg.get("centrav", {})
        return c.get("email", ""), c.get("password", "")
    except Exception as e:
        log.error("Cannot load config/portal_creds.json: %s", e)
        return "", ""


def _cookies_still_valid() -> bool:
    """Return True if both cookie files have a live laravel_session (> 5 min remaining)."""
    for f in (SESSION_FILE, ALT_COOKIES):
        if not f.exists():
            return False
        try:
            cookies = json.loads(f.read_text())
            now = time.time()
            for c in cookies:
                if c.get("name") == "laravel_session" and "centrav" in c.get("domain", ""):
                    exp = c.get("expires") or c.get("expiry", -1)
                    if exp and exp > 0:
                        # Firefox sqlite stores in ms; JSON export is in seconds
                        exp_s = exp / 1000 if exp > 1e10 else exp
                        if (exp_s - now) > 300:
                            return True
        except Exception:
            pass
    return False


def _save_cookies(cookies: list) -> None:
    """Atomically write cookies to both SESSION_FILE and ALT_COOKIES."""
    centrav = [c for c in cookies if "centrav" in c.get("domain", "")]
    if not centrav:
        log.warning("No centrav-domain cookies to save — skipping write")
        return

    for dest in (SESSION_FILE, ALT_COOKIES):
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(cookies, indent=2))
        tmp.replace(dest)

    log.info("Saved %d cookies to SESSION_FILE + ALT_COOKIES", len(centrav))
    for c in centrav:
        if c.get("name") == "laravel_session":
            exp = c.get("expires") or c.get("expiry")
            if exp and exp > 0:
                exp_s = exp / 1000 if exp > 1e10 else exp
                dt = datetime.fromtimestamp(exp_s, tz=timezone.utc)
                log.info("laravel_session expires %s (%.1fh)", dt.strftime("%H:%M UTC"),
                         (exp_s - time.time()) / 3600)


def _clear_stale_autherror() -> None:
    """Scrub stale Centrav auth_error from fare-watch state after confirmed live."""
    try:
        if not FARE_WATCH_STATE.exists():
            return
        d = json.loads(FARE_WATCH_STATE.read_text())
        changed = False
        for wid, r in (d.get("results", {}) or {}).items():
            if not isinstance(r, dict):
                continue
            blob = (str(r.get("error", "")) + " " + str(wid)).lower()
            if r.get("status") == "auth_error" and ("centrav" in blob or "session expired" in blob):
                r["status"] = "ok"
                r["error"] = ""
                r["note"] = "auth_error auto-cleared by centrav_session_relogin — session restored"
                changed = True
        warns = d.get("warnings", []) or []
        kept = [w for w in warns
                if not (("centrav" in str(w).lower() and "auth" in str(w).lower())
                        or "auth failed" in str(w).lower())]
        if len(kept) != len(warns):
            d["warnings"] = kept
            changed = True
        if changed:
            d["watches_with_errors"] = max(0, int(d.get("watches_with_errors", 0)) - 1)
            FARE_WATCH_STATE.write_text(json.dumps(d, indent=1))
            log.info("Cleared stale Centrav auth_error from fare-watch state")
    except Exception as e:
        log.warning("Could not clear fare-watch auth_error (non-fatal): %s", e)


def _telegram(msg: str) -> None:
    import os, urllib.request, urllib.parse
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")
    if not token:
        try:
            env_file = ROOT / ".env"
            for line in env_file.read_text().splitlines():
                if line.startswith("TELEGRAM_BOT_TOKEN=") or line.startswith("TELEGRAM_D2MC2C_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if token:
                        break
        except Exception:
            pass
    if not token:
        log.warning("[telegram] no token — skipping page")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": 7554895206, "text": msg}).encode()
        urllib.request.urlopen(urllib.request.Request(url, data=data, method="POST"), timeout=10)
        log.info("[telegram] sent")
    except Exception as e:
        log.warning("[telegram] failed (non-fatal): %s", e)


async def relogin() -> int:
    """
    Attempt headless Centrav re-login via persistent Firefox profile.
    Returns exit code: 0=success, 2=needs-human, 3=skip.
    """
    if not PROFILE_DIR.exists():
        log.error("Persistent Firefox profile missing: %s", PROFILE_DIR)
        log.error("Run scripts/centrav_serve.py once to create it.")
        return 3

    email, password = _load_creds()
    if not email or not password:
        log.error("No Centrav credentials in config/portal_creds.json")
        return 2

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        try:
            ctx = await p.firefox.launch_persistent_context(
                str(PROFILE_DIR),
                headless=True,
                viewport={"width": 1440, "height": 900},
                user_agent=USER_AGENT,
            )
        except Exception as e:
            log.warning("Cannot open persistent profile (locked?): %s", e)
            log.warning("session files left untouched — will retry next cycle")
            return 3

        try:
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()

            log.info("Navigating to %s", LOGIN_URL)
            try:
                await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
                await page.wait_for_timeout(2_000)
            except Exception as e:
                log.error("Navigation error: %s", e)
                return 3

            final_url = (page.url or "").lower()

            # Already authenticated (redirected to dashboard)?
            if "login" not in final_url and "trust" not in final_url:
                log.info("Already authenticated (no /login redirect) — saving cookies")
                cookies = await ctx.cookies()
                _save_cookies(cookies)
                _clear_stale_autherror()
                _telegram("⚡ CENTRAV RELOGIN — Already authenticated (no re-login needed). Cookies refreshed.")
                return 0

            # Check for reCAPTCHA (log but proceed — _GRECAPTCHA trust cookie should suppress it)
            try:
                recaptcha = await page.query_selector('iframe[src*="recaptcha"]')
                if recaptcha:
                    log.warning("reCAPTCHA iframe visible — _GRECAPTCHA trust cookie may not be active. Proceeding anyway.")
            except Exception:
                pass

            # Fill login form
            log.info("Filling login form (email=%s)...", email[:6] + "***")
            try:
                await page.fill("#FormEmail", email, timeout=6_000)
                await page.fill("#FormPassword", password, timeout=6_000)
            except Exception as e:
                # Try generic selectors as fallback
                log.warning("Named selectors failed (%s) — trying generic email/password", e)
                try:
                    await page.fill('input[type="email"]', email, timeout=4_000)
                    await page.fill('input[type="password"]', password, timeout=4_000)
                except Exception as e2:
                    log.error("Could not fill login form: %s", e2)
                    return 2

            # Submit
            log.info("Submitting login form...")
            try:
                btn = await page.query_selector('button[type="submit"], input[type="submit"]')
                if btn:
                    await btn.click(timeout=5_000)
                else:
                    await page.press('input[type="password"]', "Enter")
            except Exception as e:
                log.error("Submit failed: %s", e)
                return 2

            # Wait for navigation result
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=20_000)
                await page.wait_for_timeout(2_000)
            except Exception:
                pass

            post_url = (page.url or "").lower()
            log.info("Post-submit URL: %s", page.url)

            # OTP / trust-device page?
            if "/trust" in post_url:
                log.warning("OTP REQUIRED — landed on /trust page. Manual intervention needed.")
                _telegram(
                    "🔴 CENTRAV RELOGIN — OTP Required\n"
                    "Auto re-login got to the login form but OTP email code is needed.\n\n"
                    "Fix: open yoga browser → run:\n"
                    "  cd ~/Thunderbird && .venv/bin/python scripts/centrav_serve.py\n"
                    "(Pre-fills creds. Enter the email code on the /trust page.)"
                )
                return 2

            # Still on login page?
            if "login" in post_url:
                body = ""
                try:
                    body = (await page.evaluate("() => document.body.innerText"))[:200].lower()
                except Exception:
                    pass
                if "invalid" in body or "incorrect" in body or "error" in body:
                    log.error("Login rejected — credentials may be wrong")
                else:
                    log.error("Still on login page after submit — unknown failure")
                _telegram(
                    "🔴 CENTRAV RELOGIN FAILED\n"
                    "Headless login attempt did not reach dashboard.\n"
                    "Manual login required:\n"
                    "  cd ~/Thunderbird && .venv/bin/python scripts/centrav_serve.py"
                )
                return 2

            # Success — verify laravel_session present
            cookies = await ctx.cookies()
            has_session = any(
                c.get("name") == "laravel_session" and "centrav.com" in (c.get("domain") or "")
                for c in cookies
            )
            if not has_session:
                log.error("Dashboard reached but laravel_session missing — refusing to overwrite")
                return 2

            _save_cookies(cookies)
            _clear_stale_autherror()
            log.info("✅ RELOGIN SUCCESS — Centrav session restored autonomously")
            _telegram(
                "⚡ CENTRAV RELOGIN SUCCESS\n"
                "Session restored headlessly via trusted Firefox profile.\n"
                "Fare-watch is back LIVE. No Commander action needed."
            )
            return 0

        finally:
            try:
                await ctx.close()
            except Exception:
                pass


def main() -> None:
    ap = argparse.ArgumentParser(description="Headless Centrav re-login via trusted Firefox profile")
    ap.add_argument("--force", action="store_true",
                    help="Attempt re-login even if cookies appear valid")
    ap.add_argument("--status", action="store_true",
                    help="Print cookie status only, no login attempt")
    args = ap.parse_args()

    if args.status:
        valid = _cookies_still_valid()
        print(f"Centrav cookies: {'VALID' if valid else 'EXPIRED/MISSING'}")
        sys.exit(0 if valid else 2)

    if not args.force and _cookies_still_valid():
        log.info("Cookies still valid — no relogin needed (use --force to override)")
        sys.exit(0)

    rc = asyncio.run(relogin())
    sys.exit(rc)


if __name__ == "__main__":
    main()
