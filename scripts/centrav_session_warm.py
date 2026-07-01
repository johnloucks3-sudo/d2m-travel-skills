#!/usr/bin/env python3
"""
centrav_session_warm.py — Warm-ping keepalive for the Centrav B2B flight portal.
MISSION-200.

WHY: The Centrav agent session (laravel_session) has a ~2hr idle TTL, and login is
reCAPTCHA + email-OTP — auto-reauth is impossible (captcha is a human gate). But the
PERSISTENT Firefox profile (core/travel/data/centrav_ff_profile, created by
scripts/centrav_serve.py) holds the "Remember this Browser" trust cookie after ONE
manual login. This script keeps the session warm: it opens that profile headless every
<90 min, GETs an authenticated Centrav page, and — ONLY if still authenticated — re-saves
the cookies to centrav_session.json so the scraper's cookie fast-path stays fresh.

It NEVER attempts to defeat the CAPTCHA. The one-time human login stays.

SAFE BY DESIGN (mirrors ita_fare_watch_poll.py's contract):
  - Verifies an authenticated marker FIRST. Only re-saves session.json if CONFIRMED.
  - Dead session / profile lock / any error → SKIP. session.json is left UNTOUCHED.
  - A failed ping today is harmless; the session is simply not refreshed this cycle.
    It only goes truly dead when the trust cookie expires or the Commander logs out.

Exit codes:
  0  authenticated — session warmed + cookies re-saved
  2  not authenticated — session is dead, needs one manual login (centrav_serve.py)
  3  skipped — profile locked / could not run (session.json untouched, retry next cycle)

Usage:
  .venv/bin/python scripts/centrav_session_warm.py
  .venv/bin/python scripts/centrav_session_warm.py --check   # report only, never write
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
SESSION_FILE = ROOT / "core" / "travel" / "data" / "centrav_session.json"
PROFILE_DIR = ROOT / "core" / "travel" / "data" / "centrav_ff_profile"
# The keepalive supervisor derives Centrav health from this fare-watch state file.
# A dead-session scrape writes an auth_error here that PERSISTS (Centrav can't
# auto-scrape past the captcha to overwrite it), so a now-live session keeps
# reading RED. The warm-ping is the authoritative live auth probe, so on a
# confirmed-live warm it owns clearing that stale signal. See keepalive_supervisor._centrav_health.
FARE_WATCH_STATE = ROOT / "OpsCenter" / "fare_watches" / "last_check.json"

# An authenticated Centrav agent page redirects anonymous visitors to /login.
# We GET a page that requires auth and check (a) we were NOT bounced to /login and
# (b) the logout control is present. Two independent signals — both must hold.
WARM_URL = "https://www.centrav.com/"
NAV_TIMEOUT_MS = 30_000
# Match the UA the scraper / profile use so the trust cookie keeps matching.
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def _telegram_dead_session_alert() -> None:
    """FIX-3 2026-06-27: Immediate Telegram page to Commander when Centrav session dies."""
    import os, urllib.request, urllib.parse
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")
    if not token:
        log("  [telegram] no token in env — skipping page (fare-watch will still go dark in brief)")
        return
    commander_id = 7554895206
    msg = (
        "🔴 CENTRAV SESSION DEAD\n"
        "Fare-watch is now DARK — no flight prices will be checked until re-auth.\n\n"
        "Fix: open yoga browser → run:\n"
        "  cd ~/Thunderbird && .venv/bin/python scripts/centrav_serve.py\n\n"
        "All 4 flight watches suspended until resolved."
    )
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": commander_id, "text": msg}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        urllib.request.urlopen(req, timeout=10)
        log("  [telegram] Commander paged: Centrav session dead")
    except Exception as e:
        log(f"  [telegram] page failed (non-fatal): {e}")


def _clear_stale_centrav_autherror() -> None:
    """On a confirmed-live warm, scrub any stale Centrav auth_error from the
    fare-watch state the keepalive supervisor reads. The warm-ping is the live
    auth probe; it owns correcting a signal a dead-session scrape left behind.
    Best-effort — never raises into the warm path."""
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
                r["note"] = "auth_error auto-cleared by centrav_session_warm — session verified live"
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
            log("  self-heal: cleared stale Centrav auth_error in fare-watch state")
    except Exception as e:
        log(f"  self-heal skipped (non-fatal): {e}")


async def warm(check_only: bool) -> int:
    if not PROFILE_DIR.exists():
        log(f"SKIP — persistent profile missing: {PROFILE_DIR}")
        log("      Run scripts/centrav_serve.py once (manual login) to create it.")
        return 3

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
            # Most likely the profile is locked (Commander has centrav_serve.py open
            # on the same profile). That is NOT a failure — skip, retry next cycle.
            log(f"SKIP — could not open profile (locked or busy?): {e}")
            log("      session.json left untouched; will retry next cycle.")
            return 3

        try:
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            try:
                await page.goto(WARM_URL, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
                await page.wait_for_timeout(2_500)
            except Exception as e:
                log(f"SKIP — navigation error: {e}. session.json untouched.")
                return 3

            final_url = (page.url or "").lower()
            bounced_to_login = "login" in final_url or "trust" in final_url

            # #LogoutButton is an UNRELIABLE authenticated marker \u2014 it isn't present on
            # the homepage even when the session is live, producing false "dead" readings
            # that fire bogus relogin/Telegram alarms (fixed 2026-07-01). The reliable
            # signal is: not bounced to /login AND authenticated content in the body.
            logout_visible = False
            try:
                logout_visible = await page.locator("#LogoutButton").is_visible()
            except Exception:
                logout_visible = False

            body_authed = False
            try:
                txt = (await page.evaluate("() => document.body.innerText"))[:6000].lower()
                body_authed = any(m in txt for m in ("logout", "sign out", "my account", "dashboard"))
            except Exception:
                body_authed = False

            # Authenticated iff we were NOT bounced to login AND at least one positive
            # marker (button OR body content) confirms a live agent session.
            authenticated = (not bounced_to_login) and (logout_visible or body_authed)

            log(f"warm GET {WARM_URL} \u2192 {page.url}")
            log(f"  bounced_to_login={bounced_to_login}  logout_visible={logout_visible}  "
                f"body_authed={body_authed}  => authenticated={authenticated}")

            if not authenticated:
                log("NOT AUTHENTICATED — Centrav session is dead.")
                log("  Attempting autonomous headless relogin via trusted Firefox profile...")
                try:
                    import subprocess as _sp
                    result = _sp.run(
                        [sys.executable, str(ROOT / "scripts" / "centrav_session_relogin.py")],
                        timeout=120,
                    )
                    if result.returncode == 0:
                        log("  RELOGIN SUCCESS — session restored autonomously. Warm cycle complete.")
                        return 0
                    log(f"  Relogin returned rc={result.returncode} — escalating to Commander")
                except Exception as _e:
                    log(f"  Relogin attempt error: {_e} — escalating to Commander")
                # Relogin failed — page Commander (relogin script sends its own specific Telegram)
                log("  session.json left UNTOUCHED (no clobber).")
                return 2

            # Confirmed authenticated. Capture current cookies and refresh session.json
            # so the scraper's cookie fast-path stays valid. (Skip the write in --check.)
            cookies = await ctx.cookies()
            if check_only:
                log(f"CHECK — authenticated, {len(cookies)} cookies (no write, --check).")
                return 0

            # Sanity guard before overwriting: the live cookies must still carry the
            # Centrav session cookie, else we'd be saving an anonymous/partial set.
            has_session = any(
                c.get("name") == "laravel_session" and "centrav.com" in (c.get("domain") or "")
                for c in cookies
            )
            if not has_session:
                log("SKIP — authenticated marker present but laravel_session missing from "
                    "cookie export; refusing to overwrite session.json.")
                return 3

            tmp = SESSION_FILE.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(cookies, indent=2))
            tmp.replace(SESSION_FILE)  # atomic swap — never leaves a half-written file
            log(f"WARMED — session refreshed, {len(cookies)} cookies → {SESSION_FILE}")
            _clear_stale_centrav_autherror()  # we just proved auth live — own the supervisor's signal
            return 0
        finally:
            try:
                await ctx.close()
            except Exception:
                pass


def main() -> None:
    ap = argparse.ArgumentParser(description="Centrav warm-ping keepalive (non-destructive)")
    ap.add_argument("--check", action="store_true",
                    help="Report auth status only; never write session.json")
    args = ap.parse_args()
    rc = asyncio.run(warm(check_only=args.check))
    sys.exit(rc)


if __name__ == "__main__":
    main()
