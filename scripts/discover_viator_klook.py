#!/usr/bin/env python3
"""
Deep probe of Viator and Klook — longer waits + scroll + full DOM dump.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("/home/john/Thunderbird/core/travel/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def deep_probe(page, name: str, url: str, wait_secs: int = 10):
    print(f"\n[{name}] {url}", flush=True)

    await page.goto(url, timeout=45000, wait_until="domcontentloaded")
    await asyncio.sleep(wait_secs)

    # Scroll down to trigger lazy loading
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
    await asyncio.sleep(3)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(3)

    title = await page.title()
    print(f"  title: {title}", flush=True)

    # Screenshot
    ss = OUTPUT_DIR / f"deep_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    await page.screenshot(path=str(ss), full_page=True)
    print(f"  screenshot: {ss.name}", flush=True)

    # Dump all unique classes that look like product/card patterns
    class_counts = await page.evaluate("""
        () => {
            const counts = {};
            for (const el of document.querySelectorAll('*')) {
                const raw = el.getAttribute('class') || '';
                for (const cls of raw.split(' ')) {
                    if (cls.match(/(card|product|activity|tour|experience|listing|result|item)/i)) {
                        counts[cls] = (counts[cls] || 0) + 1;
                    }
                }
            }
            return Object.entries(counts).sort((a,b) => b[1]-a[1]).slice(0, 30);
        }
    """)
    print(f"  Card-like class counts (top 30):", flush=True)
    for cls, count in class_counts:
        print(f"    [{count:3d}] {cls}", flush=True)

    # Dump all data-testid values
    testids = await page.evaluate("""
        () => {
            const seen = {};
            for (const el of document.querySelectorAll('[data-testid]')) {
                const tid = el.getAttribute('data-testid');
                seen[tid] = (seen[tid] || 0) + 1;
            }
            return Object.entries(seen).sort((a,b) => b[1]-a[1]);
        }
    """)
    print(f"  data-testid values: {len(testids)}", flush=True)
    for tid, count in testids[:20]:
        print(f"    [{count:3d}] {tid}", flush=True)

    return {"site": name, "class_counts": class_counts, "testids": testids, "title": title}


async def run():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"],
        )
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )

        results = []
        for name, url in [
            ("viator", "https://www.viator.com/Lisbon/d538-ttd"),
            ("klook", "https://www.klook.com/en-US/search/?query=lisbon+tours"),
            ("headout", "https://www.headout.com/lisbon/"),
        ]:
            page = await ctx.new_page()
            try:
                r = await deep_probe(page, name, url)
                results.append(r)
            finally:
                await page.close()

        await browser.close()

    out = OUTPUT_DIR / f"deep_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    asyncio.run(run())
