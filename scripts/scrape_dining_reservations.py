#!/usr/bin/env python3
"""
Targeted Regent portal scraper — specialty dining reservations only.
Fetches actual reservation dates/times for Furlow, Ely, Nichols.
Uses Firefox (Akamai bypass). Output: /tmp/regent_dining_actual.json
"""
import asyncio
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright

COOKIES_FILE = Path.home() / "Thunderbird/creds/regent_cookies.json"
OUTPUT_FILE = Path("/tmp/regent_dining_actual.json")

BOOKINGS = {
    "3071222_Furlow": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?eecDnW0xAFxbgFqHZBS8Eko5Uc3K5UTVHzz%2b5iUsOMeF38Ba0f%2bR5xYgM6Gv3nm1CyaweMg7GG8DwKCVXbjhAg%3d%3d",
    "3096289_Ely": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?McWU05z77cmpnbQbEo2CdOumw8lV3LRNPvEArhnrrs3hl5RgmNGc6tgCF0LEwSWn9KttcnSG6QV03Ue0ckTSqA%3d%3d",
    "3078056_Nichols": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?P4lRDbrpl6KimySo%2fK4o%2bwDZRcXP9mymm6bgZqnsScH38MGZtQLDbVpf764ZzfTpNPFFP6eqcei3a2Ce6Xvxyh5hFqPfV%2fyA",
}

async def scrape_booking_dining(page, booking_id, url):
    print(f"\n[SCRAPE] {booking_id} ...")
    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(4000)

    title = await page.title()
    current_url = page.url
    print(f"  Title: {title}")
    print(f"  URL: {current_url[:80]}")

    if "Access Denied" in title or "login" in current_url.lower():
        return {"error": "Access denied or redirected to login", "title": title, "url": current_url}

    # Extract all text content for dining section analysis
    dining_data = await page.evaluate("""() => {
        const result = {
            pageTitle: document.title,
            diningSection: '',
            specialtyDining: [],
            allDiningText: [],
            rawSections: {}
        };

        const body = document.body;
        const fullText = body ? body.innerText : '';

        // Look for dining-related sections
        const diningKeywords = ['dining', 'restaurant', 'prime 7', 'chartreuse', 'pacific rim',
                                'compass rose', 'sette mari', 'la veranda', 'reservation',
                                'specialty dining', 'culinary'];

        // Extract section of text around dining keywords
        const lines = fullText.split('\\n');
        let diningLines = [];
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line && diningKeywords.some(kw => line.toLowerCase().includes(kw))) {
                // Get context: 3 lines before and 5 lines after
                const start = Math.max(0, i - 3);
                const end = Math.min(lines.length, i + 6);
                for (let j = start; j < end; j++) {
                    if (lines[j].trim()) {
                        diningLines.push(lines[j].trim());
                    }
                }
                diningLines.push('---');
            }
        }
        result.allDiningText = [...new Set(diningLines)];

        // Look specifically for reservation tables
        const tables = document.querySelectorAll('table');
        tables.forEach((table, idx) => {
            const tableText = table.innerText.toLowerCase();
            if (diningKeywords.some(kw => tableText.includes(kw))) {
                const rows = [];
                table.querySelectorAll('tr').forEach(tr => {
                    const cells = Array.from(tr.querySelectorAll('td, th'))
                        .map(c => c.innerText.trim())
                        .filter(c => c);
                    if (cells.length) rows.push(cells);
                });
                result.specialtyDining.push({tableIdx: idx, rows});
            }
        });

        // Look for specific restaurant mentions with dates/times
        const restaurants = ['Prime 7', 'Chartreuse', 'Pacific Rim', 'Compass Rose',
                              'Sette Mari', 'La Veranda'];
        restaurants.forEach(r => {
            const regex = new RegExp(r.replace(' ', '\\\\s+'), 'gi');
            const matches = fullText.match(regex);
            if (matches) {
                // Find context around this restaurant name
                const idx = fullText.search(regex);
                if (idx >= 0) {
                    const context = fullText.substring(Math.max(0, idx - 50),
                                                       Math.min(fullText.length, idx + 200));
                    result.rawSections[r] = context.trim();
                }
            }
        });

        // Get ALL text in dining/restaurant-related divs
        const allDivs = document.querySelectorAll('div, section, article');
        allDivs.forEach(div => {
            const text = div.innerText || '';
            if (text.length > 20 && text.length < 2000 &&
                diningKeywords.some(kw => text.toLowerCase().includes(kw))) {
                const key = text.substring(0, 40).replace(/\\s+/g, ' ').trim();
                if (!result.rawSections[key]) {
                    result.rawSections[key] = text.trim().substring(0, 500);
                }
            }
        });

        return result;
    }""")

    return dining_data


async def main():
    now = time.time()
    cookies = json.loads(COOKIES_FILE.read_text())
    valid_cookies = [c for c in cookies
                     if c.get('expires', -1) < 0 or c.get('expires', 0) > now]

    results = {
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "cookies_loaded": len(valid_cookies),
        "bookings": {}
    }

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            viewport={"width": 1280, "height": 900}
        )

        # Inject cookies
        pw_cookies = []
        for c in valid_cookies:
            entry = {
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ".rssc.com"),
                "path": c.get("path", "/"),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
            }
            if c.get("expires", -1) > 0:
                entry["expires"] = float(c["expires"])
            pw_cookies.append(entry)

        await context.add_cookies(pw_cookies)
        print(f"Injected {len(pw_cookies)} cookies")

        page = await context.new_page()

        for booking_id, url in BOOKINGS.items():
            try:
                data = await scrape_booking_dining(page, booking_id, url)
                results["bookings"][booking_id] = data
            except Exception as e:
                print(f"  ERROR {booking_id}: {e}")
                results["bookings"][booking_id] = {"error": str(e)}

        await browser.close()

    OUTPUT_FILE.write_text(json.dumps(results, indent=2))
    print(f"\n[DONE] Results saved to {OUTPUT_FILE}")
    return results


if __name__ == "__main__":
    asyncio.run(main())
