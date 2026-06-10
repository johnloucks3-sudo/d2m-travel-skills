#!/usr/bin/env python3
"""Regent parallel booking detail scrape — all 6 bookings concurrent via Playwright."""
import asyncio, json, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from playwright.async_api import async_playwright

BOOKING_URLS = {
    '3096289': ('direct', 'https://www.rssc.com/agent/myaccount/bookedcruise.aspx?McWU05z77cmpnbQbEo2CdOumw8lV3LRNPvEArhnrrs3hl5RgmNGc6tgCF0LEwSWn9KttcnSG6QV03Ue0ckTSqA%3d%3d'),
    '3078056': ('direct', 'https://www.rssc.com/agent/myaccount/bookedcruise.aspx?P4lRDbrpl6KimySo%2fK4o%2bwDZRcXP9mymm6bgZqnsScH38MGZtQLDbVpf764ZzfTpNPFFP6eqcei3a2Ce6Xvxyh5hFqPfV%2fyA'),
    '3071222': ('direct', 'https://www.rssc.com/agent/myaccount/bookedcruise.aspx?eecDnW0xAFxbgFqHZBS8Eko5Uc3K5UTVHzz%2b5iUsOMeF38Ba0f%2bR5xYgM6Gv3nm1CyaweMg7GG8DwKCVXbjhAg%3d%3d'),
    '2984034': ('direct', 'https://www.rssc.com/agent/myaccount/bookedcruise.aspx?21uwzkkXT97f7JcY1xK9hyCQmJ8KAZNizQbA8RnZf9%2b2GB6xoVkHtRcCZey5%2bUtfz14I9iYKQKotURuEHXNX822RP7fimObr'),
    '3122006': ('oa',     'https://www.rssc.com/agent/myaccount/bookedcruise.aspx?EUQc5OJShNzRnf6WDNdRorwtMN96BHdNAoCRU76%2bXT%2fsOWFoWGyj%2fal2KN%2bqYiHit2tgnul78coeYRaj31f8gA%3d%3d'),
    '3114500': ('oa',     'https://www.rssc.com/agent/myaccount/bookedcruise.aspx?7Pj2t4BavLZNCSDlo8V1DFNkwj3m8OmucLObhINqdxND5UslCJ5iHM6Ue0kxgytZatCxOTMNUr6QuB943KScOg%3d%3d'),
}

COOKIE_FILES = {
    'direct': Path('/home/john/Thunderbird/creds/regent_cookies.json'),
    'oa':     Path('/home/john/Thunderbird/creds/regent_cookies_oa.json'),
}

def load_rssc_cookies(path):
    raw = json.loads(path.read_text())
    out = []
    for c in raw:
        if 'rssc.com' not in c.get('domain', ''):
            continue
        nc = {k: v for k, v in c.items() if k != 'sameSite'}
        if c.get('sameSite') in ('Strict', 'Lax', 'None'):
            nc['sameSite'] = c['sameSite']
        out.append(nc)
    return out


async def scrape_one(ctx, bid, url, t0):
    page = await ctx.new_page()
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=40000)
        await page.wait_for_timeout(4000)
        try:
            await page.wait_for_load_state('networkidle', timeout=8000)
        except Exception:
            pass
        # Click expand buttons if present
        for sel in ['text=SHOW MY ITINERARY', 'text=GUEST DETAILS', 'text=Suite Details']:
            try:
                els = await page.query_selector_all(sel)
                for el in els[:2]:
                    await el.click()
                    await page.wait_for_timeout(400)
            except Exception:
                pass
        await page.wait_for_timeout(1500)
        text = await page.evaluate('() => document.body.innerText')
        tables = await page.evaluate('''() => {
            const kv = {};
            document.querySelectorAll('tr').forEach(tr => {
                const cells = Array.from(tr.querySelectorAll('td,th')).map(c => c.innerText.trim());
                if (cells.length >= 2 && cells[0] && cells[1] && cells[0].length < 60) {
                    kv[cells[0].replace(/:$/, '').trim()] = cells[1];
                }
            });
            return kv;
        }''')
        elapsed = round(time.perf_counter() - t0, 1)
        return {'booking_id': bid, 'text': text, 'tables': tables, 'elapsed': elapsed}
    except Exception as e:
        return {'booking_id': bid, 'error': str(e), 'elapsed': round(time.perf_counter() - t0, 1)}
    finally:
        await page.close()


def find_val(keys, kv, text, pat=None):
    for k in keys:
        if k in kv and kv[k].strip():
            return kv[k].strip()
    if pat:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1).strip()
    return ''


def parse_result(raw):
    if 'error' in raw:
        return {'booking_id': raw['booking_id'], 'error': raw['error'], 'elapsed_s': raw.get('elapsed')}
    t = raw.get('text', '')
    kv = raw.get('tables', {})
    return {
        'booking_id':  raw['booking_id'],
        'guest_name':  find_val(['Guest Name', 'Guest 1', 'Primary Guest'], kv, t,
                                r'(?:Guest|Passenger)[:\s]+([A-Z][A-Z ,]+)'),
        'ship':        find_val(['Ship', 'Vessel'], kv, t,
                                r'(Seven Seas \w+|Silver \w+)'),
        'voyage_code': find_val(['Voyage', 'Voyage Number', 'Voyage Code'], kv, t),
        'embark_date': find_val(['Embarkation Date', 'Embark Date', 'Embarkation'], kv, t,
                                r'Embark\w*[:\s]+([\w]+ \d+, \d{4}|\d{2}/\d{2}/\d{4})'),
        'debark_date': find_val(['Disembarkation Date', 'Debark Date'], kv, t,
                                r'Debark\w*[:\s]+([\w]+ \d+, \d{4}|\d{2}/\d{2}/\d{4})'),
        'nights':      find_val(['Nights', 'Duration'], kv, t, r'(\d+)\s+Night'),
        'suite':       find_val(['Suite Number', 'Suite', 'Cabin'], kv, t, r'Suite[:\s]+(\w+)'),
        'suite_cat':   find_val(['Suite Category', 'Category'], kv, t),
        'guests':      find_val(['Number of Guests', 'Guests'], kv, t, r'(\d)\s+Guest'),
        'total_fare':  find_val(['Total Cruise Fare', 'Total Fare', 'Cruise Fare'], kv, t,
                                r'Total\s+(?:Cruise\s+)?Fare[:\s]+\$([\d,]+)'),
        'amount_due':  find_val(['Amount Due', 'Balance Due', 'Due'], kv, t,
                                r'(?:Amount|Balance)\s+Due[:\s]+\$([\d,]+)'),
        'due_date':    find_val(['Payment Due Date', 'Due Date', 'Final Payment Due Date'], kv, t,
                                r'(?:Payment|Final)\s+Due\s+Date[:\s]+([\d/]+)'),
        'deposit':     find_val(['Deposit Paid', 'Deposit'], kv, t,
                                r'Deposit[:\s]+\$([\d,]+)'),
        'commission':  find_val(['Commission Amount', 'Commission'], kv, t,
                                r'Commission[:\s]+\$([\d,]+)'),
        'port_embark': find_val(['Port of Embarkation', 'Embarkation Port'], kv, t),
        'port_debark': find_val(['Port of Disembarkation', 'Disembarkation Port'], kv, t),
        'elapsed_s':   raw.get('elapsed'),
        'raw_kv_keys': list(kv.keys())[:20],
        'text_snippet': t[:500],
    }


async def main():
    t0 = time.perf_counter()
    results = {}
    ctxs = {}

    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        for acct, cf in COOKIE_FILES.items():
            cookies = load_rssc_cookies(cf)
            ctx = await browser.new_context(viewport={'width': 1440, 'height': 900})
            await ctx.add_cookies(cookies)
            ctxs[acct] = ctx

        tasks = {
            bid: asyncio.create_task(scrape_one(ctxs[acct], bid, url, t0))
            for bid, (acct, url) in BOOKING_URLS.items()
        }

        raw_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for bid, raw in zip(tasks.keys(), raw_results):
            if isinstance(raw, Exception):
                results[bid] = {'booking_id': bid, 'error': str(raw)}
            else:
                results[bid] = parse_result(raw)

        for ctx in ctxs.values():
            await ctx.close()
        await browser.close()

    total = round(time.perf_counter() - t0, 1)
    print(f'Total elapsed: {total}s\n')

    for bid, d in results.items():
        print(f'=== {bid} ===')
        for k, v in d.items():
            if k not in ('raw_kv_keys', 'text_snippet') and v:
                print(f'  {k}: {v}')
        if d.get('raw_kv_keys'):
            print(f'  raw_kv_keys: {d["raw_kv_keys"]}')
        if d.get('text_snippet'):
            print(f'  text_snippet: {repr(d["text_snippet"][:200])}')
        print()

    out = Path('/home/john/Thunderbird/validations/rssc_scrape/regent_full_scrape_20260610.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f'Saved to {out}')
    return results


if __name__ == '__main__':
    asyncio.run(main())
