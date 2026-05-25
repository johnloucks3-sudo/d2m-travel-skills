#!/usr/bin/env python3
"""
Discover current CSS selectors for tour/activity booking sites.
Navigates each site, dumps candidate product-card selectors from live DOM.
Run: python3 scripts/discover_tour_selectors.py
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("/home/john/Thunderbird/core/travel/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Candidate patterns to probe (order = priority)
CANDIDATE_PATTERNS = [
    # data-testid patterns
    "[data-testid*='card']",
    "[data-testid*='product']",
    "[data-testid*='activity']",
    "[data-testid*='experience']",
    "[data-testid*='tour']",
    "[data-testid*='item']",
    "[data-testid*='result']",
    "[data-testid*='listing']",
    # class patterns
    "[class*='product-card']",
    "[class*='activity-card']",
    "[class*='tour-card']",
    "[class*='experience-card']",
    "[class*='card-item']",
    "[class*='listing-card']",
    "[class*='result-card']",
    "[class*='ActivityCard']",
    "[class*='ProductCard']",
    "[class*='ExperienceCard']",
    "[class*='TourCard']",
    # aria patterns
    "[role='article']",
    "[role='listitem']",
    # generic article/li in known wrapper patterns
    "article[class*='card']",
    "li[class*='card']",
    "div[class*='card']",
]

SITES = [
    {
        "name": "viator",
        "url": "https://www.viator.com/Lisbon/d538-ttd",
        "wait_extra": 5,
    },
    {
        "name": "getyourguide",
        "url": "https://www.getyourguide.com/lisbon-l42/",
        "wait_extra": 5,
    },
    {
        "name": "klook",
        "url": "https://www.klook.com/en-US/search/?query=lisbon+tours",
        "wait_extra": 5,
    },
    {
        "name": "tiqets",
        "url": "https://www.tiqets.com/en/lisbon-attractions-c63751/",
        "wait_extra": 5,
    },
    {
        "name": "headout",
        "url": "https://www.headout.com/lisbon/",
        "wait_extra": 5,
    },
]


async def discover_site(page, site: dict) -> dict:
    name = site["name"]
    url = site["url"]
    print(f"\n[{name}] → {url}", flush=True)

    findings = {
        "site": name,
        "url": url,
        "page_title": "",
        "matches": [],
        "dom_snapshot": [],
        "error": None,
    }

    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(site.get("wait_extra", 3))

        findings["page_title"] = await page.title()
        print(f"  title: {findings['page_title']}", flush=True)

        # Screenshot for visual confirmation
        ss_path = OUTPUT_DIR / f"discover_{name}_{datetime.now().strftime('%Y%m%d')}.png"
        await page.screenshot(path=str(ss_path), full_page=False)

        # Probe each candidate selector
        for selector in CANDIDATE_PATTERNS:
            try:
                count = await page.locator(selector).count()
                if count >= 2:  # at least 2 = likely a results list
                    # Grab first element's class + data-testid for confirmation
                    el = page.locator(selector).first
                    el_class = await el.get_attribute("class") or ""
                    el_testid = await el.get_attribute("data-testid") or ""
                    el_tag = await el.evaluate("el => el.tagName.toLowerCase()")
                    findings["matches"].append({
                        "selector": selector,
                        "count": count,
                        "first_tag": el_tag,
                        "first_class": el_class[:120],
                        "first_testid": el_testid,
                    })
                    print(f"  MATCH [{count}] {selector!r} → tag={el_tag} testid={el_testid!r} class={el_class[:60]!r}", flush=True)
            except Exception as e:
                pass

        # Also dump top-level classes of body children for manual inspection
        dom_snap = await page.evaluate("""
            () => {
                const els = [...document.querySelectorAll('body *')];
                const seen = new Set();
                const results = [];
                for (const el of els) {
                    const testid = el.getAttribute('data-testid');
                    if (testid && !seen.has(testid)) {
                        seen.add(testid);
                        results.push({tag: el.tagName.toLowerCase(), testid, cls: (el.className || '').slice(0, 80)});
                        if (results.length >= 30) break;
                    }
                }
                return results;
            }
        """)
        findings["dom_snapshot"] = dom_snap
        print(f"  data-testid elements found: {len(dom_snap)}", flush=True)
        for item in dom_snap[:8]:
            print(f"    {item['tag']} testid={item['testid']!r} cls={item['cls'][:50]!r}", flush=True)

    except Exception as e:
        findings["error"] = str(e)
        print(f"  ERROR: {e}", flush=True)

    return findings


async def run():
    from playwright.async_api import async_playwright

    all_findings = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        for site in SITES:
            page = await context.new_page()
            try:
                result = await discover_site(page, site)
                all_findings.append(result)
            finally:
                await page.close()

        await browser.close()

    out = OUTPUT_DIR / f"selector_discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(all_findings, indent=2))
    print(f"\n\nFull results → {out}", flush=True)

    print("\n\n=== SUMMARY ===")
    for f in all_findings:
        if f["matches"]:
            best = f["matches"][0]
            print(f"  ✅ {f['site']:15} best={best['selector']!r} count={best['count']}")
        else:
            print(f"  ⚠️  {f['site']:15} no matches (check dom_snapshot)")


if __name__ == "__main__":
    asyncio.run(run())
