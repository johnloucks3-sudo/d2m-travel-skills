#!/usr/bin/env python3
"""
REGENT API SPIKE — Pass 2: Deep DOM analysis.
The booking detail page is server-rendered ASP.NET, not API-driven.
This pass extracts full page state including Vue component data.

Run:
  python3 scripts/regent_api_spike_pass2.py
"""

import asyncio, json, sys, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
COOKIE_FILE = ROOT / "creds" / "regent_cookies.json"
OUTPUT_DIR = ROOT / "validations" / "rssc_api_spike"

BOOKINGS = {
    "3071222_Furlow": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?eecDnW0xAFxbgFqHZBS8Eko5Uc3K5UTVHzz%2b5iUsOMeF38Ba0f%2bR5xYgM6Gv3nm1CyaweMg7GG8DwKCVXbjhAg%3d%3d",
}


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.async_api import async_playwright

    cookies = json.loads(COOKIE_FILE.read_text())
    rssc = [c for c in cookies if "rssc.com" in c.get("domain", "")]
    valid_ss = {"Strict", "Lax", "None"}
    cleaned = []
    for c in rssc:
        nc = {k: v for k, v in c.items() if k != "sameSite"}
        if c.get("sameSite") in valid_ss:
            nc["sameSite"] = c["sameSite"]
        if nc.get("expires") == -1:
            del nc["expires"]
        cleaned.append(nc)

    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        await ctx.add_cookies(cleaned)
        page = await ctx.new_page()

        for bid, url in BOOKINGS.items():
            print(f"\n{'='*70}")
            print(f"PASS 2 SPIKE: {bid}")
            print(f"{'='*70}")

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            result = {"booking_id": bid, "timestamp": datetime.now(timezone.utc).isoformat()}

            # 1. Extract ALL text content from the page
            all_text = await page.evaluate("() => document.body.innerText")
            result["all_text_length"] = len(all_text)

            # 2. Search for dining-related keywords
            dining_keywords = []
            for kw in ["Dining", "Specialty Dining", "Compass Rose", "Prime 7",
                       "Chartreuse", "Sette Mari", "Pacific Rim", "La Veranda",
                       "Solis", "dining reservation", "Culinary", "Kitchen",
                       "Restaurant", "reservation", "Reservation"]:
                found = kw.lower() in all_text.lower()
                # Find context around keyword
                contexts = []
                if found:
                    for m in re.finditer(re.escape(kw), all_text, re.IGNORECASE):
                        start = max(0, m.start() - 80)
                        end = min(len(all_text), m.end() + 80)
                        ctx_text = all_text[start:end].replace('\n', ' ')
                        contexts.append(ctx_text)
                dining_keywords.append({"keyword": kw, "found": found, "contexts": contexts[:3]})
            result["dining_keywords"] = dining_keywords

            # 3. Extract Vue component state
            vue_state = await page.evaluate("""() => {
                const result = {};
                // Vue 3: __vue_app__ on mount point
                const appEl = document.getElementById('app') || document.querySelector('[data-vue-app]');
                if (appEl && appEl.__vue_app__) {
                    const app = appEl.__vue_app__;
                    result.vue3_app = {
                        component_count: Object.keys(app._components || {}).length,
                        components: Object.keys(app._components || {}).slice(0, 20)
                    };
                }
                // Vue 2: __vue__ on elements
                const all = document.querySelectorAll('*');
                let vue2Components = [];
                for (const el of all) {
                    if (el.__vue__ && el.__vue__.$options) {
                        vue2Components.push(el.__vue__.$options.name || el.__vue__.$options._componentTag || 'unnamed');
                    }
                    if (vue2Components.length > 30) break;
                }
                result.vue2_components = vue2Components;

                // Vue 3 via __vnode
                let vue3Components = [];
                for (const el of all) {
                    if (el.__vueParentComponent) {
                        const c = el.__vueParentComponent;
                        const name = c.type?.name || c.type?.__name || c.type?.displayName || '';
                        if (name && !vue3Components.includes(name)) {
                            vue3Components.push(name);
                        }
                    }
                    if (vue3Components.length > 30) break;
                }
                result.vue3_components = vue3Components;

                // Check for __NUXT__ or __NEXT_DATA__ or __INITIAL_STATE__
                result.window_globals = {};
                for (const key of ['__NUXT__', '__NEXT_DATA__', '__INITIAL_STATE__', '__STATE__', '__DATA__',
                                     'window.__INITIAL_STATE__', '__vue_app__']) {
                    try {
                        const val = window[key];
                        if (val) {
                            result.window_globals[key] = typeof val === 'object' ? JSON.stringify(val).slice(0, 2000) : String(val).slice(0, 500);
                        }
                    } catch(e) {
                        result.window_globals[key] = `ERROR: ${e.message}`;
                    }
                }
                return result;
            }""")
            result["vue_state"] = vue_state

            # 4. Extract structured booking data using DOM parsing
            booking_data = await page.evaluate("""() => {
                const r = {
                    cruiseDetails: [], guestDetails: [], suiteDetails: [],
                    payments: [], todoList: [], excursions: [],
                    diningInfo: [], hotelInfo: [], allSections: {}
                };
                // Extract all heading-content pairs
                const headings = document.querySelectorAll('h1, h2, h3, h4, h5, .section-title, .heading, strong, b, label');
                const seen = new Set();
                headings.forEach(h => {
                    const text = h.textContent.trim();
                    if (text.length < 2 || text.length > 120) return;
                    if (seen.has(text)) return;
                    seen.add(text);
                    let parent = h.parentElement;
                    for (let i = 0; i < 3 && parent; i++) {
                        const pt = parent.textContent.trim();
                        if (pt.length > text.length + 10 && pt.length < 3000) {
                            r.allSections[text] = pt.slice(0, 1000);
                            break;
                        }
                        parent = parent.parentElement;
                    }
                });
                return r;
            }""")
            result["booking_data"] = booking_data

            # 5. Full HTML (first 100k for analysis)
            full_html = await page.content()
            result["html_length"] = len(full_html)
            result["html_preview"] = full_html[:50000]

            out = OUTPUT_DIR / f"spike_pass2_{bid}.json"
            out.write_text(json.dumps(result, indent=2, default=str))
            print(f"Saved: {out.name}")
            print(f"Text length: {result['all_text_length']}")
            print(f"HTML length: {result['html_length']}")

            # Print dining keyword findings
            dining_found = [k for k in result["dining_keywords"] if k["found"]]
            print(f"Dining keywords found: {len(dining_found)}/{len(result['dining_keywords'])}")
            for k in dining_found:
                print(f"  ✓ {k['keyword']}")

        await browser.close()

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
