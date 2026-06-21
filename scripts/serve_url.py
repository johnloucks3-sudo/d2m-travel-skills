#!/usr/bin/env python3
"""serve_url.py <url> — open a persistent, visible browser on yoga's screen for the Commander to drive."""
import asyncio, sys, time
from playwright.async_api import async_playwright
URL = sys.argv[1] if len(sys.argv)>1 else "https://www.google.com"
def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
async def main():
    async with async_playwright() as p:
        ctx = await p.firefox.launch_persistent_context(
            "/home/john/Thunderbird/core/travel/data/serve_url_profile",
            headless=False, viewport={"width":1440,"height":900})
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        log(f"Served {URL} — browser is YOURS. Open ~45 min.")
        for _ in range(540):
            await page.wait_for_timeout(5000)
            try: _ = page.url
            except Exception: log("Browser closed. Done."); break
        try: await ctx.close()
        except Exception: pass
if __name__=="__main__": asyncio.run(main())
