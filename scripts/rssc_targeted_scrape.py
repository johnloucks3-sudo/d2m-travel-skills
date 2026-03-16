#!/usr/bin/env python3
"""
RSSC Targeted Scrape — Pass 2
Extracts: excursion details, sailing prices, ship info via working URLs
"""

import asyncio
import json
import os
import time
from datetime import datetime
from playwright.async_api import async_playwright

OUTPUT_DIR = os.path.expanduser("~/Thunderbird/validations/rssc_scrape")
os.makedirs(f"{OUTPUT_DIR}/images", exist_ok=True)

BOOKINGS = {
    "3096289_Ely": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?McWU05z77cmpnbQbEo2CdOumw8lV3LRNPvEArhnrrs3hl5RgmNGc6tgCF0LEwSWn9KttcnSG6QV03Ue0ckTSqA%3d%3d",
    "3078056_Nichols": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?P4lRDbrpl6KimySo%2fK4o%2bwDZRcXP9mymm6bgZqnsScH38MGZtQLDbVpf764ZzfTpNPFFP6eqcei3a2Ce6Xvxyh5hFqPfV%2fyA",
    "3071222_Furlow": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?eecDnW0xAFxbgFqHZBS8Eko5Uc3K5UTVHzz%2b5iUsOMeF38Ba0f%2bR5xYgM6Gv3nm1CyaweMg7GG8DwKCVXbjhAg%3d%3d",
    "2984034_McLeod": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?21uwzkkXT97f7JcY1xK9hyCQmJ8KAZNizQbA8RnZf9%2b2GB6xoVkHtRcCZey5%2bUtfz14I9iYKQKotURuEHXNX822RP7fimObr",
}


async def extract_booking_full_detail(page, booking_id, url):
    """Deep extraction of ALL content from booking detail page."""
    print(f"\n--- {booking_id} ---")
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(3000)

    # Extract EVERYTHING from the page
    data = await page.evaluate("""() => {
        const result = {
            cruiseDetails: {},
            guestDetails: {},
            suiteDetails: {},
            todoList: [],
            payments: [],
            shoreExcursions: {summary: [], portOptions: []},
            beverages: {},
            hotelPackages: {},
            culinaryArts: [],
            shipboardCredits: {},
            customizeVoyage: {},
            allText: {}
        };

        // Helper: get text content of element matching selector
        function getText(sel) {
            const el = document.querySelector(sel);
            return el ? el.textContent.trim() : '';
        }

        // Get ALL text organized by major sections
        const body = document.body;

        // Find all heading-like elements and their content
        const headings = document.querySelectorAll('h1, h2, h3, h4, h5, .section-title, .heading, strong, b');
        const sections = {};
        headings.forEach(h => {
            const text = h.textContent.trim();
            if (text.length > 2 && text.length < 100) {
                // Get the parent section's content
                let parent = h.parentElement;
                for (let i = 0; i < 3 && parent; i++) {
                    const parentText = parent.textContent.trim();
                    if (parentText.length > text.length + 20 && parentText.length < 5000) {
                        sections[text] = parentText;
                        break;
                    }
                    parent = parent.parentElement;
                }
            }
        });
        result.allSections = sections;

        // Shore Excursion Summary - look for the table/list
        const excSummary = [];
        // Find "SHORE EXCURSION SUMMARY" section
        const allElements = document.querySelectorAll('*');
        let inExcursionSection = false;
        let excursionText = '';

        for (const el of allElements) {
            const text = el.textContent.trim();
            if (text.includes('SHORE EXCURSION SUMMARY') || text.includes('Shore Excursion Summary')) {
                inExcursionSection = true;
            }
            if (inExcursionSection && el.tagName === 'TABLE') {
                // Get table rows
                el.querySelectorAll('tr').forEach(tr => {
                    const cells = Array.from(tr.querySelectorAll('td, th')).map(c => c.textContent.trim());
                    if (cells.length > 0) {
                        excSummary.push(cells);
                    }
                });
                inExcursionSection = false;
            }
        }
        result.shoreExcursions.summary = excSummary;

        // Get the excursion dropdown options (ports)
        const portDropdowns = document.querySelectorAll('select');
        portDropdowns.forEach(sel => {
            const options = [];
            sel.querySelectorAll('option').forEach(opt => {
                if (opt.value && opt.textContent.trim()) {
                    options.push({value: opt.value, text: opt.textContent.trim()});
                }
            });
            if (options.some(o => o.text.includes('port') || o.text.includes('Port') ||
                o.text.includes('Choose') || options.length > 5)) {
                result.shoreExcursions.portOptions.push({
                    id: sel.id,
                    name: sel.name,
                    options: options
                });
            }
        });

        // Culinary Arts / Kitchen Classes
        const culinarySection = [];
        let inCulinary = false;
        for (const el of allElements) {
            const text = el.textContent.trim();
            if (text.includes('CULINARY ARTS') || text.includes('Culinary Arts') ||
                text.includes('KITCHEN CLASSES') || text.includes('Kitchen Classes')) {
                // Get this section's full content
                let parent = el;
                for (let i = 0; i < 5 && parent; i++) {
                    if (parent.textContent.trim().length > 100 && parent.textContent.trim().length < 3000) {
                        culinarySection.push(parent.textContent.trim());
                        break;
                    }
                    parent = parent.parentElement;
                }
                break;
            }
        }
        result.culinaryArts = culinarySection;

        // Payments section
        const paymentSection = [];
        for (const el of allElements) {
            const text = el.textContent.trim();
            if ((text.includes('PAYMENTS') || text.includes('Payments')) &&
                el.tagName.match(/^H[1-6]$|^STRONG$|^B$/)) {
                let parent = el.parentElement;
                for (let i = 0; i < 5 && parent; i++) {
                    const pt = parent.textContent.trim();
                    if (pt.length > 50 && pt.length < 3000) {
                        paymentSection.push(pt);
                        break;
                    }
                    parent = parent.parentElement;
                }
                break;
            }
        }
        result.payments = paymentSection;

        // Beverages, Dining, and Gratutities
        for (const el of allElements) {
            const text = el.textContent.trim();
            if (text.includes('BEVERAGES') || text.includes('Beverages')) {
                let parent = el.parentElement;
                for (let i = 0; i < 3 && parent; i++) {
                    const pt = parent.textContent.trim();
                    if (pt.length > 30 && pt.length < 2000) {
                        result.beverages = {text: pt};
                        break;
                    }
                    parent = parent.parentElement;
                }
                break;
            }
        }

        // Hotel / Land packages
        for (const el of allElements) {
            const text = el.textContent.trim();
            if (text.includes('HOTEL') || text.includes('Hotel/Land')) {
                let parent = el.parentElement;
                for (let i = 0; i < 3 && parent; i++) {
                    const pt = parent.textContent.trim();
                    if (pt.length > 30 && pt.length < 2000) {
                        result.hotelPackages = {text: pt};
                        break;
                    }
                    parent = parent.parentElement;
                }
                break;
            }
        }

        // Shipboard Credits
        for (const el of allElements) {
            const text = el.textContent.trim();
            if (text.includes('SHIPBOARD CREDITS') || text.includes('Shipboard Credits')) {
                let parent = el.parentElement;
                for (let i = 0; i < 3 && parent; i++) {
                    const pt = parent.textContent.trim();
                    if (pt.length > 20 && pt.length < 2000) {
                        result.shipboardCredits = {text: pt};
                        break;
                    }
                    parent = parent.parentElement;
                }
                break;
            }
        }

        // To-Do List items
        for (const el of allElements) {
            const text = el.textContent.trim();
            if (text.includes('My To-Do List') || text.includes('TO-DO LIST')) {
                let parent = el.parentElement;
                for (let i = 0; i < 5 && parent; i++) {
                    const pt = parent.textContent.trim();
                    if (pt.length > 50 && pt.length < 3000) {
                        result.todoList.push(pt);
                        break;
                    }
                    parent = parent.parentElement;
                }
                break;
            }
        }

        // Get FULL page text (organized)
        const mainContent = document.querySelector('.main-content, #content, main') || document.body;
        result.fullPageText = mainContent.textContent.trim().substring(0, 15000);

        return result;
    }""")

    # Also try selecting each port in the excursion dropdown to see what's booked
    excursion_by_port = {}
    dropdowns = data.get("shoreExcursions", {}).get("portOptions", [])

    for dropdown in dropdowns:
        dd_id = dropdown.get("id")
        if not dd_id:
            continue

        for option in dropdown.get("options", []):
            port_name = option.get("text", "")
            port_value = option.get("value", "")

            if not port_value or port_name.lower().startswith("choose") or port_name.lower().startswith("select"):
                continue

            try:
                # Select the port
                await page.select_option(f"#{dd_id}", port_value)
                await page.wait_for_timeout(2000)

                # Check if any excursion details appeared
                port_excursions = await page.evaluate("""() => {
                    const items = [];
                    // Look for excursion results/cards that appeared
                    document.querySelectorAll('.excursion-item, .tour-item, .activity-item, [class*="excursion"], [class*="tour-result"]').forEach(el => {
                        items.push(el.textContent.trim().substring(0, 500));
                    });

                    // Also check for any table that might have appeared
                    document.querySelectorAll('table').forEach(t => {
                        const rows = [];
                        t.querySelectorAll('tr').forEach(tr => {
                            const cells = Array.from(tr.querySelectorAll('td, th')).map(c => c.textContent.trim());
                            if (cells.some(c => c.length > 0)) rows.push(cells);
                        });
                        if (rows.length > 0) items.push(JSON.stringify(rows));
                    });

                    return items;
                }""")

                if port_excursions:
                    excursion_by_port[port_name] = port_excursions

            except Exception as e:
                print(f"    Port dropdown error for {port_name}: {e}")

    data["excursionsByPort"] = excursion_by_port

    # Take a high-res screenshot
    ss = f"{OUTPUT_DIR}/{booking_id}_detail_full.png"
    await page.screenshot(path=ss, full_page=True)
    print(f"  Screenshot: {ss}")

    return data


async def extract_sailings_with_prices(page):
    """Extract all sailing cards with prices from the search page."""
    print("\n--- SAILINGS & PRICES ---")
    await page.goto("https://www.rssc.com/agent/cruises", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(5000)

    # Extract sailing cards
    sailings = await page.evaluate("""() => {
        const results = [];

        // Find all cruise result cards
        const cards = document.querySelectorAll('.cruise-result, .cruise-card, [class*="cruise-result"], [class*="sailing"], .search-result');
        cards.forEach(card => {
            results.push({
                text: card.textContent.trim().substring(0, 600),
                html: card.innerHTML.substring(0, 1500)
            });
        });

        // If no cards found, get the full results area
        if (results.length === 0) {
            const resultsArea = document.querySelector('.results, .search-results, [class*="results"], .cruise-list') || document.body;
            // Split by visual separators
            const text = resultsArea.textContent.trim();
            results.push({text: text.substring(0, 15000), type: 'full_page'});
        }

        // Also get filter options for reference
        const filters = {};
        document.querySelectorAll('select').forEach(sel => {
            const opts = Array.from(sel.options).map(o => ({value: o.value, text: o.textContent.trim()}));
            if (opts.length > 1) {
                filters[sel.name || sel.id || 'unknown'] = opts;
            }
        });

        // Get specific price elements
        const prices = [];
        document.querySelectorAll('[class*="price"], [class*="rate"], [class*="fare"]').forEach(el => {
            const text = el.textContent.trim();
            if (text.match(/\$[\d,]+/)) {
                prices.push(text);
            }
        });

        return {cards: results, filters, prices};
    }""")

    # Try scrolling to load more
    for i in range(3):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)

    # Re-extract after scroll
    more_sailings = await page.evaluate("""() => {
        const results = [];
        const cards = document.querySelectorAll('.cruise-result, .cruise-card, [class*="cruise-result"], [class*="sailing"]');
        cards.forEach(card => {
            results.push(card.textContent.trim().substring(0, 600));
        });
        return results;
    }""")

    sailings["after_scroll"] = more_sailings

    ss = f"{OUTPUT_DIR}/sailings_prices_full.png"
    await page.screenshot(path=ss, full_page=True)
    print(f"  Screenshot: {ss}")

    return sailings


async def scrape_ship_via_agent_portal(page, ship_slug):
    """Try ship pages via the agent portal navigation."""
    print(f"\n--- SHIP: {ship_slug} (agent portal) ---")

    results = {"pages": {}, "images": []}

    # The nav showed ships with underscores
    ship_urls = [
        f"https://www.rssc.com/ships/seven_seas_{ship_slug}",
        f"https://www.rssc.com/agent/ships/seven_seas_{ship_slug}",
        f"https://www.rssc.com/fleet/seven-seas-{ship_slug}",
        f"https://www.rssc.com/fleet/{ship_slug}",
    ]

    for url in ship_urls:
        try:
            print(f"  Trying: {url}")
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            status = resp.status if resp else 0
            title = await page.title()
            print(f"    Status: {status}, Title: {title[:60]}")

            if status < 400 and "Access Denied" not in title and "404" not in title:
                content = await page.evaluate("""() => {
                    return {
                        text: document.body.textContent.trim().substring(0, 10000),
                        images: Array.from(document.querySelectorAll('img')).filter(i =>
                            i.src && i.naturalWidth > 100 && !i.src.includes('pixel')
                        ).map(i => ({src: i.src, alt: i.alt, w: i.naturalWidth, h: i.naturalHeight})),
                        links: Array.from(document.querySelectorAll('a')).filter(a => {
                            const t = a.textContent.trim().toLowerCase();
                            return t.includes('suite') || t.includes('deck') || t.includes('dining') || t.includes('gallery');
                        }).map(a => ({text: a.textContent.trim(), href: a.href}))
                    };
                }""")

                results["pages"][url] = content
                ss = f"{OUTPUT_DIR}/{ship_slug}_agent.png"
                await page.screenshot(path=ss, full_page=True)
                print(f"    ✓ Got content, screenshot saved")

                # Follow suite/deck links
                for link in content.get("links", [])[:5]:
                    href = link.get("href", "")
                    if href:
                        try:
                            await page.goto(href, wait_until="domcontentloaded", timeout=15000)
                            sub_resp_status = resp.status if resp else 0
                            sub_content = await page.evaluate("""() => {
                                return {
                                    title: document.title,
                                    text: document.body.textContent.trim().substring(0, 8000),
                                    images: Array.from(document.querySelectorAll('img')).filter(i =>
                                        i.src && i.naturalWidth > 150
                                    ).map(i => ({src: i.src, alt: i.alt, w: i.naturalWidth, h: i.naturalHeight}))
                                };
                            }""")
                            results["pages"][href] = sub_content
                            slug_part = href.split("/")[-1] or "sub"
                            ss2 = f"{OUTPUT_DIR}/{ship_slug}_{slug_part}.png"
                            await page.screenshot(path=ss2, full_page=True)
                        except:
                            pass

                break  # Found a working URL
        except Exception as e:
            print(f"    Error: {e}")

    # Try finding ship info through the agent dashboard links
    if not results["pages"]:
        print("  Trying via dashboard navigation...")
        await page.goto("https://www.rssc.com/agent/dashboard/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        # Find the ship link in nav
        ship_link = await page.evaluate(f"""() => {{
            const links = Array.from(document.querySelectorAll('a'));
            const match = links.find(a => {{
                const text = a.textContent.trim().toLowerCase();
                const href = (a.href || '').toLowerCase();
                return text.includes('{ship_slug}') || href.includes('{ship_slug}');
            }});
            return match ? {{text: match.textContent.trim(), href: match.href}} : null;
        }}""")

        if ship_link:
            print(f"  Found nav link: {ship_link['text']} → {ship_link['href'][:80]}")
            try:
                await page.goto(ship_link["href"], wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(3000)
                content = await page.evaluate("""() => ({
                    title: document.title,
                    text: document.body.textContent.trim().substring(0, 10000),
                    images: Array.from(document.querySelectorAll('img')).filter(i =>
                        i.src && i.naturalWidth > 100
                    ).map(i => ({src: i.src, alt: i.alt, w: i.naturalWidth, h: i.naturalHeight}))
                })""")
                results["pages"][ship_link["href"]] = content
                ss = f"{OUTPUT_DIR}/{ship_slug}_nav.png"
                await page.screenshot(path=ss, full_page=True)
            except Exception as e:
                print(f"    Error following link: {e}")

    return results


async def download_images(page, image_list, prefix):
    """Download images for brochure assets."""
    downloaded = []
    seen_srcs = set()

    for i, img in enumerate(image_list[:25]):
        src = img.get("src", "") if isinstance(img, dict) else img
        if not src or src in seen_srcs:
            continue
        if any(x in src.lower() for x in ["pixel", "track", "analytics", "doubleclick", "adsrvr", "1x1"]):
            continue
        seen_srcs.add(src)

        try:
            resp = await page.request.get(src)
            if resp.ok:
                body = await resp.body()
                if len(body) < 1000:  # Skip tiny images
                    continue
                ct = resp.headers.get("content-type", "")
                ext = "jpg"
                if "png" in ct: ext = "png"
                elif "webp" in ct: ext = "webp"

                filename = f"{OUTPUT_DIR}/images/{prefix}_{i:03d}.{ext}"
                with open(filename, "wb") as f:
                    f.write(body)
                downloaded.append({
                    "file": filename,
                    "src": src,
                    "alt": img.get("alt", "") if isinstance(img, dict) else "",
                    "size_kb": len(body) // 1024
                })
                print(f"    ↓ {os.path.basename(filename)} ({len(body)//1024}KB)")
        except:
            pass

    return downloaded


async def main():
    start = time.time()
    results = {
        "scraped_at": datetime.now().isoformat(),
        "bookings": {},
        "sailings": {},
        "ships": {},
        "downloaded_images": {}
    }

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = await context.new_page()

        # Block tracking
        await page.route("**/*onetrust*", lambda route: route.abort())
        await page.route("**/*doubleclick*", lambda route: route.abort())
        await page.route("**/*analytics*", lambda route: route.abort())

        # ── 1. BOOKING DETAILS + EXCURSIONS ──
        for bid, url in BOOKINGS.items():
            try:
                data = await extract_booking_full_detail(page, bid, url)
                results["bookings"][bid] = data
            except Exception as e:
                print(f"  ERROR: {e}")
                results["bookings"][bid] = {"error": str(e)}

        # ── 2. SAILINGS & PRICES ──
        try:
            results["sailings"] = await extract_sailings_with_prices(page)
        except Exception as e:
            print(f"  SAILINGS ERROR: {e}")

        # ── 3. SHIP DETAILS — Splendor & Grandeur ──
        for slug in ["splendor", "grandeur"]:
            try:
                results["ships"][slug] = await scrape_ship_via_agent_portal(page, slug)
            except Exception as e:
                print(f"  SHIP ERROR {slug}: {e}")

        # ── 4. Try the search page filtered by ship for prices ──
        for ship_name, slug in [("Seven Seas Splendor", "splendor"), ("Seven Seas Grandeur", "grandeur")]:
            print(f"\n--- Sailings for {ship_name} ---")
            try:
                await page.goto("https://www.rssc.com/cruises", wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(3000)

                # Look for ship filter
                ship_data = await page.evaluate(f"""() => {{
                    // Try to find and click ship filter
                    const allText = document.body.textContent;
                    const hasShip = allText.includes('{ship_name}');

                    // Get all select elements
                    const selects = Array.from(document.querySelectorAll('select')).map(s => ({{
                        id: s.id,
                        name: s.name,
                        options: Array.from(s.options).map(o => ({{value: o.value, text: o.textContent.trim()}}))
                    }}));

                    // Get checkbox/radio filters
                    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"], input[type="radio"]')).map(c => ({{
                        id: c.id,
                        name: c.name,
                        value: c.value,
                        label: c.labels?.[0]?.textContent.trim() || '',
                        checked: c.checked
                    }})).filter(c => c.label.toLowerCase().includes('{slug}') || c.value.toLowerCase().includes('{slug}'));

                    return {{hasShip, selects, checkboxes}};
                }}""")

                results["ships"][f"{slug}_sailings_filter"] = ship_data

            except Exception as e:
                print(f"  Filter error: {e}")

        # ── 5. Download any images we found ──
        all_images = []
        for bid, data in results["bookings"].items():
            # Booking pages usually don't have brochure images
            pass

        for slug, ship_data in results["ships"].items():
            if isinstance(ship_data, dict):
                for url, page_data in ship_data.get("pages", {}).items():
                    if isinstance(page_data, dict):
                        imgs = page_data.get("images", [])
                        if imgs:
                            print(f"\n  Downloading {len(imgs)} images from {slug}...")
                            dl = await download_images(page, imgs, slug)
                            results["downloaded_images"][slug] = dl

        await page.close()

    # Save results
    output_file = f"{OUTPUT_DIR}/rssc_targeted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"TARGETED SCRAPE COMPLETE — {elapsed:.1f}s")
    print(f"Output: {output_file}")
    print(f"{'='*60}")
    return output_file


if __name__ == "__main__":
    asyncio.run(main())
