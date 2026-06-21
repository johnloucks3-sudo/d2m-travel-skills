"""
Pull exact excursion times for Loucks 3122006 via the Excursions handlers.
Navigate booking page first (Akamai-valid session), then in-page fetch the
excursion JSON endpoints + scrape the booked-excursions detail view.
"""
import asyncio, json, time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path('/home/john/Thunderbird')
COOKIE_FILE = ROOT / 'creds' / 'regent_cookies_oa.json'
BOOKING_URL = 'https://www.rssc.com/agent/myaccount/bookedcruise.aspx?EUQc5OJShNzRnf6WDNdRorwtMN96BHdNAoCRU76%2bXT%2fsOWFoWGyj%2fal2KN%2bqYiHit2tgnul78coeYRaj31f8gA%3d%3d'
ENC = 'EUQc5OJShNzRnf6WDNdRorwtMN96BHdNAoCRU76%2bXT%2fsOWFoWGyj%2fal2KN%2bqYiHit2tgnul78coeYRaj31f8gA%3d%3d'
OUT = ROOT / 'validations' / 'rssc_scrape'

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
    captured = []
    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        ctx = await browser.new_context(viewport={'width': 1440, 'height': 900})
        await ctx.add_cookies(load_rssc_cookies(COOKIE_FILE))
        page = await ctx.new_page()

        async def grab(resp):
            u = resp.url
            if 'Excursions/Handlers' in u or 'excursion' in u.lower() or 'shorex' in u.lower():
                try:
                    body = await resp.text()
                    captured.append({'url': u, 'status': resp.status, 'body': body[:20000]})
                except Exception:
                    pass
        page.on('response', lambda r: asyncio.create_task(grab(r)))

        await page.goto(BOOKING_URL, wait_until='domcontentloaded', timeout=45000)
        await page.wait_for_timeout(3000)

        for sel in ['text=VIEW PURCHASES', 'text=Shore Excursions Booked',
                    'text=SHORE', 'text=CUSTOMIZE']:
            try:
                for el in (await page.query_selector_all(sel))[:1]:
                    await el.click()
                    await page.wait_for_timeout(3000)
            except Exception:
                pass
        try:
            await page.wait_for_load_state('networkidle', timeout=8000)
        except Exception:
            pass
        await page.wait_for_timeout(2000)

        candidates = [
            f'/agent/Controls/MyAccount/Excursions/Handlers/GetBookedExcursions.ashx?{ENC}',
            f'/agent/Controls/MyAccount/Excursions/Handlers/GetExcursions.ashx?{ENC}',
            f'/agent/Controls/MyAccount/Excursions/Handlers/GetItinerary.ashx?{ENC}',
            f'/agent/Controls/MyAccount/Excursions/Handlers/GetBookingNumber.ashx?{ENC}',
            f'/agent/Controls/MyAccount/Excursions/Handlers/GetGuests.ashx?{ENC}',
            f'/agent/Controls/MyAccount/Excursions/Handlers/GetCart.ashx?{ENC}',
        ]
        fetched = {}
        for path in candidates:
            try:
                res = await page.evaluate('''async (p) => {
                    try {
                        const r = await fetch(p, {credentials:'include'});
                        const t = await r.text();
                        return {status:r.status, body:t.slice(0,20000)};
                    } catch(e){ return {error:String(e)}; }
                }''', path)
                fetched[path] = res
            except Exception as e:
                fetched[path] = {'error': str(e)}

        body_text = await page.evaluate('() => document.body.innerText')
        await page.screenshot(path=str(OUT / '3122006_Loucks_excursions_detail.png'), full_page=True)

        result = {
            'captured_handler_responses': captured,
            'direct_fetch': fetched,
            'body_text': body_text,
            'elapsed_s': round(time.perf_counter()-t0, 1),
        }
        (OUT / '3122006_Loucks_excursion_times.json').write_text(json.dumps(result, indent=2, default=str))

        print('=== CAPTURED HANDLER RESPONSES ===')
        for c in captured:
            print(f'\n--- {c["status"]} {c["url"][:110]}')
            print(c['body'][:1200])
        print('\n\n=== DIRECT FETCH RESULTS ===')
        for p, r in fetched.items():
            name = p.split("/")[-1].split("?")[0]
            st = r.get('status', r.get('error', '?'))
            print(f'\n--- {name}: status={st}')
            if r.get('body'):
                print(r['body'][:1500])
        print('\nSaved:', OUT / '3122006_Loucks_excursion_times.json')
        await ctx.close()
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
