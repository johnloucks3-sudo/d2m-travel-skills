#!/usr/bin/env python3
"""
M-061 — Regent probe via nodriver (pure CDP, no Playwright wrapper)
nodriver uses a patched Chromium binary launched via CDP directly.
"""
import asyncio
import sys

REGENT_LOGIN = "https://www.rssc.com/login"
REGENT_PORTAL = "https://www.rssc.com/travel-agents"

BOT_SIGNALS = [
    "access denied", "cloudflare", "just a moment",
    "checking your browser", "ddos-guard", "403",
    "captcha", "are you human", "datadome",
]

async def main():
    try:
        import nodriver as uc
    except ImportError as e:
        print(f"nodriver not available: {e}")
        sys.exit(1)

    print(f"nodriver version: {uc.__version__}")
    print(f"Probing Regent: {REGENT_LOGIN}")

    browser = await uc.start(headless=True)
    page = await browser.get(REGENT_LOGIN)
    await asyncio.sleep(4)

    title = await page.evaluate("document.title")
    url = await page.evaluate("window.location.href")
    body_text = (await page.evaluate("document.body.innerText") or "").lower()[:500]

    print(f"  URL:   {url}")
    print(f"  Title: {title!r}")
    print(f"  Body:  {body_text[:250]!r}")

    bot_hit = next((s for s in BOT_SIGNALS if s in body_text or s in title.lower()), None)
    if bot_hit:
        print(f"\n❌ BOT DETECTED: {bot_hit!r}")
    else:
        # Check for login form
        has_pw = await page.evaluate(
            "!!document.querySelector(\"input[type='password']\")"
        )
        has_email = await page.evaluate(
            "!!document.querySelector(\"input[type='email'], input[type='text'], input[name='email']\")"
        )
        if has_pw and has_email:
            print(f"\n✅ LOGIN FORM FOUND — nodriver bypassed bot detection!")
        else:
            print(f"\n? No login form and no bot signal — title={title!r}")

    browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
