"""Probe Regent /api/browse/v1/ for the voyage detail / port descriptions endpoint."""
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path('/home/john/Thunderbird/validations/rssc_scrape')
VOY = 'GRA261229'
CANDIDATES = [
    f'/api/browse/v1/cruises/{VOY}',
    f'/api/browse/v1/cruise/{VOY}',
    f'/api/browse/v1/cruises/{VOY}/itinerary',
    f'/api/browse/v1/cruises/{VOY}/ports',
    f'/api/browse/v1/voyages/{VOY}',
    f'/api/browse/v1/voyage/{VOY}',
    f'/api/browse/v1/itinerary/{VOY}',
    f'/api/browse/v1/cruises/{VOY}?siteCountry=US',
    f'/api/browse/v1/cruises/detail/{VOY}',
    f'/api/browse/v1/cruises/{VOY}/summary',
    f'/api/browse/v1/cruises/{VOY}/details',
    f'/api/cruise/v1/cruises/{VOY}',
    f'/api/browse/v1/cruises?voyageCode={VOY}',
    f'/api/browse/v1/ports',
    f'/api/browse/v1/destinations',
]

async def main():
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0')
        page = await ctx.new_page()
        # land on a valid rssc origin
        await page.goto('https://www.rssc.com/cruises/GRA261229/summary', wait_until='domcontentloaded', timeout=40000)
        await page.wait_for_timeout(3000)
        results = {}
        for path in CANDIDATES:
            try:
                r = await page.evaluate('''async (p) => {
                    try {
                        const res = await fetch(p, {headers:{'Accept':'application/json'}, credentials:'include'});
                        const ct = res.headers.get('content-type')||'';
                        const t = await res.text();
                        return {status:res.status, ct, len:t.length, body:t.slice(0,1200)};
                    } catch(e){ return {error:String(e)}; }
                }''', path)
                results[path] = r
                st = r.get('status', r.get('error'))
                ln = r.get('len','')
                ct = r.get('ct','')[:20]
                flag = ''
                bd = (r.get('body') or '').lower()
                if any(k in bd for k in ['cabo','cartagena','acapulco','cayman','quetzal','description','port']):
                    flag = '  <-- PORT DATA?'
                print(f'{str(st):>4} {ct:20} len={str(ln):>7} {path}{flag}')
            except Exception as e:
                print('ERR', path, str(e)[:60])
        (OUT/'browse_api_probe.json').write_text(json.dumps(results, indent=2, ensure_ascii=False))
        # show bodies of any that looked like port data
        print('\n=== Promising bodies ===')
        for p, r in results.items():
            bd = (r.get('body') or '')
            if r.get('status')==200 and any(k in bd.lower() for k in ['cabo','cartagena','acapulco','cayman','quetzal']) :
                print(f'\n--- {p} ---\n{bd[:1000]}')
        await ctx.close(); await b.close()

asyncio.run(main())
