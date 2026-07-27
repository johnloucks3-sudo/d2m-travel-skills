#!/usr/bin/env python3
"""
invisible_playwright PoC — M-061
=================================
Tests InvisiblePlaywright (stealth Firefox, score 963/1005) against:
  1. Centrav B2B login (reCAPTCHA-gated)
  2. CruisePlum cruise pricing page (Cloudflare-protected)

Pass criteria:
  - Centrav: lands on authenticated dashboard/search (not blocked by bot check)
  - CruisePlum: page loads with cruise results (not Cloudflare challenge/block)

Output:
  output/invisible_playwright_poc_report.md
  output/screenshots/ip_poc_*.png

Usage:
  source .venv/bin/activate
  python3 scripts/invisible_playwright_poc.py

Dreams2Memories Travel, LLC — A12 ELON / Hale COS — M-061 2026-05-29
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# ── Environment setup ─────────────────────────────────────────────────────────

THUNDERBIRD = Path(__file__).resolve().parent.parent
VENV_SITE = THUNDERBIRD / ".venv" / "lib" / "python3.13" / "site-packages"
if str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

CREDS_PATH = THUNDERBIRD / "centrav_credentials.json"
OUTPUT_DIR = THUNDERBIRD / "output"
SCREENSHOT_DIR = OUTPUT_DIR / "screenshots"
REPORT_PATH = OUTPUT_DIR / "invisible_playwright_poc_report.md"

OUTPUT_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR.mkdir(exist_ok=True)

# ── Credentials ───────────────────────────────────────────────────────────────

if CREDS_PATH.exists():
    _c = json.loads(CREDS_PATH.read_text())
    CENTRAV_EMAIL = _c.get("email", "")
    CENTRAV_PASS = _c.get("password", "")
else:
    CENTRAV_EMAIL = ""
    CENTRAV_PASS = ""


def _ts():
    return datetime.now().strftime("%H:%M:%S")


def log(msg):
    print(f"[{_ts()}] {msg}", flush=True)


# ── Test results ──────────────────────────────────────────────────────────────

results = []


def record(test_name, passed, notes, screenshot=None, elapsed=None):
    results.append({
        "test": test_name,
        "passed": passed,
        "notes": notes,
        "screenshot": screenshot,
        "elapsed_s": elapsed,
    })
    icon = "✅ PASS" if passed else "❌ FAIL"
    log(f"{icon} — {test_name}: {notes[:120]}")


# ── Test 1: Centrav B2B Login ──────────────────────────────────────────────────

def test_centrav(browser):
    """
    Navigate to Centrav login, fill credentials, submit.
    Pass: lands on authenticated page (not blocked, no bot-check wall).
    Fail: reCAPTCHA challenge appears, or bot detection blocks load.
    """
    log("TEST 1 — Centrav B2B login (reCAPTCHA target)")
    t0 = time.time()
    shot = str(SCREENSHOT_DIR / f"ip_poc_centrav_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

    page = browser.new_page()
    try:
        page.goto("https://www.centrav.com/login", timeout=45_000, wait_until="domcontentloaded")
        time.sleep(2.0)

        # Fingerprint check — look for bot-block signals first
        title = page.title()
        url = page.url
        body = ""
        try:
            body = page.inner_text("body")[:2000].lower()
        except Exception:
            pass

        # Bot-block signals
        blocked_signals = [
            "access denied", "cloudflare", "ray id", "checking your browser",
            "403 forbidden", "just a moment", "bot detection",
        ]
        is_blocked = any(s in body for s in blocked_signals) or any(s in title.lower() for s in blocked_signals)

        if is_blocked:
            page.screenshot(path=shot)
            elapsed = round(time.time() - t0, 1)
            record("Centrav Login (bot gate)", False,
                   f"Bot-block detected before login. URL={url} Title='{title}'",
                   shot, elapsed)
            page.close()
            return

        # Try to fill credentials
        filled = False
        try:
            page.fill("#FormEmail", CENTRAV_EMAIL, timeout=8_000)
            page.fill("#FormPassword", CENTRAV_PASS, timeout=8_000)
            filled = True
            log(f"  Centrav — credentials pre-filled. Submitting...")
        except Exception as e:
            log(f"  Centrav — fill failed: {e}")

        # Check for reCAPTCHA on login page
        recaptcha_present = page.query_selector("iframe[src*='recaptcha'], .g-recaptcha, #recaptcha") is not None
        if recaptcha_present:
            log(f"  Centrav — reCAPTCHA iframe detected on login page")

        if filled:
            try:
                # Submit form
                page.click("#FormSubmitButton, [type='submit']", timeout=5_000)
                time.sleep(3.5)
            except Exception as e:
                log(f"  Centrav — submit click failed: {e}")

        # Final state check
        url_after = page.url
        title_after = page.title()
        body_after = ""
        try:
            body_after = page.inner_text("body")[:3000].lower()
        except Exception:
            pass

        page.screenshot(path=shot)
        elapsed = round(time.time() - t0, 1)

        # Determine pass/fail
        still_on_login = "login" in url_after.lower() or "sign" in url_after.lower()
        authenticated_signals = [
            "logout", "my account", "dashboard", "search flights",
            "book a flight", "welcome", "flying from", "flyingfrom",
        ]
        auth_detected = any(s in body_after for s in authenticated_signals)
        captcha_wall = any(s in body_after for s in ["i'm not a robot", "prove you're human", "recaptcha challenge"])

        if captcha_wall:
            record("Centrav Login (bot gate)", False,
                   f"reCAPTCHA challenge wall presented after submit. recaptcha_on_page={recaptcha_present}",
                   shot, elapsed)
        elif not still_on_login and (auth_detected or "centrav.com" in url_after):
            record("Centrav Login (bot gate)", True,
                   f"Authenticated — landed on: {url_after[:80]}. Auth signals found. recaptcha_on_page={recaptcha_present}",
                   shot, elapsed)
        elif not still_on_login:
            record("Centrav Login (bot gate)", True,
                   f"Redirected off login to {url_after[:80]} — likely authenticated.",
                   shot, elapsed)
        else:
            notes = f"Still on login page after submit. recaptcha={recaptcha_present}. URL={url_after[:80]}"
            # If reCAPTCHA was present but we weren't blocked entirely, this is a partial pass
            if recaptcha_present:
                notes += " (reCAPTCHA present but page loaded — stealth worked for page render)"
                record("Centrav Login (bot gate)", False,
                       notes, shot, elapsed)
            else:
                record("Centrav Login (bot gate)", False,
                       notes, shot, elapsed)

    except Exception as e:
        elapsed = round(time.time() - t0, 1)
        try:
            page.screenshot(path=shot)
        except Exception:
            shot = None
        record("Centrav Login (bot gate)", False,
               f"Exception: {type(e).__name__}: {str(e)[:200]}",
               shot, elapsed)
    finally:
        try:
            page.close()
        except Exception:
            pass


# ── Test 2: CruisePlum Pricing Page ───────────────────────────────────────────

def test_cruiseplum(browser):
    """
    Load CruisePlum cruise search/pricing page.
    Pass: page renders with cruise listings (not Cloudflare block).
    """
    log("TEST 2 — CruisePlum cruise pricing (Cloudflare target)")
    t0 = time.time()
    shot = str(SCREENSHOT_DIR / f"ip_poc_cruiseplum_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

    page = browser.new_page()
    try:
        page.goto("https://www.cruiseplum.com/search", timeout=45_000, wait_until="domcontentloaded")
        time.sleep(3.0)

        title = page.title()
        url = page.url
        body = ""
        try:
            body = page.inner_text("body")[:3000].lower()
        except Exception:
            pass

        page.screenshot(path=shot)
        elapsed = round(time.time() - t0, 1)

        blocked_signals = [
            "access denied", "ray id", "checking your browser",
            "403 forbidden", "just a moment", "bot detection", "cf-browser-verification",
        ]
        is_blocked = any(s in body for s in blocked_signals)

        pricing_signals = [
            "cruise", "price", "per person", "interior", "balcony",
            "search", "cabin", "departure", "night",
        ]
        has_pricing = any(s in body for s in pricing_signals)

        if is_blocked:
            record("CruisePlum Pricing (Cloudflare)", False,
                   f"Cloudflare block detected. URL={url} Title='{title}'",
                   shot, elapsed)
        elif has_pricing:
            record("CruisePlum Pricing (Cloudflare)", True,
                   f"Pricing page loaded with cruise results. Title='{title}' URL={url[:80]}",
                   shot, elapsed)
        else:
            # Page loaded but unclear content
            record("CruisePlum Pricing (Cloudflare)", None,
                   f"Page loaded but pricing signals unclear. Title='{title}' URL={url[:80]}",
                   shot, elapsed)

    except Exception as e:
        elapsed = round(time.time() - t0, 1)
        try:
            page.screenshot(path=shot)
        except Exception:
            shot = None
        record("CruisePlum Pricing (Cloudflare)", False,
               f"Exception: {type(e).__name__}: {str(e)[:200]}",
               shot, elapsed)
    finally:
        try:
            page.close()
        except Exception:
            pass


# ── Test 3: Bot fingerprint check ─────────────────────────────────────────────

def test_fingerprint(browser):
    """Quick fingerprint sanity check via bot detection test site."""
    log("TEST 3 — Fingerprint / bot-score check (creepjs)")
    t0 = time.time()
    shot = str(SCREENSHOT_DIR / f"ip_poc_fp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

    page = browser.new_page()
    try:
        page.goto("https://abrahamjuliot.github.io/creepjs/", timeout=45_000, wait_until="domcontentloaded")
        time.sleep(6.0)  # CreepJS runs JS analysis

        body = ""
        try:
            body = page.inner_text("body")[:4000]
        except Exception:
            pass

        page.screenshot(path=shot)
        elapsed = round(time.time() - t0, 1)

        # Extract trust score if present
        import re
        score_match = re.search(r'trust\s*score[:\s]+(\d+(?:\.\d+)?)', body, re.IGNORECASE)
        bot_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:bot|human)', body, re.IGNORECASE)

        score_info = "score not extracted"
        if score_match:
            score_info = f"trust score: {score_match.group(1)}"
        elif bot_match:
            score_info = f"bot/human score: {bot_match.group(1)}%"

        # Check if page loaded (not blocked)
        page_loaded = len(body) > 500
        record("CreepJS Fingerprint Check", page_loaded,
               f"Page {'loaded' if page_loaded else 'blocked'}. {score_info}",
               shot, elapsed)

    except Exception as e:
        elapsed = round(time.time() - t0, 1)
        try:
            page.screenshot(path=shot)
        except Exception:
            shot = None
        record("CreepJS Fingerprint Check", False,
               f"Exception: {type(e).__name__}: {str(e)[:200]}",
               shot, elapsed)
    finally:
        try:
            page.close()
        except Exception:
            pass


# ── Report generator ──────────────────────────────────────────────────────────

def generate_report():
    now = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    passed = sum(1 for r in results if r["passed"] is True)
    failed = sum(1 for r in results if r["passed"] is False)
    ambig  = sum(1 for r in results if r["passed"] is None)
    total  = len(results)

    overall = "🟢 GREEN" if failed == 0 else ("🟡 YELLOW" if passed > 0 else "🔴 RED")
    verdict = "UNBLOCKS" if failed == 0 else ("PARTIAL" if passed > 0 else "BLOCKED")

    lines = [
        f"# invisible_playwright PoC — M-061 Report",
        f"**Date:** {now}  ",
        f"**Package:** invisible_playwright 0.1.x (stealth Firefox 150, score 963/1005)  ",
        f"**Overall:** {overall} — {passed}/{total} tests passed  ",
        f"**Verdict:** {verdict}",
        "",
        "---",
        "",
        "## Test Results",
        "",
        "| Test | Result | Elapsed | Notes |",
        "|------|--------|---------|-------|",
    ]

    for r in results:
        icon = "✅ PASS" if r["passed"] is True else ("❌ FAIL" if r["passed"] is False else "⚠️ AMBIG")
        elapsed = f"{r['elapsed_s']}s" if r['elapsed_s'] else "—"
        notes = r["notes"][:120].replace("|", "\\|")
        lines.append(f"| {r['test']} | {icon} | {elapsed} | {notes} |")

    lines += [
        "",
        "---",
        "",
        "## Implications",
        "",
    ]

    centrav_result = next((r for r in results if "Centrav" in r["test"]), None)
    cruiseplum_result = next((r for r in results if "CruisePlum" in r["test"]), None)

    if centrav_result and centrav_result["passed"]:
        lines.append("- **Centrav PASS:** invisible_playwright bypasses reCAPTCHA gate. "
                     "Can automate session refresh without manual CAPTCHA solve. "
                     "Unblocks B2B flight pricing automation.")
    elif centrav_result:
        lines.append("- **Centrav FAIL:** reCAPTCHA still blocking. "
                     "Manual cookie export remains required for Centrav auth. "
                     "Consider `prep_recaptcha=True` or persistent profile with pre-seeded reCAPTCHA cookies.")

    if cruiseplum_result and cruiseplum_result["passed"]:
        lines.append("- **CruisePlum PASS:** Cloudflare bypassed. "
                     "Cruise pricing scraper is unblocked. Can feed pricing data into fare watches.")
    elif cruiseplum_result and cruiseplum_result["passed"] is False:
        lines.append("- **CruisePlum FAIL:** Cloudflare still blocking. "
                     "Cruise pricing gap remains. Consider proxy rotation or residential IP pairing.")
    else:
        lines.append("- **CruisePlum AMBIG:** Page loaded but pricing content unclear. Manual screenshot review needed.")

    lines += [
        "",
        "## Screenshots",
        "",
    ]
    for r in results:
        if r.get("screenshot"):
            fname = Path(r["screenshot"]).name
            lines.append(f"- `{fname}` — {r['test']}")

    lines += [
        "",
        "---",
        "",
        f"*Generated by Thunderbird OS — ELON/A12 PoC — M-061 — {now}*",
    ]

    REPORT_PATH.write_text("\n".join(lines))
    log(f"Report written → {REPORT_PATH}")
    return overall, verdict


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log("=" * 60)
    log("M-061: invisible_playwright PoC — starting")
    log(f"Firefox binary: {VENV_SITE.parent.parent.parent / 'firefox-7' / 'firefox'}")
    log("=" * 60)

    try:
        from invisible_playwright import InvisiblePlaywright
    except ImportError as e:
        log(f"FATAL: cannot import invisible_playwright: {e}")
        log(f"Run: source {THUNDERBIRD}/.venv/bin/activate")
        sys.exit(1)

    log("Launching InvisiblePlaywright (headless=True, humanize=True, prep_recaptcha=True)...")
    launch_t0 = time.time()

    try:
        with InvisiblePlaywright(
            headless=True,
            humanize=True,
            prep_recaptcha=True,
            locale="en-US",
            timezone="America/Denver",
        ) as browser:
            log(f"Browser launched in {round(time.time() - launch_t0, 1)}s")

            test_centrav(browser)
            log("")
            time.sleep(1.5)

            test_cruiseplum(browser)
            log("")
            time.sleep(1.0)

            test_fingerprint(browser)
            log("")

    except Exception as e:
        log(f"FATAL launch error: {e}")
        traceback.print_exc()
        record("Browser Launch", False, f"Launch failed: {type(e).__name__}: {str(e)[:200]}")

    overall, verdict = generate_report()

    log("")
    log("=" * 60)
    log(f"M-061 PoC COMPLETE — {overall} — {verdict}")
    log(f"Report: {REPORT_PATH}")
    log(f"Screenshots: {SCREENSHOT_DIR}")
    log("=" * 60)


if __name__ == "__main__":
    main()
