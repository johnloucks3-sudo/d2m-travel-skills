#!/usr/bin/env python3
"""
REGENT API SPIKE — Phase 1 of Regent Portal Automation Plan.
Discover the API endpoints behind the booking detail page Vue.js app.

What this does:
1. Injects Regent cookies into a headless Firefox context
2. Navigates to each booking's detail page
3. Captures ALL network requests/responses (XHR, fetch, API calls)
4. Identifies endpoints for dining reservations and excursions
5. Saves the captured API contracts for scraper development

Run:
  python3 scripts/regent_api_spike.py

Requires fresh Regent cookies at creds/regent_cookies.json.
Run after Commander re-exports cookies from Firefox.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
COOKIE_FILE = ROOT / "creds" / "regent_cookies.json"
OUTPUT_DIR = ROOT / "validations" / "rssc_api_spike"
BOOKINGS = {
    "3071222_Furlow": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?eecDnW0xAFxbgFqHZBS8Eko5Uc3K5UTVHzz%2b5iUsOMeF38Ba0f%2bR5xYgM6Gv3nm1CyaweMg7GG8DwKCVXbjhAg%3d%3d",
    "3078056_Nichols": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?P4lRDbrpl6KimySo%2fK4o%2bwDZRcXP9mymm6bgZqnsScH38MGZtQLDbVpf764ZzfTpNPFFP6eqcei3a2Ce6Xvxyh5hFqPfV%2fyA",
    "3096289_Ely": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?McWU05z77cmpnbQbEo2CdOumw8lV3LRNPvEArhnrrs3hl5RgmNGc6tgCF0LEwSWn9KttcnSG6QV03Ue0ckTSqA%3d%3d",
}


def load_cookies() -> list[dict]:
    if not COOKIE_FILE.exists():
        print(f"Cookie file not found: {COOKIE_FILE}")
        print("Commander must re-export from Firefox first.")
        sys.exit(1)
    cookies = json.loads(COOKIE_FILE.read_text())
    rssc = [c for c in cookies if "rssc.com" in c.get("domain", "")]
    print(f"Loaded {len(rssc)} rssc.com cookies from {COOKIE_FILE.name}")
    return rssc


def normalize_cookies(raw: list[dict]) -> list[dict]:
    valid_ss = {"Strict", "Lax", "None"}
    cleaned = []
    for c in raw:
        nc = {k: v for k, v in c.items() if k != "sameSite"}
        if c.get("sameSite") in valid_ss:
            nc["sameSite"] = c["sameSite"]
        if nc.get("expires") == -1:
            del nc["expires"]
        cleaned.append(nc)
    return cleaned


async def spike_booking(booking_id: str, url: str) -> dict:
    """Navigate to booking page, capture all API traffic."""
    print(f"\n{'='*60}")
    print(f"SPIKE: {booking_id}")
    print(f"{'='*60}")

    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    captured = {
        "booking_id": booking_id,
        "timestamp": datetime.utcnow().isoformat(),
        "requests": [],
        "api_endpoints": {},
        "auth_status": None,
        "sections_found": [],
    }

    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="en-US",
        )

        cookies = normalize_cookies(load_cookies())
        await ctx.add_cookies(cookies)

        page = await ctx.new_page()

        # Intercept ALL network responses
        async def on_response(response):
            url = response.url
            status = response.status
            content_type = response.headers.get("content-type", "")

            entry = {
                "url": url,
                "status": status,
                "content_type": content_type[:80],
                "timing": response.request.timing,
            }

            # Capture JSON response bodies
            if "json" in content_type or url.endswith(".json"):
                try:
                    body = await response.json()
                    entry["body_preview"] = str(body)[:500]
                except Exception:
                    entry["body_preview"] = None

            captured["requests"].append(entry)

            # Identify API endpoints
            if "/api/" in url or "api." in url or url.endswith(".aspx"):
                short = url.split("?")[0]
                if short not in captured["api_endpoints"]:
                    captured["api_endpoints"][short] = {
                        "method": response.request.method,
                        "statuses": [],
                        "content_types": [],
                    }
                captured["api_endpoints"][short]["statuses"].append(status)
                captured["api_endpoints"][short]["content_types"].append(content_type[:60])

        page.on("response", on_response)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"  NAVIGATION FAILED: {e}")
            await browser.close()
            return captured

        await page.wait_for_timeout(3000)

        # Check auth
        html = await page.content()
        if "Sign Out" in html or "Logout" in html or "myBookings" in html:
            captured["auth_status"] = "AUTHENTICATED"
            print("  Auth: AUTHENTICATED")
        else:
            captured["auth_status"] = "STALE"
            print("  Auth: STALE — cookies need refresh")
            await browser.close()
            return captured

        # Try to find and click dining section
        dining_selectors = [
            "a=Specialty Dining", "a=Dining", "a=Dining Reservations",
            "[data-testid*='dining']", "a[href*='dining']", "//*[contains(text(),'Dining')]",
            "a=Make Dining Reservations",
        ]
        for sel in dining_selectors:
            try:
                if sel.startswith("//"):
                    el = await page.wait_for_selector(f"xpath={sel}", timeout=3000)
                else:
                    el = await page.wait_for_selector(sel, timeout=3000)
                if el:
                    await el.click()
                    await page.wait_for_timeout(2000)
                    section = sel.replace("a=", "").replace("[", "").replace("]", "")
                    captured["sections_found"].append(f"dining_via_{section}")
                    print(f"  Clicked dining section via: {sel}")
                    break
            except Exception:
                continue
        else:
            print("  Dining section not clickable via selectors")

        # Try shore excursions
        for sel in ["a=Shore Excursions", "a=Excursions", "a[href*='excursion']",
                     "[data-testid*='excursion']", "//*[contains(text(),'Excursion')]"]:
            try:
                if sel.startswith("//"):
                    el = await page.wait_for_selector(f"xpath={sel}", timeout=2000)
                else:
                    el = await page.wait_for_selector(sel, timeout=2000)
                if el:
                    await el.click()
                    await page.wait_for_timeout(2000)
                    captured["sections_found"].append(f"excursion_via_{sel}")
                    print(f"  Clicked excursion section via: {sel}")
                    break
            except Exception:
                continue
        else:
            print("  Excursion section not clickable via selectors")

        await page.wait_for_timeout(3000)
        await browser.close()

    # Deduplicate API endpoints
    for ep in captured["api_endpoints"]:
        captured["api_endpoints"][ep]["statuses"] = list(set(captured["api_endpoints"][ep]["statuses"]))
        captured["api_endpoints"][ep]["content_types"] = list(set(captured["api_endpoints"][ep]["content_types"]))

    print(f"  API endpoints found: {len(captured['api_endpoints'])}")
    print(f"  Total network requests: {len(captured['requests'])}")
    print(f"  Sections found: {captured['sections_found']}")

    return captured


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"REGENT API SPIKE — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Cookie file: {COOKIE_FILE}")
    print(f"Output dir: {OUTPUT_DIR}")
    print(f"Bookings: {list(BOOKINGS.keys())}")

    all_results = {}
    for booking_id, url in BOOKINGS.items():
        result = await spike_booking(booking_id, url)
        all_results[booking_id] = result

        out = OUTPUT_DIR / f"spike_{booking_id}.json"
        out.write_text(json.dumps(result, indent=2, default=str))
        print(f"  Saved: {out.name}")

    # Summary
    summary = {"timestamp": datetime.utcnow().isoformat(), "bookings": len(all_results)}
    for bid, r in all_results.items():
        summary[bid] = {
            "auth": r["auth_status"],
            "endpoints": len(r["api_endpoints"]),
            "sections": r["sections_found"],
        }
    summary_path = OUTPUT_DIR / "spike_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary saved: {summary_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
