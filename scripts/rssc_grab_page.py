#!/usr/bin/env python3
"""
RSSC Page Grabber — scrapes whatever page is open in Chrome (port 9222).
Usage: python rssc_grab_page.py [label]
"""

import asyncio
import json
import os
import sys
import re
from datetime import datetime
from playwright.async_api import async_playwright

OUTPUT_DIR = os.path.expanduser("~/Thunderbird/validations/rssc_scrape")
os.makedirs(f"{OUTPUT_DIR}/images", exist_ok=True)

async def grab_current_page(label="page"):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        pages = context.pages

        # Prefer RSSC page, then last (most recent) non-extension page
        page = None
        candidates = []
        for pg in pages:
            url = pg.url
            if url.startswith("http") and "extension" not in url and "doubleclick" not in url and "adsrvr" not in url and "iperceptions" not in url and "ipredictive" not in url:
                if "rssc.com" in url:
                    page = pg
                    break
                candidates.append(pg)
        if not page and candidates:
            page = candidates[-1]  # last opened tab

        if not page:
            print("No suitable page found. Open tabs:")
            for pg in pages:
                print(f"  {pg.url[:80]}")
            return

        url = page.url
        title = await page.title()
        print(f"URL: {url}")
        print(f"Title: {title}")

        # Extract everything
        data = await page.evaluate("""() => {
            const result = {
                title: document.title,
                url: location.href,
                sections: {},
                images: [],
                tables: [],
                links: []
            };

            // Get all text organized by headings
            const body = document.querySelector('main, .main-content, #content, .page-content') || document.body;
            result.fullText = body.textContent.trim().substring(0, 30000);

            // All images > 100px
            document.querySelectorAll('img').forEach(img => {
                if (img.src && (img.naturalWidth > 100 || img.width > 100) &&
                    !img.src.includes('pixel') && !img.src.includes('track') &&
                    !img.src.includes('doubleclick') && !img.src.includes('analytics')) {
                    result.images.push({
                        src: img.src,
                        alt: img.alt || '',
                        w: img.naturalWidth || img.width,
                        h: img.naturalHeight || img.height
                    });
                }
            });

            // Background images
            document.querySelectorAll('[style*="background-image"]').forEach(el => {
                const style = el.getAttribute('style');
                const match = style.match(/url\\(['"]*([^'"\\)]+)['"]*\\)/);
                if (match) {
                    result.images.push({src: match[1], alt: 'bg', w: 0, h: 0});
                }
            });

            // All tables
            document.querySelectorAll('table').forEach(t => {
                const rows = [];
                t.querySelectorAll('tr').forEach(tr => {
                    const cells = Array.from(tr.querySelectorAll('td, th')).map(c => c.textContent.trim());
                    if (cells.some(c => c.length > 0)) rows.push(cells);
                });
                if (rows.length > 0) result.tables.push(rows);
            });

            // Relevant links
            document.querySelectorAll('a').forEach(a => {
                const text = a.textContent.trim();
                const href = a.href || '';
                if (text.length > 2 && text.length < 200 && href.startsWith('http')) {
                    result.links.push({text, href});
                }
            });

            return result;
        }""")

        # Screenshot
        ts = datetime.now().strftime("%H%M%S")
        ss_path = f"{OUTPUT_DIR}/{label}_{ts}.png"
        await page.screenshot(path=ss_path, full_page=True)
        print(f"Screenshot: {ss_path}")

        # Download images
        downloaded = []
        seen = set()
        for i, img in enumerate(data.get("images", [])[:30]):
            src = img.get("src", "")
            if not src or src in seen:
                continue
            if any(x in src.lower() for x in ["pixel", "track", "1x1", "spacer", "analytics"]):
                continue
            seen.add(src)
            try:
                resp = await page.request.get(src)
                if resp.ok:
                    body = await resp.body()
                    if len(body) < 1000:
                        continue
                    ct = resp.headers.get("content-type", "")
                    ext = "jpg"
                    if "png" in ct: ext = "png"
                    elif "webp" in ct: ext = "webp"
                    fname = f"{OUTPUT_DIR}/images/{label}_{i:03d}.{ext}"
                    with open(fname, "wb") as f:
                        f.write(body)
                    downloaded.append({"file": fname, "src": src, "alt": img.get("alt",""), "kb": len(body)//1024})
                    print(f"  ↓ {os.path.basename(fname)} ({len(body)//1024}KB) {img.get('alt','')[:40]}")
            except:
                pass

        data["downloaded_images"] = downloaded
        data["screenshot"] = ss_path

        # Save JSON
        json_path = f"{OUTPUT_DIR}/{label}_{ts}.json"
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Data: {json_path}")
        print(f"Images: {len(downloaded)}, Tables: {len(data.get('tables',[]))}, Links: {len(data.get('links',[]))}")
        print(f"Text: {len(data.get('fullText',''))} chars")

        return data

if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "page"
    asyncio.run(grab_current_page(label))
