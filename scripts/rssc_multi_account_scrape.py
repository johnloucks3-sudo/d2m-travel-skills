#!/usr/bin/env python3
"""
RSSC Multi-Account Booking Scraper — RESUABLE PROCEDURE v1.0
================================================================
Saves booking data (screenshot + JSON) to ~/Thunderbird/validations/rssc_scrape/

Usage:
    python3 rssc_multi_account_scrape.py                # Scrape all known accounts
    python3 rssc_multi_account_scrape.py --d2m-only     # D2M account only
    python3 rssc_multi_account_scrape.py --oa-only      # OA account only

Key changes from prior scripts (June 2, 2026):
- Firefox REQUIRED (headless Chromium blocked by Akamai)
- Login uses ASP.NET WebForms postback IDs:
    #uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox
    #uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox
    #uxAgentHomePage_uxAgentRegister_uxRememberMeCheckbox
    #uxAgentHomePage_uxAgentRegister_uxLoginButton
- Booking URLs are found by scanning the DOM for <a href*="bookedcruise.aspx">
  NOT by regex on page HTML (URLs contain %-encoded chars that break regex)
- Each booking page loads data dynamically via AJAX. The "Loading" text in
  tables is replaced after ~3-5s. wait_for_load_state("networkidle") then
  wait_for_timeout(3000) is sufficient.
- Screenshot saved for visual reference alongside JSON text dump.
- Can't extract data from collapsed accordion sections without clicking them.
  The script clicks: SHOW MY ITINERARY, GUEST DETAILS, Suite Details, etc.
"""
import asyncio, json, os, re, sys
from datetime import datetime
from playwright.async_api import async_playwright

OUT_DIR = os.path.expanduser("~/Thunderbird/validations/rssc_scrape")
os.makedirs(OUT_DIR, exist_ok=True)

# D2M Account
D2M = {"email": "jl3lovegrouptravel@gmail.com", "password": "Falcons4me!"}
D2M_BOOKINGS = {
    "3071222_Furlow":         "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?eecDnW0xAFxbgFqHZBS8Eko5Uc3K5UTVHzz%2b5iUsOMeF38Ba0f%2bR5xYgM6Gv3nm1CyaweMg7GG8DwKCVXbjhAg%3d%3d",
    "3078056_Nichols":        "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?P4lRDbrpl6KimySo%2fK4o%2bwDZRcXP9mymm6bgZqnsScH38MGZtQLDbVpf764ZzfTpNPFFP6eqcei3a2Ce6Xvxyh5hFqPfV%2fyA",
    "3096289_Ely":            "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?McWU05z77cmpnbQbEo2CdOumw8lV3LRNPvEArhnrrs3hl5RgmNGc6tgCF0LEwSWn9KttcnSG6QV03Ue0ckTSqA%3d%3d",
    "2984034_McLeod_Dec2026": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?21uwzkkXT97f7JcY1xK9hyCQmJ8KAZNizQbA8RnZf9%2b2GB6xoVkHtRcCZey5%2bUtfz14I9iYKQKotURuEHXNX822RP7fimObr",
}

# OA Account
OA = {"email": "johnloucks3@gmail.com", "password": "Canal4me!"}

BOOKING_LABELS = {
    "3122006": "Loucks",
    "3114500": "McLeod",
    "3071222": "Furlow",
    "3078056": "Nichols",
    "3096289": "Ely",
    "2984034": "McLeod_D2M"
}

async def login(page, email, password, label="account"):
    print(f"\n--- Login: {label} ---")
    await page.goto("https://www.rssc.com/agent/default.aspx", wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(2000)
    try:
        btn = await page.query_selector("#onetrust-accept-btn-handler")
        if btn: await btn.click(); await page.wait_for_timeout(500)
    except: pass

    body = await page.evaluate("() => document.body.innerText")
    if "Logout" in body or "Return to dashboard" in body:
        print("  Already logged in")
        return True

    await page.fill("#uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox", email)
    await page.fill("#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox", password)
    await page.check("#uxAgentHomePage_uxAgentRegister_uxRememberMeCheckbox")
    await page.click("#uxAgentHomePage_uxAgentRegister_uxLoginButton")
    await page.wait_for_load_state("networkidle", timeout=30000)

    body = await page.evaluate("() => document.body.innerText")
    if "incorrect" in body.lower():
        print("  ERROR: Login failed")
        return False
    print(f"  OK: {page.url[:80]}")
    return True

async def logout(page):
    print("\n--- Logout ---")
    await page.goto("https://www.rssc.com/agent/logout.aspx", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)
    print("  Done")

async def scrape_booking(page, bid, url):
    print(f"\n=== {bid} ===")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(5000)

    for target in ["SHOW MY ITINERARY", "GUEST DETAILS", "Suite Details",
                    "Air Schedule", "Payments", "Shore Excursions",
                    "Culinary Arts", "Customize", "SHOW SUITE DETAILS"]:
        try:
            els = await page.query_selector_all(f'*:has-text("{target}"):not(:has(*))')
            for el in els:
                try: await el.click(); await page.wait_for_timeout(800)
                except: pass
        except: pass

    await page.wait_for_timeout(2000)
    text = await page.evaluate("() => document.documentElement.innerText")
    await page.screenshot(path=f"{OUT_DIR}/{bid}.png", full_page=True)

    result = {
        "booking_id": bid, "url": url,
        "time": datetime.now().isoformat(), "text": text,
        "key_data": extract_key(text)
    }
    with open(f"{OUT_DIR}/{bid}.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  Saved ({len(text)} chars)")
    return result

def extract_key(text):
    d = {}
    m = re.search(r'GUEST DETAILS\s*\n(.+?)(?=\n[A-Z ]{3,})', text, re.DOTALL)
    if m: d["guests"] = [g.strip() for g in m.group(1).split('\n') if g.strip() and 'GUEST' not in g and 'COMPLETE' not in g and 'TICKET' not in g]
    m = re.search(r'Suite Category is (.+)', text)
    if m: d["suite_category"] = m.group(1).strip()
    m = re.search(r'Suite Number is (\d+)', text)
    if m: d["suite_number"] = m.group(1).strip()
    m = re.search(r'Suite Location is (.+)', text)
    if m: d["suite_location"] = m.group(1).strip()
    m = re.search(r'Total Booking Amount:\s*\$?([0-9,]+\.\d{2})', text)
    if m: d["total"] = m.group(1)
    m = re.search(r'Paid to Date:\s*\$?([0-9,]+\.\d{2})', text)
    if m: d["paid"] = m.group(1)
    m = re.search(r'Balance Due:\s*\$?([0-9,]+\.\d{2})', text)
    if m: d["balance"] = m.group(1)
    m = re.search(r'Invoice No\.?\s*(\d+)', text, re.IGNORECASE)
    if m: d["invoice"] = m.group(1)
    m = re.search(r'Reservation No[:\s]*(\d+)', text)
    if m: d["invoice"] = m.group(1)
    m = re.search(r'(\d+ of \d+ Dining Reservations Completed)', text)
    if m: d["dining"] = m.group(1)
    m = re.search(r'(Departs on .+?)\n', text)
    if m: d["departure"] = m.group(1).strip()
    m = re.search(r'(Returns on .+?)\n', text)
    if m: d["return"] = m.group(1).strip()
    m = re.search(r'Sails on (.+)', text)
    if m: d["ship"] = m.group(1).strip()
    todo = re.findall(r'([A-Z]+ \d+, \d{4})\s*\n(.+?)(?=\n[A-Z]+ \d+, \d{4}|\Z)', text, re.DOTALL)
    if todo: d["to_do"] = [{"date": t[0].strip(), "items": [x.strip() for x in t[1].split('\n') if x.strip()]} for t in todo]
    return d

async def find_oa_bookings(page):
    """Find OA booking URLs from the dashboard."""
    print("\n--- Finding OA bookings ---")
    await page.goto("https://www.rssc.com/agent/dashboard/#myBookings", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_load_state("networkidle", timeout=15000)
    await page.wait_for_timeout(3000)

    links = await page.evaluate("""() =>
        Array.from(document.querySelectorAll('a')).filter(a => a.href.includes('bookedcruise')).map(a => ({
            text: a.textContent.trim(), href: a.href
        }))
    """)
    print(f"  Found {len(links)} booking(s)")
    for l in links:
        label = "UNKNOWN"
        for inv, name in BOOKING_LABELS.items():
            if inv in l['href'] or inv in l['text']:
                label = f"{inv}_{name}"
                break
        print(f"    {label}: {l['href'][:60]}...")
    return links

async def main():
    d2m_only = "--d2m-only" in sys.argv
    oa_only = "--oa-only" in sys.argv
    results = {}

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        # Phase 1: D2M Account
        if not oa_only:
            if await login(page, D2M["email"], D2M["password"], "D2M"):
                for bid, url in D2M_BOOKINGS.items():
                    results[bid] = await scrape_booking(page, bid, url)

        # Phase 2: OA Account
        if not d2m_only:
            if not oa_only:
                await logout(page)
            if await login(page, OA["email"], OA["password"], "OA"):
                oa_links = await find_oa_bookings(page)
                for link in oa_links:
                    label = "OA_unknown"
                    for inv, name in BOOKING_LABELS.items():
                        if inv in link['href'] or inv in link['text']:
                            label = f"{inv}_{name}"
                            break
                    results[label] = await scrape_booking(page, label, link['href'])

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        combined = f"{OUT_DIR}/all_bookings_{timestamp}.json"
        with open(combined, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n=== Combined: {combined} ===")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
