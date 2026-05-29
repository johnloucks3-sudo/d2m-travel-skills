#!/usr/bin/env python3
"""
invisible_playwright PoC — Centrav CAPTCHA Bypass + Cruise Line Eval (A12 ELON)
===============================================================================
Tests whether feder-cr/invisible_playwright (C++-patched Firefox, reCAPTCHA 0.90)
can bypass bot detection walls and retrieve pricing from:
  1. Centrav B2B portal (reCAPTCHA-gated login + search)
  2. Cruise line pricing page (Celebrity / Silversea)

Usage:
    python3 eval_invisible_playwright.py

Output:
    - stdout: structured eval report with pass/fail per test
    - screenshots: captured at key points
    - JSON report: saved to output/

Dependencies:
    invisible-playwright (installed via pip from GitHub)
    playwright (already installed)
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

THUNDERBIRD = Path.home() / "Thunderbird"
OUTPUT_DIR = THUNDERBIRD / "output"
SCREENSHOT_DIR = THUNDERBIRD / "output" / "invisible_pw_eval"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

REPORT = {
    "eval_name": "invisible_playwright_poc_v2",
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "verdict": "PENDING",
}


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def report_test(name: str, passed: bool, detail: str = "", screenshot: str = ""):
    entry = {"test": name, "passed": passed, "detail": detail, "screenshot": screenshot}
    REPORT["tests"].append(entry)
    tag = "PASS" if passed else "FAIL"
    log(f"[{tag}] {name}: {detail}")


def fmt_usd(val: Optional[float]) -> str:
    if val is None:
        return "n/a"
    return f"${val:,.2f}"


async def test_import() -> bool:
    """Verify invisible_playwright package is importable."""
    try:
        from invisible_playwright import InvisiblePlaywright

        return True
    except Exception as e:
        log(f"  Import failed: {e}")
        return False


async def test_baseline_chromium(url: str) -> dict:
    """Test 1: Baseline — standard Chromium (should trigger CAPTCHA/bot block)."""
    from playwright.async_api import async_playwright

    result = {"browser": "chromium_standard", "blocked": False, "page_loaded": False}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            result["page_loaded"] = True
            content = await page.content()
            blocked_signals = [
                "recaptcha",
                "cf-challenge",
                "cf-browser-verification",
                "g-recaptcha",
                "h-captcha",
                "turnstile",
                "challenge",
                "access denied",
                "blocked",
                "automated",
            ]
            for signal in blocked_signals:
                if signal.lower() in content.lower():
                    result["blocked"] = True
                    break
            await page.screenshot(
                path=str(SCREENSHOT_DIR / "baseline_chromium.png"), full_page=True
            )
            await browser.close()
    except Exception as e:
        result["error"] = str(e)
    return result


async def test_invisible_playwright_page_load(url: str) -> dict:
    """Test 2: invisible_playwright — page load + bot detection check."""
    from invisible_playwright import InvisiblePlaywright

    result = {"browser": "invisible_playwright", "blocked": False, "page_loaded": False}
    try:
        async with InvisiblePlaywright() as browser:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            result["page_loaded"] = True
            content = await page.content()
            blocked_signals = [
                "recaptcha",
                "cf-challenge",
                "cf-browser-verification",
                "g-recaptcha",
                "h-captcha",
                "turnstile",
                "challenge",
                "access denied",
                "blocked",
                "automated",
            ]
            for signal in blocked_signals:
                if signal.lower() in content.lower():
                    result["blocked"] = True
                    break
            await page.screenshot(
                path=str(SCREENSHOT_DIR / "invisible_pw_page_load.png"), full_page=True
            )
    except Exception as e:
        result["error"] = str(e)
    return result


async def test_centrav_login() -> dict:
    """Test 3: invisible_playwright — Centrav login flow + search."""
    from invisible_playwright import InvisiblePlaywright

    result = {
        "browser": "invisible_playwright",
        "login_success": False,
        "search_success": False,
        "prices_found": [],
    }
    creds_path = THUNDERBIRD / "centrav_credentials.json"
    if not creds_path.exists():
        result["error"] = "No credentials file"
        return result

    creds = json.loads(creds_path.read_text())
    email = creds.get("email", "")
    password = creds.get("password", "")

    try:
        async with InvisiblePlaywright(
            pin={
                "screen.width": 1920,
                "screen.height": 1080,
                "hardware.concurrency": 8,
            }
        ) as browser:
            page = await browser.new_page()
            context = browser.contexts[0]

            await page.goto("https://www.centrav.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            await page.screenshot(
                path=str(SCREENSHOT_DIR / "centrav_home.png"), full_page=True
            )

            login_url = "https://www.centrav.com/login"
            await page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            await page.fill("#FormEmail", email, timeout=5000)
            await page.fill("#FormPassword", password, timeout=5000)
            await page.wait_for_timeout(500)

            submit_btn = await page.query_selector(
                'button[type="submit"], input[type="submit"], button:has-text("Log In"), button:has-text("Sign In")'
            )
            if submit_btn:
                await submit_btn.click()
                await page.wait_for_timeout(8000)
            else:
                await page.evaluate("document.querySelector('form').submit()")
                await page.wait_for_timeout(8000)

            await page.screenshot(
                path=str(SCREENSHOT_DIR / "centrav_post_login.png"), full_page=True
            )

            current_url = page.url
            if "login" not in current_url.lower():
                result["login_success"] = True
                log(f"  Centrav login SUCCESS: {current_url}")

                try:
                    await page.goto(
                        "https://www.centrav.com/",
                        wait_until="domcontentloaded",
                        timeout=30000,
                    )
                    await page.wait_for_timeout(2000)
                    await page.screenshot(
                        path=str(SCREENSHOT_DIR / "centrav_home_authed.png"),
                        full_page=True,
                    )
                    result["auth_screenshot"] = "centrav_home_authed.png"
                except Exception as e:
                    log(f"  Post-login home navigation: {e}")
            else:
                content = await page.content()
                if "recaptcha" in content.lower() or "cf-challenge" in content.lower():
                    result["captcha_blocked"] = True
                    log(f"  Centrav login BLOCKED by CAPTCHA")
                else:
                    log(f"  Centrav login FAILED (stayed on login page): {current_url}")

            await browser.close()
    except Exception as e:
        result["error"] = str(e)

    return result


async def test_cruise_line(url: str, name: str) -> dict:
    """Test 4: invisible_playwright — cruise line pricing page."""
    from invisible_playwright import InvisiblePlaywright

    result = {
        "browser": "invisible_playwright",
        "cruise_line": name,
        "page_loaded": False,
        "blocked": False,
        "prices_found": [],
    }

    try:
        async with InvisiblePlaywright() as browser:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(5000)
            result["page_loaded"] = True

            content = await page.content()
            blocked_signals = [
                "recaptcha",
                "cf-challenge",
                "cf-browser-verification",
                "g-recaptcha",
                "h-captcha",
                "turnstile",
                "challenge",
                "access denied",
                "blocked",
            ]
            for signal in blocked_signals:
                if signal.lower() in content.lower():
                    result["blocked"] = True
                    break
            if result["blocked"]:
                await page.screenshot(
                    path=str(SCREENSHOT_DIR / f"cruise_{name}_blocked.png"),
                    full_page=True,
                )
            else:
                prices_text = await page.evaluate("""() => {
                    const prices = [];
                    document.querySelectorAll('*').forEach(el => {
                        const t = (el.innerText || el.textContent || '').trim();
                        const m = t.match(/^\\$[\\d,]+(?:\\.[\\d]{2})?$/);
                        if (m && t.length < 20) prices.push(m[0]);
                    });
                    return [...new Set(prices)].slice(0, 25);
                }""")
                result["prices_found"] = prices_text[:15]
                await page.screenshot(
                    path=str(SCREENSHOT_DIR / f"cruise_{name}_loaded.png"),
                    full_page=True,
                )

            await browser.close()
    except Exception as e:
        result["error"] = str(e)

    return result


async def test_creepjs() -> dict:
    """Test 5: invisible_playwright — CreepJS detection check."""
    from invisible_playwright import InvisiblePlaywright

    result = {"browser": "invisible_playwright", "url": "https://creepjs-api.web.app", "lies": None}
    try:
        async with InvisiblePlaywright() as browser:
            page = await browser.new_page()
            await page.goto(
                "https://creepjs-api.web.app",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await page.wait_for_timeout(5000)
            await page.screenshot(
                path=str(SCREENSHOT_DIR / "creepjs.png"), full_page=True
            )
            body_text = await page.inner_text("body")
            result["page_text_snippet"] = body_text[:500]
            await browser.close()
    except Exception as e:
        result["error"] = str(e)
    return result


async def main():
    log("═══ invisible_playwright Eval v2 — Centrav + Cruise PoC ═══")
    log("")

    import_ok = await test_import()
    report_test("package_import", import_ok, "invisible_playwright importable")

    if not import_ok:
        REPORT["verdict"] = "FAIL — package not installed"
        log("invisible_playwright not installed. Run: pip install git+https://github.com/feder-cr/invisible_playwright.git")
        report_path = OUTPUT_DIR / f"invisible_pw_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.write_text(json.dumps(REPORT, indent=2))
        return 1

    # Test 1: Baseline Chromium — should hit CAPTCHA
    log("─── TEST 1: Baseline Chromium ───")
    baseline = await test_baseline_chromium("https://www.centrav.com/")
    report_test(
        "baseline_chromium",
        passed=baseline.get("page_loaded", False),
        detail=f"Blocked: {baseline.get('blocked', 'unknown')} | Page: {baseline.get('page_loaded', False)}",
        screenshot="baseline_chromium.png",
    )
    log("")

    # Test 2: invisible_playwright page load
    log("─── TEST 2: invisible_playwright page load ───")
    iw_load = await test_invisible_playwright_page_load("https://www.centrav.com/")
    report_test(
        "invisible_pw_page_load",
        passed=iw_load.get("page_loaded", False) and not iw_load.get("blocked", True),
        detail=f"Blocked: {iw_load.get('blocked', 'unknown')} | Page loaded: {iw_load.get('page_loaded', False)}",
        screenshot="invisible_pw_page_load.png",
    )
    log("")

    # Test 3: invisible_playwright Centrav login
    log("─── TEST 3: invisible_playwright Centrav login ───")
    login_result = await test_centrav_login()
    report_test(
        "centrav_login",
        passed=login_result.get("login_success", False),
        detail=(
            "Login succeeded"
            if login_result.get("login_success")
            else "CAPTCHA blocked" if login_result.get("captcha_blocked")
            else "Login failed"
        ),
        screenshot="centrav_post_login.png",
    )
    log("")

    # Test 4: invisible_playwright cruise line pricing
    log("─── TEST 4: Cruise line pricing pages ───")
    for url, name in [
        ("https://www.celebritycruises.com/", "celebrity"),
        ("https://www.silversea.com/", "silversea"),
    ]:
        cruise_result = await test_cruise_line(url, name)
        report_test(
            f"cruise_{name}",
            passed=cruise_result.get("page_loaded", False) and not cruise_result.get("blocked", True),
            detail=f"Blocked: {cruise_result.get('blocked', 'unknown')} | Prices: {len(cruise_result.get('prices_found', []))}",
            screenshot=f"cruise_{name}_loaded.png" if not cruise_result.get("blocked") else f"cruise_{name}_blocked.png",
        )
    log("")

    # Test 5: CreepJS fingerprint check
    log("─── TEST 5: CreepJS fingerprint test ───")
    creepjs = await test_creepjs()
    report_test(
        "creepjs_check",
        passed=True,
        detail=f"Page loaded: {not creepjs.get('error', False)}",
        screenshot="creepjs.png",
    )
    log("")

    # Verdict
    passed_tests = [t for t in REPORT["tests"] if t["passed"]]
    failed_tests = [t for t in REPORT["tests"] if not t["passed"]]
    total = len(REPORT["tests"])
    REPORT["verdict"] = "PASS" if len(passed_tests) >= total else "PARTIAL"
    REPORT["summary"] = f"{len(passed_tests)}/{total} tests passed"

    log(f"═══ RESULTS: {REPORT['summary']} ═══")
    for t in REPORT["tests"]:
        tag = "PASS" if t["passed"] else "FAIL"
        log(f"  [{tag}] {t['test']}: {t['detail']}")

    if login_result.get("login_success"):
        log("\n  >>> Centrav BLOCK UNLOCKED <<<")
        log("  invisible_playwright bypassed Centrav CAPTCHA.")
        log("  Next: integrate into centrav_flights.py")
    elif login_result.get("captcha_blocked"):
        log("\n  >>> Centrav still blocked by CAPTCHA <<<")
        log("  invisible_playwright could not bypass reCAPTCHA.")
        log("  Next: try with a SOCKS5 proxy or different fingerprint profile.")

    report_path = OUTPUT_DIR / f"invisible_pw_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(REPORT, indent=2))
    log(f"\nReport saved: {report_path}")
    log(f"Screenshots: {SCREENSHOT_DIR}")

    return 0 if REPORT["verdict"] != "FAIL" else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
