#!/usr/bin/env python3
"""
Audit MAG My Site capability via CDP to existing Chrome session.
Navigates myagentgenie.com, finds My Site / agent website section,
screenshots every page and extracts feature inventory.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("/home/john/Thunderbird/core/travel/data")
SS_DIR = OUTPUT_DIR / "mag_mysite_audit"
SS_DIR.mkdir(parents=True, exist_ok=True)

CDP_URL = "http://localhost:9222"

REPORT = []


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)
    REPORT.append(msg)


async def screenshot(page, label: str) -> str:
    ts = datetime.now().strftime("%H%M%S")
    path = SS_DIR / f"{ts}_{label}.png"
    await page.screenshot(path=str(path), full_page=True)
    log(f"  📸 {path.name}")
    return str(path)


async def extract_nav_links(page) -> list[dict]:
    """Pull all navigation links from current page."""
    links = await page.evaluate("""
        () => {
            const results = [];
            for (const a of document.querySelectorAll('a, [role="menuitem"], [role="tab"]')) {
                const text = (a.innerText || a.getAttribute('aria-label') || '').trim();
                const href = a.getAttribute('href') || '';
                if (text && text.length < 100) {
                    results.push({text, href});
                }
            }
            return results;
        }
    """)
    return links


async def find_mysite_section(page, base_url: str) -> list[str]:
    """Search nav for My Site / website / public-facing links."""
    links = await extract_nav_links(page)
    candidates = []
    for link in links:
        text_lower = link["text"].lower()
        if any(kw in text_lower for kw in ["my site", "website", "agent site", "public", "landing", "profile", "microsite", "web page", "marketing"]):
            candidates.append(link)
            log(f"  Candidate nav item: '{link['text']}' → {link['href']}")
    return candidates


async def run():
    from playwright.async_api import async_playwright

    log("Connecting to Chrome CDP...")
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        log(f"Connected. Contexts: {len(browser.contexts)}")

        # Use existing context or create new
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        page.set_default_timeout(30000)

        # ── STEP 1: Navigate to MAG portal ──────────────────────────────
        log("\n═══ STEP 1: MAG Portal Homepage ═══")
        await page.goto("https://www.myagentgenie.com/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        title = await page.title()
        url = page.url
        log(f"  Title: {title}")
        log(f"  URL:   {url}")
        await screenshot(page, "01_mag_homepage")

        # Check if we're logged in
        body = await page.inner_text("body")
        is_logged_in = any(kw in body.lower() for kw in ["dashboard", "logout", "sign out", "my account", "welcome"])
        log(f"  Logged in: {is_logged_in}")

        if not is_logged_in:
            log("  NOT LOGGED IN — looking for session from vault or existing tab...")
            # Check if there's an existing authenticated tab
            for pg in ctx.pages:
                pg_url = pg.url
                if "myagentgenie.com" in pg_url and pg_url != "https://www.myagentgenie.com/":
                    log(f"  Found existing MAG tab: {pg_url}")
                    page = pg
                    await screenshot(page, "01b_existing_mag_tab")
                    break

        # ── STEP 2: Scan navigation ──────────────────────────────────────
        log("\n═══ STEP 2: Nav Scan ═══")
        candidates = await find_mysite_section(page, "https://www.myagentgenie.com")
        all_links = await extract_nav_links(page)
        log(f"  Total nav links: {len(all_links)}")
        log(f"  My Site candidates: {len(candidates)}")

        # ── STEP 3: Try common My Site URLs ─────────────────────────────
        log("\n═══ STEP 3: Direct URL Probes ═══")
        probe_urls = [
            "https://www.myagentgenie.com/my-site",
            "https://www.myagentgenie.com/mysite",
            "https://www.myagentgenie.com/agent-website",
            "https://www.myagentgenie.com/website",
            "https://www.myagentgenie.com/marketing",
            "https://www.myagentgenie.com/agent/website",
            "https://www.myagentgenie.com/agent/marketing",
            "https://www.myagentgenie.com/agent/my-site",
            "https://www.myagentgenie.com/profile",
            "https://www.myagentgenie.com/agent/profile",
            "https://book.myagentgenie.com/my-site",
            "https://book.myagentgenie.com/agent/website",
        ]

        found_pages = []
        for probe_url in probe_urls:
            try:
                resp = await page.goto(probe_url, wait_until="domcontentloaded", timeout=10000)
                await asyncio.sleep(2)
                final_url = page.url
                title = await page.title()
                status = resp.status if resp else "?"

                # Check if redirected to login (=not found) vs actual page
                is_404 = status == 404 or "not found" in title.lower()
                is_login_redirect = "login" in final_url or "sign-in" in final_url or "signin" in final_url
                is_real = not is_404 and not is_login_redirect and final_url != "https://www.myagentgenie.com/"

                icon = "✅" if is_real else ("🔒" if is_login_redirect else "❌")
                log(f"  {icon} {status} {probe_url} → {final_url[:80]}")
                log(f"      title: {title[:60]}")

                if is_real:
                    label = probe_url.split("/")[-1] or "root"
                    await screenshot(page, f"03_{label}")
                    body_text = await page.inner_text("body")
                    found_pages.append({
                        "url": probe_url,
                        "final_url": final_url,
                        "title": title,
                        "content_snippet": body_text[:800],
                    })
            except Exception as e:
                log(f"  💥 {probe_url} → {str(e)[:60]}")

        # ── STEP 4: Try the booking portal ──────────────────────────────
        log("\n═══ STEP 4: Booking Portal (book.myagentgenie.com) ═══")
        try:
            await page.goto("https://book.myagentgenie.com/", wait_until="domcontentloaded")
            await asyncio.sleep(3)
            title = await page.title()
            url = page.url
            log(f"  Title: {title}")
            log(f"  URL: {url}")
            await screenshot(page, "04_booking_portal")

            # Look for agent tools / My Site in booking portal nav
            candidates_b = await find_mysite_section(page, "https://book.myagentgenie.com")
            all_links_b = await extract_nav_links(page)
            log(f"  Booking portal nav links: {len(all_links_b)}")
            log(f"  My Site candidates in booking portal: {len(candidates_b)}")

            # Dump top links for inspection
            for lk in all_links_b[:20]:
                log(f"    [{lk['text'][:50]}] → {lk['href'][:80]}")
        except Exception as e:
            log(f"  ERROR: {e}")

        # ── STEP 5: Save report ──────────────────────────────────────────
        report = {
            "audited_at": datetime.now().isoformat(),
            "was_logged_in": is_logged_in,
            "my_site_candidates": candidates,
            "found_pages": found_pages,
            "screenshots_dir": str(SS_DIR),
            "log": REPORT,
        }

        report_path = OUTPUT_DIR / f"mag_mysite_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.write_text(json.dumps(report, indent=2))
        log(f"\n✅ Report saved: {report_path}")
        log(f"📸 Screenshots: {SS_DIR}")

        await page.close()


if __name__ == "__main__":
    asyncio.run(run())
