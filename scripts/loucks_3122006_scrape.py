"""
Focused scrape — Loucks booking 3122006 (Seven Seas Grandeur, Dec 29 2026).
Pulls: (1) booking ground-truth, (2) shore excursions already booked.
Uses oa cookie set. Firefox headless (Akamai-tolerant).
"""
import asyncio, json, re, time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path('/home/john/Thunderbird')
COOKIE_FILE = ROOT / 'creds' / 'regent_cookies_oa.json'
BOOKING_URL = 'https://www.rssc.com/agent/myaccount/bookedcruise.aspx?EUQc5OJShNzRnf6WDNdRorwtMN96BHdNAoCRU76%2bXT%2fsOWFoWGyj%2fal2KN%2bqYiHit2tgnul78coeYRaj31f8gA%3d%3d'
OUT = ROOT / 'validations' / 'rssc_scrape'
OUT.mkdir(parents=True, exist_ok=True)

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

async def main():
    t0 = time.perf_counter()
    xhr_log = []
    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        ctx = await browser.new_context(viewport={'width': 1440, 'height': 900})
        await ctx.add_cookies(load_rssc_cookies(COOKIE_FILE))
        page = await ctx.new_page()

        def on_resp(resp):
            u = resp.url
            if any(k in u.lower() for k in ['excursion', 'shore', 'tour', 'api', 'json', 'booking', 'reservation']):
                xhr_log.append({'url': u, 'status': resp.status, 'ct': resp.headers.get('content-type', '')})
        page.on('response', on_resp)

        await page.goto(BOOKING_URL, wait_until='domcontentloaded', timeout=45000)
        await page.wait_for_timeout(4000)
        try:
            await page.wait_for_load_state('networkidle', timeout=10000)
        except Exception:
            pass

        final_url = page.url
        title = await page.title()
        bounced = ('login' in final_url.lower() or 'signin' in final_url.lower()
                   or 'access denied' in title.lower())

        for sel in ['text=SHOW MY ITINERARY', 'text=GUEST DETAILS', 'text=Suite Details',
                    'text=Shore Excursions', 'text=EXCURSIONS', 'text=My Excursions']:
            try:
                for el in (await page.query_selector_all(sel))[:2]:
                    await el.click()
                    await page.wait_for_timeout(500)
            except Exception:
                pass
        await page.wait_for_timeout(1500)

        body_text = await page.evaluate('() => document.body.innerText')
        kv = await page.evaluate('''() => {
            const kv = {};
            document.querySelectorAll('tr').forEach(tr => {
                const c = Array.from(tr.querySelectorAll('td,th')).map(x=>x.innerText.trim());
                if (c.length>=2 && c[0] && c[1] && c[0].length<60) kv[c[0].replace(/:$/,'').trim()] = c[1];
            });
            return kv;
        }''')
        links = await page.evaluate('''() => Array.from(document.querySelectorAll('a'))
            .map(a => ({t:(a.innerText||'').trim().slice(0,50), h:a.href}))
            .filter(x => x.h && (
              /excursion|shore|tour|itinerary|activit/i.test(x.t) ||
              /excursion|shore|tour/i.test(x.h)))''')

        await page.screenshot(path=str(OUT / '3122006_Loucks_booking.png'), full_page=True)

        result = {
            'booking_id': '3122006',
            'final_url': final_url,
            'page_title': title,
            'bounced_to_login': bounced,
            'kv_pairs': kv,
            'excursion_links': links,
            'xhr_endpoints': xhr_log,
            'body_text': body_text,
            'elapsed_s': round(time.perf_counter()-t0, 1),
        }
        (OUT / '3122006_Loucks_full.json').write_text(json.dumps(result, indent=2, default=str))

        print('=== AUTH CHECK ===')
        print('final_url:', final_url[:90])
        print('title:', title)
        print('BOUNCED TO LOGIN:', bounced)
        print('\n=== BOOKING KV ('+str(len(kv))+' pairs) ===')
        for k, v in list(kv.items())[:30]:
            print(f'  {k}: {v}')
        print('\n=== EXCURSION LINKS ('+str(len(links))+') ===')
        for l in links[:20]:
            print(f'  [{l["t"]}] -> {l["h"][:90]}')
        print('\n=== XHR ENDPOINTS ('+str(len(xhr_log))+') ===')
        for x in xhr_log[:25]:
            print(f'  {x["status"]} {x["ct"][:25]} {x["url"][:100]}')
        print('\n=== BODY TEXT (first 1500 chars) ===')
        print(body_text[:1500])
        print('\nSaved:', OUT / '3122006_Loucks_full.json')

        await ctx.close()
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
