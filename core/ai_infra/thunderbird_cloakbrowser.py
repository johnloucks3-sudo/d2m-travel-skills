#!/usr/bin/env python3
"""
thunderbird_cloakbrowser.py — CloakBrowser stealth Chromium adapter.
Wraps cloakbrowser for Akamai/Imperva/Cloudflare/bot-check bypass on ANY
site, ANY project — first built against Regent's Akamai wall, but not
scoped to cruise portals. MIT-licensed, no usage cap. Use it wherever a
plain fetch or Tier-1/2 escalation comes back walled or JS-empty.
Falls back to regular Playwright if CloakBrowser unavailable.

Usage:
    from core.ai_infra.thunderbird_cloakbrowser import stealth_fetch, get_stealth_page
    html = await stealth_fetch("https://www.regentoceanicvoyages.com/...")
"""
from __future__ import annotations
import asyncio
from typing import Optional


async def stealth_fetch(url: str, wait_ms: int = 2000, timeout: int = 30000) -> str:
    """Fetch a URL with stealth browser. Returns page HTML."""
    try:
        from cloakbrowser import CloakBrowser
        async with CloakBrowser() as browser:
            page = await browser.new_page()
            await page.goto(url, timeout=timeout)
            await page.wait_for_timeout(wait_ms)
            return await page.content()
    except ImportError:
        # Fallback to playwright with stealth-ish headers
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            page = await ctx.new_page()
            await page.goto(url, timeout=timeout)
            await page.wait_for_timeout(wait_ms)
            html = await page.content()
            await browser.close()
            return html


def stealth_fetch_sync(url: str, wait_ms: int = 2000) -> str:
    """Blocking wrapper around stealth_fetch."""
    return asyncio.run(stealth_fetch(url, wait_ms=wait_ms))


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://httpbin.org/headers"
    print(stealth_fetch_sync(url)[:2000])
