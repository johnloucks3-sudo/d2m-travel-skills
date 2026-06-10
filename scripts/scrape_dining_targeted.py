#!/usr/bin/env python3
"""
Targeted dining scraper — uses correct login procedure from rssc_multi_account_scrape.py
Fetches actual specialty dining reservation details for Furlow/Ely/Nichols.
Output: /tmp/regent_dining_actual.json
"""
import asyncio, json
from datetime import datetime
from playwright.async_api import async_playwright

TARGET_BOOKING_IDS = {"3071222": "Furlow", "3096289": "Ely", "3078056": "Nichols"}
D2M = {"email": "jl3lovegrouptravel@gmail.com", "password": "Falcons4me!"}


async def login(page, email, password):
    print("[LOGIN] Navigating to agent portal...")
    await page.goto("https://www.rssc.com/agent/default.aspx", wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(2000)
    try:
        btn = await page.query_selector("#onetrust-accept-btn-handler")
        if btn: await btn.click(); await page.wait_for_timeout(500)
    except: pass

    body = await page.evaluate("() => document.body.innerText")
    if "Logout" in body or "Return to dashboard" in body:
        print("[LOGIN] Already logged in")
        return True

    await page.fill("#uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox", email)
    await page.fill("#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox", password)
    try:
        await page.check("#uxAgentHomePage_uxAgentRegister_uxRememberMeCheckbox")
    except: pass
    await page.click("#uxAgentHomePage_uxAgentRegister_uxLoginButton")
    await page.wait_for_load_state("networkidle", timeout=30000)

    body = await page.evaluate("() => document.body.innerText")
    if "incorrect" in body.lower() or "invalid" in body.lower():
        print("[LOGIN] FAILED — invalid credentials")
        return False
    print(f"[LOGIN] OK — {page.url[:80]}")
    return True


async def find_booking_links(page):
    """Navigate to My Bookings and extract links for our target bookings."""
    print("[BOOKINGS] Searching for booking links on dashboard...")
    await page.goto("https://www.rssc.com/agent/dashboard/#myBookings", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(4000)

    links = await page.evaluate("""() => {
        return Array.from(document.querySelectorAll('a[href*="bookedcruise.aspx"]')).map(a => ({
            href: a.href,
            text: a.textContent.trim()
        }));
    }""")
    print(f"[BOOKINGS] Found {len(links)} booking link(s) on dashboard")

    # If dashboard didn't show links, try the myaccount page
    if not links:
        await page.goto("https://www.rssc.com/agent/myaccount/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        links = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a[href*="bookedcruise.aspx"], a[href*="booking"]')).map(a => ({
                href: a.href,
                text: a.textContent.trim()
            }));
        }""")
        print(f"[BOOKINGS] Found {len(links)} links on myaccount page")

    return links


async def scrape_booking_dining(page, label, url):
    """Scrape specialty dining data from a booking page."""
    print(f"\n[SCRAPE] {label} — {url[:70]}")
    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_load_state("networkidle", timeout=15000)
    await page.wait_for_timeout(4000)

    title = await page.title()
    print(f"  Page title: {title}")

    if "Access Denied" in title or "Login" in title:
        return {"error": "Access denied", "title": title}

    # Click any "show" buttons to expand collapsed sections
    for expand_text in ["SHOW MY ITINERARY", "DINING", "Show Details"]:
        try:
            btns = await page.query_selector_all(f'button:text("{expand_text}"), a:text("{expand_text}")')
            for btn in btns:
                if await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(1000)
        except: pass

    # Extract full page text
    full_text = await page.evaluate("() => document.body.innerText")

    # Extract dining section specifically
    dining_result = await page.evaluate("""() => {
        const result = {
            specialtyDining: [],
            diningText: [],
            reservations: []
        };

        const diningKeywords = ['prime 7', 'chartreuse', 'pacific rim', 'compass rose',
                                'sette mari', 'la veranda', 'specialty dining',
                                'dining reservation', 'restaurant'];
        const timePattern = /\\d{1,2}:\\d{2}\\s*[AP]M/gi;
        const datePattern = /(?:aug|sep|august|september)\\s+\\d{1,2}/gi;

        // Get all text nodes and their contexts
        const fullText = document.body.innerText;
        const lines = fullText.split('\\n').map(l => l.trim()).filter(l => l);

        for (let i = 0; i < lines.length; i++) {
            const lc = lines[i].toLowerCase();
            if (diningKeywords.some(kw => lc.includes(kw))) {
                // Get context window: 3 lines before + 8 after
                const start = Math.max(0, i - 2);
                const end = Math.min(lines.length, i + 9);
                const ctx = lines.slice(start, end).join(' | ');
                result.diningText.push(ctx);
            }
        }

        // Look specifically for reservation data (date + time + restaurant)
        const allText = document.body.innerText;
        const restaurantNames = ['Prime 7', 'Chartreuse', 'Pacific Rim'];
        restaurantNames.forEach(name => {
            const lc = allText.toLowerCase();
            const idx = lc.indexOf(name.toLowerCase());
            if (idx >= 0) {
                const context = allText.substring(Math.max(0, idx - 100), idx + 300);
                const times = context.match(/\\d{1,2}:\\d{2}\\s*[AP]M/gi) || [];
                const dates = context.match(/(?:Aug|Sep|August|September)\\s+\\d{1,2}/gi) || [];
                result.reservations.push({
                    restaurant: name,
                    context: context.trim(),
                    times: times,
                    dates: dates
                });
            }
        });

        // Also extract tables with dining data
        document.querySelectorAll('table').forEach((t, idx) => {
            const tt = t.innerText.toLowerCase();
            if (diningKeywords.some(kw => tt.includes(kw))) {
                const rows = [];
                t.querySelectorAll('tr').forEach(tr => {
                    const cells = Array.from(tr.querySelectorAll('td, th'))
                        .map(c => c.innerText.trim()).filter(c => c);
                    if (cells.length) rows.push(cells);
                });
                result.specialtyDining.push({tableIdx: idx, rows});
            }
        });

        return result;
    }""")

    # Save a snippet of the full text around dining keywords
    dining_lines = []
    in_dining = False
    for line in full_text.split('\n'):
        stripped = line.strip()
        lc = stripped.lower()
        if any(kw in lc for kw in ['dining', 'prime 7', 'chartreuse', 'pacific rim', 'restaurant']):
            in_dining = True
            dining_lines.append(stripped)
        elif in_dining and stripped:
            dining_lines.append(stripped)
            if len(dining_lines) > 5:
                in_dining = False

    return {
        "label": label,
        "scraped_at": datetime.now().isoformat(),
        "page_title": title,
        "dining_extracted": dining_result,
        "dining_lines_from_text": dining_lines[:50],
        "full_text_length": len(full_text)
    }


async def main():
    results = {"scraped_at": datetime.now().isoformat(), "bookings": {}}

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()

        if not await login(page, D2M["email"], D2M["password"]):
            print("LOGIN FAILED — aborting")
            return

        # Find booking links on dashboard
        all_links = await find_booking_links(page)

        # Match to our target bookings
        target_links = {}
        for link in all_links:
            for bid, label in TARGET_BOOKING_IDS.items():
                if bid in link["href"] or bid in link["text"]:
                    target_links[label] = link["href"]
                    print(f"  Found: {label} ({bid})")

        if not target_links:
            print("[WARN] No booking links found on dashboard — trying direct booking URLs")
            # Fall back to known URLs from rssc_targeted_scrape.py
            target_links = {
                "Furlow": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?eecDnW0xAFxbgFqHZBS8Eko5Uc3K5UTVHzz%2b5iUsOMeF38Ba0f%2bR5xYgM6Gv3nm1CyaweMg7GG8DwKCVXbjhAg%3d%3d",
                "Ely": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?McWU05z77cmpnbQbEo2CdOumw8lV3LRNPvEArhnrrs3hl5RgmNGc6tgCF0LEwSWn9KttcnSG6QV03Ue0ckTSqA%3d%3d",
                "Nichols": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?P4lRDbrpl6KimySo%2fK4o%2bwDZRcXP9mymm6bgZqnsScH38MGZtQLDbVpf764ZzfTpNPFFP6eqcei3a2Ce6Xvxyh5hFqPfV%2fyA",
            }

        # Scrape each booking
        for label, url in target_links.items():
            try:
                data = await scrape_booking_dining(page, label, url)
                results["bookings"][label] = data
            except Exception as e:
                print(f"  ERROR {label}: {e}")
                results["bookings"][label] = {"error": str(e)}

        await browser.close()

    output = "/tmp/regent_dining_actual.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[DONE] Results saved to {output}")


if __name__ == "__main__":
    asyncio.run(main())
