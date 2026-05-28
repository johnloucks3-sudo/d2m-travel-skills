#!/usr/bin/env python3
"""
M-061 — invisible_playwright eval
Probes Regent + Viking portals with:
  1. Vanilla Playwright (baseline — expect bot block)
  2. playwright-stealth 2.x (Stealth class)
Reports: URL reached, page title, bot detection signal, login form found Y/N
"""
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
CREDS_PATH = THUNDERBIRD / "config" / "portal_creds.json"
REPORT_PATH = THUNDERBIRD / "output" / f"m061_stealth_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

TARGETS = {
    "regent": {
        "login_url": "https://www.rssc.com/login",
        "portal_url": "https://www.rssc.com/travel-agents",
    },
    "viking": {
        "login_url": "https://www.viking.com/travel-advisor",
        "portal_url": "https://login.viking.com",
    },
}

BOT_SIGNALS = [
    "cloudflare", "just a moment", "checking your browser", "ddos-guard",
    "403 forbidden", "access denied", "bot", "captcha", "please wait",
    "are you human", "datadome", "imperva", "incapsula", "distilnetworks",
]

LOGIN_FORM_SIGNALS = [
    "input[type='password']", "input[type='email']",
    "input[name='username']", "input[name='email']",
    "input[placeholder*='assword']", "input[placeholder*='ser']",
]


async def probe_one(page, target_name: str, urls: dict, mode: str) -> dict:
    result = {
        "target": target_name,
        "mode": mode,
        "login_url": urls["login_url"],
        "final_url": None,
        "title": None,
        "status": None,
        "bot_detected": False,
        "bot_signal": None,
        "login_form_found": False,
        "login_form_selector": None,
        "page_text_excerpt": None,
        "error": None,
    }

    try:
        resp = await page.goto(urls["login_url"], wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(2_500)
        result["final_url"] = page.url
        result["title"] = await page.title()
        result["status"] = resp.status if resp else None

        body_text = (await page.inner_text("body")).lower()[:500]
        result["page_text_excerpt"] = body_text[:200]

        for sig in BOT_SIGNALS:
            if sig in body_text or sig in result["title"].lower():
                result["bot_detected"] = True
                result["bot_signal"] = sig
                break

        for sel in LOGIN_FORM_SIGNALS:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2_000):
                    result["login_form_found"] = True
                    result["login_form_selector"] = sel
                    break
            except Exception:
                continue

    except Exception as e:
        result["error"] = str(e)

    return result


async def run_vanilla(target_name: str, urls: dict) -> dict:
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await ctx.new_page()
        result = await probe_one(page, target_name, urls, "vanilla")
        await browser.close()
    return result


async def run_stealth(target_name: str, urls: dict) -> dict:
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        stealth = Stealth(
            navigator_languages_override=["en-US", "en"],
            navigator_vendor_override="Google Inc.",
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        )
        await stealth.apply_stealth_async(ctx)
        page = await ctx.new_page()
        result = await probe_one(page, target_name, urls, "stealth")
        await browser.close()
    return result


async def main():
    print(f"M-061 Stealth Probe — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    all_results = []

    for target_name, urls in TARGETS.items():
        print(f"\n[{target_name.upper()}]")

        print(f"  vanilla ... ", end="", flush=True)
        r_vanilla = await run_vanilla(target_name, urls)
        _print_result(r_vanilla)
        all_results.append(r_vanilla)

        print(f"  stealth ... ", end="", flush=True)
        r_stealth = await run_stealth(target_name, urls)
        _print_result(r_stealth)
        all_results.append(r_stealth)

    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(json.dumps(all_results, indent=2))
    print(f"\nReport → {REPORT_PATH}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in all_results:
        bot = "BOT-BLOCKED" if r["bot_detected"] else ("FORM-FOUND" if r["login_form_found"] else "UNKNOWN")
        err = f" ERR:{r['error'][:40]}" if r["error"] else ""
        print(f"  {r['target']:8s}  {r['mode']:8s}  {bot}  title={r['title']!r:.40}{err}")

    return all_results


def _print_result(r):
    if r["bot_detected"]:
        print(f"BOT ({r['bot_signal']}) — url={r['final_url']}")
    elif r["login_form_found"]:
        print(f"LOGIN FORM FOUND ({r['login_form_selector']}) — url={r['final_url']}")
    elif r["error"]:
        print(f"ERROR: {r['error'][:80]}")
    else:
        print(f"UNKNOWN — title={r['title']!r} url={r['final_url']}")


if __name__ == "__main__":
    asyncio.run(main())
