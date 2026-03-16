#!/usr/bin/env python3
"""
ProjectExpedition Tour Search — Travel Advisor Net Pricing
Dreams2Memories Travel, LLC

Usage:
    python3 pe_tour_search.py --location "Kyoto"
    python3 pe_tour_search.py --attraction "Mount Fuji"
    python3 pe_tour_search.py --location "Tokyo" --type private
    python3 pe_tour_search.py --attraction "Arashiyama Bamboo Forest" --type private
    python3 pe_tour_search.py --location "Kyoto" --keyword "food"
    python3 pe_tour_search.py --country "Japan"  (no filter, all tours)

Requires: playwright, saved browser profile at ~/Thunderbird/browser_profiles/projectexpedition/
"""

import argparse
import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

PROFILE_DIR = os.path.expanduser("~/Thunderbird/browser_profiles/projectexpedition")
SCREENSHOT_DIR = os.path.expanduser("~/Thunderbird/screenshots")
LOG_DIR = os.path.expanduser("~/Thunderbird/logs")


def log(msg):
    print(f"[PE] {msg}", file=sys.stderr)


async def search_tours(country="Japan", location=None, attraction=None, tour_type=None, keyword=None, max_results=50):
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        # Navigate: Home → Destinations → Country
        log(f"Navigating to {country}...")
        await page.goto('https://www.projectexpedition.com/')
        await page.wait_for_timeout(3000)
        await page.click('text=Destinations')
        await page.wait_for_timeout(2000)
        await page.click(f'a:has-text("{country}")')
        await page.wait_for_timeout(8000)

        count_before = await page.evaluate(
            r"() => document.body.innerText.match(/(\d+) experiences/)?.[1] || 'unknown'"
        )
        log(f"{country}: {count_before} total experiences")

        # Apply location filter (Start Locations section)
        if location:
            log(f"Filtering by location: {location}")
            result = await page.evaluate("""(loc) => {
                const allInputs = document.querySelectorAll('input[type=checkbox]');
                for (const inp of allInputs) {
                    const lbl = inp.closest('label');
                    if (lbl && lbl.textContent.trim() === loc) {
                        inp.click();
                        return 'ok';
                    }
                }
                return 'not_found';
            }""", location)
            if result == 'not_found':
                log(f"WARNING: Location '{location}' not found in filters")
            await page.wait_for_timeout(6000)

        # Apply attraction filter (Attractions section)
        if attraction:
            log(f"Filtering by attraction: {attraction}")
            result = await page.evaluate("""(attr) => {
                const allInputs = document.querySelectorAll('input[type=checkbox]');
                for (const inp of allInputs) {
                    const lbl = inp.closest('label');
                    if (lbl && lbl.textContent.trim() === attr) {
                        inp.click();
                        return 'ok';
                    }
                }
                return 'not_found';
            }""", attraction)
            if result == 'not_found':
                log(f"WARNING: Attraction '{attraction}' not found in filters")
            await page.wait_for_timeout(6000)

        # Apply type filter (Private Tours, Small Group, etc.)
        if tour_type:
            type_map = {
                'private': 'Private Tours',
                'small_group': 'Small Group Tours',
                'shore': 'Shore Excursions',
                'multiday': 'Multiday Trips',
                'group': 'Guided Group Tours',
            }
            type_label = type_map.get(tour_type.lower(), tour_type)
            log(f"Filtering by type: {type_label}")
            result = await page.evaluate("""(typeLabel) => {
                const allInputs = document.querySelectorAll('input[type=checkbox]');
                for (const inp of allInputs) {
                    const lbl = inp.closest('label');
                    if (lbl && lbl.textContent.trim() === typeLabel) {
                        inp.click();
                        return 'ok';
                    }
                }
                return 'not_found';
            }""", type_label)
            if result == 'not_found':
                log(f"WARNING: Type '{type_label}' not found in filters")
            await page.wait_for_timeout(6000)

        # Scroll to trigger lazy loading
        await page.evaluate("window.scrollBy(0, 500)")
        await page.wait_for_timeout(3000)

        # Get filtered count
        count_after = await page.evaluate(
            r"() => document.body.innerText.match(/(\d+) experiences/)?.[1] || 'unknown'"
        )
        log(f"After filters: {count_after} experiences")

        # Extract tour data
        tours = await page.evaluate("""(maxResults) => {
            const anchors = document.querySelectorAll('a[href*="/tour-activity/"]');
            const seen = new Set();
            const results = [];
            for (const a of anchors) {
                if (seen.has(a.href)) continue;
                // Skip review links (they contain tour URLs but are in review section)
                if (a.closest('.review, [class*=review]')) continue;
                seen.add(a.href);
                const card = a.closest('.col-xs-12, .search-result, [class*=card]') || a.parentElement.parentElement;
                if (!card) continue;
                const text = card.innerText.trim();
                // Parse the card text
                const lines = text.split('\\n').map(l => l.trim()).filter(l => l);
                const title = lines[0] || '';
                // Find price
                let price = '';
                let perPerson = false;
                for (const line of lines) {
                    if (line.includes('US$')) {
                        price = line.replace('From ', '');
                        perPerson = line.includes('Per Person');
                        break;
                    }
                }
                // Find rating
                let rating = '';
                for (const line of lines) {
                    if (line.match(/^[0-9]\.[0-9]$/)) { rating = line; break; }
                }
                // Find review info
                let reviews = '';
                for (const line of lines) {
                    if (line.includes('verified review') || line.includes('operator rating')) {
                        reviews = line.replace(/[()]/g, ''); break;
                    }
                }
                // Find location
                let location = '';
                for (const line of lines) {
                    if (line.includes(', Japan') || line.includes(', Italy') || line.includes(', France') || line.match(/, [A-Z]/)) {
                        location = line; break;
                    }
                }
                // Find duration
                let duration = '';
                for (const line of lines) {
                    if (line.match(/\d+ (Hour|Minute|Day)/i)) { duration = line; break; }
                }
                // Find type
                let tourType = '';
                for (const line of lines) {
                    if (line.includes('Private') || line.includes('Small Group') || line.includes('Single Day') || line.includes('Multiday')) {
                        tourType = line; break;
                    }
                }
                // Find activities
                let activities = [];
                for (const line of lines) {
                    if (line.match(/^(Cooking|Food|Sightseeing|Local|Cultural|City|Hiking|Boating|Eco|Walking|Night|Brewery|Cycling|Helicopter|Train|Temple|Museum|Tea|Cable|Sake|Cherry)/)) {
                        activities.push(line);
                    }
                }

                results.push({
                    title: title,
                    url: a.href,
                    price: price,
                    per_person: perPerson,
                    rating: rating,
                    reviews: reviews,
                    location: location,
                    duration: duration,
                    type: tourType,
                    activities: activities.slice(0, 3).join(', ')
                });
                if (results.length >= maxResults) break;
            }
            return results;
        }""", max_results)

        # Apply keyword filter (client-side)
        if keyword:
            kw = keyword.lower()
            tours = [t for t in tours if kw in t['title'].lower() or kw in t['activities'].lower()]
            log(f"Keyword filter '{keyword}': {len(tours)} matches")

        # Screenshot
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filter_tag = location or attraction or country
        ss_path = f"{SCREENSHOT_DIR}/pe_search_{filter_tag}_{ts}.png"
        await page.screenshot(path=ss_path)
        log(f"Screenshot: {ss_path}")

        await browser.close()

        return {
            "country": country,
            "location_filter": location,
            "attraction_filter": attraction,
            "type_filter": tour_type,
            "keyword_filter": keyword,
            "total_before_filter": count_before,
            "total_after_filter": count_after,
            "tours_extracted": len(tours),
            "tours": tours,
            "screenshot": ss_path,
            "timestamp": datetime.now().isoformat()
        }


def print_results(data):
    filters = []
    if data['location_filter']:
        filters.append(f"Location: {data['location_filter']}")
    if data['attraction_filter']:
        filters.append(f"Attraction: {data['attraction_filter']}")
    if data['type_filter']:
        filters.append(f"Type: {data['type_filter']}")
    if data['keyword_filter']:
        filters.append(f"Keyword: {data['keyword_filter']}")
    filter_str = " | ".join(filters) if filters else "None"

    print(f"\n{'='*80}")
    print(f"  PROJECTEXPEDITION — TA NET PRICING")
    print(f"  Dreams2Memories Travel, LLC")
    print(f"{'='*80}")
    print(f"  Country: {data['country']}  |  Filters: {filter_str}")
    print(f"  Total: {data['total_after_filter']} experiences  |  Extracted: {data['tours_extracted']}")
    print(f"  Searched: {data['timestamp'][:19]}")
    print(f"{'='*80}\n")

    if not data['tours']:
        print("  No tours found matching your criteria.\n")
        return

    # Print table
    print(f"  {'#':>3}  {'Price':>10}  {'Rtg':>4}  {'Dur':>8}  {'Type':<20}  Title")
    print(f"  {'─'*3}  {'─'*10}  {'─'*4}  {'─'*8}  {'─'*20}  {'─'*40}")

    for i, t in enumerate(data['tours'], 1):
        price = t['price'] or '—'
        if t['per_person']:
            price += '/pp'
        rating = t['rating'] or '—'
        dur = t['duration'][:12] if t['duration'] else '—'
        ttype = t['type'][:20] if t['type'] else '—'
        title = t['title'][:60]

        print(f"  {i:>3}  {price:>10}  {rating:>4}  {dur:>8}  {ttype:<20}  {title}")

    print(f"\n{'─'*80}")
    print(f"  DETAIL URLs:\n")
    for i, t in enumerate(data['tours'], 1):
        print(f"  {i:>3}. {t['title'][:70]}")
        print(f"       {t['url']}")
        if t['activities']:
            print(f"       Activities: {t['activities']}")
        if t['reviews']:
            print(f"       Reviews: {t['reviews']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Search ProjectExpedition tours (TA net pricing)")
    parser.add_argument("--country", default="Japan", help="Country to search (default: Japan)")
    parser.add_argument("--location", help="Start location filter (e.g. Kyoto, Tokyo, Osaka)")
    parser.add_argument("--attraction", help="Attraction filter (e.g. 'Mount Fuji', 'Arashiyama Bamboo Forest', 'Nishiki Market')")
    parser.add_argument("--type", dest="tour_type", help="Tour type: private, small_group, shore, multiday, group")
    parser.add_argument("--keyword", help="Keyword filter on title/activities (client-side)")
    parser.add_argument("--max", type=int, default=50, help="Max results to extract (default: 50)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of table")
    args = parser.parse_args()

    data = asyncio.run(search_tours(
        country=args.country,
        location=args.location,
        attraction=args.attraction,
        tour_type=args.tour_type,
        keyword=args.keyword,
        max_results=args.max
    ))

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print_results(data)

    # Save to log
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, "pe_tour_searches.jsonl")
    with open(log_path, "a") as f:
        f.write(json.dumps(data) + "\n")
    log(f"Results logged to {log_path}")


if __name__ == "__main__":
    main()
