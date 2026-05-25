#!/usr/bin/env python3
"""Quick probe — find working Headout URL for tour listings."""
import asyncio
from pathlib import Path

OUTPUT_DIR = Path("/home/john/Thunderbird/core/travel/data")

HEADOUT_URLS = [
    "https://www.headout.com/s/lisbon/",
    "https://www.headout.com/lisbon/things-to-do/",
    "https://www.headout.com/lisbon/tours/",
    "https://www.headout.com/c/lisbon-l42/",
]


async def probe(page, url):
    print(f"\n  URL: {url}", flush=True)
    try:
        await page.goto(url, timeout=20000, wait_until="domcontentloaded")
        await asyncio.sleep(4)
        title = await page.title()
        print(f"  title: {title}", flush=True)

        # Check the styled card containers
        for selector in [
            "[class*='activity-card']",
            "[class*='ProductCard']",
            "[class*='product-card']",
            "[class*='ExperienceCard']",
            "[class*='experience-card']",
            "[class*='CardTile']",
            "[class*='card-tile']",
            "article",
        ]:
            count = await page.locator(selector).count()
            if count >= 2:
                el = page.locator(selector).first
                cls = await el.get_attribute("class") or ""
                print(f"  MATCH [{count:3d}] {selector!r} → {cls[:80]!r}", flush=True)

        ss = OUTPUT_DIR / f"headout_{url.split('/')[-2] or 'root'}_{__import__('datetime').datetime.now().strftime('%H%M%S')}.png"
        await page.screenshot(path=str(ss))
        print(f"  screenshot: {ss.name}", flush=True)
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)


async def run():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
        page = await ctx.new_page()
        for url in HEADOUT_URLS:
            await probe(page, url)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
