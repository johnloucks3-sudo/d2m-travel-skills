#!/usr/bin/env python3
"""
RSSC Agent Portal — Full Scrape
Connects via Chrome CDP (port 9222) to authenticated session.
Scrapes: excursions, sailings/rates, suite descriptions, images, deck plans
"""

import asyncio
import json
import os
import time
from datetime import datetime
from playwright.async_api import async_playwright

OUTPUT_DIR = os.path.expanduser("~/Thunderbird/validations/rssc_scrape")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Known booking detail URLs
BOOKINGS = {
    "3096289_Ely": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?McWU05z77cmpnbQbEo2CdOumw8lV3LRNPvEArhnrrs3hl5RgmNGc6tgCF0LEwSWn9KttcnSG6QV03Ue0ckTSqA%3d%3d",
    "3078056_Nichols": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?P4lRDbrpl6KimySo%2fK4o%2bwDZRcXP9mymm6bgZqnsScH38MGZtQLDbVpf764ZzfTpNPFFP6eqcei3a2Ce6Xvxyh5hFqPfV%2fyA",
    "3071222_Furlow": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?eecDnW0xAFxbgFqHZBS8Eko5Uc3K5UTVHzz%2b5iUsOMeF38Ba0f%2bR5xYgM6Gv3nm1CyaweMg7GG8DwKCVXbjhAg%3d%3d",
    "2984034_McLeod": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?21uwzkkXT97f7JcY1xK9hyCQmJ8KAZNizQbA8RnZf9%2b2GB6xoVkHtRcCZey5%2bUtfz14I9iYKQKotURuEHXNX822RP7fimObr",
}

# Ships we want suite info for
TARGET_SHIPS = ["Seven Seas Splendor", "Seven Seas Grandeur"]

async def scrape_excursions(page, booking_id, booking_url):
    """Navigate to booking detail and find excursion links/data."""
    print(f"\n{'='*60}")
    print(f"EXCURSIONS — {booking_id}")
    print(f"{'='*60}")

    await page.goto(booking_url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(3000)

    result = {"booking_id": booking_id, "excursions": [], "excursion_links": []}

    # Look for excursion-related links and sections
    excursion_data = await page.evaluate("""() => {
        const data = {links: [], sections: [], buttons: [], allText: []};

        // Find all links with excursion-related text
        document.querySelectorAll('a').forEach(a => {
            const text = a.textContent.trim();
            const href = a.href || '';
            if (text.toLowerCase().includes('excursion') ||
                text.toLowerCase().includes('shore') ||
                text.toLowerCase().includes('customize') ||
                href.toLowerCase().includes('excursion') ||
                href.toLowerCase().includes('shore')) {
                data.links.push({text, href, id: a.id, classes: a.className});
            }
        });

        // Find buttons
        document.querySelectorAll('button, input[type="button"], input[type="submit"]').forEach(b => {
            const text = b.textContent?.trim() || b.value || '';
            if (text.toLowerCase().includes('excursion') ||
                text.toLowerCase().includes('shore') ||
                text.toLowerCase().includes('customize')) {
                data.buttons.push({text, id: b.id, classes: b.className});
            }
        });

        // Find any section/div with excursion content
        document.querySelectorAll('div, section, table').forEach(el => {
            const text = el.textContent?.trim() || '';
            if (text.toLowerCase().includes('shore excursion') && text.length < 2000) {
                data.sections.push({
                    tag: el.tagName,
                    id: el.id,
                    classes: el.className,
                    text: text.substring(0, 500)
                });
            }
        });

        // Get the customize section content
        const customizeSection = document.querySelector('.booking-customize, .customize-section, [class*="customize"]');
        if (customizeSection) {
            data.customizeContent = customizeSection.innerHTML.substring(0, 3000);
        }

        return data;
    }""")

    result["excursion_page_data"] = excursion_data

    # Try clicking into excursion link if found
    for link in excursion_data.get("links", []):
        if "excursion" in link.get("text", "").lower() or "shore" in link.get("text", "").lower():
            href = link.get("href", "")
            if href and href.startswith("http"):
                print(f"  Found excursion link: {link['text']} → {href[:80]}")
                try:
                    await page.goto(href, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)

                    # Scrape the excursion page
                    exc_page_data = await page.evaluate("""() => {
                        const data = {excursions: [], pageTitle: document.title, pageText: ''};

                        // Try to find excursion cards/items
                        document.querySelectorAll('.excursion, .shore-excursion, [class*="excursion"], .activity-card, .tour-card').forEach(card => {
                            data.excursions.push({
                                html: card.innerHTML.substring(0, 1000),
                                text: card.textContent.trim().substring(0, 500)
                            });
                        });

                        // Get all port/day sections
                        document.querySelectorAll('.port-day, .itinerary-day, [class*="port"], [class*="day-"]').forEach(day => {
                            data.excursions.push({
                                type: 'day_section',
                                html: day.innerHTML.substring(0, 1000),
                                text: day.textContent.trim().substring(0, 500)
                            });
                        });

                        // Fallback: get meaningful page content
                        const main = document.querySelector('main, .main-content, #content, .page-content') || document.body;
                        data.pageText = main.textContent.trim().substring(0, 5000);

                        return data;
                    }""")

                    result["excursion_detail_page"] = exc_page_data

                    # Take screenshot
                    ss_path = f"{OUTPUT_DIR}/{booking_id}_excursions.png"
                    await page.screenshot(path=ss_path, full_page=True)
                    print(f"  Screenshot: {ss_path}")

                except Exception as e:
                    print(f"  Error navigating to excursion page: {e}")
                break

    # Also look for the "CUSTOMIZE" tab/link on booking detail
    if not result.get("excursion_detail_page"):
        await page.goto(booking_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        # Try clicking CUSTOMIZE tab
        try:
            customize_link = await page.query_selector('a:has-text("CUSTOMIZE"), a:has-text("Customize")')
            if customize_link:
                await customize_link.click()
                await page.wait_for_timeout(3000)

                customize_content = await page.evaluate("""() => {
                    const main = document.querySelector('main, .main-content, #content') || document.body;
                    return main.textContent.trim().substring(0, 5000);
                }""")
                result["customize_tab_content"] = customize_content

                ss_path = f"{OUTPUT_DIR}/{booking_id}_customize.png"
                await page.screenshot(path=ss_path, full_page=True)
                print(f"  Customize screenshot: {ss_path}")
        except Exception as e:
            print(f"  No CUSTOMIZE tab found: {e}")

    return result


async def scrape_sailings_rates(page):
    """Scrape available sailings and immediate confirmation rates."""
    print(f"\n{'='*60}")
    print("SAILINGS & RATES — Immediate Confirmation")
    print(f"{'='*60}")

    result = {"sailings": [], "screenshots": []}

    # Navigate to the search/sailings page
    search_urls = [
        "https://www.rssc.com/agent/cruises",
        "https://www.rssc.com/agent/search",
        "https://www.rssc.com/cruises",
        "https://www.rssc.com/agent/dashboard/",
    ]

    # First, go to dashboard and find the search/cruise link
    await page.goto("https://www.rssc.com/agent/dashboard/", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)

    # Find navigation links to sailings/cruises
    nav_links = await page.evaluate("""() => {
        const links = [];
        document.querySelectorAll('a').forEach(a => {
            const text = a.textContent.trim();
            const href = a.href || '';
            if (text.toLowerCase().includes('cruise') ||
                text.toLowerCase().includes('sail') ||
                text.toLowerCase().includes('search') ||
                text.toLowerCase().includes('find') ||
                text.toLowerCase().includes('voyage') ||
                text.toLowerCase().includes('book') ||
                href.includes('/cruise') ||
                href.includes('/sail') ||
                href.includes('/search') ||
                href.includes('/find')) {
                links.push({text: text.substring(0, 100), href, id: a.id});
            }
        });
        return links;
    }""")

    print(f"  Found {len(nav_links)} navigation links:")
    for link in nav_links[:15]:
        print(f"    {link['text'][:50]} → {link['href'][:80]}")

    result["nav_links"] = nav_links

    # Try the main cruises search page
    for url in search_urls[:3]:
        try:
            print(f"\n  Trying: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)

            page_title = await page.title()
            print(f"  Page title: {page_title}")

            if "404" in page_title or "error" in page_title.lower():
                continue

            # Extract sailing data
            sailing_data = await page.evaluate("""() => {
                const data = {sailings: [], filters: [], pageText: ''};

                // Look for sailing cards/results
                document.querySelectorAll('.cruise-card, .sailing-card, .voyage-card, .result-card, [class*="cruise"], [class*="sailing"], [class*="voyage"]').forEach(card => {
                    data.sailings.push({
                        html: card.innerHTML.substring(0, 2000),
                        text: card.textContent.trim().substring(0, 800)
                    });
                });

                // Look for filter options
                document.querySelectorAll('select, .filter, [class*="filter"]').forEach(f => {
                    data.filters.push({
                        id: f.id,
                        name: f.name,
                        text: f.textContent?.trim().substring(0, 200)
                    });
                });

                // Get page content
                const main = document.querySelector('main, .main-content, #content, .page-content') || document.body;
                data.pageText = main.textContent.trim().substring(0, 8000);

                return data;
            }""")

            if sailing_data.get("sailings") or len(sailing_data.get("pageText", "")) > 100:
                result["sailings_page"] = sailing_data
                ss_path = f"{OUTPUT_DIR}/sailings_search.png"
                await page.screenshot(path=ss_path, full_page=True)
                result["screenshots"].append(ss_path)
                print(f"  Got sailing data, screenshot: {ss_path}")
                break

        except Exception as e:
            print(f"  Error: {e}")
            continue

    # Try to find "Quick Search" or sailing search on agent portal
    try:
        await page.goto("https://www.rssc.com/agent/dashboard/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        # Look for search forms or quick-search widgets
        search_forms = await page.evaluate("""() => {
            const forms = [];
            document.querySelectorAll('form').forEach(f => {
                forms.push({
                    id: f.id,
                    action: f.action,
                    method: f.method,
                    text: f.textContent.trim().substring(0, 300)
                });
            });
            return forms;
        }""")
        result["search_forms"] = search_forms

    except Exception as e:
        print(f"  Dashboard search error: {e}")

    return result


async def scrape_ship_suites(page, ship_name):
    """Scrape suite descriptions, photos, and deck plans for a ship."""
    print(f"\n{'='*60}")
    print(f"SHIP DETAILS — {ship_name}")
    print(f"{'='*60}")

    result = {"ship": ship_name, "suites": [], "deck_plans": [], "images": [], "screenshots": []}

    # Try various URLs for ship info
    ship_slug = ship_name.lower().replace("seven seas ", "").strip()

    urls_to_try = [
        f"https://www.rssc.com/ships/{ship_slug}",
        f"https://www.rssc.com/ships/seven-seas-{ship_slug}",
        f"https://www.rssc.com/agent/ships/{ship_slug}",
        f"https://www.rssc.com/ships/{ship_slug}/suites",
        f"https://www.rssc.com/ships/seven-seas-{ship_slug}/suites",
        f"https://www.rssc.com/ships/{ship_slug}/deck-plans",
        f"https://www.rssc.com/ships/seven-seas-{ship_slug}/deck-plans",
    ]

    for url in urls_to_try:
        try:
            print(f"  Trying: {url}")
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            if resp and resp.status == 404:
                continue
            await page.wait_for_timeout(2000)

            page_title = await page.title()
            page_url = page.url

            if "404" in page_title or resp.status >= 400:
                continue

            print(f"  ✓ Loaded: {page_title} ({page_url})")

            # Extract suite data
            suite_data = await page.evaluate("""() => {
                const data = {suites: [], images: [], links: [], pageText: ''};

                // Find suite sections
                document.querySelectorAll('.suite, .cabin, .stateroom, [class*="suite"], [class*="cabin"], .room-type, .accommodation').forEach(el => {
                    const imgs = [];
                    el.querySelectorAll('img').forEach(img => {
                        if (img.src && !img.src.includes('pixel') && !img.src.includes('track')) {
                            imgs.push({src: img.src, alt: img.alt});
                        }
                    });
                    data.suites.push({
                        text: el.textContent.trim().substring(0, 1000),
                        images: imgs,
                        html: el.innerHTML.substring(0, 2000)
                    });
                });

                // Get ALL meaningful images
                document.querySelectorAll('img').forEach(img => {
                    if (img.src &&
                        img.naturalWidth > 100 &&
                        !img.src.includes('pixel') &&
                        !img.src.includes('track') &&
                        !img.src.includes('analytics') &&
                        !img.src.includes('doubleclick')) {
                        data.images.push({
                            src: img.src,
                            alt: img.alt || '',
                            width: img.naturalWidth,
                            height: img.naturalHeight
                        });
                    }
                });

                // Find deck plan links
                document.querySelectorAll('a').forEach(a => {
                    const text = a.textContent.trim();
                    const href = a.href || '';
                    if (text.toLowerCase().includes('deck') ||
                        text.toLowerCase().includes('suite') ||
                        text.toLowerCase().includes('cabin') ||
                        href.toLowerCase().includes('deck') ||
                        href.toLowerCase().includes('suite')) {
                        data.links.push({text: text.substring(0, 100), href});
                    }
                });

                // Page content
                const main = document.querySelector('main, .main-content, #content, .page-content') || document.body;
                data.pageText = main.textContent.trim().substring(0, 8000);

                return data;
            }""")

            if suite_data.get("suites") or suite_data.get("images") or len(suite_data.get("pageText", "")) > 200:
                result["pages"] = result.get("pages", [])
                result["pages"].append({
                    "url": page_url,
                    "title": page_title,
                    "data": suite_data
                })

                ss_path = f"{OUTPUT_DIR}/{ship_slug}_{url.split('/')[-1] or 'main'}.png"
                await page.screenshot(path=ss_path, full_page=True)
                result["screenshots"].append(ss_path)
                print(f"  Screenshot: {ss_path}")

        except Exception as e:
            print(f"  Error: {e}")
            continue

    # Try to navigate to deck plans specifically
    for plan_url_part in ["deck-plans", "deckplans", "deck-plan"]:
        try:
            url = f"https://www.rssc.com/ships/seven-seas-{ship_slug}/{plan_url_part}"
            print(f"  Deck plan: {url}")
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            if resp and resp.status < 400:
                await page.wait_for_timeout(2000)

                deck_data = await page.evaluate("""() => {
                    const data = {decks: [], images: [], svgs: []};

                    // Find deck images
                    document.querySelectorAll('img').forEach(img => {
                        if (img.src && img.naturalWidth > 200) {
                            data.images.push({src: img.src, alt: img.alt, w: img.naturalWidth, h: img.naturalHeight});
                        }
                    });

                    // Find SVG deck plans
                    document.querySelectorAll('svg').forEach(svg => {
                        data.svgs.push({width: svg.getAttribute('width'), viewBox: svg.getAttribute('viewBox')});
                    });

                    // Deck labels
                    document.querySelectorAll('[class*="deck"], .floor, .level').forEach(el => {
                        data.decks.push(el.textContent.trim().substring(0, 300));
                    });

                    return data;
                }""")

                result["deck_plans"] = deck_data
                ss_path = f"{OUTPUT_DIR}/{ship_slug}_deckplans.png"
                await page.screenshot(path=ss_path, full_page=True)
                result["screenshots"].append(ss_path)
                print(f"  Deck plan screenshot: {ss_path}")
                break
        except:
            continue

    return result


async def download_images(page, image_urls, prefix):
    """Download images for brochure use."""
    downloaded = []
    img_dir = f"{OUTPUT_DIR}/images"
    os.makedirs(img_dir, exist_ok=True)

    for i, img in enumerate(image_urls[:30]):  # Cap at 30 images per ship
        src = img if isinstance(img, str) else img.get("src", "")
        if not src or "pixel" in src or "track" in src:
            continue
        try:
            resp = await page.request.get(src)
            if resp.ok:
                content_type = resp.headers.get("content-type", "")
                ext = "jpg"
                if "png" in content_type:
                    ext = "png"
                elif "webp" in content_type:
                    ext = "webp"

                filename = f"{img_dir}/{prefix}_{i:02d}.{ext}"
                body = await resp.body()
                with open(filename, "wb") as f:
                    f.write(body)
                downloaded.append({"file": filename, "src": src, "size": len(body)})
                print(f"    ↓ {filename} ({len(body)//1024}KB)")
        except Exception as e:
            pass

    return downloaded


async def main():
    start = time.time()
    all_results = {
        "scraped_at": datetime.now().isoformat(),
        "excursions": {},
        "sailings": {},
        "ships": {},
    }

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = await context.new_page()

        # Block tracking/ad domains
        await page.route("**/*onetrust*", lambda route: route.abort())
        await page.route("**/*doubleclick*", lambda route: route.abort())
        await page.route("**/*analytics*", lambda route: route.abort())
        await page.route("**/*adsrvr*", lambda route: route.abort())

        # ── 1. EXCURSIONS for all 4 bookings ──
        for booking_id, url in BOOKINGS.items():
            try:
                exc_data = await scrape_excursions(page, booking_id, url)
                all_results["excursions"][booking_id] = exc_data
            except Exception as e:
                print(f"  ERROR scraping {booking_id}: {e}")
                all_results["excursions"][booking_id] = {"error": str(e)}

        # ── 2. SAILINGS & RATES ──
        try:
            sailings = await scrape_sailings_rates(page)
            all_results["sailings"] = sailings
        except Exception as e:
            print(f"  ERROR scraping sailings: {e}")
            all_results["sailings"] = {"error": str(e)}

        # ── 3. SHIP DETAILS — Splendor & Grandeur ──
        for ship in TARGET_SHIPS:
            try:
                ship_data = await scrape_ship_suites(page, ship)
                all_results["ships"][ship] = ship_data

                # Download images for brochures
                all_images = []
                for pg in ship_data.get("pages", []):
                    all_images.extend(pg.get("data", {}).get("images", []))

                if all_images:
                    slug = ship.lower().replace("seven seas ", "")
                    downloaded = await download_images(page, all_images, slug)
                    all_results["ships"][ship]["downloaded_images"] = downloaded

            except Exception as e:
                print(f"  ERROR scraping {ship}: {e}")
                all_results["ships"][ship] = {"error": str(e)}

        # ── 4. Try the public ship pages for better images/content ──
        for ship_slug in ["splendor", "grandeur"]:
            print(f"\n  Public page: rssc.com/ships/seven-seas-{ship_slug}")
            try:
                await page.goto(f"https://www.rssc.com/ships/seven-seas-{ship_slug}",
                              wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(3000)

                public_data = await page.evaluate("""() => {
                    const data = {sections: [], images: [], heroImages: []};

                    // Hero/banner images
                    document.querySelectorAll('.hero img, .banner img, [class*="hero"] img, [class*="banner"] img, .carousel img').forEach(img => {
                        if (img.src && img.naturalWidth > 300) {
                            data.heroImages.push({src: img.src, alt: img.alt, w: img.naturalWidth, h: img.naturalHeight});
                        }
                    });

                    // Background images
                    document.querySelectorAll('[style*="background-image"]').forEach(el => {
                        const style = el.getAttribute('style');
                        const match = style.match(/url\(['"]?([^'")\s]+)['"]?\)/);
                        if (match) {
                            data.heroImages.push({src: match[1], alt: 'background', w: 0, h: 0});
                        }
                    });

                    // All large images
                    document.querySelectorAll('img').forEach(img => {
                        if (img.src && img.naturalWidth > 200 && !img.src.includes('pixel')) {
                            data.images.push({src: img.src, alt: img.alt || '', w: img.naturalWidth, h: img.naturalHeight});
                        }
                    });

                    // Content sections
                    document.querySelectorAll('section, .section, [class*="section"]').forEach(s => {
                        const text = s.textContent.trim();
                        if (text.length > 50 && text.length < 3000) {
                            data.sections.push(text.substring(0, 1000));
                        }
                    });

                    return data;
                }""")

                all_results["ships"][f"public_{ship_slug}"] = public_data

                ss_path = f"{OUTPUT_DIR}/{ship_slug}_public.png"
                await page.screenshot(path=ss_path, full_page=True)
                print(f"  Screenshot: {ss_path}")

                # Download hero/feature images
                all_pub_images = public_data.get("heroImages", []) + public_data.get("images", [])
                if all_pub_images:
                    downloaded = await download_images(page, all_pub_images, f"{ship_slug}_public")
                    all_results["ships"][f"public_{ship_slug}"]["downloaded"] = downloaded

            except Exception as e:
                print(f"  Error on public page: {e}")

        # ── 5. Navigate sub-pages: suites, dining, deck plans ──
        for ship_slug in ["splendor", "grandeur"]:
            for subpage in ["suites", "dining", "deck-plans", "onboard", "gallery"]:
                try:
                    url = f"https://www.rssc.com/ships/seven-seas-{ship_slug}/{subpage}"
                    print(f"  Sub-page: {url}")
                    resp = await page.goto(url, wait_until="domcontentloaded", timeout=15000)

                    if resp and resp.status < 400:
                        await page.wait_for_timeout(2000)

                        sub_data = await page.evaluate("""() => {
                            const data = {text: '', images: [], cards: []};

                            const main = document.querySelector('main, .main-content, #content') || document.body;
                            data.text = main.textContent.trim().substring(0, 10000);

                            document.querySelectorAll('img').forEach(img => {
                                if (img.src && img.naturalWidth > 150 && !img.src.includes('pixel')) {
                                    data.images.push({src: img.src, alt: img.alt, w: img.naturalWidth, h: img.naturalHeight});
                                }
                            });

                            // Cards (suite cards, dining cards, etc)
                            document.querySelectorAll('.card, [class*="card"], .tile, [class*="tile"]').forEach(c => {
                                data.cards.push({
                                    text: c.textContent.trim().substring(0, 500),
                                    images: Array.from(c.querySelectorAll('img')).map(i => ({src: i.src, alt: i.alt})).filter(i => i.src)
                                });
                            });

                            return data;
                        }""")

                        key = f"{ship_slug}_{subpage}"
                        all_results["ships"][key] = sub_data

                        ss_path = f"{OUTPUT_DIR}/{key}.png"
                        await page.screenshot(path=ss_path, full_page=True)
                        print(f"    ✓ {len(sub_data.get('images',[]))} images, {len(sub_data.get('text',''))} chars")

                        # Download suite/dining images
                        if sub_data.get("images"):
                            await download_images(page, sub_data["images"], key)

                except Exception as e:
                    print(f"    ✗ {e}")

        await page.close()

    # Save all results
    output_file = f"{OUTPUT_DIR}/rssc_full_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"SCRAPE COMPLETE — {elapsed:.1f}s")
    print(f"Output: {output_file}")
    print(f"Screenshots: {OUTPUT_DIR}/")
    print(f"Images: {OUTPUT_DIR}/images/")
    print(f"{'='*60}")

    return output_file


if __name__ == "__main__":
    asyncio.run(main())
